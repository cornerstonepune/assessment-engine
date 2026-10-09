# ADR 0049 — A case is a case of its own taxonomy, written in tags code measures

**Status:** accepted (2026-10-09, slice M1 of BUILD-ORDER "Inserted now: multiplication and division")
Goal: goals/md1-taxonomy-rows.yaml

## What happened

M1 makes the 247 multiplication and division cases rows the bank is counted against, as the 270 addition and
subtraction cases are. Measuring before the build found three things the second document breaks:

- 54 of the 270 addition and subtraction cases name no operation. R06 is any `odd_even` question, E01 any equation
  whose sign is missing, W01 any story of joining. They were written when + and − were the only operations, so "no
  operation" meant "+ or −". The first × odd-or-even question would have counted as R06.
- `case_dimension` was the document's §12 matrix, copied in and read by nothing. The 270 cases are written in 22 tags
  it does not name (`planted`, `structure`, `regroup_at`, `knock_on` …), and its `word_structure` values were never
  measured by anything.
- The drafted document had two cases that are one: D03 (2 ÷ 1 digits, one exchange from the tens) and D04 (the same,
  "the answer past the tables"). Every 2-digit by 1-digit division with an exchange from the tens goes past the tables.

## Decision

1. **A case is first a case of its taxonomy.** Every row names its document (`taxonomy_case.taxonomy`, ADD_SUB or
   MUL_DIV), and so does every alternative of its match. A question's `taxonomy` tag is read from its own operations
   (`skills.operations`, the one owner of them): MUL_DIV when any of them is × or ÷. So a × odd-or-even question is
   never R06, and a story that multiplies and then adds is multiplication's.
2. **The dimension rows are the vocabulary every case is written in.** `case_dimension` holds each tag a case of
   either document reads, with the values it may take and why it matters (67 rows). A test fails on a case that reads
   a tag no row names, or a value its row does not allow. `word_structure` is gone; `structure` is the tag every story
   case reads. The loader removes a dimension the seed no longer names.
3. **A case's match is measured, never typed.** `research/md_rows.py` gives each case an example and the list of tags
   it is about. Its match is what `tags.derive` reads those tags to be on that example, so it can only say what code
   measures.
4. **Two cases are one when they hold the same questions.** The test reads every straight × and ÷ question a paper
   prints up to four digits, in a line and in columns (about 100,000), and no two cases may hold the same set. That is
   what found D03 and D04. D03 is now by 2, 3, 4 or 5 and D04 by 6, 7, 8 or 9; `divisor_group` measures it.

## Rejected

- **Adding `operation: [ADD, SUB]` to the 54 cases.** Equations and two-step stories carry no single operation, so
  each of those cases would stop holding its own questions.
- **A "not × or ÷" condition in the matcher.** It is new grammar for one use, and it still leaves the question
  without a statement of which document it belongs to.
- **Judging duplicates by examples alone** (each case holds the other's example). Two cases about different things,
  a method and a carry pattern, may hold each other's examples and still be two cases: G11 (compact columns) and T07
  (a carry from the ones, the answer grows) both hold 34 × 6 in columns. Comparing the questions each holds tells a
  duplicate from an overlap.

## Consequences

- Every stored question's tags change once, adding `taxonomy`. `engine bank relabel` writes them, and `bin/update-live`
  runs it straight after `engine load`, before anything reads a case. Locally: 21,289 tags changed. The cases changed
  on 912 questions, the 864 of `MUL.1D` and the 48 of `MUL.GROUPS`. No addition or subtraction question's cases changed.
- Refill now judges `MUL.1D`'s questions by their declared digits, since × questions carry `operand_1_digits`. On the
  local copy all 864 fit, so none is retired. The rehearsal on a copy of live says the same or names them.
- The deploy checks that live has every migration its commit carries before the engine starts, so the code that
  reads `taxonomy_case.taxonomy` never runs before the column exists.
- Kinds that do not exist yet (grid, lattice, short division, stories that share) are cases now: M2 to M4 build them
  to state the method, shape or structure their case reads.
