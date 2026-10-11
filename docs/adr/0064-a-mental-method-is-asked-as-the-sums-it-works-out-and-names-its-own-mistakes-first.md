# ADR 0064 — A mental method is asked as the sums it works out, and names its own mistakes first

**Status:** accepted (2026-10-11, slice M4a of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md4a-mental-methods.yaml

## What happened

MD.MENTAL is the drafted document's mental multiplication and division: twelve cases on four levels. Measured before
the build (STATE.md "M4 — measured before the build"):
- **Nothing drew seven of them.** Doubling, halving, × 8 by doubling three times, × 9, × 11, double one and halve the
  other, and × 25: no generator made them.
- **One drew only on another skill.** A fact scaled by ten (H10) read MUL.TENS's round-number shape; on a level with
  none it drew nothing.
- **Three grades disagreed with the school's objectives (A6).** LO-G2-0498 "Apply doubling and halving strategies" puts
  halving at Grade 2, where the draft had Grade 3. H10 (60 × 7) sat at Grade 2, but multiplying by a multiple of ten is
  Grade 3's. H09 (240 ÷ 5 as 24 × 2) sat at Grade 3, but dividing by 10 is Grade 4's at every level.
- **One method, two cases.** G06's label said × 2, × 4 and × 8; × 8 by doubling three times is H05's own case.

## Decision

1. **A mental method is asked as the sums it works out**, each in a box with its sum printed beside it, then the
   answer's: 13 × 8 as 13 × 2 = □, 13 × 4 = □, 13 × 8 = □.
   - A step is printed as a sum of the question's own numbers, never as the step before it doubled ("double 26 ="), so
     no box gives another's key away, and every key is the sum beside it. Read, marked and recomputed by a scenario like
     any other sum.
   - `assess/mental.py` makes seven methods: doubling (× 2, × 4), halving (÷ 2, ÷ 4), × 8 doubled three times, × 9 as
     ten groups less one, × 11 as ten groups and one more, double one and halve the other, and × 25 as a hundred groups
     divided by 4. The five built before keep their makers (`times_kinds.shortcut`, `facts_kinds`, `divide_kinds`).
   - Doubling is × 2 and × 4. G06's label loses "× 8", which is H05's.
   - The website draws each step and the answer as its sum with a blank (`components/question.tsx`).
2. **Numbers.** A method works on a 2-digit number that is not a multiple of ten (LO-G2-0496: "Multiply and divide
   2-digit numbers by single-digit numbers"), beside the method's own number.
   - Halving keeps to numbers that halve into whole numbers.
   - Double one and halve the other keeps to a pair whose doubled number is a multiple of ten (16 × 5, 35 × 4).
   - A fact scaled by ten on a level with no round-number rule of its own builds its numbers: a table number from 2 to 9,
     ten times bigger, beside another (`draw_times.built`). MUL.TENS keeps drawing its own.
3. **Levels from the school's objectives (A6):**

   | Level | Grade | Cases |
   |---|---|---|
   | Easy | G2 | G06 doubling, G25 halving |
   | Medium | G3 | H10, H01, H04, H08 |
   | Hard | G3 | H02, H03, H05, H07 |
   | Advance | G4 | H06, H09 |

   Corrected at the source (`research/md_taxonomy.py`): halving moves from Grade 3 to Grade 2, H10 from Grade 2 to
   Grade 3, H09 from Grade 3 to Grade 4.
4. **A method's own mistakes are named first on its answer**, each wrong value theirs alone. 14 × 11 answered 140 is a
   step short here, not the table's row out.
   - Two are new: stopping a step short (`M_MENTAL_STOPS_SHORT`: 13 × 8 doubled twice, 52), and one taken away or added
     for a whole group (`M_MENTAL_ONE_NOT_GROUP`: 23 × 9 as 230 − 1).
   - Two acts compensation already names get a × row: putting the answer right the wrong way (`M_COMPENSATION_SIGN`,
     subtraction's: 23 × 9 as 230 + 23), and doubling both numbers (`M_CONFUSES_COMPENSATION`, both changed the same
     way: 16 × 5 as 32 × 10).
   - Every other slip is its sum's, as that operation names it. A value two of division's mistakes write names both
     (`div_mistakes.in_box`): halving 74 as 32 is short division's exchange lost.
   - The five built shortcuts name their method's own mistakes from today. A copy stored before keeps its key, which
     names fewer but never names wrongly: the stale rules retire a key whose named mistakes are wrong. A wrong answer it
     cannot name goes to a person, as any unnamed answer does.
   - `named` (one wrong answer, one name) moves from `counting.py` to `misconceptions.py`, the mistake module. In
     `counting.py` it made `mental` → `counting` → `words` → `times_kinds` → `mental` a cycle.
5. **What it counts against.** A method's own mistake counts against mental maths (NUM.OPS.05, its row). A slip counts
   against the operation of the sum it is made in. A right answer counts for mental maths, reasoning (the kind's) and the
   question's operation.
6. **Rows.** MD.MENTAL on rung R47 (NUM.OPS.05) in a topic of its own, "Mental multiplication and division", untaught
   until an educator says so. Its mistake list, the four rows, and Achal's question (`md4a-mental-methods`).

## Rejected

- **A step printed from the step before** ("double 28 =" after 14 × 2 = 28): the second box would print the first's
  key.
- **New codes for the wrong way and for both doubled**: compensation already names both acts, on + and −.
- **A new code for halving each digit**: it is the exchange lost.
- **Keying the stored shortcuts again in place**: an item is ring A, never edited. Retiring them would keep their
  numbers out of the bank for good, as a retired key always does (ADR 0063).
- **One name per wrong answer across a whole box**: division names both where two of its mistakes write one value, and
  the other box tells them apart. Only the method's own take a value from the rest.

## Consequences

- **Live:** migration `20261105090000` adds the three names to MUL.2D1D's list and the step stopped short to DIV.3D1D's.
  `bin/update-live` loads MD.MENTAL, its topic and its rows, and fills its levels, 12 of every case. It waits for one
  approval on the Skill Map, and no screen or paper shows it until an educator switches it on.
- **Ratchet:** `bands.py`'s untyped findings fell from 279 to 272, as `efficient_method`'s generator became a typed
  `_shortcut`.
