# W3 gate 1 — every paper, entered

Rebuilt 2026-09-20 after the whole corpus was entered and read. No child is named here: names live
in `pii` and in the manifest outside git (CLAUDE.md rule 6). Counts only.

## Why this file exists

To read a used paper, the paper must first exist as a `sheet_template` with **one answer slot per
answer on the page** — not one per printed question. `legacy.import_scan` looks up every answer by
`n`+`part`; anything with no slot is dropped. A paper entered with too few slots silently loses
answers on every child who sat it, which is not hypothetical: `G2-CAM-A` was entered with 24 slots
for a 27-answer page, and `G2-WORD-SEP17` was entered with one page of a two-page paper, so four
answers per child were lost on every import until 2026-09-20.

## The corpus, counted from disk

- **84 files, 194 pages, 16 children.**
- **In scope: 71 files, 108 pages.** Excluded: 8 SOF Olympiad booklets (76 pages — multiple choice,
  excluded from W3's bar by `goals/w3-read-and-graph.yaml`) and 5 typed Grade 3 reports (10 pages —
  they are the gold, not the input).
- **49 sittings.** `manifest.md` says 37 and an earlier count here said 52; both are wrong.
  One file it lists as a Week 2 paper is a 10-page Olympiad booklet, so that child has no Week 2
  paper at all.

## The papers

`slots` is what the database holds. Every row was checked against a printed page on 2026-09-20.

| # | paper | code | children | slots | pages |
|---|---|---|---|---|---|
| 1 | G2 Cambridge U3 — Level A | `G2-CAM-A` | 4 | 27 | 2 |
| 2 | G2 Cambridge U3 — Level B | `G2-CAM-B` | 4 | 24 | 2 |
| 3 | G2 Cambridge U3 — Level C | `G2-CAM-C` | 1 | 20 | 2 |
| 4 | G2 Cambridge U3 — Level D | `G2-CAM-D` | 1 | 20 | 2 |
| 5 | G2 September Week 2 · Set 1 | `G2-SEPW2-S1` | 6 | 12 | 2 |
| 6 | G2 September Week 2 · Set 2 | `G2-SEPW2-S2` | 1 | 10 | 2 |
| 7 | G2 September Week 2 · Set 3 | `G2-SEPW2-S3` | 1 | 8 | 2 |
| 8 | G2 Word Problems 17-Sep | `G2-WORD-SEP17` | 6 | 10 | 2 |
| 9 | G2 Mathematics Assessment, Set B | `G2-DIAG-B` | 6 | 15 | 3 |
| 10 | G3 baseline diagnostic (16 q) | `G3-BASE16` | 5 | 18 | 2 |
| 11 | G3–4 Mathematics Quiz (20 q) | `G3-QUIZ20` | 5 | 20 | 2 |
| 12 | G3 September Week 1 — Level A | `G3-SEPW1-A` | 2 | 40 | 3 |
| 13 | G3 September Week 1 — Level B | `G3-SEPW1-B` | 1 | 30 | 2 |
| 14 | G3 September Week 2 | `G3-SEPW2` | 4 | 9 | 2 |
| 15 | G4 September Week 1 | `G4-SEPW1` | 1 | 40 | 3 |
| 16 | G4 September Week 2 | `G4-SEPW2` | 1 | 9 | 2 |
| — | SOF Olympiad (2 forms, 8 booklets) | — | 7 | — | 76 |

**16 of 16 entered.** The Olympiad is multiple choice: its own floor is set once there is a
measurement to set it from, and it is not read here.

## What entering them settled

1. **The Cambridge paper runs at four levels and September Week 2 at three sets.** Ten children sat
   four different Cambridge forms and eight sat three different Week 2 sets; only one of each was
   in the database.
2. **The eighteen loose Grade 2 photographs are a paper of their own** — a 15-question diagnostic,
   three pages per child, six children — not extra pages of something else.
3. **Each Grade 3 child's four photographs are two papers of two pages**, not one paper of four.
   `8500 − 3647 = 5147` is question 5 of the second one, not of the baseline.
4. **Nothing was attributed by file name.** The level band, the set number and which photograph is
   which page were all read off the page. One child's four Grade 3 photographs are in a different
   order from every other child's, so a name-based guess would have mis-filed two of them.

## How a paper gets entered

Engine prepares, person approves: the engine reads the page and proposes one slot per answer, a
person confirms or edits. The slot count is what must be right — a paper whose slot count does not
match its page is the defect this file exists to prevent.
