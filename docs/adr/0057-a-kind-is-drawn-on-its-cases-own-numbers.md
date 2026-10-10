# ADR 0057 — A kind is drawn on its case's own numbers; a box in the other operation names no wrong operation

**Status:** accepted (2026-10-10, slice M3b1 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md3b1-facts-advance.yaml

## What happened

Measured before the build (STATE.md "M3b — measured before the build"):

- **The kinds drew their own numbers.**
  - A story, a fact family and a check each drew numbers by their own rule: a story's are 2 digits by 1, with no table
    fact and nothing round. The case then kept only the draws that landed in it.
  - On a tables level, whose every question is a table fact, almost none would land; on the tens level, only round
    numbers whose zeros leave a fact.
- **Seven × kind cases were on no level.** The document placed Q01, Q02, Q06, Y09 and H08 on `MUL.FACTS`'s Advance, and
  Q14 and H10 on `MUL.TENS`'s, and no slice built them. Nothing checked a level against the document's placements.

Built, one more question came up:

- **A box in the other operation.** A × fact family asks two divisions (4 × 7 = 28 gives 28 ÷ 4 = □). The table backwards
  asks a multiplication (42 ÷ 6 = □ because 6 × □ = 42).
  - A mistake is named by its question's operation (`core/mistake_names.py`, M0c). `M_WRONG_OP` is "added instead of
    multiplying" in a × question and "multiplied instead of dividing" in a ÷ one.
  - So a division box in a × question that names `M_WRONG_OP` would call a child who multiplied "added".

## Decision

1. **A kind is drawn on its case's own numbers.** The fact family, the table backwards, a fact from a known fact, a fact
   scaled by ten and a story that divides each take the two numbers their case draws (`draw._pair`), as a straight
   question does, then build their boxes around them (`assess/facts_kinds.py`).
   - A tables level's are table facts and the tens level's round numbers, each with the level's own defaults: no × 1, no
     0, no ÷ itself unless the case is about it.
   - A kind refuses numbers it cannot use (7 × 7 has two facts, not four; 45 × 100 has no fact under its zeros), and
     they are drawn again.
2. **A box worked in the other operation from its question's names no "wrong operation"**, whose name is the question's.
   It names every other mistake its sum shows (the divisor taken away, the table one row out), each named by one name
   in every operation.
3. **Every level holds every case the document places on it, or names the slice that will** (`test_facts_advance.py`).
   A slice's line goes when it is built; a line nothing waits for fails.
4. **A missing factor's or divisor's mistakes are drafted from + and −'s** (`facts_kinds.missing_mistakes`), for Achal to
   correct:
   - the sign misread: × as + (8 × □ = 72 → 64) and ÷ as − (□ ÷ 4 = 7 → 11);
   - the table one row out (→ 8);
   - a zero too few where the box is 10, 100 or 1000 and no table fact (45 × □ = 4500 → 10);
   - the two numbers multiplied where the divisor is the box (56 ÷ □ = 8 → 448).

## Rejected

- **Each kind keeping its own numbers, its rule widened per level.** Every kind would need its own reading of every
  level's shape (tables, round numbers, digits). `_pair` already reads all of them for the straight questions.
- **A mistake named by its box's operation.** It would change every report, card and screen that names a mistake, and
  the website's `mistake_name`, for two kinds. The box's mistakes are still named; only the one code whose name differs
  by operation is not.
- **The seven × cases left for M4.** Q01, Q02, Q06 and Q14 are on no `MD.*` skill, so no later slice would have built
  them; M3b1 builds ÷'s missing numbers on the same path anyway.
