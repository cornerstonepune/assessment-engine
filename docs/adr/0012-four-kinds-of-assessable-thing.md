# ADR 0012 — four kinds of assessable thing, and the question says which it is

Date: 2026-09-19. Status: accepted. Extends ADR 0009 (subject plugins) downwards, from the
subject to the individual question.

## Decision

Every question carries an `eval_type`, one of four, declared on its skill set (a row) and
stamped onto the item when it is generated. Marking dispatches on it —
`assess/evaluate.judge(eval_type, response, written)` — instead of inferring from the question's
shape.

| eval_type | How the question is produced | How a wrong answer is recognised |
|---|---|---|
| `computable` | a formula with slots; code enumerates | computed — each named mistake's wrong answer is calculated with the right one |
| `closed_set` | sampled from a table of content that already exists (capitals, dates, vocabulary, a labelled diagram) | exact match; the wrong options are confusable neighbours from that same table |
| `rule_governed` | a generator constrained by rules (grammar, spelling, balancing an equation, significant figures) | a checker decides, and the rule violations *are* the mistake list |
| `open_response` | written once as a prompt/rubric pair | no enumerable answer set — judged against a rubric, and its mistakes are **discovered by clustering real answers**, never predicted |

Only `computable` and `open_response` have evaluators today. `closed_set` and `rule_governed`
are named and **refuse loudly** (`NotImplementedError`) rather than falling through to the
computable evaluator. A question the engine cannot judge must never be quietly marked: a wrong
mark reaches a child's record as a fact about that child.

Today, of 17 skill sets: 14 `computable`, 3 `open_response` (explain-a-claim, find-the-mistake,
choose-the-efficient-method — the three that ask for a sentence as well as a number).

## Why

The engine's cleverness rests on two things that are true of arithmetic and of almost nothing
else: a question is a formula whose space code can enumerate, and a mistake is a deterministic
slip in a procedure, so the wrong answer can be *computed*. Neither survives contact with
comprehension, history, or science reasoning. Without naming that boundary, the first non-maths
subject would either get silently mis-marked by the arithmetic evaluator or need the pipeline
rebuilt.

Nimish, 2026-09-19: *"for other subjects, how will this work? … for every possible question, we
figure out the set of answers at scale as part of the process. We are not expecting teachers to
do that."* He is right that the answer cannot be "a teacher enumerates the wrong answers." The
rule this ADR fixes is:

> **Predict the error where the subject allows prediction. Discover it from real answers where
> it does not. Never ask a person to enumerate errors question by question.**

For the first three kinds nothing is enumerated by hand — a formula, a content table, or a rule
set does it. For `open_response` the error vocabulary grows from the bottom: a wrong answer that
matches nothing is already recorded as `unclassified` (`assess/mark.py`), and a person names a
recurring cluster **once**, after which it is predicted like any other. That is the same
economics ADR 0010 chose for generation — pay once per pattern, never once per question.

## Consequences

- `skill_set.eval_type` and `item.eval_type` (Postgres enum), set from rows; `bank._insert`
  stamps every generated item.
- `assess/evaluate.py` holds the dispatch and the vocabulary; `tests/test_evaluate.py` proves
  each branch, including that an unbuilt kind raises rather than marks.
- The *report of unclassified answers* is no longer a nice-to-have. For any subject beyond
  maths it is the only mechanism by which the mistake list can ever grow, and it is not built
  yet — it is the first thing the `open_response` kind needs.
- `subject.mark_mode` (`lookup` | `rubric`) stays as the subject-level default; `eval_type` is
  the per-question truth, because one paper mixes them — find-the-mistake asks for a tick, a
  number and a sentence in a single question.
- Difficulty remains unsolved outside `computable`. For maths, Easy/Hard is a machine-checkable
  rule (digit counts, exchanges). For an open response it is a judgment about text complexity
  and inference depth. The registry's activity rows carry the school's own three-level mastery
  descriptors (`activity.level_1/2/3`), written by teachers — that is where a non-maths
  difficulty rule should start rather than from scratch.
