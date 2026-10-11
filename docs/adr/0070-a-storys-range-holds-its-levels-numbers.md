# ADR 0070 — A story's range holds its level's numbers

**Status:** accepted (2026-10-11, slice M4d2a of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md4d2a-story-ranges.yaml

## What happened

Assumption A9 (docs/design/multiplication-division-taxonomy.md): "Each story template carries the range its numbers may
take, so no box holds 933 pencils." Measured before the build (STATE.md "M4d2 — measured before the build"): 74 of the
76 older templates said no range and took their sizes from the level alone. The bank held "has 9685 marbles", 93 × 96
combinations of stickers and backgrounds, rows of 98 chairs, 3442 mangoes put in a basket. Grade 4's additions and
subtractions run to four digits, and none of the older stories' worlds (a child's marbles, a bus's seats) holds a
number in the thousands.

## Decision

1. **Each older template says its range** (`range`: each number's [lo, hi]), the bounds of the world the story is in:
   a bus's seats to 60, a box of pencils to 24, a rickshaw holds six, a library's books to 9999. A story that sets its
   own numbers keeps `numbers` (ADR 0068); a question of numbers alone (`bare_sum`) has no story to fit.
2. **The level still sizes the numbers, and the story must hold them** (`words.fitting`): the older makers draw a
   template and the level's numbers as before; where the template's world does not hold them, another template of the
   same shape and operation that does is drawn instead; where none does, the numbers are drawn again, as a maker already
   says when its numbers do not make a story. A level whose stories all hold its numbers draws exactly as it did.
3. **Twelve stories whose numbers run to four digits** — a library, a mela's visitors, a stadium, a school's fund, a
   day's steps, a fair, a toy factory, a shop's notebooks, a train's passengers, a park's flowers — one or more for each
   shape Grade 4's additions and subtractions draw.
4. **A stored story outside its range is outside its level** (`cases.outside_their_level`, `words.range_problems`): the
   bank's refill retires it and draws its replacement.

## Rejected

- **Drawing each number from the template's range** in place of the level's sizes. The level's rule decides what a
  question asks (its digits, its regrouping, its case); a story drawn from its range alone would leave its level. The
  range bounds the level's numbers; it does not replace them.
- **Clamping a drawn number into the range.** A clamped number is not the level's: 3442 mangoes clamped to 100 is a
  2-digit question on a 4-digit level.

## Consequences

- The ranges are the engine's draft of each story's world; Achal corrects any in `word_templates.json`, the file the
  school edits, and the tests hold every level to whatever it says.
- The bank's stories drawn before this keep their numbers until `bin/update-live` runs the refill, which retires them.
