# ADR 0062 — A model of division is a kind or a shape of its own, and counts for division alone

**Status:** accepted (2026-10-10, slice M3c of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md3c-division-models.yaml

## What happened

`DIV.GROUPS` (Grade 2) lists nine cases of the drafted taxonomy:
- dots shared into rings (G15) and ringed in groups (G16);
- a number taken away again and again to 0 (G17);
- jumps back on a number line (G18);
- an array divided (G19);
- stories of sharing, grouping, an array and "each" (B02, B03, B05, B24).

Measured before the build (STATE.md "M3c — measured before the build"), none drew:
- `equal_groups` made a × picture whatever its case asked, which the case refused, without a word;
- repeated subtraction, filed by the draft as a `bare_sum`, printed as a straight division (ADR 0054's defect);
- the number line handed ÷ to its + and − jumps and stopped on a `KeyError`;
- no ÷ story template had the four stories' shapes.

Three more were found with them:
- `skills.by_kind` gives every equal-groups question multiplication and addition, so a sharing picture answered right
  would have counted for both;
- nothing bounded a story's numbers, which a model skill may not bound by `within` (ADR 0054);
- the story path that checks a sentence on its way in (`verify.to_item`) named a division's other operation `a + b`,
  where the ÷ row says "multiplied".

## Decision

1. **Division's models are made from the level's `groups` and `size`** (`assess/divide_models.py`), as
   multiplication's are. The number divided is their product, and the divisor is the number the question gives. So
   every question is the exact division `a ÷ b`, and its tags, its key and the scenarios' check read it as one.
2. **Equal groups divide by their case's method.**
   - SHARING: the dots loose and the rings empty; the rings are the divisor.
   - GROUPING: the dots loose and no ring; the group's size is the divisor.
   - ARRAY: in all ÷ rows = in each row, three labelled boxes, as G05's array is read.

   Asked for an operation other than × or ÷, equal groups refuse in a sentence. The operation is chosen where kinds
   are wired (`bands._groups`).
3. **The number line is one kind drawn three ways:** ÷ as jumps back to 0. There is a mark at every number and no
   jump is drawn, for the child draws them.
4. **Repeated subtraction is a kind of its own** (`repeated_subtraction`), printed whole from its numbers. Its
   taxonomy row is corrected where it was drafted (`research/md_rows.py`) and written again.
5. **Three new mistakes, each a row**, drafted for Achal:
   - `M_DIV_ALL_COUNTED`: counts them all;
   - `M_DIV_GROUPS_FOR_SIZE`: writes the number the question gives for the one it asks;
   - `M_DIV_START_COUNTED`: counts the start as a jump.

   The kinds name these beside multiplying (`M_WRONG_OP`) and one group taken away (`M_DIV_SUBTRACTED`), each where
   its act can happen.
6. **A kind's own skills may differ by operation** (`skills.by_kind`, `skills.kind_skills`). Equal groups that
   multiply use multiplication and addition (Grade 1's groups added again). Equal groups that divide use division
   alone.
7. **The four stories divide a table to 10 read backwards.** Their rows say so (`fact`, `fact_group`), as every one of
   their examples does.
8. **A story template names the mistake its other operation is** (`wrong_op_as`, which was `added`).
   - "5 for each child" multiplied is `M_KEYWORD_OVERGENERALISED`, with a ÷ row of its own; the "any" row's hint is
     about subtraction.
   - The predictors own a story's other operation for every operation (`misconceptions.predict`): `verify.to_item` no
     longer writes `a + b` over a division's `a × b`.

## Rejected

- **Repeated subtraction as a `bare_sum` printed by its method.** Every reader of `bare_sum` would carry the exception
  (ADR 0054).
- **Division's pictures inside `counting.equal_groups`.** `divide_models` reads `counting.named`, so the choice would be
  an import cycle hidden in a function.
- **`within` on `DIV.GROUPS`.** Placing would hold 12 ÷ 3 in it and in `DIV.FACTS`, two skills for one question
  (ADR 0054).
- **A cap on the number divided, read by the division drawer.** It would be one more way of saying a level's numbers,
  when the cases' own examples already say they are table facts.
- **Drawing again where the number given is the answer** (9 dots into 3 rings). `MUL.MODELS` keeps its squares, and
  their other mistakes still show.

## Consequences

- An equal-groups question that multiplies keeps the skills it had. One that divides counts for division alone.
- A + or − story checked on its way in no longer names its other operation where a 0 or a 1 makes that the right
  answer, or another mistake's.
- `question.tsx` was at 382 of 400 lines. The website's drawn kinds moved to `pictures.tsx` (`Drawn`), where the
  engine's `pictures.py` keeps the paper's.
- `MD.WORD` (M4) holds B02, B03 and B05 too, so its stories of those shapes will be table facts.
