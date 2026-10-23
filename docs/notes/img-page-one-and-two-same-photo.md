# IMG: a paper's page 2 is never page 1 drawn again

W3 (read), R2's rule ("a page that cannot be lined up goes whole to a person") extended to a page that is another page
again. Goal: `goals/img_page_one_and_two_same_photo.yaml`. Branch `claude/img-page-one-and-two-same-photo`, from main at
284b61d. Not touched: the duplicate listing (DUP), `capture/check`, `capture/[id]/card.tsx` (CHK).

## Root cause (reproduced on synthetic pages, 2026-10-23)

1. `placing._best` lays a copy's photographs on DISTINCT pages whatever they fit. A file whose second photograph is page 1
   again, measured with the Grade 1 template: photo 2 fits page 1 at 0.811 and page 2 at 0.000, and `placing.placed`
   returned `[1, 2]` (also `(2, 2)` → `[1, 2]`). So page 1's photograph was stored as page 2.
2. The reader then reads page 2's questions in page 2's boxes on page 1's pixels (on a seeded copy: "p2: 3 answers read,
   3 for a person; read in its boxes", all blank). Which answers: every answer of the repeated page's slot (Q9–12 on the
   Grade 1 paper). None settles alone (ADR 0029: a blank or wrong waits for a person), but the person is shown page 1
   under "Question 10", and a blank signed off there is wrong evidence.
3. `legacy.page_crop` answers a page past the file's end with the file's last page (by design for a single photograph),
   so a file with no page 2 also draws page 1 as page 2.
Not the cause: the same file path reused (the cut is named by copy, first page and code), `_best` giving one page to two
photographs (it cannot), Read again (it re-runs the same placing), the panel (it draws what `file_page` says).
Not established: whether the 22 Oct file really holds page 1 twice. CK2's live measure found a distinct page on all 20
photographs, so that copy's screen may instead be a reading made before CK2 deployed. Both are covered.

## What changed

- `placing.place` (new): a photograph that clearly is a page (fits it `read.page_margin` times better than any other)
  that an earlier photograph clearly is already is refused; the rest are placed as before. Ties keep the earlier one.
- `copies._placing` returns `Where(read, placed, twice, refused)`; a refused photograph is not stored in the copy's file.
  Pages the file then lacks go whole to a person (`reading._not_found`): answers `not_found`, `page_found: false`, why
  "page 2 not found: no photograph of it is in the file"; `lacks` says "page 2 of the file is page 1 again".
- `same_page.py` (new): `fingerprint` (hash of a page's pixels), `repeats`, `pages_of` → `GET /capture/{id}/pages`.
  Works on readings already stored, so no evidence row is edited.
- `capture/[id]/page.tsx`: "The whole page" prints "Page 2 not found. …" instead of a photograph for such a page.

## Verified

Filled in at the commit boundary below.

## Handoff

- Live: nothing until merged and deployed. Then Read again on the 22 Oct file once; copies whose answers a person already
  checked keep their checks but may have been checked against page 1's picture: look at the ones that now say "Page 2 not found".
- Cost: a refusal is only possible where the copy is measured (as CK2 does); false refusal sends a page to a person.
