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

CI then failed, for two more reasons. The five could not fill while the old `MUL.1D` held questions with the same
numbers, since a question lives in one level; so the re-homing planned as M2c had to ship in this slice. And the
tables' Easy and Medium sat in Grade 1, against the Grade 1 decision of 2026-10-06 (Grade 1 is exactly what its
educator taught).

A second reader then found ten more defects, among them:
- the long multiplication's rows reused the `.work` class, so the reader took the answer boxes as working, and a page
  printed in an older layout would have re-rendered differently;
- MUL.TENS drew far past its labels (6700 × 1000 at Grade 3);
- Easy levels drew Medium's answers;
- one wrong answer named two mistakes by construction (7 × 1 → 8 as both "× 1 adds one" and "added the numbers");
- "one row out in the table" was predicted for 68 × 17;
- four tests could not fail.

## Decision

1. **Five shapes, one home.** MUL.FACTS is every table fact (both numbers to 12). MUL.TENS is every round-number ×
   that is not a fact: by 10, 100 or 1000, or a multiple of ten, one or both numbers. MUL.2D1D, MUL.3D1D and MUL.2D2D
   are the rest by their digits. A skill's shape is what any of its levels holds (`placing.shape`). A test reads every
   straight × in the five's reach and finds exactly one home, and a level, for each. TZ01 (230 × 4) and TZ07
   (23 × 40) join TP10 at MUL.TENS Advance.
2. **A × case reads the longer number and the shorter** (`digits_max`, `digits_min`; `research/md_rows.py` `DM`),
   as `assess/md_tags.py` already measured the working. Only T03 and T13 are about the 1-digit number coming first;
   they print in a line, and in columns the longer number goes on top. ÷ keeps the order: 72 ÷ 4 is not 4 ÷ 72.
3. **Every question in reach is a case, and every case says what its label says.** New cases fill the gaps:
   - T27 and T28 for 19 × 14 and 68 × 17;
   - TZ09 for 401 × 3, a zero in the middle with the answer grown;
   - TP11 for 30 × 100.

   So there are 251 cases. Label and match now agree:
   - Easy cases keep to Easy's answer size (T02, T03, T11, TZ02);
   - MUL.TENS's cases are bounded to their words ("× 1 digit", "2 digits × a multiple of ten", "×1000 of a number to 2
     digits");
   - TP10 holds 11 × 20, as its words do.

   A test holds every drawn question to its case's label, written in plain arithmetic in the test.
4. **Assumption A4 is what a level holds, not only what it draws.**
   - The tables' Easy to Hard leave out the facts that need the 11 or 12 tables, measured by `fact_group`, and their
     Advance holds every table. So an old paper's 12 × 7 is placed at Advance.
   - 12 × 0 and 11 × 1 are the facts of 0 and 1.
   - MUL.TENS Hard holds 110 × 5, which is Grade 4's, after the tables' Advance at Grade 3.
5. **Grade 1 stays its educator's list.** A level the objectives put in Grade 1 sits in Grade 2 until the Grade 1
   educator says it is taught (the drafted document's A6 now says so).
6. **An Advance only where the document gives it straight questions no lower level holds**: the 11 and 12 tables, and
   a round number with no table fact under it. MUL.2D1D's, MUL.3D1D's and MUL.2D2D's Advance are kinds M2b makes.
7. **The drawer makes ×** (`assess/draw_times.py`). A fact comes from the tables, a number a case lets be round is a
   number times 10, 100 or 1000, nothing is × 1 unless its case is about × 1, and a case that names its method is
   printed that way.
8. **A mistake is worked the way the child sets it out, and one act names one mistake** (`assess/mul_mistakes.py`).
   Where two predictors give one wrong answer on every such question, the less particular refuses:
   - adding the numbers on × 0 and × 1;
   - the placeholder row on a multiplier ending in 0;
   - column by column on a repeated digit or two round numbers;
   - reversed units on one digit or a round number;
   - no carry where every carry lands on a zero;
   - row-by-row mistakes on × 10, 100 and 1000.

   "One row out" needs a multiplier with a table.
9. **A stored question whose mistake key a predictor has since corrected leaves the bank** (`verify.key_problems`, the
   comparison `engine bank recheck` already made). It is not changed in place, so a paper printed with it still reads
   as it did.
10. **A long multiplication's rows print only in the layout row that adds them** (`render.layouts` 2026-10-09,
    `long_rows`). They are one working space for the reader, never an answer box. A page printed in an older layout
    re-renders as it printed.
11. **`MUL.1D` is re-homed onto the five and removed** (`replaces`). An old paper's × sums are filed on the five's
    rungs (`placing.OPERATIONS`). Rung M1 stays for the papers' ÷ questions until M3.

12. **A level whose target is all it holds is filled to its last question** (`draw._rest`, `draw_times.every`). CI's
    bank stopped MUL.2D1D Easy at 66 of its 69. 3 × 21 turns up once in about 3,000 random draws, and the drawer
    called a case dry after 2,000 misses in a row. Now a × case that runs dry is listed whole: every pair its numbers
    can be, at most 20,000 for one pair of digit counts. A case too large to list keeps the misses; MUL.TENS's
    × 1000 is one, and no level drawn whole is.

## Rejected

- **`min_items` lowered to what the drawing happens to reach.** It would make the target a guess about luck,
  not what the level holds.
- **More tries before a case is called dry.** It makes the miss rarer, not impossible, and costs every refill.
- **A fixed random seed in CI.** CI would pass while a fill on live stopped short.

- **A shape that is a list of alternatives written by hand** (MUL.TENS as "a power of ten, or a scaled fact"). The
  shape is the union of the levels' own `within`, which the rows already state.
- **`operand_max`, a drawing-only bound for A4.** A question that arrives another way (a re-homing, an old paper)
  ignored it, which is how 12 × 7 was re-homed to Medium.
- **A 1-digit-first case at every level, as addition has.** It doubles every × case to say what A10 says once.
- **Advance as Hard's cases until M2b.** `engine load` names two levels holding one region, and 3 × 1's Advance (T13)
  held only questions Easy to Hard hold.
- **M2c as its own slice.** It could not ship green alone.
- **Changing a stored question's key in place.** A printed paper would no longer read as it did.

## Consequences

- `MUL.1D`'s questions move by `engine bank rehome`. On the local copy, 596 of 864 moved and 268 stories were retired
  and kept, with none lost. Some 2 × 2 questions carry keys this slice corrected, and refill retires and redraws them.
- `taxonomy_case` gains T27, T28, TZ09 and TP11 and rewrites the matches of the × cases it bounds or reads either way
  round. `engine bank relabel` rewrites the cases every stored question is.
- The week-note eval's gold names the new skills for its two multiplication notes. Its score is recorded again by
  `bin/engine eval week_skills` where the model is.
