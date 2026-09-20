# W3 gate 1 — every paper that must be entered before anything can be read

Built 2026-09-20 by counting `~/cornerstone/assessments` from disk and reading each paper's printed
header, not from `manifest.md` (which undercounts — see below). No child is named here: names live
in `pii` and in the manifest outside git (CLAUDE.md rule 6). Counts only.

## Why this file exists

To read a used paper, the paper must first exist as a `sheet_template` with **one answer slot per
answer on the page** — not one per printed question. `legacy.import_scan` looks up every answer the
model returns by `n`+`part`; anything with no slot lands in `unmatched` and is **dropped silently**.
So a paper entered with too few slots silently loses answers on every child who sat it.

That is not hypothetical: `G2-CAM-A` was entered with 24 slots for a 27-answer page, and all three
children read against it lost the same 3 answers each.

## The corpus, counted from disk

- **84 files, 194 pages, 16 children.**
- **52 sittings** — not the 37 in `manifest.md`, which omits the WhatsApp images entirely
  (20 Grade 3 baseline pages and 15 Grade 2 extra pages).
- Per child: 5 sittings ×4 children, 4 ×3, 3 ×4, 2 ×3, 1 ×2. Two children have only one paper.
- Every file is attributed; none is orphaned.

## The papers

`slots` is what the database holds today. `verified` means checked against a real page by eye.

| # | paper | children | pages | entered as | slots | verified |
|---|---|---|---|---|---|---|
| 1 | G2 Cambridge U3 — **Level A** | 4 | 8 | `G2-CAM-A` | 24 | **WRONG — the page has 27** |
| 2 | G2 Cambridge U3 — **Level B** | 4 | 8 | `G2-CAM-B` | 24 | page 1 correct (20 of 20); page 2 unchecked |
| 3 | G2 Cambridge U3 — **Level C?** | 1 | 2 | — | — | **not entered**; its questions match neither A nor B |
| 4 | G2 Cambridge U3 — **Level D** | 1 | 2 | — | — | **not entered**; foundational, single-digit |
| 5 | G2 September Week 2 | 9 | ~25 | `G2-SEPW2-S1` | 12 | unchecked; two children's files are 10p and 3p, so variants are likely |
| 6 | G2 Word Problems 17-Sep | 6 | 12 | `G2-WORD-SEP17` | 6 | unchecked |
| 7 | G2 extra pages (larger working) | 5 | 15 | — | — | **not entered**; includes an explain-your-answer item |
| 8 | **G3 baseline diagnostic (16 q)** | 5 | 20 | — | — | **not entered — this is the gold paper** |
| 9 | G3 September W1 Level A | 2 | 6 | — | — | **not entered** |
| 10 | G3 September W1 Level B | 1 | 2 | — | — | **not entered** |
| 11 | G3 September W2 | 4 | 8 | — | — | **not entered** |
| 12 | G4 September W1 | 1 | 3 | — | — | **not entered** |
| 13 | G4 September W2 | 1 | 2 | — | — | **not entered** |
| 14 | SOF Olympiad (G2 and G3 forms) | 7 | 66 | — | — | **not entered**; multiple-choice, only its add/sub items map to a rung |

**4 entered, of which 1 is proven wrong and 2 are unchecked. 10 never entered.**

## What this changes

1. **The Cambridge paper runs at four levels, not two.** Only A and B exist in the database. Seven
   of the ten Grade 2 children who sat it are on C or D or an unchecked B page. They cannot be read
   until their level is entered.
2. **Every Grade 3 paper is unenterable today** — including #8, the 16-question baseline that all
   five of Aseem's reports are written from, and where `8500 - 3647 = 5147` lives. The gold set for
   the whole pipeline is behind this gate.
3. **The child with the fewest papers is on the paper nobody entered.** One child has a single
   sitting, on Level D, and their answers (`4+3=55`, `6+2=45`, `5+4=35`, `9+4=49`) show no working
   at all and no relation to the operands. That is not an arithmetic slip; the child is not
   computing. It is the sharpest signal in the corpus and it is currently invisible to the engine.

## How a paper gets entered

Engine prepares, person approves (Nimish's standing rule): the engine reads the **blank** page and
proposes one slot per answer, a person confirms or edits. Not a teacher typing 27 rows into a form.
The slot count is what must be right — a paper whose slot count does not match its page is the
defect this whole file exists to prevent, so entering a paper ends with that count checked against
the page, and `engine audit` should refuse a template whose slots and pages disagree.
