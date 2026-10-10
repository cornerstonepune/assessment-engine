# ADR 0058 — A box is keyed by the act that finds it

**Status:** accepted (2026-10-10, slice M3b2 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md3b2-divide-advance.yaml

## What happened

Measured before the build (STATE.md "M3b2 — measured before the build"), over every question `DIV.2D1D`'s and
`DIV.3D1D`'s numbers can make:

- **A digit missing in the number divided** (7□ ÷ 4 = 18). Keyed by the division's own mistakes, run backwards, 66 of
  212 2-digit questions named no mistake at all.
- **The remainder missing with the quotient printed** (85 ÷ 4 = 21 r □). No named division mistake keeps the printed
  quotient and changes only the remainder, so 556 of 556 named nothing.
- **A digit missing in the quotient** (936 ÷ 3 = 3□2). Any wrong quotient's digit at the box's place names nearly every
  question, but takes its digits from 933 or 2808 (÷ read as − or ×). Those numbers do not fit the printed boxes.

Every question needs a named mistake: the bar a scenario holds. The question was which mistakes a box should name.

## Decision

1. **A box is keyed by the act a child does to fill it**, measured to name every question its level holds:
   - **A digit in the number divided** is found by multiplying (18 × 4 = 72). Its box names:
     - that multiplication's named mistakes, the wrong product's digit at the box's place copied (the carry left out
       gives 42: 4 in a tens box);
     - each division mistake that, made with another digit there, gives the quotient shown.
     - Every 2-digit question names one, and all but 2.4% of 3-digit ones; those are drawn again.
   - **A remainder** is found by taking away (85 − 21 × 4). Its box names that subtraction's mistakes, and the
     multiplication's with its product taken away rightly. One group short leaves the division's own remainder too big
     (r + 4), named too. Every question names one.
   - **A digit in the quotient** names each division mistake whose quotient is as long as the printed one, that
     quotient's digit at the box's place. A wrong quotient of another length does not fit the boxes, and says nothing
     about what is written in this one. 11% of questions name none and are drawn again.
   - **A check** (96 ÷ 4 = 21 r 2? 21 × 4 + 2 = □) names the multiplication's mistakes. **A step** (240 ÷ 10 = □) names its
     own division's.
2. **A box worked in another operation names no "wrong operation"** (ADR 0057). The digit found by multiplying and the
   remainder found by taking away are such boxes; a mistake is named by its question's operation.
3. **A claimed answer is right, or what a named mistake writes, one as often as the other.**
   - "Could it be right?" claims the right answer, or one group short with its remainder too big (85 ÷ 4 = 20 r 5).
   - The check claims the right answer, or a slip of the division layout with its remainder (96 ÷ 4 = 21 r 2, each digit
     divided alone). ÷ read as − or × is no slip of the layout.
4. **Code works every box, and a scenario recomputes it independently** (`checks/scenarios.py`): a digit in a printed
   division (only one may fit), an estimate's first box from the rounding its question states, a claim's tick, and a
   check worked × before +.
5. **An estimate of a division** rounds the number divided to the nearest hundred, asked only where the divisor divides
   that hundred (412 ÷ 8 ≈ 400 ÷ 8 = 50), so the estimate is the one its rounding gives. Or it asks how many digits the
   quotient has, its exact answer printed in as many boxes as the number divided has digits (M3b1).

## Rejected

- **Every wrong quotient's digit in a quotient's box, whatever its length.** It names nearly every question, but with
  digits a child who misread the sign would never write between the printed digits.
- **Every shown digit kept.** A child who works a product wrong copies the digit at the box's place without checking
  the rest: 85% of quotient boxes and 140 of 212 number-divided boxes would name nothing.
- **"A remainder left out" as a new mistake** (73 ÷ 4 = 18 r 1, answering 3 in 7□ ÷ 4 = 18). Every question names a
  mistake without it. It is drafted for Achal, not added.
- **An estimate rounded to the nearest multiple of ten times the divisor.** It always divides, but its stem cannot say
  it in a child's words. The nearest hundred is the school's own rounding, and the draws it cannot divide are drawn
  again.
