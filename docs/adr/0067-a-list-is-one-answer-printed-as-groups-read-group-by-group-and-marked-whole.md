# ADR 0067 — A list is one answer: printed as groups with room to spare, read group by group, marked as a whole

**Status:** accepted (2026-10-11, slice M4c of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md4c-multiples-and-factors.yaml

## What happened

MD.MULTIPLES is the drafted document's multiples, factors and divisibility, eight cases at Grades 3 and 4. Measured
before the build (STATE.md "M4c — measured before the build"):
- **Seven of the eight were a kind no generator makes** (`multiples`); F08, a product odd or even, drew already.
- **Four answers are lists** — the multiples of 6 up to 60, the factors of 12, the factor pairs of 24, the common
  multiples of 3 and 4 below 30 — and everything after the drawer took one number per answer: the reader reads one
  strip of boxes per answer (`boxes.read_page`), marking compares one number with one key (`marking.mark`), evidence is
  one row per answer.
- **A list keyed box by box marks one omission as many mistakes.** Smallest first, 1, 2, 3, 6, 12 for the factors of
  12 marks the fourth and fifth boxes wrong and the sixth blank: three pieces of evidence for one factor left out.
- **A box per member tells the child how many there are**, which is half of what "all the factors" asks.

## Decision

1. **A list is one answer** (`Response.kind` `list`), its key its members in any order ("1, 2, 3, 4, 6, 12"; a pair
   "1 × 24", either way round). Marking compares it as a whole (`multiples.judge`, from `marking._not_one_number`):
   right when it holds every member once, else one wrong answer naming each thing it shows — a member left out (one
   code however many), and each number beyond the key for what it is by the question's own numbers (a multiple written
   for a factor, a number that does not divide, past the limit, a multiple of one number only, a pair turned round and
   written twice). One answer, one piece of evidence, its mistakes counting against multiples and factors.
2. **It prints as groups of boxes, two more than it holds**, each with room for its widest number, beside the words
   "You may not need every space" (`straight_pages.multiples`): `list#3` for the third number, `list#3.1` and
   `list#3.2` for a pair's two either side of ×. The count of boxes does not give the answer's size away.
3. **The reader reads each group as it reads any number and joins them** (`w3_read/lists.py`): the same ink, floor and
   doubt rules per group, the empty groups left out, the members in the order written. One group doubted, a group's
   print not found, or a pair with one number written makes the whole list a person's, what was read the guess. A
   list is read, not handed over: `lists.READ` is the kinds read in their boxes, digits and lists.
4. **No group's crop is kept for the reader to learn from.** What a person types for a list is the whole list, not
   the number in any one group, so it labels no one crop (`crops`).
5. **Every yes-or-no is right one way as often as the other in each place it is asked** — a multiple or not, each of
   divisible by 2, 5 and 10, divisible by 3 — and a wrong tick names what it shows where the question's numbers say
   so: the last-digit rule used where it does not work (is 34 a multiple of 4?), the first digit read for the last
   (805), divisible by 5 taken for 10 (345). Otherwise it names the claim reversed.
6. **The scenario check works out every list and tick from the question's sentence** (`checks/multiples.py`): the
   numbers in its words, never the spec the code stored with it; a digit sum is its box's own sentence.

## Rejected

- **A box per member, keyed smallest first** (option (a) in the measurement): one omission shifts every box after it.
- **A box per member keyed by membership** (option (b)): one omission becomes one blank, but a member written twice
  counts twice unless a rule reads across an answer's boxes, which no path that marks one box at a time (a person's
  check, a re-mark) can see.
- **The list typed by a person every time:** the reader reads numbers in boxes well enough to be trusted per kind
  (ADR 0032); a list is several of those, and its trust is earned the same way, per kind.

## Consequences

- Factor pairs are asked of numbers up to 100: up to 60 only 17 numbers have three to five pairs with one from the
  tables, too few for a level to hold 24 different questions. All the factors stay up to 60, four to eight of them.
- `render_item` draws the kinds drawn whole (an equation, a claim to explain, multiples) through one table
  (`straight_pages.PAGES`): its complexity fell (C901 19 → 18, PLR0915 56 → 54) and is written down.
