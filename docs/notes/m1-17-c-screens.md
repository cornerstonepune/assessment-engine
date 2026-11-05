# M1-17 brick C — the class picture and a child's page, in the real app

W3, gate N10 (reading side). Stacked on brick B (#404, which also gets a route fix found here). No migration, no model
call. Design: `docs/notes/m1-17-design.md` (#402).

## What a person can now do
- `/k2/<class>`: the class's children by Sr. No. against the skills anyone was seen on; a chip (icon, word, level) where seen, a
  dash where not. A strip of counts by state. Paged ten children at a time (the site's one table, `DataTable`).
- `/k2/<class>/<Sr. No.>`: where the child is on each skill (with the educator's sentence when the engine releases it),
  ready next (confirmed links only), and how the child has moved (months, level, days, a trend in words, no score).
- Both read the engine's own refusal as the gate: with the educator switch off, or for a class that is not the person's,
  the page says so in the engine's words and shows no child. **The staff-preview gate (4b, `educator.preview_roles`) is not
  merged, so it is not wired and there is no menu entry**; the pages are reached by address. I wrote no gate of my own.

## Decisions made without an answer
- **Chip** (`lib/k2-child.ts`, `components/child-state-chip.tsx`), no terracotta on a child: the words and colour are the `child_state`
  rows, as the engine sends them with every cell; web code names no state (CI's `test_no_file_names_a_state_or_a_subject` caught my
  first version, a TS table of states). Only the colour's look is here: green is olive with a tick, amber is amber with a clock, red
  and grey are monsoon (a child is never red; the rows' red reads as quiet) with a ring or a dashed square. Each with its word.
  **Consequence:** the lowest state reads "under half right", the row's words for written papers; it does not fit an observed skill.
  An earlier version said "just starting"; that wording is now an open point for the school and a seed-row edit if wanted.
- Growth's trend "down" reads "lower this month", in amber-free plain text with an icon, not a chip.
- The links in the grid are basalt (the site's default link colour is terracotta).
- **The ground is white** (`app/(app)/k2/layout.tsx`, the app's own `bg-white`), not `--surface` from `tokens.css`. The orchestrator asked
  for the tokens to be imported; I did not, because the browser test showed that importing them for these pages changes the
  body font of every page after the first visit (both files define `--font-body`; the app's Source Serif 4 became Jost). That is
  `docs/design-tokens.md`, decision 1, which is not this task's. When it is decided, the layout imports the tokens and uses
  `--surface`: one file. A test holds that the ground is white and that the app's font is unchanged after leaving the pages.

## Verified (local database from `bin/testdb fresh`; never live)
- `cd apps/web && npx playwright test tests/m1-17-k2-picture-and-child.spec.ts` → 5 passed, 1 skipped (the empty-class test
  skips on a database that already holds the class's observations; it ran and passed on the first run). Checks: switch off →
  engine's words, no grid; grid cells equal the rows; a child not seen has a dash and no "not secure"; no element of the late
  tone anywhere; no sideways page scroll at 390 px; walkthrough counted: class picture → Sr. No. 1 (1 tap) → back (1 tap);
  growth shows first/last seen, months with level and days, no score; a confirmed link lists a skill under ready next and a
  proposed one does not; token check (no raw colour, no terracotta, no late tone in the state table).
- Screenshots at 1280 and 390 px: `docs/screens/m1-17/`.
- Neighbours: `tests/u51-ux-rules.spec.ts` and `tests/m1-04-k2-voice-notes.spec.ts` passed with it (24 in one run, 15 in the next);
  `tests/test_layout.py` and `tests/test_ux_rules.py` → 16 passed; `bin/check` → 34 passed; eslint clean; `tsc --noEmit` shows
  only the two `LayoutProps` errors that exist on main (generated types).
- A real defect found by the browser and fixed on #404: the route's response model dropped `growth` and `ready_next`
  (the function tests had passed). Test added first, seen failing.
- **`/code-review` (medium) and `/simplify` run; fixed:** the state table moved to the rows (see Chip); the growth and link reads now run before the name check (its failed read
  would abort the transaction); growth names come with the growth rows (a skill from another grade); `/k2/child`'s trend is a
  closed set in the route model; the web read turns an engine restart into the usual words instead of an error page; links are
  encoded; one `Notice` for the six hand-written empty states; dates through the site's `dateWords` ("19-Oct-2026");
  `names` copied once, not per row. **Skipped, on purpose:** `ready_next` also listing a skill already practising (where the
  educator pushes next; the plan section above it is a different view); the name check covering only this class's children
  (M1-03's documented limit); the chip's copied class string (minor); paging the class on the engine side.
- **CI caught three source-scan rules I had not run (all fixed, all mine):** no web file names a grade code (my page header said "K2": now
  "Children" and "Class picture"); no web code names the raw link tables (the browser test now sets its two links up with
  `packages/engine/tests/k2_link_fixture.py`, a script beside the engine's own tests); no browser test may skip itself (the empty-class
  test now makes its own empty class). The browser spec also had its own class (`M117`) because the voice-notes spec leaves
  observations in `M104` and CI shares a database per shard. Since then I run the whole set of tests that read source files, not only the
  K2 ones, on a clean database before a push; checked in CI's order (voice notes spec, then this one, then the UX-rules spec): 26 passed.
- **Not run:** the sharded whole suites; the whole browser suite (CI).

## Handoff
Next: wire the 4b preview gate when it lands; a menu entry for staff in preview; the white ground when it lands.
