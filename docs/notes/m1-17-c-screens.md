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
- **Chip table** (`lib/k2-child.ts`), no terracotta on a child: secure, ready to move up → olive; secure to re-check,
  practising, repeating a mistake → amber; just starting, not enough yet → monsoon. Each with an icon and a word. The seed's
  `child_state.colour` (red for emerging) is not read. "Emerging" is worded "just starting" (the engine's "under half right"
  is a written-paper phrase); *unverified with the school*.
- Growth's trend "down" reads "lower this month", in amber-free plain text with an icon, not a chip.
- The links in the grid are basalt (the site's default link colour is terracotta).
- The page ground is the app shell's cream, not white: `design-system/tokens.css` is not imported by the app yet and the
  white-ground update has not landed. My panels use the app's own classes; no raw colour is in the new files (a test reads them).

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
- **Not run:** `/code-review` and `/simplify`; the sharded whole suites; the whole browser suite (CI).

## Handoff
Next: wire the 4b preview gate when it lands; a menu entry for staff in preview; the white ground when it lands.
