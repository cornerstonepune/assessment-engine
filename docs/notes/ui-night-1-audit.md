# ui-night-1-audit: the educator's site at 1440 px, screen by screen

Written 2026-10-22 (night), for Nimish's night orders (desktop first; every screen as an educator teaching a week would
use it). Walked on a copy of the database holding the test suite's own fake classes and children (no real names), signed
in as the e2e account, at 1440 x 900, every screen in the menu and the pages they open. Each screen was drawn and
measured (rows per table, hand-drawn tags, filter row, status chips, main action and next step). The screenshots are on
the Artifact page that goes with this note. Slices are the PRs of UI night 1 (mine) or UI part 2 (the other session).

## What is wrong everywhere (fixed once, in the design system, PR #290)

| What | Fix | Slice |
|---|---|---|
| Lists are floating tags and cards, not tables (Assessments had topic tags, stage tags, week folds) | `DataTable`: fixed widths, text left, numbers right, status centred, sticky head, hover | UI-1 (#290) |
| No filter row, or a different one on each page | `FilterBar`, same place on every table page, active filters visible, one click to clear | UI-1 (#290) |
| Status is a coloured pill with no icon, and a different set of colours per page | `StatusChip`: icon + word + green / amber / red, one map | UI-1 (#290) |
| Top bar: Class and Subject small, a wide strip for search | 40 px / 15 px selectors, 240 px search that grows on focus | UI-1 (#290) |
| The menu has four tabs and the week has nine steps; "Marking", "Approve", "Make", "Home" are reached only by links | One menu in the order of the week (step 3) | UI-2 |
| A red count on Today only | already so; hold with a test | UI-2 |

## Screen by screen, in the order of an educator's week

| Screen | What is wrong (as an educator) | The fix | Slice |
|---|---|---|---|
| **Today** (`/today`) | A long page: five-line summary, three groups of cards, a table at the foot. "Check them" and four other buttons compete; the cards are lists of different shapes; the weekly table repeats numbers in the cards | Check against the new blocks: one table style for "what waits", a filter row (class, status), the one main action first, the reader's table behind "details" | UI-3 Today |
| **Taught this week** (inside Today, "Topics not taught yet") | Not a page of its own, so the Wednesday step ("say what was taught") is buried at the foot of Today; no list of topics per class | Decide with the docs: a page of its own, a table (class, topic, taught on, status), a filter row | UI-4 Taught this week |
| **Papers to approve** (`/papers/approve`) | One heading per class and week, each with a hand-built table; "Change level" and "See the paper" are small orange links in a row; the pack button is far from the children it approves; no filters | `DataTable` per class (child, level, paper, status chip), a filter row (class, week, status), the one button "Approve the pack" at the top | UI-5 Papers to approve |
| **Print and give** (`/make`, `/home`) | `/make` is called "Home assessments" and `/home` "Home Assignments": two names for one thing; 24 rows with no filter | One page "Print and give": table (class, assessment, papers, status), filter row, "Print" as the action, "Given on" as the next step | UI-6 Print and give |
| **Upload papers** (`/capture`, "Read a scan") | The upload box repeats on Assessments, Marking and the scans page; three views (By child, By class, By worksheet) are tag buttons; 10 hand-built tables | One upload page: the box first, a table of files read (file, pages, status), the reader's statistics behind "details" | UI-7 Upload papers |
| **Assessments** (`/papers`) | (fixed in #290) | Table, filter row, status chip | UI-1 (#290) |
| **Assessment card** (`/papers/card`) | Has a copies table without a filter and a status in pills | Copies as a `DataTable`, `StatusChip`, filter row (status) | UI-8 Assessments detail |
| **Check answers** (`/capture/check`) | Already on the blocks; one hand-drawn "← Marking" tag (fixed in #290) | Keep; the next step names the next answer | done |
| **Marking** (`/capture`, "Papers in, and where every answer stands") | A 2-line summary, then tabs, then expandable class rows; the reader's statistics (a long paragraph and a table) sit on the main page, which is for the reader's builders, not the educator | Table of papers in (class, child, paper, status chip) with a filter row; the reader's numbers behind "details" | UI-9 Marking |
| **Class results** (`/growth`, `/growth/class/[section]`) | A list of classes as collapsed rows with a sentence each ("3 children · 1 needs help"); no columns, so classes cannot be compared; "Children who need you" is a list of sentences | Table: class, grade, children, needs help, answers waiting (status chip), filter row (grade, status); each class row opens the class | UI-10 Class results |
| **A child** (`/growth/[id]`) | Four tables and six tags on one page, hand-built | Part 2 (not mine): tabs per subject, `DataTable`s | UI part 2 |
| **Parent reports** (`/growth/reports`) | 17 tags, a table of 9 rows with no filter | Part 2 | UI part 2 |
| **Curriculum** (`/`) | Grade accordions only; "Taught in each class" hidden under a fold; no table, no subject column | Part 2 (Nimish: "tables instead of tags" is first here) | UI part 2 |
| **Question bank** (`/library`) | 8,000 px tall, two tables of 26 and 50 rows, 29 tags | Part 2 | UI part 2 |
| **Worksheets** (`/worksheets`, `/worksheets/[qr]`) | Two tables of 26 and 50 rows, no filters | Part 2 | UI part 2 |
| **Approve the skills**, **Questions to answer** | Not in the menu: reached from Today only | Part 2 | UI part 2 |

## The menu (step 3, the component and its order are mine)

Today (the one red count) · Taught this week · Papers to approve · Print and give · Upload papers · Check answers ·
Class results · then, apart, the setup: Curriculum · Question bank. The current page is marked; every page ends on
the link to the next step; the same words in the menu, the title and the next-step link.

## Held by the build from now on (PR #290)

`tests/test_ux_rules.py` and `u51-ux-rules.spec.ts` fail on a tag list where a table belongs, a table of six rows or
more with no filter row, a status with no icon, a top-bar control under 40 px.

## Merge of main (23 Oct 2026): #313, #315, #316 into the design system

Conflicts were `assessments-table.tsx`, `copies-table.tsx`, `queries-papers.ts`; `workflows.json` merged on its own.
- Assessments: kept #290's `DataTable` and `StatusChip`. From #316 kept the query that counts a child once (`extras`, and
  `qrs`/`copies` that leave extras out) and said the extra copy in words under "Papers in" ("and N extra"), beside "and N spare".
- Copies: kept #290's `DataTable`. From #316 kept the extra-copy sentence under the table, and put the "every answer blank" /
  "none right: is this the right page?" warning under the Score cell (same `data-warn` hook, now from the shared table).
- Checked here: `bin/check` (31 passed), `npx tsc --noEmit` clean after `next typegen`. Not run here: the Playwright specs
  (u51, u52, u9, u37), which need the local database copy; they run in CI.

## CI repair, 2026-10-23
- The design system added `subject` to the shared papers query; main's Across-every-class query did `select p.*, … as subject`, so Postgres said "column reference subject is ambiguous" and the page crashed. Fixed in `apps/web/lib/queries-across.ts` by naming the columns.
- Proof: `cd apps/web && npx playwright test tests/s43-across-classes.spec.ts` → 4 passed (was 1 failed, 3 did not run); the full browser job had 345 passed, 1 failed. `npx tsc --noEmit` clean; `bin/check` → 30 passed, 1 skipped.
