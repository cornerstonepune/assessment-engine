# 0022 — A blank page rebuilt from the children's copies: built, measured, parked

Date: 2026-09-21
Status: parked — the code stays (`engine/stencil.py`, `bin/engine read stencil`), the blanks are
moved to `data/paper-templates.parked/`, and the reader reads exactly as before without them.

## Context

The standard form pipeline aligns each scan to a blank template and reads each field where the
template says it is. There is no unmarked copy of any paper, so the blank was rebuilt from the
corpus: every child's copy of a page aligned to one of them (ORB features, RANSAC homography) and
the per-pixel median taken. Three copies at least, or a child's own answers survive into the blank.
19 pages across 9 printed forms had enough copies; `G4-SEPW1` names `printed_as: G3-SEPW1-A`
because it is the same printed sheet.

The finding that justified it was real and is still true: on one Grade 3 page the answers
30, 8, 70, 100, 13 and 1113 were all tagged PRINT by Textract at 98–99%, each read correctly and
then set aside as the paper's — nine answers in nine printed boxes came back as one.

## What was tried, and what each measured

**First design — read the child's page in the blank's frame, anchored on the blank's lines.**
`read eval` → **55.4% exact, 18 silently wrong** (from 81.9%, 1). On flat scans a child's page lines
up with its blank to half a percent of the page; on a curved phone photograph to ten; and a blank
averaged from photographs is soft enough that Textract misread its question numbers, so every
answer on one quiz landed on the question below. Rejected.

**Second design — read on the child's own page; the blank answers only "is this 'printed' number
really the paper's?"** A PRINT-tagged number is given to the child where the blank's pixels are
empty there, never for a number the page prints (questions, headings, question numbers), and
handwriting is never turned into print. `read eval` → 81.9% (68/83), 1 silently wrong — no harm on
the gold. On the corpus re-read: +16 newly settled, 6 old silent "blank" claims fixed (75, 95, 58,
610, 201 and 204→252), and **5 new silent errors**: 812→752, 65→15, 600→46, 35→5, 13→3. Every one
was checked on the page. The stencil was right about WHOSE ink it was — the faint working it found
is the child's — and that extra ink made the region rule "the last number is the answer" pick
working instead of the answer. Fixing six silent errors by adding five is still the trade rule 5
forbids. Parked.

## Decision

Parked, not deleted, and not patched further. Nimish stopped the reader work the same evening and
commissioned research (`research/reports/Reading handwritten worksheet answers.md`). Its finding
explains both failures: every working system fixes WHERE an answer is before reading it; this
engine infers location from ink, so anything that changes what ink is visible changes where
answers are thought to be. The stencil's reconstruction and alignment are the building blocks of
the location-first approach that report recommends; its "promote" rule is not, on its own.

## Consequences

- Nothing is read through a stencil unless `data/paper-templates/` holds a blank, which it does not.
- A re-read never touches a paper a person has signed off or corrected (`legacy.worked_on`) — the
  guard this experiment's re-reads showed was missing.
