# ADR 0065 — An estimate is drawn on its example's sizes, and a judged answer names a mistake on every question

**Status:** accepted (2026-10-11, slice M4b1 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md4b1-estimates.yaml

## What happened

MD.ESTIMATE is the drafted document's estimating and judging, ten cases at Grade 4. Measured before the build (STATE.md
"M4b — measured before the build"), drawn alone on a level of cases with no shape of its own, as MD.ESTIMATE's are:
- **Seven drew past their examples or not at all.** V01, V02, V03 and V07 failed (`KeyError: 'digits'`); V04, V09 and
  V10 drew 4-digit numbers past Grade 4 (8686 ÷ 3). On the skill each also sits on (MUL.2D1D, MUL.2D2D, DIV.2D1D,
  DIV.3D1D) they drew their example's sizes, from that level's shape. A row said what its case was about, never its
  numbers' sizes, though every example says them (48 × 6, 67 × 75, 156 ÷ 4).
- **Three refused ×.** Odd or even, the closest estimate and whether an answer can be right were + and − only.
- **The judging kinds named no mistake on most of what they asked.** The closest hundred named one on 50 of 313 draws;
  a right claim judged possible named none, half of what that kind asks. No scenario held those levels (R04, R05 on
  ESTIMATE.HUNDRED), and none worked out an odd or even answer or a closest estimate: both counted as nothing to work.
- **V06 and F08 were one kind of question,** a product odd or even, under two codes.

## Decision

1. **A case's row says its example's sizes.** V01 to V10 are about their numbers' sizes as much as their shape: a × by
   its longer and shorter number (either way round, A10), a ÷ as written. Each shared case's example has the sizes of
   its other home, so that home draws the very questions it drew before (a test draws them both ways). The sizes are
   written where the rows are made (`research/md_rows.py`), from the example the engine measures.
2. **A product is judged the three ways a sum is,** each built on the two numbers its case draws, as a division's
   estimates are (`reasoning.parity_of_product`, `closest_product`, `possible_product`; `draw.one` asks
   `reasoning.builder`):
   - odd or even (V06): three products in four are even, so an even one is kept one time in three, and the two are
     asked about as often;
   - the closest estimate (V08): the larger number rounded to three tens in a row, each times the other, the nearest
     ten right, which is also the option nearest the product;
   - whether it can be right (V05): the product, or what a named slip of it gives with another number of digits (812 is
     23 × 4 with its products side by side), one as often as the other.
3. **Every judging question names a mistake its wrong answer shows, + and − too:**
   - a wrong option is what rounding done wrong gives: up always (`M_ROUNDS_AWAY_ZERO`, now with a row for any
     operation), down always (`M_ROUNDS_TOWARD_ZERO`, new, drafted for Achal), or one number rounded and the other left
     (`M_ROUNDS_ONE_NUMBER`);
   - ticking no to a right claim judges a true claim false (`M_REVERSES_CLAIM_TRUTH`), as a division's claim already
     named; yes to a wrong one accepts it without checking its size (`M_IGNORES_SIZE`).
4. **The right option sits first, in the middle or last a third of the time each.** The closest hundred draws its place
   first, then numbers whose rounding slip shows among the options. The closest estimate of a product draws its place
   by the number: rounding the larger number up is the slip shown where it should round down, so the right option is
   first or in the middle, and the mirror where it should round up; weighted two to one, each place is a third.
5. **A scenario works out odd or even and the closest estimate** from the question's two numbers
   (`checks/scenarios._without_working`); two options as near is a question with two answers, and fails.
6. **V06 and F08 are told apart by their numbers:** F08 a table fact (6 × 7, multiples and factors, Grade 3), V06 a
   product past the tables (6 × 13, Grade 4). Corrected at the source: V06's example is 6 × 13 and 7 × 15, 7 × 9 being
   F08's; F08 is about the fact, not a shape of its own.
7. **The closest estimate's options are what rounding to a ten gives** (52 × 9: 360, 450 or 540), corrected at the
   source: the draft's 400 and 500 were what no rounding gives, so a wrong choice could name nothing.
8. **Rows.** MD.ESTIMATE on rung R48 (NUM.PV.03, NUM.PRB.03), Grade 4 at every level as drafted (no school objective
   names estimating a product, A6), in a topic of its own, untaught; its mistake list; the two rounding rows; Achal's
   question.

## Rejected

- **A level that lists a shape for each of its cases.** The sizes are the case's own, the same on every level it sits
  on; written on each level they could disagree.
- **Drawing again where the place drawn shows no slip.** A subtraction's slips sit next to the right answer, so its
  right option sat in the middle half the time; and needing a slip in all three places asked no subtraction at all.
- **Odd and even balanced by a coin.** Keeping a product when a coin agreed with its parity left three in four even.
- **The draft's options (400, 450, 500).** No rounding a child does gives 400 or 500 for 52 × 9 rounded to a ten.
- **Restricting the closest estimate to numbers that round down.** Then always rounding down would always be right.
- **A × row for each rounding mistake.** Rounding up always is the same act in any operation; one row for any operation
  says it once.

## Consequences

- **Live:** `engine load` updates the ten case rows (MUL.2D1D, MUL.2D2D, DIV.2D1D and DIV.3D1D draw as before), loads
  MD.ESTIMATE, its topic and the rows, and `bank refill` fills its levels. It waits for one approval on the Skill Map and
  for an educator to switch it on.
- **Addition's estimating:** new closest-hundred questions are drawn the new way; a stored one keeps its key and names
  fewer mistakes, never wrongly, as ADR 0064 holds.
- **Ratchet:** `reasoning.py` is typed throughout (123 untyped findings to none), and `bands.py`'s fell from 272 to 268.
