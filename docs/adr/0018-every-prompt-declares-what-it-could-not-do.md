# 0018 — Every prompt declares what it could not do, and the code routes on that

Date: 2026-09-20
Status: accepted

## Context

Nimish, 2026-09-20: *"I keep saying that none of this is patchwork. The more instances I'm giving
you and the more use cases I get, let's figure out a very core solution to these things … The
prompts need to then consider this kind of use case. When the system is not able to comprehend the
prompt, it should exactly tell the system what to do."*

He is right, and the evidence is one session's worth of fixes to one small feature:

| fix | the symptom it treated |
|---|---|
| `question_extract` v2 adds a `part` field | `35 (p)` and `35 (q)` collapsed into one question |
| masking became a default, not a flag | a child's handwritten name reached a model |
| conflict resolution prefers the page holding a run of questions | a cover page invented a question |
| `read stability` fingerprints its responses | five cached replies were counted as five samples |

Four patches, four symptoms, **one cause**: the engine asks a model to do a job, receives something
well-shaped, and has no way to tell whether the model could actually do that job. It treats the
*shape* of a reply as evidence of its *substance*.

The sharpest instance: on both SOF covers — a page carrying a title, a logo and a name band and no
questions at all — `question_extract` v1 invented a plausible question, despite being told in plain
words to return an empty list for such a page. The code could not tell that invented question from a
real one, because **an empty list and an unreadable page look identical to the caller.**

That collapse is already forbidden in this repository, for children. Rule 5: *"Three signals, never
two. Blank, wrong, and wrong-with-working are distinct everywhere. Nothing collapses them to
'incorrect'."* The school decided years of pedagogy ago that "wrote nothing" and "I cannot tell what
they wrote" are different facts. The engine never applied the same rule to itself.

## Decision

**Rule 5 applies to the model's own output.** Every prompt in this repository returns its payload
*and* a declaration of what it could not do, in one shared shape, and the code routes on the
declaration rather than assuming the payload is complete.

Every prompt's `json_schema` gains a required `resolution` object:

```
resolution:
  status:     "complete" | "partial" | "cannot"
  saw:        one sentence naming what the input actually was, in the model's own words
  unresolved: [ { what, why, needs } ]
```

`needs` is a closed vocabulary, because it is the thing **code branches on** — it is the model
telling the system what to do, which is precisely what was asked for:

| `needs` | what the engine does with it |
|---|---|
| `a_person` | route to the approval queue; never graph it (counts against the flag rate, ADR 0017's loop) |
| `more_of_the_input` | the page was cropped, blurred or masked over — re-render and retry, do not re-prompt |
| `a_new_row` | the vocabulary has no name for this — a skill, a misconception (ADR 0017's held evidence) |
| `nothing` | genuinely absent, and that is a correct and complete answer |

`nothing` is the load-bearing one. "This page holds no questions" becomes an assertion the model
makes, not an absence the caller has to interpret. A cover page returns
`status: complete, saw: "a title page with a name band", questions: []` — and inventing a question
now requires contradicting its own `saw`, which is a far harder failure than filling an empty list.

Three consequences follow, and none of them is a new mechanism:

1. **A prompt may never report confidence in itself.** `skill_match` v1 returned
   `clear | arguable | none`, and measurement showed the same question earning different labels on
   different passes — 22 of 37 stable, a money question landing on four codes in five runs. Self-
   reported confidence is one pass's opinion of itself. Confidence is **measured** from agreement
   across runs, by code, or it is not reported. `resolution` says what the model could not do; it
   never says how sure it is.
2. **Every prompt's eval includes its refusals.** Rule 7 says every model output ships with an eval.
   The gold set must therefore contain inputs whose correct answer is `cannot` or `nothing` — a
   blank page, a cover, an illegible scan, a question testing a skill the registry lacks. A prompt
   that never refuses has not been shown to be able to.
3. **A measurement must prove its samples were independent.** Five identical responses, billed at
   three input tokens, were reported as perfect stability. Any command that repeats a model call
   fingerprints each response and refuses to call identical replies agreement.

## Alternatives rejected

**Keep strengthening prompt wording.** This is what v1 → v2 was, and it is the patchwork Nimish is
objecting to. v1 already said, in plain English, to return an empty list for a page with no
questions. It invented one anyway, on both forms. Instruction without a structured channel for "I
cannot" gives the model nowhere to put a refusal, so it produces the shape that was asked for.

**Validate every output in code instead.** Code can check arithmetic and it already does — that is
why the bank is enumerated rather than generated. But code cannot check whether a transcription
matches a page it has not seen, or whether a question tests a skill. Where judgement is genuinely
the job, the honest instrument is the model saying what it could not judge.

**A per-prompt bespoke field.** `legacy_extract` has `page_note`, `question_extract` had nothing,
`skill_match` had `confidence`. Three prompts, three private vocabularies, and no caller can route
generically. One shared shape is what lets the approval queue, the flag rate and the held-evidence
report all be built once rather than per prompt.

## Consequences

- All 17 prompt rows migrate to the contract. A prompt's text and schema change together, which is a
  new version row plus its eval (rule 2, rule 7) — so this is deliberate work, not a sweep.
- `engine audit` gains an invariant: every active prompt's schema requires `resolution`. A prompt
  that cannot say "I cannot" does not ship.
- `question_extract` v2 and `skill_match` v1, written earlier today, do not satisfy this and are the
  first two to migrate. Their measurements stand and are re-run against the new versions.
- The flag rate ADR 0017 promises to record is now well defined: it is the count of `needs:
  a_person` against the total, per batch.
