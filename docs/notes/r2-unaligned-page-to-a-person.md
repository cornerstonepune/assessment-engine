# R2: a printed page that cannot be lined up goes whole to a person

W3 (read). Goal: `goals/r2-unaligned-page-to-a-person.yaml`. Branch `claude/r2-unaligned-page-to-a-person`.

## Why

On 2026-10-22 every page of the Grade 1 file "Equal groups (repeated addition)" failed to line up and fell to the reader
by words (`ocr.answers_for`). A ring of dots prints no words: 49 of 120 answers "not found", and where several
questions' words were missing the field left over went to all of them (copy 3, one box to Q1, Q7 and Q8;
`docs/notes/r1-every-question-found.md`, "Measured on live, before the code"). Nimish approved on 2026-10-22: such a
page goes whole to a person.

## What changed

- `reading.read_pages`: a page of a paper this system printed (its boxes recorded) whose boxes are not found is read
  by nobody. Every answer on it waits for a person, with no reading and no guess; a number says "the page did not
  line up with the paper it printed from", a tick or a reason stays a person's as before. Marking shows the whole
  page, since no answer has a box.
- A paper entered by hand, which records no boxes, is still read by its words, unchanged.
- `_by_region` lost the two branches only a printed page ever reached; the test that asserted the old behaviour on a
  printed page is replaced by the two below.

## Verified

- `cd packages/engine && uv run pytest -q -p no:cacheprovider tests/test_each_answer.py -k "whole_to_a_person or by_hand"`
  before the fix: `1 failed, 1 passed` ("a printed page is never read by its words": it was). After: `2 passed`.
- Goal criteria: see "engine done" under Handoff once run.

## Handoff

- Live: nothing yet; reaches live when Nimish merges and it deploys.
- Next: R1b's re-read, which waits on a Drive link to the file (see the R1b note).
