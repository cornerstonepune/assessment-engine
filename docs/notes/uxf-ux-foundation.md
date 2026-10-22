# uxf-ux-foundation: the educator's site is built to rules

Nimish, 2026-10-22: "a significant shift to the ui/ux - ensuring there are proper rules/flows/tabular views, no long
table, all info displayed is consistent, well formatted, every page has a purpose, a sequence and all pages, flows, views
are educator backward." Goal: `goals/uxf-ux-foundation.yaml`. Rules and how to use the blocks: `docs/ux-rules.md`.
Slice UXF of the locked scope of 22 Oct, beside S1: web only, no migration, no new table. One page moved: Check answers.

## Verified

- Five blocks in `apps/web/components/`: `PageShell` (required `action` and `next`, optional `details`), `DataTable`
  (required `more`: grouped or paged; empty-column hiding; a labelled list on a phone), `StatusChip` (one set of states),
  `EmptyState`, `Count` (`data-count`, also on the menu's badges). The numbers are in `apps/web/lib/ux-rules.ts`.
- Failing first: `tests/test_ux_rules.py` with Check answers off the list, before it was moved:
  `AssertionError: build these on PageShell … ['/capture/check']`; passes after.
- The list (`workflows.json` `ux.frozen`) is measured, not guessed: 29 pages, all 29 break "shell", 19 build a table by
  hand, 10 have a line under the title past 140 characters (30 pages before Check answers left it). The ratchet
  (`engine ratchet`, `tests/test_ratchet.py`) refuses a page joining it or a rule coming back.
- `bin/check` → 30 passed.
- `cd apps/web && npx playwright test tests/u51-ux-rules.spec.ts` → 6 passed (on `bin/testdb fresh` of this branch).
  It holds each page off the list to the five rendered rules; Check answers is the page off it.
- Check answers on the blocks, the same answers as before: the older specs that read the page still hold:
  `s4-validation-queue`, `u3-marking`, `u50-the-picture-is-the-question`, `u43`, `u45`, `u47`, `u49`, `u1`, `u38`, `u9`,
  `s1`, `u33`, `u15` → all pass (62 of 67 first run; the one failure was a missing "← Marking" link, restored, re-run green).
- Full suite on a `bin/testdb fresh` copy, with this sandbox's Chromium linked in: 323 passed, 2 failed, 3 not run.
  The 2 are `u15-menu-and-today` ("Today lists everything…") and `u26-my-classes-first` ("the coordinator sees every
  class"): Today lists five class packs and then "and N more", and by this point of the run the copy holds more test
  classes than that. They fail the same way on the unchanged base commit (5ffb020) on the same copy (2 failed, same
  names), and ux9c-one-role.md records both failing on a local copy before this branch. Today is not touched here.
  `bin/engine done uxf-ux-foundation`: all five of Nimish's sentences PROVED, the rule tests, the Check answers specs
  (34) and `bin/check` PASSED; "every page still holds" FAILED on those two. CI's fresh copy decides.
- Before and after of Check answers, desktop and phone, seeded test rows only: the one decision (Yes, the child wrote 1 /
  Right, Wrong, Blank / type it) moved to the top, under the title, as the one main action; the ways round it stay beside
  the picture; "Later — show the next one" became the page's next step at the foot (at the end of the queue: "See the
  class results"); the count is one `Count`; a chip says whether the answer is a spot-check, for judging, or waiting.
  Words, picture and forms are unchanged.

- **Main merged in (2026-10-22), and CI's two reds found their cause.** CI's merge of this branch with the main of that hour
  failed `test_the_list_only_shrinks`: Today (`/`) no longer breaks the "purpose" rule after main's declutter, so its entry
  was out of date; it now lists `shell` and `table` only. With today's main, S2's new page `/papers/card` was a page not on
  the list that broke "shell" and "table". It is not added to the list: it is built on `PageShell` (the stage's one action
  at the top, "All assessments" as the next step) and `DataTable` (the children still out first, ten to a page).
  `bin/check` → 30 passed; `test_ux_rules`, `test_layout`, `test_ratchet` → 17 passed; `s42-the-assessment-card` and
  `u51-ux-rules` → 12 passed, and the six specs that read the card (`m4`, `s7`, `u11`, `u17`, `u36`, `u37`) → 34 passed,
  on a `bin/testdb fresh` copy of this branch. `DataTable` now has a rendered page (the card's table).

- **CI on head 5fcc0e2: all 17 checks green** (12 engine shards, engine, engine-checks, web, browser, Vercel).
- `bin/engine done uxf-ux-foundation` on a `bin/testdb fresh` copy of this branch: all five of Nimish's sentences PROVED;
  "no hand-built table and no long purpose line" PASSED (8); "Check answers on the blocks, and every page against the
  rules, rendered" PASSED (34); `bin/check` PASSED (30); "every page still holds" 328 passed and the same two failures as
  before, `u15-menu-and-today` ("Today lists everything…") and `u26-my-classes-first` ("the coordinator sees every
  class"): Today shows five class packs and "and 2 more", and a copy that has run 328 specs holds more classes than five.
  They fail the same way on unchanged main on the same copy, and the same specs pass in CI's browser job on a fresh copy.
  So `done` reads NOT DONE on a used copy; CI's fresh copy is the decider. Today is not touched here.

## Not held yet, said plainly

- The menu shows a red count on every tab; rule 5 allows red on Today alone. It changes every page, so it waits for the
  slice that moves Today (PRs #274, #278 change Today, Papers, Children and Curriculum).
- `DataTable` is rendered by one page, the assessment card; its paging past ten children is proved on the pure functions
  (`u51`), not by a card with eleven children.
- A listed page's rendered tables depend on the rows in the database, so they are measured, not frozen: on the test copy,
  /make, /growth, /growth/reports, /library, /worksheets, /worksheets/taxonomy and /worksheets/[qr] drew tables past 10
  rows, and /, /make/[section] and /growth a column of zeros or dashes. The spec records them in its annotations.
- Rules 6 and 8 (the school's words, setup behind "details") are reviewed by eye, not tested.
- This session could not read the Claude Doc (its viewer needs the Docs connector); the eight rules are the ones in the
  task, as Nimish approved them.

## Handoff

- **Live:** nothing until merged and deployed. No migration.
- **Next slices:** move each page off `ux.frozen`, one at a time, after #274 and #278 merge: Today, Papers, Children,
  Curriculum first. A page leaves the list by being built on `PageShell` and `DataTable` and deleting its entry
  (`docs/ux-rules.md`).
- **Changed on purpose:** `components/nav.tsx` carries `data-count` on the menu badge (no visible change);
  `globals.css` holds the phone list layout for `table.grid.list`.
