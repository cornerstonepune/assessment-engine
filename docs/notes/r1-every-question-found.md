# R1: every printed question found, each answer in its own box

W3 (read). Goal: `goals/r1-every-question-found.yaml`. Branch `claude/r1-every-question-found`.

## Measured on live, before the code (2026-10-22)

The Grade 1 file "Equal groups (repeated addition)", 20 pages, 10 copies x 12 answers, read on Marking that morning.
Command: `.github/measure/scan_vs_eye.py`, run inside `.github/workflows/engine-logs.yml` on this branch (runs 28–30,
read only: codes, question numbers, counts and image sizes; no name, no image).

| | every one of the 20 pages |
|---|---|
| reader's note | "did not line up with the paper it printed from" |
| child's printed PDF kept | yes (10 of 10) |
| the scan page | one picture, 1080 x 2399 px (a phone in portrait), covering 57.5% of an A4 page |
| ORB features agreeing on a map | 113 and 130 (copy 1); 16 and 55 (copy 4) |
| that map, the photograph's corners | 2.4–3.0 printed pages of area: refused (the check allowed 0.5–2) |
| tiles of print found | 0 of 149 (page 1), 0 of 72 (page 2) |

- So every page fell to the reader by words (`ocr.answers_for`), which finds a question by its printed words. A ring of
  dots has none: 49 of 120 answers "the printed question was not found on the page", and where several questions'
  words were not found the field left over went to all of them (copy 3, one box to Q1, Q7 and Q8).
- Cause: `stencil.plausible` asked the whole photograph to land on about one page. True of a scan app's crop; not of a
  phone's picture with the desk above and below the paper, laid on an A4 page with white beside it.

## Verified

- A phone's picture laid on an A4 page as on live lines up, both pages of the Grade 1 paper; every question of it is
  found where the test put its boxes, each in its own; a picture with no paper in it still does not line up.
  `cd packages/engine && uv run pytest -q tests/test_lineup.py` → 13 passed. Without the change to `lineup.py`, 4 of
  them fail (the 2 line-ups and the 2 pages' questions).
- The reader's other files: `uv run pytest -q tests/test_boxes.py tests/test_stencil.py tests/test_sorting.py
  tests/test_copies.py tests/test_legacy.py tests/test_inbox.py tests/test_crops.py tests/test_ink_line.py
  tests/test_second_reader.py` → see the PR for the run with a database.

## Handoff

- Live: nothing yet; the change reaches live when Nimish merges and it deploys.
- Next, with Nimish's approval: read the 2026-10-22 file again through the read-again path, then the measure above:
  how many of 120 are found in their boxes, and how many agree with the person's reading (key Q1 8, Q2 18, Q3 6,
  Q4 12, Q5 12, Q6 6, Q7 4, Q8 10 | Q9 10, Q10 9, Q11 6, Q12 12).
- Open: the digits on those pages are read from a picture of about 5 pixels a millimetre (1080 px across the paper).
  Whether the digit reader reads them as well as it reads a scan app's page is measured only by that re-read.
- Open, not changed here: a page of a printed paper that does not line up is still read by its words, which on a page
  of pictures hands one field to several questions. Whether such a page should go to a person whole instead is
  Nimish's call.
