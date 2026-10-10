# ADR 0061 — A mistake's words are its row alone

**Status:** accepted (2026-10-10, slice M3b3 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md3b3-divide-mistakes-and-stories.yaml

## What happened

A worked division whose mistake a child finds (C04, C05, C07) asks the child why it is wrong. A worked answer's "why"
printed the mistake's name, from a copy the code kept beside each predictor. Measured on 2026-10-10 (STATE.md "M3b3 —
names, measured before the build"):

- The code held its own copy of 41 mistakes' names and repair hints, in `misconceptions.py`'s tables,
  `mul_mistakes.PREDICTORS` and `written_methods.NAMES`.
- Two names said otherwise than the rows the school edits (`supabase/seed/misconceptions.json`). Six repair hints
  differed.
- The copies were read in three places:
  - a worked answer's "why", shown on the Question bank as "Looks for", beside the same mistake named from its row;
  - Jev's shortlist (`mistake_guess.options`);
  - one test, which alone read the repair hints.
- A division's mistakes had no copy at all, so a worked division's "why" would have printed a code.

## Decision

1. **The rows are the one source of a mistake's words** (rule 1). The code keeps only how a mistake is made: each
   table maps a code to its predictor, nothing more. `written_methods.NAMES` and `misconceptions.catalogue` go.
2. **A worked answer's "why" names no mistake.** Its rubric says what is judged ("Names the mistake its worked answer
   shows"). The Question bank names the planted mistake from its row beside it. For a question stored before this, the
   website shows that same sentence, not the name it stored.
3. **Jev is shown the rows' names** for the sum's operation (`mistake_guess.options(conn, op)`). The codes it may
   choose from are code's (`mistake_guess.codes`), and so are those a person may name a wrong answer by.
4. **Every mistake the code can make, plant or name in a story has its row**, with a name and a repair hint
   (`test_mistake_rows.py`). The remainder not rounded up, new in this slice, is a row like any other.

## Rejected

- **Copies held equal to the rows by a test.** That is two sources and a check that they agree. A person editing a
  row would fail a test they cannot read. ADR 0060 rejected the same for the reader's trust.
- **The "why" filled in with the row's name when a question is made.** The assess library is pure and cannot read a
  row. A stored question would also keep the name the row had that day.
- **Rewriting the stored questions' rubrics.** Questions are truth (ring A); a batch job never edits them. The website
  shows the sentence instead.

## Consequences

- Jev's input changes for one mistake, `M_ZERO_DROPPED`, whose copy said "a placeholder zero" where its row says "a
  leading, trailing or internal zero". `engine eval mistake_guess` runs on the server after the deploy, and its score
  goes in DECISIONS-LOG.md.
- Renaming a mistake is an edit to its row, and every screen, report and Jev's next question reads it.
