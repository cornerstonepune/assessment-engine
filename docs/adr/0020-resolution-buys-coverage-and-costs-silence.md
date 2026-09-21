# 0020 — More pixels is not the answer: resolution buys coverage and costs silence

Date: 2026-09-21
Status: accepted

## Context

A third of everything reaching a teacher — 83 answers of 242 — sat at 50–69% confidence, one band
under the floor. `HANDOFF.md` called this "a resolution problem: the page goes to Textract at 150
dpi and a 40×25-pixel answer inside it is at the limit", and set a target of recovering half of them
by re-reading the crop larger.

The diagnosis was right about the cause and wrong about the cure, and the difference was only
visible by measuring.

**The scans hold more than the engine reads.** A scanner writes a 2331×3165 photograph into an
A4-sized PDF page: 282 dpi. Across the corpus the embedded scans are 198–282 dpi and every one of
them is rendered at 150, discarding up to 47% of the pixels the file already holds — not for the
doubtful answers, for every answer of every scan. That looked like free accuracy lying on the floor.

## Decision

**The page is read at 150 dpi. A flagged answer, and only a flagged answer, is looked at again
larger.** Both halves are measured on the 82-response gold set, and the number that decides is
`silently wrong`, never `exact`.

```
  page rendered at        exact            silently wrong
  150 dpi (in service)    79.3% -> 81.7%   1      <- with the second look
  200 dpi                 84.2%            5
  the scan's own dpi      76.8%            1      (198-282, per file)
```

200 dpi reads five more answers correctly and stands behind five wrong ones. That is the trade
rule 5 exists to refuse: `silently_wrong` is what protects a child from being recorded as failing a
skill she did not fail, and coverage is never bought with it. The scan's own resolution is worse
outright — Textract reads these particular scans better at 150 than at 282, which is a fact about
the service and not something to argue with.

**The second look** (`ocr.reread_dpi`, `ocr.reread_pad`) crops one flagged answer out of the page,
re-renders it at 500 dpi where the source has the resolution to give, and sends that. It is
allowed to go large where the page is not, because nothing it returns is believed unless it clears
the same 70% floor on its own — it cannot lower the bar, only bring more evidence to it. Two
guards were each paid for by a silent error on the gold:

- **It may not see fewer digits than the page did.** "Answer=43" came back from its crop as "4" at
  91.7% and would have entered a child's graph as 4. More pixels may add a digit the page missed;
  they cannot take one away.
- **What it resolves a mark into faces the echo test again.** The page read a fragment "3892" of
  the printed "38,924" beside it, which matched no echo and survived; the crop read the mark
  properly, at 99.3%, and it is the paper's own operand.

A crop holding two numbers is refused rather than chosen between: the neighbouring answer came with
it, the original reading was already below the floor, and a person was always going to see it.

## What this cost, honestly

**7 answers of 83, not half.** The reason is now understood rather than guessed: past the embedded
resolution there is nothing more to see, and the pixels the second look wants were discarded
upstream by a 150-dpi render that the same measurement says must stay.

## Rejected, with the measurement

**White margins around the crop.** Textract is a document reader: handed a bare 960×344 strip
holding one word it returns `wer-`, `L`, and handed the *same strip inside white margins* it reads
`Answer=43`. The reading is plainly better and the gold set still says no — 80.5% against 81.7%,
silently wrong 1 against 2. A margin makes a crop readable, which also makes a *fragment* readable:
where the page had seen only the "2" of a child's "72", the framed crop confirmed "2" over the
floor and the engine stood behind it. Widening the crop to 0.03 and 0.06 of the page did not reach
the missing digit. There is no signal left to separate that case from a real one, so it waits for a
gold set large enough to price the trade. The finding is recorded in `adapters/ocr.py` so it is not
rediscovered from scratch.

## Consequences

- `render_pdf.DPI` carries its own measurement in a comment. Raising it without putting the
  silent-error count beside it is a regression however good the exact rate looks.
- `printed_boxes` had two sizes in pixels where everything else was a fraction of the page — a
  25-pixel threshold neighbourhood and a 3-pixel closing dilation. At 150 dpi they are unchanged;
  at any other scale they broke the box detector, and the Cambridge sheet fell from 23 of 27 to 17
  of 27 on a change that gave it *more* to read. They are fractions now, so the next person to try
  a different resolution measures the idea rather than the bug.
