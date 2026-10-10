# ADR 0063 — A written division is a kind of its own, and the draft is corrected where it contradicts itself

**Status:** accepted (2026-10-10, slice M3d of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md3d-division-methods.yaml

## What happened

Assumption A1 (ADR 0047) has Easy to Hard print each calculation in every written method the drafted document lists for
the skill, in fair shares; ADR 0055 built it for multiplication. Measured before the build (STATE.md "M3d — measured
before the build"):
- **Refused:** partitioning the number divided (`break_apart` made + and − only).
- **Never drawn:** chunking and long division. A division in columns by one digit is measured as short division, so
  nothing the drawer printed was long division.
- **Drawn, never read:** short division printed as the plain division layout, its exchanges neither written nor read.
- **No method on any level:** a division printed in a line or in the division layout and nothing else.

The drafted document, read against itself:
- **No line for 3 digits.** Its methods column gives DIV.3D1D chunking, short and long division, against A2 ("division
  prints in a line by default", from the school's July papers).
- **Halving in two homes.** G25 sat on DIV.2D1D's methods and on MD.MENTAL's Hard. A1's division methods do not include
  it, and doubling, its mirror, is MD.MENTAL's alone.
- **Chunking could not print a 3-digit division.** It took ten lots at a time, and the document places it on DIV.3D1D:
  588 ÷ 3 would print nineteen take-aways of 30, then 6.
- **D02 was a case and a method at once**, as T02 was before ADR 0055.

## Decision

1. **A written division is a kind of its own, each step a box.**
   - `assess/divide_methods.py` makes partitioning the number divided (`partitioning`, method `PARTITION_DIVIDEND`),
     chunking (`chunking`) and long division (`long_division`).
   - `assess/divide_pages.py` prints chunking and long division. Partitioning prints as multiplication's does, a part's
     remainder after "r" beside it (`written_pages.partitioning`). The website draws each (`components/methods.tsx`).
   - `assess/written.py` names every written method of both operations, so the drawer, the stale keys and the placing
     read one table: partitioning prints either operation's.
2. **Short division is the division layout, each exchange written small** (G23), as compact columns are columns with
   the carry written small (G11).
   - A small box stands before every digit but the first. The ones a remainder is exchanged into are read, each keyed
     by the remainder carried (`division.exchanges`); the rest are room, as columns draw a carry's room over every column.
   - A new print layout, `2026-10-10` (`render.layouts`, `exchanges`), draws them. A paper printed before keeps its own
     layout and is read as it printed.
   - A division stored in its layout before its exchanges had boxes is a key problem (`stale._unread_exchanges`): the
     refill retires it and draws another, never changing a printed key in place.
   - Printed with its boxes, the layout's spec says where they are (`exchanged`), so it is a question of its own. A
     question once in the bank, even retired, is never drawn again, and DIV.2D1D's levels have few numbers: without it,
     the retired layouts would have kept their numbers out of the division layout for good (measured on the copy: the
     Medium level refilled with no division layout at all). A division with nothing to exchange is the question it was.
3. **Each method's steps.**
   - **Partitioning:** the most tens of lots of the divisor, then the rest (72 ÷ 4 is 40 ÷ 4 and 32 ÷ 4). It needs both:
     35 ÷ 4 has no ten lots and 80 ÷ 4 no rest, so those numbers are refused and drawn again.
   - **Chunking:** for each place of the quotient, largest first, the lots it is worth, what they take away and what is
     left (96 ÷ 4: 20 lots, 80, 16 left; 4 lots, 16, 0 left). A 3-digit division is three take-aways at most.
   - **Long division:** the first number divided is the leading digits, as few as reach the divisor; then for each, its
     product and what is left with the next digit brought down. The last row is the remainder.
   - A written division divides by 2 to 9. ÷ 1 is a fact, and a 2-digit divisor's long division is D13's, in no grade.
4. **The mistakes, worked from the numbers.** No new code; every one is a row already.
   - A part's or a lot's quotient with its zero left out (40 ÷ 4 written 1, 20 lots written 2), carried into the total
     it makes (`M_DIV_QUOTIENT_ZERO_DROPPED`).
   - One group short, leaving too much (`M_DIV_REMAINDER_TOO_BIG`), and a digit not brought down
     (`M_DIV_BRING_DOWN_MISSED`, named before a chance slip that writes the same number).
   - A part names its own small division's slips, and an exchange its small division's remainder slips (7 ÷ 4: the 7
     carried whole, or its quotient written instead).
   - A product names its multiplication's slips, and a number left its take-away's. Never "the wrong operation": on a
     division that name is the division's own.
5. **What a slip counts against** (A11).
   - Long division and chunking multiply and take away, and use both (`skills.by_method`).
   - Partitioning's answers, and chunking's lots, are tens and ones put together, which never carries: no addition is
     carried out.
   - A mistake with no row for the question's own operation counts against the one other operation it has a row for
     *among those the question carries out* (`skills.charges`). `M_FACT_PM1` has a + row and a − row, and a long
     division carries out only −. Before, it counted against division.
   - Measured on the copy's 26,102 stored questions with mistakes: none is charged otherwise.
6. **The levels' methods are rows** (`skill_sets.json`):

   | Skill | Methods |
   |---|---|
   | `DIV.2D1D` | D02, G21, G22, G23 |
   | `DIV.3D1D` | D15, G22, G23, G24 |

   - DIV.2D1D's Easy holds D01 alone, "2 ÷ 1 digits, every digit divides", printed in every method.
   - D02 is "2 ÷ 1 digits in a line", and D15 "3 ÷ 1 digits in a line", as T02 and T14 are multiplication's.
7. **Corrected at the source** (`research/md_taxonomy.py`, `research/md_rows.py`; the document and the rows written again,
   252 cases):
   - D15 added; DIV.3D1D prints in a line (A2).
   - G25 halving is MD.MENTAL's alone (M4, BUILD-ORDER).
   - Chunking takes the lots of each place.
   - G21, G22 and G24 name the kinds that print them.
   - A straight division accepts every written method of its operation and the kinds that print them, as a straight
     multiplication does.
8. **A level is topped up in every way it prints a case** (`refill.top_up`, `draw.split`): a case's share is dealt over
   its ways, and each way is drawn what it is short of. Topped up per case, a level the bank filled before it listed
   methods stayed in its old ways: on the copy, DIV.2D1D's Easy kept its 46 questions in a line and in the division
   layout and gained no partitioning or chunking. Multiplication's levels, filled the same way before ADR 0055, are
   topped up in their methods too.
9. **A scenario recomputes every step** (`scenarios._division_steps`), from its two numbers, apart from the code that
   made it: the exchanges, the parts, the take-aways and the long division's rows. On every number from 10 to 999 by 2
   to 9, 23,222 written divisions and every division layout agree.

## Rejected

- **Chunking ten lots at a time**, as drafted. The document's own placement on DIV.3D1D cannot print it.
- **Halving among DIV.2D1D's methods.** It would give one question two homes. A1 does not list it, and its mirror,
  doubling, is mental maths.
- **A line only for 2-digit division**, as the drafted table had it. Today's DIV.3D1D printed in a line, and A2 and the
  school's papers say a division is written so.
- **Short division as a kind of its own.** The division layout already is short division: a new kind would leave every
  reader of a column division with two kinds for one layout.
- **An exchange box only where an exchange happens.** The printed layout would tell the child where to exchange. Room
  before every digit, read where the key has an exchange, is how columns draw a carry.
- **Addition for partitioning and chunking.** The parts' answers are tens and ones put together, with nothing to get
  wrong, and a right answer would have counted for addition.

## Consequences

- **Live:** `bin/update-live` loads the corrected cases and the layout row, and `bank levels --apply` carries the levels'
  methods to DIV.2D1D and DIV.3D1D, which wait for one approval on the Skill Map. Migration `20261104090000` puts the
  methods' mistakes on the two skills' lists. The refill retires the division layouts printed before their exchanges had
  boxes and fills every level in its methods.
- **Split along a real responsibility, as the files grew past 400 lines:**
  - `assess/straight_pages.py` holds a calculation's question and boxes (a line, columns, the division layout, a
    missing digit, an estimate, the quickest method), moved out of `render.py`.
  - `assess/draw_pair.py` holds two numbers for a case and the defaults they keep, moved out of `draw.py`. A
    division's numbers now pass the method's own check there, as a multiplication's always did.
- **Typed as touched:** `answer_space.py` 33 untyped findings to 0, `render.py` 317 to 314.
- **Rejected with them:** topping a level up per case and retiring the questions of the older ways to make room. They
  are right questions; a level may hold more than its target, never fewer of a method.
