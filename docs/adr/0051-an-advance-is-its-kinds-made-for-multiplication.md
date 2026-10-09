# ADR 0051 — An Advance is its kinds, made for multiplication as for addition

**Status:** accepted (2026-10-09, slice M2b of BUILD-ORDER "Inserted now: multiplication and division")
Goal: goals/md2b-times-advance.yaml

## What happened

MUL.2D1D, MUL.3D1D and MUL.2D2D had no Advance after M2a. The document's Advance cases for them are all kinds that
are not straight sums: a missing digit, finding the mistake, an estimate, a story, a shortcut, a missing row. Measured
before the build (STATE.md "M2b — measured before the build"):
- every one of those kinds refused ×;
- their case rows named no kind, so the drawer had nothing to draw them with;
- T13 (6 × 125 in a line), placed at MUL.3D1D Advance, is a question the skill's Easy to Hard already hold, since a ×
  case reads the longer number and the shorter (ADR 0050).

## Decision

1. **An Advance is Hard's straight cases with the document's Advance cases**, as addition's is (ADD.2D1D: A14 to A16
   with missing numbers, stories and finding the mistake), on the skill's own numbers and at the document's grade.
2. **Every case that is not a straight sum names its kind in its row** (`research/md_rows.py`), as addition's rows do.
3. **Each kind makes × beside + and −**, saying so through `operations.require`. None makes ÷ yet (M3).
   - **A missing digit** hides digits of the larger number or of the answer, never the 1-digit multiplier.
   - **Finding the mistake** plants a multiplication slip the predictors compute from the question's own numbers.
     There are four: products written side by side, carries left out, a carry onto a zero lost, and the second row not
     moved. A × slip with no level behind it decides the operation and the numbers it needs.
   - **An estimate** asks one of four things first, then the exact product: the larger number rounded to the ten, both
     rounded, how many digits the product has, or the digit it ends in.
   - **A story** is a template row with its shape: the cost of many, times as many, or combinations.
   - **A shortcut** asks the step it names, then the answer: × 5 as × 10 then halved, or a number near a round one.
   - **A missing row** is the second row of a long multiplication, moved its place (`assess/times_kinds.py`).
4. **A missing-digit box names the digit its column allows alone, when there is exactly one other**: 9□ × 4 = 364
   names 6, since 6 × 4 ends in 4 as 1 × 4 does; 48 × 2 = □6 names 8, the carry forgotten. A question with no box that
   names one is drawn again, so every question has a mistake to mark against.
5. **T13 joins the ways MUL.3D1D's questions are printed**, beside T14. MUL.3D1D's Advance is Q16 and C09.
6. **C06 (partitioning, tens taken as ones) waits for the methods (M2d)**. Its mistake is a method's, and no row or
   predictor names it yet.

## Rejected

- **A tolerance on a × estimate**, as + and − have. The question says how to round, so there is one estimate.
  A tolerance wide enough to matter at 300 would also pass 240, the estimate from rounding the wrong way.
- **A "fact one out" for a × box no carry reaches**, as + and − name. One out in a column's product is no digit a
  child writes for a missing digit; a box that names nothing is drawn again instead.
- **The × kinds in `assess/items.py`.** It is frozen at its 540 lines; the two kinds only multiplication has are a
  module of their own (`assess/times_kinds.py`).
- **T13 as the Advance's straight case.** Every question it holds is placed at Easy to Hard, so the level would add
  nothing harder.

## Consequences

- Three Advance levels reach live with `bin/update-live` (`engine load`, `bank refill`, `library build`).
- The renderer draws a × estimate's question in its own words (how many digits, the last digit), and a shortcut's
  step and answer, from two helpers rather than more branches in `render_item`. Its complexity fell, 25 to 24.
