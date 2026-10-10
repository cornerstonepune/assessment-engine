# ADR 0056 — A remainder is an answer of its own, in a box only where there is one

**Status:** accepted (2026-10-10, slice M3a of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md3a-straight-division.yaml

## What happened

Measured before the build (STATE.md "M3 — measured before the build"):

- **One answer only.** A question asked for one number, so `operations.compute` refused 85 ÷ 4 rather than round it
  down (ADR 0047, A3), and none of the 85 division placements drew.
- **No layout of its own.** In columns, a division printed as a column sum.
- **No mistakes keyed.** No division mistake was a row, so a wrong quotient could name nothing.

Built, two more questions came up:

- **A value two mistakes write in one box.** 17 ÷ 5 = 3 r 2 answered 2 r 3 is the quotient and remainder swapped.
  With the first-named mistake winning each box, its quotient box named "one group short" (20 r 5's mistake, which
  writes 2 here too) and its remainder box "the remainder added on" (which writes 3).
- **An Advance of Hard's own questions.** `engine load` refused `DIV.2D1D` and `DIV.3D1D` with an Advance that held
  exactly Hard's cases: two levels on one region.

## Decision

1. **A division is two answers when it leaves a remainder, each in a box of its own.**
   - The quotient's box is `ans`; the remainder's, after "r", is `rem`, and it is printed only where there is a
     remainder. 85 ÷ 4 reads "85 ÷ 4 = □□ r □"; 84 ÷ 4 reads "84 ÷ 4 = □□".
   - A child is never shown a box whose right answer is 0. Its presence alone would say whether the division is exact,
     and the box asks nothing the quotient's does not. This is the assumption the drafted document leaves open, for
     Achal to correct.
   - Each box is read and marked by itself, as every several-answer question is (M0a).
   - Made in `assess/division.py`, through `verify.division`, the one door the drawer and a model's candidate both use.
2. **The division layout is the school's.** The quotient's boxes stand on top, one over each digit of the number
   divided, so 156 ÷ 4 = 39 is written over the 5 and the 6 and the box over the 1 stays empty. Under them come the
   divisor and its bracket, then the number divided under its bar, with "r □" beside the quotient
   (`answer_space.divided`).
   - It is a column question's (`column_grid`) print for ÷.
   - The reader finds every box by the paper's own key, which records each box's position.
3. **A box names every mistake that writes its value there**, as marking already names every match. The other box
   tells them apart: 2 r 3 is "swapped" in both boxes, and "one group short" in only one.
   - Where two mistakes are the same act on these numbers, by construction, only the more particular is predicted, as
     multiplication's are (`mul_mistakes.py`, second reader 2026-10-09). Measured on every straight division, three
     pairs:
     - an exchange lost that is only a first digit smaller than the divisor is that digit skipped (17 ÷ 5 → 1 r 2);
     - stopping before the last digit of an exact division whose only zero ends its quotient is that zero left out
       (840 ÷ 4 → 21);
     - a number taken from itself is ÷ itself read as nothing left (7 ÷ 7 → 0).
   - Every other coincidence is by chance (36 cases or fewer in thousands for each pair), and both mistakes are named.
   - An exact division's one answer is its quotient's box, so an old paper's ÷ sum is keyed by these mistakes too
     (`misconceptions.predict`).
4. **No Advance of Hard's own questions.** `DIV.2D1D` and `DIV.3D1D` have Easy, Medium and Hard until M3b gives them
   the kinds an Advance needs, as `MUL.2D1D` had none until M2b. `DIV.FACTS` and `DIV.TENS` have an Advance in M3a
   because the document gives them straight Advance questions no lower level holds:
   - the 11 and 12 tables, a 2-digit divisor, and a remainder under a 1-digit quotient;
   - ÷ 10, 100 or 1000 with a remainder.

## Rejected

- **One box holding "21 r 1".** The reader reads digits, one to a box, and a key with a space and a letter in it is
  not a number marking can compare. One wrong value would also hide which half was wrong.
- **A remainder box on every division, its key 0 when exact.** It gives the exactness away, and it counts a box a
  child could not get wrong as a right answer.
- **First named wins in a box.** It always discarded the same mistake where two met: the swap lost to "one group
  short" on every such quotient.
- **Marking the two boxes together**, as an equation's are (`marking._group`). An equation's boxes decide together
  whether its sides hold: one box's right answer depends on the other's. A division's boxes are each right or wrong
  on their own, so each is marked by itself (M0a), and the pair still shows in what they name: a swap is named in
  both boxes, "one group short" in one.
