# 0026 — Every question in the bank sits on a numbered worksheet

Date: 2026-09-21
Status: accepted (step 3 of the five, `BUILD-ORDER.md`)

## Context

Nimish, 2026-09-21: *"If you tell me that there are already 12,000-odd questions generated, these
questions should already be converted into the worksheets … at least 10 worksheets each, created
for easy, medium, hard, and advanced … they can also start getting mapped to worksheet IDs."*
The database held 9 generated papers, all for one skill, drawn per child at print time.

The bank is uneven by design: 55 of the 68 skill-levels hold 216 questions (a class of 16 plus two
spares, twelve each — ADR 0016); one holds 145; the 12 Grade 1 levels hold 22–107, which is every
distinct question their arithmetic allows (ADR 0011).

## Decision

- A worksheet is a `sheet_template` row with `source = 'library'`, a `code` such as `R5-H07`
  (rung, level initial, number — never reused), no child and no week, and the 12 question ids of
  one skill at one level (`assemble.items_per_sheet`). Which worksheets a question is on is read
  from those ids; nothing is copied onto the question.
- A level gets W = max(10, ⌈N ÷ 12⌉) worksheets, so every active question is on at least one. Each
  worksheet's share of each kind is fixed first, in proportion to the level's kinds; then each kind's
  questions are dealt into those places in laps, a fresh order each lap, never twice on one
  worksheet — so where 12 × W exceeds N (the Grade 1 levels, and the 145) every question is used an
  equal number of times, ±1. (A first version dealt by rounds sorted by kind: on the real bank a
  level of two kinds got 8 of one and 4 of the other per worksheet.) On a worksheet the questions
  print grouped by kind, in the skill's own order of kinds. 1,123 worksheets for today's bank.
- `engine library build` is idempotent. Removing or correcting a question on the website goes through
  the engine, which in the same transaction retires every worksheet the question was on
  (`retired_at`) and deals replacements from what is active. Where a patch would leave a small
  level's questions used unevenly, or two worksheets alike, the whole level is retired and dealt
  afresh. A worksheet is never edited in place, because a child's printed paper points at it.
- A worksheet prints on demand (`GET /worksheet/{code}.pdf`), through the same renderer as a
  child's paper, its code where a child's paper has the QR's.

## Rejected

- **Exactly ten per level.** Leaves 5,305 of the 12,567 questions on no worksheet (96 in each of
  the 55 levels of 216, 25 of the 145) — the opposite of what was asked.
- **Only disjoint worksheets.** Gives a Grade 1 level as few as one worksheet; ten sharing questions
  is what the arithmetic allows, and the page says so.
- **Rendering 1,123 PDFs up front.** Minutes of Chromium and a folder to copy to the server for
  pages most will never print; rendering the one asked for costs a second or two, once.
- **Handing a child a library worksheet in this step.** It changes W2's proven assembly (12 of 12
  scenarios) and its approval query; it is the next change after these five, agreed separately.
