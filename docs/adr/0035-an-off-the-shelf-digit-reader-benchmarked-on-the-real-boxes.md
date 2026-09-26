# 0035 — Which reader reads a digit in a box: benchmarked on the real 24 Sep crops

Date: 2026-09-26
Status: **proposed — shown to Nimish before anything merges**
Goal: goals/s17-step1-reread-both-scans.yaml
Harness: `docs/adr/0035-bench/` (scripts, the gold, every reader's reading of every answer; no crops — rule 6)

## Context

Step 1's box reader, on the real 24 Sep scan, settled 80 of 192 answers against a floor of 144 (HANDOFF,
2026-09-26 later). The last session's diagnosis was "Textract is a document reader and will not reach 75% on
digits in boxes", and its proposed fix was a digit reader of our own (step 3). Nimish, 2026-09-26: *"before
building any reader logic, benchmark off-the-shelf digit readers against Textract on the real 24 Sep box crops …
Use whichever wins; don't write our own reader."*

## What was measured

- **The crops.** The 24 Sep file (Drive `13Zsrf3…`), each page lined up and each answer's run of boxes re-found
  exactly as `w3_read/boxes.py` on this branch does it (`extract.py`). 14 of 16 pages line up; copies 01–02 do not
  (37–40 matched features against 60), so 168 answers, 158 with ink. Two crops per answer: **cleaned** (what
  `boxes.strip` hands Textract today — every printed pixel grown 0.8 mm and removed, everything not pencil made
  white) and **uncleaned** (the settled run of boxes as photographed, 2 mm around it).
- **The gold.** Labelled by the session, by eye, from the uncleaned crops, **not yet by a person**. 133 answers
  sure; 27 unsure (overwritten digits, mirror-written digits, erased marks) left out; 8 blank. Nimish or an
  educator confirming `gold.json` is owed before this becomes accepted.
- **The readers**, all off the shelf, none trained on our papers:
  Textract (`detect_document_text`, production's call and production's `decide`);
  TrOCR `microsoft/trocr-base-handwritten`; PaddleOCR 3.7 (`PaddleOCR(lang="en")` detect + recognise, and
  `TextRecognition()` alone), both with oneDNN off (Paddle 3.3's oneDNN path fails on CPU);
  `farleyknight-org-username/vit-base-mnist` from the Hugging Face hub; and a standard two-layer CNN (the PyTorch
  MNIST example's shape) trained on EMNIST-digits, 99.38% on EMNIST's own 40,000 test digits. The MNIST-style two
  read one box at a time; the others read the run.
- **The rule a reading stands by** is production's: as many digits as boxes hold ink, and confidence at or over a
  floor. Floors 0.70 (production's) and 0.90 were fixed before scoring.

## Result (133 answers with a sure gold)

| reader | crop | exact | stands @ 0.70 (wrong) | stands @ 0.90 (wrong) |
|---|---|---|---|---|
| Textract — **today** | cleaned | 68 (51%) | 64 (6) | 50 (2) |
| Textract | uncleaned | 93 (70%) | 85 (2) | 66 (**0**) |
| **PaddleOCR detect + recognise** | uncleaned | 113 (85%) | 117 (5) | **102 (1)** |
| PaddleOCR recognise only | uncleaned | 117 (88%) | 123 (7) | 107 (2) |
| PaddleOCR detect + recognise | cleaned | 111 (83%) | 121 (10) | 110 (7) |
| PaddleOCR and Textract agree | uncleaned | 113 (85%) | 77 (1) | 57 (0) |
| TrOCR base-handwritten | cleaned | 81 (61%) | 31 (1) | 10 (0) |
| TrOCR base-handwritten | uncleaned | 2 (2%) | 0 | 0 |
| ViT-MNIST (hub), per box | cleaned | 98 (74%) | 114 (24) | 98 (14) |
| EMNIST CNN, per box | cleaned | 73 (55%) | 80 (25) | 39 (5) |

On the goal's own measure (blanks plus readings that stand, of all 192): today 81; Textract uncleaned 104;
**PaddleOCR detect + recognise, uncleaned, @ 0.90: 119**. The 24 answers on copies 01–02 cap any reader at 168.

## What the numbers say

1. **The cleaning is the largest single defect, and it is ours, not the reader's.** Removing every printed pixel
   grown 0.8 mm also removes the pencil lying on the line: an 8 touching the box's side became a 3, a 6 a comma,
   a 3 hanging below its box was cut to a 2. Every reader then stood behind the same wrong number (348 → 343,
   364 → 354, 322 → 222). The same Textract, given the uncleaned crop, goes from 51% to 70% exact and from 6
   wrong readings stood behind to 2 (0 at 0.90).
2. **PaddleOCR is the best reader of these digits by a wide margin**: 85–88% exact against Textract's 70% on the
   same crops, and at 0.90 it stands behind 102 answers with one wrong (a 4 read as 9, `copy10_q02`) against
   Textract's 66 with none.
3. **The MNIST/EMNIST route loses and is dropped.** Per box, a child's 4, 7 and 1 in pencil on a phone photo are
   not MNIST's: 24–25 wrong readings stood behind at 0.70. TrOCR is an English line reader: it turns a strip of
   digits into words ("super-mass express" for 1210) and reads the box lines as text.

## Decision (proposed)

- **PaddleOCR (detect + recognise, `en`) becomes the reader of digits in boxes**, on the uncleaned run of settled
  boxes, standing at 0.90 under the same count rule; a reading below that goes to a person, as now. It runs
  inside the engine (an adapter in `packages/engine/engine/adapters/`, rule C), no service called.
- **`boxes.strip` stops whitening the print** for the reader. Code keeps deciding blank / how many boxes hold
  ink / working shown from the cleaned mask, where it is right; the reader gets the photograph.
- **Textract stays for what it does well** — the printed-code fallback (#64) and the old papers — and is **not**
  a second vote on boxes by default: agreement buys 0 wrong instead of 1 at the cost of 45 answers to a person.
  Whether that trade is worth it is Nimish's call; the table above is the evidence.
- Step 3 ("our own digit reader") is **not** pulled forward. It stays as ADR "every stage learns, behind a
  gate": a trained model replaces PaddleOCR only by beating it on held-back, person-checked answers.

## What this does not prove, said plainly

- **133 answers, 14 copies, three worksheets** (R27-H03 alone is 7 copies of the same 12 questions). 1 wrong in
  102 against 0 in 66 is not a measured difference in safety; it is one digit.
- **The gold is the session's reading**, not a person's. Two shared misreadings (`copy07_q09` "145" read 195 by
  four readers; `copy10_q02` "419" read 919) are where a person should look first.
- **Floors were fixed in advance, but on this one scan.** The 0.90 floor must be re-checked on the 23 Sep scan
  and on the first answers people validate (step 2) before it is trusted.
- **The server**: PaddlePaddle on the Lightsail box (memory, CPU time per page) is not measured here; nor is
  its time per page. Both are measured before the adapter is merged.
- Copies 01–02 not lining up is a separate cause, not touched by any reader.

## Rejected

- **Writing our own reader now** — Nimish's instruction, and nothing here needs it: an off-the-shelf reader
  closes most of the gap once our own cleaning stops damaging the digits.
- **MNIST/EMNIST per-box classifiers** and **TrOCR** — measured above.
- **Keeping Textract and tuning its floor** — the ceiling is its 70% exact on the same uncleaned crops.
