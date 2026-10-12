# ADR 0071 — The story reader chooses a case, and code works what is left over

**Status:** accepted (2026-10-12, slice M4d2b1 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md4d2b1-times-story-shape.yaml

## What happened

`story_shape` (ADR 0036, goals/j3-story-shape.yaml) places a story typed by an educator: Jev chooses its shape, code does
the rest. v1 offered the 18 shapes of the + and − story cases, keyed by shape. Measured before the build (STATE.md
"M4d2b — measured before the build"): the taxonomy holds 27 × and ÷ story cases, and a shape does not name them. Five
are one shape, GROUPING, told apart by what the story does with what is left over (exact, B03; dropped, B14; rounded up,
B15; asked for, B16; both, B17); three shapes are each two cases (ARRAY × and ÷, B04 and B05; a price and a price list,
B06 and B26; a number the story does not need, + and − or ×, W25 and B25).

## Decision

1. **Jev chooses a case.** Each story case of the taxonomies a version reads is one option, under its shape's name, or,
   where cases share a shape, its shape and the first of what sets them apart (what is left over, the operation, a
   price list, the taxonomy): GROUPING_ROUND_UP, ARRAY_DIV, RATE_TOTAL_TABLE_OR_CHART, EXTRA_INFORMATION_MUL. The names
   are worked from the case rows, so a case added to the taxonomy is offered without code.
2. **The version's row says what it reads** (`json_schema.taxonomies`). v1's row says nothing and reads + and − alone,
   shown exactly the words it was scored on; v2 reads both. A version is scored before it answers (rule 7), so v2 is
   built switched off and `engine eval story_shape --version 2` scores it on the server.
3. **Code works the answer and what is left over** (`divide_stories.answered`, the rule the story maker's boxes use):
   the full boxes, one more rickshaw for those left, the remainder, or both, beside the answer.
4. **Code holds the choice to the numbers.** A case that says nothing is left over, read for numbers that leave some, is
   a person's: what the story does with them is the story's words, and Jev did not read them as a remainder. A
   remainder dropped or rounded up, read for numbers that leave nothing, is exact grouping: nothing is over, so the
   story is the Easy case, not the Hard one.
5. **The gold names a case** and carries three stories for each × and ÷ case; the eval scores the gold of the taxonomies
   the version reads, so v1 is still held to its 65.

## Rejected

- **Two questions to Jev: the shape, then what is done with the remainder.** Two calls per story, and the second only
  for one shape; one choice among 45 options is within Jev's 255 and its eval will say whether it reads them.
- **Case codes as option names (B14).** A name that says nothing leaves all the meaning to the description; the
  taxonomy's own words (GROUPING_ROUND_UP) say it twice.
- **Changing v1's options in place.** v1 is scored on what it is shown; a new option set is a new version.

## Consequences

- Live answers with v1 until v2's score is recorded in DECISIONS-LOG and becomes the bar (M4d2b2).
- A two-step × and ÷ story is placed but not keyed: which numbers its steps take is in its words, and code does not
  guess them, as for + and −.
