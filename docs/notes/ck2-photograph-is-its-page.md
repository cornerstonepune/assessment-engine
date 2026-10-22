# CK2: a photograph is the page it prints

W3 (read), the check screen's picture. Goal: `goals/ck2-photograph-is-its-page.yaml`. Branch
`claude/ck2-photograph-is-its-page`, from `claude/ck1-the-picture-is-the-question` (PR #276) with main merged in. Builds
beside PR #270 (R2), which it does not duplicate: R2 sends a page that cannot be lined up whole to a person; this decides
which paper page a photograph is before anything is lined up against it.

## Measured on live, before the code (2026-10-22)

Command: `.github/measure/photo_is_page.py`, run inside `.github/workflows/engine-logs.yml` on this branch (run 35, read
only: tile counts and page numbers, no name, no image). The 22 Oct Grade 1 file, 20 pages, 10 copies of a two-page paper.
Tiles of print found when a photograph is laid on each printed page (page 1 has 149 tiles, page 2 has 72):

| copy | photo 1 (page 1 / page 2) | photo 2 (page 1 / page 2) | the photographs are |
|---|---|---|---|
| 1, 2, 5, 6, 9, 10 | 143–147 / 21–51 | 19–50 / 60–70 | page 1, page 2 (in order) |
| 3 | 20 / 69 | 147 / 50 | page 2, page 1 (swapped) |
| 4 | 17 / 69 | 143 / 50 | page 2, page 1 (swapped) |
| 7 | 21 / 66 | 147 / 50 | page 2, page 1 (swapped) |
| 8 | 19 / 69 | 146 / 20 | page 2, page 1 (swapped) |

- The person's reading of the file (paper page 1 at PDF pages 1, 3, 6, 8, 9, 11, 14, 16, 17, 19) is exactly what the
  engine's own fit says: four swapped copies, six in order. `boxes._fits` (layout times own print) gives 0.57–0.88 for the
  right page and 0.00–0.04 for the other, on all 20 photographs, so a clear margin exists on live.
- The printed pages say no number in words (`printed page says its number: [False, False]`) and the QR is the same on both
  pages of a copy, so the print is all that tells them apart.
- How the engine derived the page: `boxes._placing` returned `1…k` in file order, unmeasured, whenever a copy had as many
  photographs as the paper has pages (`if k >= n`), and its test said so ("a whole copy is its pages in order and nothing
  is measured"). Question 10 (page 2) was then looked for in the first page's photograph and the check screen showed that
  photograph, with the line "Page 2, as it was photographed".
- Reconciled with CK1 ("not a page offset", `ck1-the-picture-is-the-question.md`): CK1 compared the stored page with the
  page the printed layout puts the question on, and the file page with the paper page, both of which came from the same
  file-order assumption, so they agreed with each other. It never looked at what the photograph contained. Both findings
  stand; they measure different things.

## What changed

- `w3_read/placing.py` (split out of `boxes.py`, which went over its ceiling): each photograph is laid on every page it
  could be, and for a copy of the whole paper the file's order stands unless another order fits `read.page_margin` (1.25) times
  better than it (CI found that a clean six-page paper, whose pages share a layout, was otherwise skipped as "could not be
  told apart"); for a copy of part of a paper, the way of laying them on distinct pages that fits best stands if it fits that
  much better than the next best. The next best is exact: the best with each of the best's pairs forbidden in turn (dynamic over
  the pages used, no n!). A photograph that lines up with neither page is the page the other leaves; no photograph lining up
  with any page keeps the file's order and each page goes whole to a person (R2). More photographs than pages, or a paper of
  one page, are not measured, as before.
- `POST /read/run/{run_id}/again`, `engine read file-again <name>`, and a "Read again" button on each finished scan on
  Marking (`readAgain`). A run of its own is started and the file read with `again`: every copy no person has worked on is
  read anew and its old capture superseded (`superseded_by`, never edited, rule 4), a copy a person has worked on is read
  into the same capture and only the answers nobody checked take the new reading (`checked.UNTOUCHED`), so a person's
  checks stay. Not while the file is being read, and only while the inbox still keeps it.
- The check screen needed no change: it shows `raw_read.file_page`, which `copies` now sets from the placed page.

## Verified

- Fail first, on the unfixed `boxes._placing`: `tests/test_photograph_page.py`, 6 of 10 failed, among them the template's own
  render in the order (2, 1) and a desk photograph beside a page.
- After: `tests/test_photograph_page.py tests/test_boxes.py` → 33 passed; route and refusal tests pass; `bin/check` → 30 passed.
  The end-to-end `tests/test_copies.py::test_a_copy_photographed_second_page_first_...` and the screen spec
  `apps/web/tests/u51-read-an-uploaded-file-again.spec.ts` need the test database and the web build, which this sandbox
  has not: CI is their first run.
- Cost, named: a copy with as many photographs as pages is now measured, n² fits per copy (4 for a two-page paper; the live measure took about 6 s a photograph for the
  tiles and fits on both pages) where it was none.
- Flake, found and fixed (2026-10-22; PRs 285 and 288 red on shard 6). `test_copies.py` built its paper from the first twelve
  word problems of the bank, and the bank is a fresh random draw on every database (CI builds one per runner). In some
  draws the true placement of a copy missing its first page beat the next laying by 1.21, under `read.page_margin` 1.25:
  `placing.placed` returned None, `copies.read` rightly skipped the copy (it goes whole to a person, R2), and a skipped
  entry has no `capture_id`: `KeyError`. Reproduced: 1 draw in 33 of random twelves (ratio 1.21; the rest 1.28–1.50).
  The code is right, the test's paper was not fixed. The paper is now twelve stories made from `random.Random(7)`.

## Handoff

- Live: nothing yet; reaches live when Nimish merges and it deploys.
- Next, once live: Read again on the 22 Oct file ONCE (Marking → the scan → Read again), then the engine-logs measure:
  copies in order and swapped, answers found of 120, answers agreeing with the key on copies 3, 4, 7, 8 (Q1 8, Q2 18, Q3 6,
  Q4 12, Q5 12, Q6 6, Q7 4, Q8 10 | Q9 10, Q10 9, Q11 6, Q12 12). Answers already read stay as they are until then: the
  65 waiting still show the first page under "question 10" on the four swapped copies.
- Open: a photograph that lines up with no page and cannot be had by elimination (both photographs unreadable) keeps the
  file's order; the check screen then shows the photograph the person took, which may be the other page. That needs a
  person, and the screen says it could not find the question.
