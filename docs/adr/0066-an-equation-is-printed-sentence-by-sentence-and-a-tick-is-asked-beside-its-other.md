# ADR 0066 — An equation with × and ÷ is printed sentence by sentence, and a true-or-false is asked beside its other

**Status:** accepted (2026-10-11, slice M4b2 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md4b2-equality.yaml

## What happened

MD.EQUALITY is the drafted document's equations with × and ÷, eighteen cases at Grades 3 and 4. Measured before the
build (STATE.md "M4b2 — measured before the build"):
- **Eleven were shapes no kind makes** (`equality.equation` raised "no equation shape"), and the missing sign and the
  comparison were + and −'s only.
- **A remainder could not be checked** (DR09): the division check refused any division with one. **A ÷ claim could not
  be explained** (C08): the claim to explain was addition's only.
- **Three drew past their examples' sizes** (8644 × 0, 167 × 417, 4424 ÷ 7): their rows said nothing of their numbers.
- **Two of the draft's true-or-falses were false on every paper** (9 ÷ 0 = 0, 12 ÷ 3 = 3 ÷ 12), and one true on
  every paper (7 × 6 = 6 × 7): a child ticking one place every time would score them all.
- **The scenario check worked out no equation it could not read as one × or ÷:** of EQUALITY.INVERSE's + and −
  questions it worked out none of Medium's 24 or Advance's 24 and half of Hard's; a comparison of two equal sums named
  no mistake.

## Decision

1. **× and ÷ equations are a module of their own** (`assess/times_equality.py`), one function per shape, each drawing
   its numbers from its example's pattern (Grade 3's table facts, Grade 4's 2-digit numbers). `equality.from_rule`
   hands a case's shape there when the case is multiplication's (`taxonomy`, a drawer hint that draws nothing), so the
   missing sign and the comparison are × and ÷'s own there and + and −'s own on their cases.
2. **Each sentence is printed with its own box or its own tick.** A response's label is its sentence; the paper prints
   each on its own row, the box where its □ stands, or its ticks after it (`straight_pages.equation`). One sentence,
   one box, one tick: the reader finds each where the key says, and marking marks each by itself.
3. **A true-or-false, a sign and a comparison are asked beside their other, in either order** — a true claim beside a
   false one (9 ÷ 0 = 0 beside 0 ÷ 9 = 0, a division turned round beside a product, a product turned round beside a
   difference), a × sentence beside a ÷ one — so each place is right one way as often as the other.
4. **Every question names a mistake its wrong answer shows**, from the vocabulary: = read as "the answer comes next",
   every number added (never where that is a bracket's value too), × 0 kept as the number, × 1 adding one, a number ÷
   itself as 0, 0 ÷ a number as the number, the wrong sign, a comparison turned round, a division or a difference
   turned round, a claim's truth reversed; and three new, drafted for Achal: **÷ 0 read as 0**, **a remainder left out
   of its check**, **a bigger divisor taken to give a bigger answer**. A comparison of two equal sums (+) names the
   first number's change seen and its partner's missed (`M_APPLIES_COMPENSATION_ONE`).
5. **A division is checked with its remainder** where its case asks for one (DR09): the claim is right or a named slip
   of the layout with a remainder, one as often as the other; its check adds the remainder back, and the product
   written alone is the remainder left out — on DIV.2D1D's checks too, whose wrong claims carry one (a migration puts
   the code on that skill's list). Yes to a remainder too big accepts that mistake.
6. **A wrong ÷ answer is explained by multiplying back** (C08): the claim is a named slip of the layout with nothing
   left over (804 ÷ 4 = 21, the zero left out); the product is a box keyed by multiplication's slips; the reason is
   read by a person. Nothing to tick: the product written is the check.
7. **Five rows say their examples' sizes** (Y04 3 digits by a zero, Y09 a table fact, Y10 and DR09 2 digits by 1, C08 3
   by 1), written where the rows are made. Y09 and Y10 draw on MUL.FACTS and DIV.2D1D exactly what they drew before.
8. **The scenario check works out every equation from its own sentence** (`checks/sentences.py`): an exact reader of
   whole numbers, + − × ÷ and brackets, apart from the code that wrote them. A box is the one whole number that makes
   its sentence true (a sentence given before it, ", so", true too); a tick the one sign, comparison or truth its
   sentence asks; a balance's pans are one sentence. A sentence with no single answer is worked out as having none and
   fails, never skipped.
9. **The draft is corrected at its source:** Y07, Y08 and Y16 are asked beside their others, and the three new
   mistakes are in its table for Achal to correct.
10. **Rows.** MD.EQUALITY on rung R49 (NUM.OPS.05, NUM.PRB.03), Grade 3 at Easy and Medium and Grade 4 at Hard and
   Advance as drafted ("Missing numbers in equations" is the school's objective at both grades), in a topic of its own,
   untaught; its mistake list; the three rows; Achal's question.

## Found on the way, fixed at its cause

**The + and − missing sign printed a difference below zero** (7 □ 9 = -2): it took a larger number from a smaller one
about one draw in thirty-five, on a Grade 2 skill. The new check could not work it out, which is how it was found. The
larger number now comes first, and a stored one is retired by `bank refill` (`stale.key_problems`); a rehearsed copy of
live held two.

## Rejected

- **One sentence holding every box, the boxes after it** (the + and − equation's way). Two boxes after "37 × 1 and 37 ÷
  1" say neither which is which nor where each is read.
- **Asking 9 ÷ 0 = 0 alone, as drafted.** Its answer is false on every paper.
- **A yes-or-no tick for C08.** Ticking no is guessable; writing 84 is not.
- **Brute force alone in the scenario check.** A product's box (180) lies past the numbers its sentence prints; a
  line in □ is solved straight back, and only a box that divides is tried number by number.
- **Retiring a sign question by its level's rule.** A negative difference is outside every level, not one; the stale-key
  rules are where a kind's corrected rule retires what it made before.

## Consequences

- **Live:** the migration adds the remainder left out to DIV.2D1D's list; `engine load` updates the case rows (MUL.FACTS
  and DIV.2D1D draw as before), loads MD.EQUALITY, its topic, the three rows and Achal's question, and `bank refill`
  fills its levels and retires the two sign questions below zero. It waits for one approval on the Skill Map and for an
  educator to switch it on.
- **Stored questions keep their keys:** a stored equal-sums comparison names fewer mistakes, a stored division check
  without its remainder's name, never wrongly (ADR 0064).
- **Ratchet:** `render_item` fell to 56 statements; untyped findings fell in `render.py` from 314 to 301 and in
  `equality.py` from 164 to 127 (the missing sign typed); the two new modules are typed throughout.
