# ADR 0055 — A written method is a kind of its own, its steps its boxes

**Status:** accepted (2026-10-10, slice M2d2 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md2d2-multiplication-methods.yaml

## What happened

Assumption A1 (ADR 0047) has Easy to Hard print each calculation in every written method the drafted document lists
for the skill, in fair shares. Measured before the build (STATE.md "M2d2 — measured before the build"):
- **Drawn:** a line, columns and long multiplication.
- **Refused:** partitioning (`break_apart` made + and − only).
- **Never drawn:** the grid, expanded columns and the lattice. The drawer printed a calculation in a line or in columns
  and nothing else.
- **No method on any level:** the straight cases accepted only the three standard methods, T01 fixed columns, and T02
  fixed a line and no regrouping.
- **No rows:** neither C06's mistake nor the grid's was a row.
- **No charge to addition:** no multiplication used addition, so the rows added without a carry (A11) could not count
  against it.
- **Never read:** a long multiplication's rows were drawn, never read.

## Decision

1. **A written method is a kind of its own, each step a box.** The four kinds are `partitioning`, `grid_method`,
   `expanded_columns` and `lattice`.
   - `assess/written_methods.py` makes them, `assess/written_pages.py` prints them, and the website draws them.
   - Each step is a response with its own key, so the reader reads it and marking marks it by itself. This is M0a's
     every-answer reading, unchanged.
2. **A level's methods are a row**, `methods`: the method cases the document lists for the skill.

   | Skill | Methods |
   |---|---|
   | `MUL.2D1D` | T02, G07, G08, G10, G11 |
   | `MUL.3D1D` | T13, T14, G10, G11 |
   | `MUL.2D2D` | T22, G09, G12, G13 |

   - The drawer deals each case's share evenly over the methods it can be printed in (`draw_case.ways`, `draw.level`).
     Each draw is the case's numbers and the method's conditions together (`taxonomy.within`), so a grid of Easy's
     numbers is an Easy question, measured as both.
   - A case that writes the 1-digit number first is never set out in columns, where the longer number goes on top.
3. **A straight case is about its numbers.** It accepts every written method of its operation and the kinds that print
   them. Corrected at their source (`research/md_rows.py`, `research/md_taxonomy.py`):
   - T01 is "2 × 1 digits, no regrouping", in any method.
   - T02 is "2 × 1 digits in a line": `MUL.2D1D`'s in-a-line method, as T14 is `MUL.3D1D`'s and T22 `MUL.2D2D`'s.
   - `MUL.2D1D`'s Easy holds T01 and T03.
   - A grid's size is its shorter number's (`digits_min`, A10), so 3 × 21 in a grid is a 2 × 1 grid.
   - A written method is a straight calculation wherever one is read: drawn on Easy to Hard, and placed as a child's
     answer is placed where its numbers in a line would be (`placing.CALCULATION` is `draw.STRAIGHT`), never at
     Advance.
4. **The methods' mistakes**, worked from the numbers:
   - a part with its tens taken as ones (`M_PARTITION_TENS_AS_ONES`): 20 × 4 written 8, and the total it makes,
     2 × 4 + 3 × 4 = 20;
   - a grid added without its ones-by-ones cell (`M_GRID_CELL_DROPPED`);
   - the steps or rows added without a carry (`M_NOCARRY`, addition's own row), on long multiplication's answer too.

   A step is a small multiplication and names that multiplication's slips. A method's total names its own mistakes and
   the numbers added. It never names a column method's slips (a carry dropped, the second row not moved): it cannot
   show them.
5. **A11 is a row and a rule.**
   - A written method that adds its steps uses addition (`skills.by_method`).
   - A mistake with no row for the question's one operation, and one row for another operation the question also
     carries out, counts against that other one (`skills.charges`). So the rows added without a carry count against
     addition.
   - Every other mistake is charged as it was.
6. **An old key is a key problem.** The refill retires the question and draws another; stored questions are never
   changed in place.
   - A long multiplication keyed before its rows' mistake had a name (`verify._stale_rows`).
   - A written method whose boxes its rules, or the predictors its steps use, now key otherwise (`verify._stale_method`):
     made again from its own numbers, every box is compared. Without it, a × slip predicted later would never reach the
     steps already in the bank.
   - A written method of a zero is refused (`CannotMake`), as every kind refuses numbers it cannot use: 0 has no parts.
7. **C06 plants the partitioning slip in a worked answer** (`diagnosis._shaped`, "partitioned"), on `MUL.2D1D`'s
   Advance.

## Rejected

- **Partitioning as `break_apart`** (G07's draft). `break_apart` is + and −'s mental strategy (347 + 25, the tens and
  then the ones). Its kind's row counts every one of its questions for mental maths (NUM.OPS.05), which a written
  multiplication is not.
- **The grid, expanded columns and lattice as `column_grid`**, printed by their method (the draft's rows). Every reader
  of a column sum would carry each method's exception: the page, the website, the layout (ADR 0054's reason).
- **Method cases among a level's `cases`.** A case is drawn on the level's `within` alone, and `within` does not carry
  the level's number rule (Easy's "no regrouping" is T01's). A grid of Hard's numbers would have been an Easy question.
- **Charging any single-row mistake to its row's operation on every question.** It would also move charges on the
  two-operation budget questions, which this slice does not touch.

## Consequences

- **The skills' mistake lists** for `MUL.2D1D`, `MUL.3D1D` and `MUL.2D2D` name what their questions now show: the seed
  for a new database, migration `20261101090000` for one loaded before.
- **The levels' `methods`** reach live through `bank levels --apply`, and each changed skill waits for one approval.
- **Addition counts too.** A right answer to a long multiplication or a written method now counts for addition
  (ADR 0023): `bank relabel` adds NUM.OPS.01 to those questions' skills.
- **Typed as touched.** Untyped findings fell and are written down:

  | File | Before | After |
  |---|---|---|
  | `skills.py` | 77 | 1 |
  | `diagnosis.py` | 117 | 48 |
  | `draw.py` | 177 | 127 |
  | `taxonomy.py` | 36 | 11 |
  | `tags.py` | 241 | 240 |
  | `verify.py` | 99 | 96 |
  | `placing.py` | 35 | 1 |
