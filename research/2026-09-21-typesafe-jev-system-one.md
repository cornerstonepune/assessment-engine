# Is TypeSafe's Jev (a "System One model") useful to us?

Researched 2026-09-21, the day it was announced. **Recommendation: no, not now. It does neither of
the two jobs that are hard for us, and the one job it fits has cost ₹39 in total. Revisit when it
can read images, and then judge it on the gold set's silently-wrong count.**

## What it is

Source: the vendor's launch post, typesafe.ai/blog/introducing-system-one-models-and-jev. Nothing
independent exists yet, so every number below is the vendor's own. They say their speed figures are
"on the higher end of real world gains" and that their own staff ran the workflow evals.

- Text or structured data in; one choice from a list fixed in advance out (up to 255 options),
  with a probability. It never writes free text ("Jev gives up string generation") and does not
  read images ("not on images (yet…)").
- 70–500 ms a call. $0.042 per million input tokens; output free.
- Early access, from a waitlist. Hosted service only, run from the US West Coast. Python wrapper only.

## Every job a model does for us, and whether Jev could do it

The page reader in service is not a language model at all: it is AWS Textract (ADRs 0019–0020).
The 11 active prompts (`select purpose from prompt where active`):

| Prompt | Job | Jev? |
|---|---|---|
| `legacy_extract`, `question_extract`, `read_page`, `read_cells` | read a scanned page | no: images |
| `item_generate`, `word_context`, `parent_note`, `misconception_list` | write questions, sentences, notes, proposals | no: writes text |
| `language_review`, `pedagogy_review` | judge a template | the verdict yes; the reasons it must give, no |
| `skill_match` | match a question's text to a registry skill, graded clear / arguable / none | **yes**, except `proposed_skill`, the name it writes when nothing matches |

`skill_match` is the one real fit. What it would save, from `flow_run` on 2026-09-21: 36 calls,
185,377 input tokens, **₹39.17 in total**, 44 s a call, once per imported paper. At Jev's price the
same input costs under ₹1. The registry has 244 skills; Jev's ceiling is 255.

## Why the decisions in between are not a fit either

They look like Jev's "smart if-statements", but each one is code on purpose:

- **Which mistake made a wrong answer.** A predictor reproduces the exact wrong number
  (8500 − 3647 → 5147 is `M_SMALL_FROM_LARGE`). Exact and free; a probability would be a downgrade.
- **A child's state and next step (W4).** `level_rule` (12 rows) and `threshold` (26 rows): the
  school's pedagogy written down, which a teacher can read as a reason. A vendor model's probability
  is not a reason a teacher can check, and we have no data of our own to calibrate it on.
- **Sure versus doubtful.** Routing reads measured human overturn rates on our own papers
  (ADR 0007, point 5). That is calibration from our data, which beats a vendor's on theirs.

## If it learns to read images

ADR 0019 is the warning: a model that knows arithmetic writes the right answer where the child
wrote a wrong one, and no prompt fixes it. A smarter reader is not automatically a better one.
The test is `bin/engine read eval` on the gold set with silently-wrong beside exact, the rule
ADR 0020 set.

## Revisit when any of these holds

1. Jev reads images, and beats Textract on the gold set with no more silently-wrong answers.
2. A person waits in real time on a model choosing from a list. Nobody does today.
3. Model spend on choosing from a list becomes material. It is ₹39 in total today.

Risks if adopted anyway: announced 2026-09-21; early access; US-hosted, so a second AI vendor to vet
for children's data; only the vendor's own benchmarks; a registry past 255 skills no longer fits
`skill_match` in one choice.
