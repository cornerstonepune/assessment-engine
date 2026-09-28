# ADR 0038 — A copy is read in the layout it was printed in

**Status:** accepted (Nimish, 2026-09-28: "Recover layout (Recommended)")
**Goal:** `goals/s18-read-as-printed.yaml`

## What happened

The 23 Sep Grade 2 papers are library worksheets (R8-H01, R8-H02, R2-E12, R5-H14) printed before L3
(2026-09-23 10:08 UTC). R8-H02 as printed has four boxes an answer, four questions a page and three pages. Today
it prints two boxes, three questions a page and four pages. The reader lines a copy up against the worksheet's
PDF, and that PDF is rendered on demand into `data/worksheets/`, inside the engine's container. Every deploy
rebuilds the container, so the layout the children wrote on was gone. 87 of 108 answers fell back to the old
whole-page reader, and 55 of 108 settled, under step 1's floor of 75%.

## Decision

Every layout the renderer has printed is a row, `render.layouts` in `config`, oldest first, the last being
today's. A row holds the three things that have ever changed since the library began (2026-09-21):
- how many boxes an answer gets (`cells` before L3, `digits` since);
- the working space's heights;
- the QR's error correction (`m` until 2026-09-24, `h` since).

The renderer draws a worksheet in any of them (`render_item`, `sheet_html`, `render_sheet` take `layout`; `page_css`
holds the page's CSS and what a row draws differently). The library caches each layout under its own name
(`library.pdf(conn, code, layout)`, `library.printed`). A copy with no kept PDF is read in the layout its pages match
(`copies._as_printed` → `boxes.as_printed`). The match is made on the page's long horizontal lines — box edges and
rules, not words or pencil — near where any layout prints an answer, among the layouts with as many pages as the copy.

A layout change is a new row; a row is never edited or removed once a paper has printed in it.

Every deploy runs `engine load --settings` (prompts, thresholds, config) from the seed of the commit deployed, so a
row merged with the code that reads it is live with that code. Before this, seed rows reached live only through
`bin/update-live` run from Nimish's Mac. The `mistake_guess` prompt (#84) was one such row.

## Rejected

- **Keep every printed PDF on the server's disk.** It fixes papers printed from now on, but the 23 Sep PDF is already
  gone, and a PDF downloaded on someone's own machine is never on the server at all.
- **Render the old papers with the old code from git** (22f7ffe^, in a workflow against the live database). That is
  faithful by construction, but it carries a second copy of the engine and its dependencies of the day. It must run
  wherever the questions are, and it would be done again for every future layout change. The layouts differ in
  three settings; those are data.
- **Drop 23 Sep from step 1's goal.** That lowers a floor set before the work (CLAUDE.md rules 11 and 14).

## Measured

The synthetic test (`test_boxes.py::test_a_copy_is_read_in_the_layout_it_was_printed_in`) uses the same six sums in
both layouts, written in, then tilted, softened, compressed and with the top cut off.

- **Whole page:** a pre-L3 copy scored 0.84 for its own layout against 0.66–0.80 for today's. The text, the same in
  both, diluted the difference.
- **Answer areas only, long horizontal lines:** 0.59–0.67 against 0.43 or 0 for pre-L3 copies. Today's copies scored
  0.81–0.85 against 0, because they do not line up with the old layout at all.
