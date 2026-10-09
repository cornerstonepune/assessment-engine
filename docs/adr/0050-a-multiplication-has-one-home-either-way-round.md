# ADR 0050 — A multiplication has one home, read either way round

**Status:** accepted (2026-10-09, slice M2a of BUILD-ORDER "Inserted now: multiplication and division")
Goal: goals/md2a-straight-multiplication.yaml

## What happened

M2a makes straight multiplication five skills whose levels are the drafted document's cases. Measuring the document's
levels against the questions they would hold, before writing them as rows, found four defects in the draft:

- TP10 (23 × 30, MUL.TENS Advance) and TZ07 (23 × 40 in columns, MUL.2D2D Medium) hold the same questions. A
  child's answer is graphed on one skill (`assess/placing.py` refuses a question two skills hold).
- T03 ("the 1-digit number first", 3 × 21) read only the order, so MUL.2D1D Easy held 7 × 99.
- Every other × case read the order the numbers are written in (`operand_1_digits` 2, `operand_2_digits` 1), so
  3 × 47 was in no case at all, though assumption A10 asks both orders. Addition does not have this gap, because its
  document lists a smaller-first case at each level (A08, A09, A12, A13).
- The 2 × 2 cases crossed the rows' regrouping with the carry in adding them and left two combinations out, among
  them the error table's own examples 19 × 14 and 68 × 17. No level could print them.

## Decision

1. **Five shapes, one home.** MUL.FACTS is every table fact (both numbers to 12). MUL.TENS is every round-number ×
   that is not a fact: by 10, 100 or 1000, or a multiple of ten, one or both numbers. MUL.2D1D, MUL.3D1D and MUL.2D2D
   are the rest by their digits. A test reads every straight × a paper prints to four digits and finds exactly one
   home for each. TZ01 (230 × 4) and TZ07 (23 × 40) join TP10 at MUL.TENS Advance.
2. **A × case reads the longer number and the shorter** (`digits_max`, `digits_min`; `research/md_rows.py` `DM`),
   as `assess/md_tags.py` already measured the working. Only T03 and T13 are about the 1-digit number coming first,
   and T03, like its example and like addition's A08, regroups nothing. ÷ keeps the order: 72 ÷ 4 is not 4 ÷ 72.
3. **Every 2 × 2 question is a case.** T27 (adding the rows carries, a 3-digit answer: 19 × 14) and T28 (one row or
   none regroups, adding the rows carries, a 4-digit answer: 68 × 17) are new, both at MUL.2D2D Hard. 249 cases.
4. **An Advance only where the document gives it straight cases** (the 11 and 12 tables; round numbers with no fact
   under them; the 1-digit number first). MUL.2D1D's and MUL.2D2D's Advance are all kinds M2b makes.
5. **The drawer makes ×** (`assess/draw_times.py`). A fact comes from the tables, to a level's `operand_max` (the 11 and
   12 tables only at Advance, assumption A4, as a row). A number a case lets be round is a number times 10, 100 or
   1000. Nothing is × 1 unless its case is about × 1. A case that names its method is printed that way.
6. **A mistake is worked the way the child sets it out**, the longer number by the shorter (`assess/mul_mistakes.py`).
   The eight the document names for columns, zeros and the tables' edges are predicted from the question's numbers.

## Rejected

- **A shape that is a list of alternatives** (MUL.TENS as "a power of ten, or a scaled fact"). It is new grammar in
  `taxonomy.within`, and it makes every case two alternatives, one of which can never hold.
- **A new measured tag for "worked as a fact with zeros"** to split MUL.TENS from the column skills.
  `place_value_factor` and `fact` already say it.
- **A 1-digit-first case at every level, as addition has.** It doubles every × case to say what A10 says once: both
  orders, everywhere. The order is its own case only where it is the point.
- **Advance as Hard's cases for MUL.2D1D and MUL.2D2D until M2b.** `engine load` names two levels holding one region
  as a defect, and a level that adds nothing to the one below is one.
- **Drawing only what `placing` would put at that level.** Addition's levels overlap (ADD.2D1D Advance holds A14 to
  A16), and a level is the union of its cases. The test that matters is the one home per skill.

## Consequences

- The five overlap the old `MUL.1D`, which holds questions of the same numbers until M2c re-homes it. A question
  lives in one level, so three levels fill short until then: MUL.FACTS Hard 97 of 121 and Advance 38 of 62, and
  MUL.2D1D Medium 208 of 216. M2c re-homes `MUL.1D` in the same session.
- The stored `MUL.1D` questions keep their keys (`engine bank recheck` → 0 mismatches). A predictor added later
  reaches a stored question only through the codes it already carries.
- `taxonomy_case` gains T27 and T28 and rewrites the match of 44 × cases (their digits read either way round, and
  T03's regrouping); `engine bank relabel` rewrites the cases every stored question is.
