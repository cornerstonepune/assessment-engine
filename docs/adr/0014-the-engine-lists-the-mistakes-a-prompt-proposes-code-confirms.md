# 0014 — The mistake list is the engine's output, not a teacher's checklist

Date: 2026-09-19
Status: accepted

## Context

Every skill set carries `misconception_codes`: which wrong methods the engine builds distractors
for and the marker recognises. Until now that list was hand-picked — by an engineer, from the
seeded vocabulary, checked by eye — and the skill-set screen showed it to a teacher as a column of
checkboxes to tick.

Nimish, 2026-09-19: "A certain learning objective having all possible conceptions is the job of the
engine, not of the teacher… this whole misconception thing needs to be an extremely strong engine
prompt. Whenever a certain question or a certain concept is done, all the potential mistakes need
to be a very strong list. We can get that from a prompt if we have designed the prompt well."

## Decision (amended the same day — see "Amendment: two halves" below)

One prompt row, `misconception_list`, is asked for the whole list of wrong methods a skill set can
produce, from its learning objective, philosophy, formats and four difficulty rules. Code then
checks every proposal before anything is stored:

1. The model states both the right answer and what the method produces on its own example. If its
   right answer is wrong, the entry is dropped — its wrong answer proves nothing.
2. If a predictor that already exists reproduces that wrong answer, the proposal **is** that
   misconception. It is not stored again under a new name.
3. Only what nothing reproduces becomes a new `misconception` row, with the prompt and model in
   `source`.
4. Several structural methods may explain one wrong answer, and all of them are kept: the answer
   alone cannot separate them, the child's written working does. A fact slip (one out, ten out) is
   reported only when nothing structural explains the answer, because it collides numerically with
   real procedural mistakes often enough to be noise.

The list is **added to, never replaced** — `--apply` unions the proposals with what is already
there, so a curated code cannot be lost to a model's omission. Attaching a changed list withdraws
the skill set's ratification, which is correct: a person signs the list they were shown.

The prompt is asked blind, without being shown the existing vocabulary. That is what makes its
eval meaningful and what lets it find something nobody has named.

The eval (rule 7) is recall against the lists people already wrote: v1 scored **0.40** over three
skill sets, v2 **0.53** at ₹0.95 a skill set. v2 names the six families it must cover and makes the
model state its own arithmetic. Both numbers are in `STATE.md`; the prompt is not yet strong enough
and the next lever is a third version, not a bigger model.

## Alternatives rejected

- **A teacher ticks the misconceptions.** What the repository did until today. It spends the
  scarcest thing in the school on work the engine can do, and a teacher cannot be expected to
  enumerate wrong methods from memory in a form.
- **Match proposals to the vocabulary by name.** Cheaper to read, and it needs a second model to
  judge whether two phrasings mean the same thing. Matching by the arithmetic a predictor computes
  is code, not judgment, and it is the same bar the bank already holds every item to.
- **Show the model the existing vocabulary.** It raises apparent coverage and destroys the eval:
  a list that echoes its input cannot be measured, and it would never find what nobody named.
- **A bigger model.** `claude-sonnet-5` on the hardest of the three sets found 4/9 against haiku's
  3/9 for eight times the cost — the ceiling is the prompt's, not the model's. (It also exposed a
  real adapter bug: a thinking model spent all 8,000 tokens thinking and returned no text, which
  the adapter reported as "did not return JSON: ''". Fixed.)

## Consequences

- `engine bank misconceptions <skill-set> [--apply]` is the command; nothing is stored without
  `--apply`, and applying withdraws that set's ratification.
- The vocabulary now grows from two directions: this prompt before children answer, and
  `engine bank unclassified` after they do, which is the same table and the same codes.
- **"New" is not the same as "real".** Code checks the model's *correct* answer; it cannot check
  that the wrong answer follows from the method described, because a method expressed as code is
  exactly what a predictor is. A real run proved it: "subtracts in the wrong order, digit by digit"
  on 52 − 18 was filed as new with the child writing 36, but that method gives 46 — the entry is a
  slip wearing the clothes of a discovery. So a proposal that matches nothing is a candidate for a
  person to read, never an automatic distractor.
- A new misconception row has no predictor, so no distractor is computed from it yet. It is a named
  thing a teacher can see and mark by eye (`detectable_by`), until someone writes the predictor.
  That gap is deliberate and visible rather than hidden behind a fabricated wrong answer.

## Amendment: two halves (2026-09-19, same day)

The first cut of this decision asked one prompt for the whole list and scored it on recall against
the lists people had written: 0.40, then 0.53 after a second prompt version. Nimish's rule — fix the
cause, not the symptom — makes that the wrong target. Most of the list is not judgment at all: run
the predictors over the numbers a band's own rule allows and code enumerates every named wrong method
reachable in it, exactly, for nothing. A model was being asked to remember what arithmetic can
produce.

So the list has two halves:

* **Code** (`assess/bands.py`): sample the band's numbers, build items with the same generators the
  bank uses, read the misconception codes off them. It cannot drift from what the bank computes for
  a real item, because it is the same code. Recall against a curated list stops being an eval and
  becomes a test: `test_code_finds_every_computable_mistake_a_curated_list_names`.
* **The model** (`misconception_list` v4): told what code has already covered, asked only for the
  families code cannot reach — how a story is misread, a method with no predictor, a reasoning slip.
  Its eval is what survives as an addition: **0.75** of proposals, ₹0.53 a skill set.

Two prompt versions followed from that, each fixing a cause rather than a symptom: v4 makes the
worked example optional, because a mistake in an explanation has no wrong number and demanding one
produced invented arithmetic (3 of 5 proposals thrown away on `REASON.EXPLAIN`); and an example
carries however many numbers the band asks for, because a three-addend band could not state its own
example and the schema rejected the entire reply.

The test earned itself immediately: four specs claimed mistakes the engine could not mark. Two were
unreachable in their own bands (`ADDSUB.2D.NOREG` naming a method that gives the right answer where
no exchange happens; `SUB.3D.ZERO` naming misalignment where every band is equal-length) and were
corrected in the seed; two named real mistakes nothing computed, so the predictors were written
(`multi_concat` for several addends, the wrong-operation answer in `word_budget`). A spec claiming
more than the engine can do is the defect this guard exists to catch.
