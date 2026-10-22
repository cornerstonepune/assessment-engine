# CK1: the picture is the question

W3 (read) and the check screen. Goal: `goals/ck1-the-picture-is-the-question.yaml`. Branch
`claude/ck1-the-picture-is-the-question`. Builds beside PR #270 (R2), which it does not duplicate: R2 stops a printed
page that cannot be lined up from being read by its words; this stops a reading by words from carrying a box at all, and
stops the screen trusting a box that is not a question's own.

## Measured on live, before the code (2026-10-22)

Command: `.github/measure/box_is_question.py`, run inside `.github/workflows/engine-logs.yml` on this branch (run 34,
read only: counts, question numbers and pages; no name, no image). Answers waiting for a person: 65, on 12 pages, all on
Home assessment papers (no class assessment is waiting).

| what the picture shows for the answer | answers |
|---|---|
| no box stored: the whole page | 29 |
| a box another question of the same page also has (one box for 3 questions: 1 time; for 2: 2 times) | 5 |
| a box nearer another question's printed place than its own | 6 |
| not checkable: fewer than 3 boxes on the page to lay over the printed layout | 13 |
| a box verified as its own question's | 12 |

- The 6 wrong boxes are neighbours, not a shift: Q2 shows Q1 (twice) and Q3, Q7 shows Q2, Q3 shows Q5, Q5 shows Q4.
- Not a page offset: for no answer did the stored page differ from the page the printed layout puts that question on,
  nor the copy's file page from the paper's page.
- Cause: the page was read by the words printed above each answer (`stencil.read_page`), which finds a region, not the
  question; where a question's words are not found (a ring of dots has none) the field left over went to several, and a
  region could land on the next question's. The box it stored was shown as "the part of the page the answer was read
  from". The box reader (`boxes.read_page`) cuts each answer from that question's own printed cells and stores `boxes`
  with its box; R1's test already proves those are unique and each its own (`tests/test_lineup.py`).
- Not measured: the exact path that showed Q11 for Q8 on Nimish's screen (the picture cannot leave the school's disk).
  The rule below makes it impossible whichever it was: a box that is not cut from the question's own printed boxes is
  never shown.

## What changed

- `stencil.read_page` (the reading by words) no longer returns a box. Its readings are unchanged. Cost, named: the
  second opinion (ADR 0091) crops by a reading's box, so a paper entered by hand, which is read by words, no longer gets
  one.
- `lib/own-box.ts`: one rule for the three queries that give a screen a box: shown only where the reading was cut from
  the question's own printed boxes (`raw_read.boxes`) and no other question of the same page has the same box. Rows
  read before this are covered without a change to them (append-only); a person's checks stay as they are.
- `/capture/check`: the heading names the question and its printed words. A trustworthy box shows its crop (up to 560 px
  tall, the column wide). Otherwise the page shows whole, the column wide, and a click opens it to its full size to
  scroll about in, under "We could not find question N on this page: it is somewhere on this page."

## Verified

- Fail first: `cd apps/web && npx playwright test --project=steps u50-the-picture-is-the-question` on the screen and
  queries as they were: 5 of 6 failed (the own-box case passes either way), and the screenshot of question 2 shows
  "11 How many dots are there in all?" under "the part of the page the answer was read from". The words-reader test
  `tests/test_stencil.py::test_a_page_read_by_its_words_stores_no_box` failed before `stencil.py` changed.
- After: the same spec, `6 passed`. `s4-validation-queue` and the u50 spec together, `23 passed` (the first s4 test found
  the picture by its alt text, which the whole-page version had changed; both now say "What <child> wrote for question N").
- `bin/engine done ck1-the-picture-is-the-question`, 2026-10-22, on a database built by `bin/testdb fresh`: all five of
  Nimish's sentences PROVED; the reader's files `test_stencil test_second_reader test_legacy test_lineup test_boxes` → 119
  passed; the spec → 6 passed; `bin/check` → 30 passed. NOT DONE only for: not on main, the live database unreachable from
  here, and the manual check after deploy.
- Screenshots, seeded test data only (a page the test draws itself; no child's name, no scan): `docs/notes/ck1-the-picture-is-the-question/`,
  `before-words-region-q2.png` and `after-words-region-q2.png` are the reported bug and its fix; `after-shared-box-q8.png`,
  `after-own-box-q4.png`, `after-whole-page-q3.png` the other cases. (The sandbox needed the browser build the repo's
  Playwright asks for linked to the one installed; nothing in the repository changed for it.)

## Handoff

- Live: nothing yet; reaches live when Nimish merges and it deploys.
- After deploy, the waiting answers of the 22 Oct file show the whole page with the plain line until the file is read
  again (R1b, blocked on the file being in Drive, `docs/notes/r2-unaligned-page-to-a-person.md`).
