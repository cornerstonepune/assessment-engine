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
   names 6, since 6 × 4 ends in 4 as 1 × 4 does; 48 × 2 = □6 names 8, the carry forgotten. **Else it names the table
   read one row out** (M_MUL_ROW_OUT): in the larger number the digit next to the right one, below where that is a digit
   (3□ × 9 = 297 names 2); in the answer the column worked one group short. The larger number's lead has no digit its
   column allows alone: the whole rest of the answer fixes it. Only a box on the answer's last carry names nothing, and
   a question none of whose boxes names one is drawn again.
7. **A worked answer asks the column of its first wrong digit only where that column can move**, for every operation
   (`diagnosis.asks_where`). The columns a slip's first wrong digit falls in are counted once, over 2,000 calculations
   drawn as its questions are, from a seed of their own. Where it is one column, the question asks the right answer and
   why. A stored question that asks it is retired by `bank refill` (`verify.key_problems`) and made again.
   - Measured: a carry lost onto a zero in 3 digits by 1 is always lost in the tens, and MUL.3D1D's Advance plants no
     other slip, so its tick was one box every time.
   - So were ADD.2D1D's Advance (numbers lined up from the left, always the ones), ADD.3D2D's (lined up from the left,
     or copied out of a line: the ones) and ADD.4D's (a final carry dropped: the top digit).
   - The one-column slips: lined up from the left, copied out of a line, a final carry dropped, an exchange from the
     wrong place, the two across-a-zero exchanges, and a decrement forgotten in 2 digits. A bank built today held 485
     such questions of its 1,199 finding the mistake.
5. **T13 joins the ways MUL.3D1D's questions are printed**, beside T14. MUL.3D1D's Advance is Q16 and C09.
6. **C06 (partitioning, tens taken as ones) waits for the methods (M2d)**. Its mistake is a method's, and no row or
   predictor names it yet.

## Rejected

- **A tolerance on a × estimate**, as + and − have. The question says how to round, so there is one estimate.
  A tolerance wide enough to matter at 300 would also pass 240, the estimate from rounding the wrong way.
- **Drawing a × box again until its column alone allows a second digit** (this ADR's first version). It kept only the
  ones after an even multiplier: Q07 was never asked after 3, 7 or 9, nor in the lead. The table one row out is a
  digit a child writes, and every box but the answer's last carry has one.
- **"A level mixes it with others"**, the ground `_spread` gave for keeping a tick a slip always answers the same way.
  Measured over every level that plants a slip, it held for none of ADD.2D1D's, ADD.3D2D's, ADD.4D's or MUL.3D1D's
  Advance. Mixed or not, a tick whose answer the slip decides asks the child nothing the right answer does not.
- **Listing every pair for a × slip and counting + and − differently.** One count, drawn as the questions are, serves
  both: + and − at 4 digits are too many pairs to list, and one rule is read in one place.
- **The × kinds in `assess/items.py`.** It is frozen at its 540 lines; the two kinds only multiplication has are a
  module of their own (`assess/times_kinds.py`).
- **T13 as the Advance's straight case.** Every question it holds is placed at Easy to Hard, so the level would add
  nothing harder.

## Consequences

- Three Advance levels reach live with `bin/update-live` (`engine load`, `bank refill`, `library build`).
- The renderer draws a × estimate's question in its own words (how many digits, the last digit), and a shortcut's
  step and answer, from two helpers rather than more branches in `render_item`. Its complexity fell, 25 to 24.
- **+ and − change on live:** their find-the-mistake questions of a one-column slip lose the column tick. `bin/update-live`
  retires the stored ones and makes them again (`bank refill`); a paper already printed still reads as it did, since a
  question leaves the bank rather than being changed in place. Their numbers are drawn as before, draw for draw.
- A request no question can meet is refused by name (`CannotMake`): a number near a round one of 3 digits, × 5 as
  × 10 then halved on 1 digit, rounding a 1-digit number to the ten, a × slip in a table fact or one its numbers cannot
  show, a missing digit in a table fact.
