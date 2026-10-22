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

## Not held yet, said plainly

- The menu shows a red count on every tab; rule 5 allows red on Today alone. It changes every page, so it waits for the
  slice that moves Today (PRs #274, #278 change Today, Papers, Children and Curriculum).
- `DataTable` has no page yet, so it is proved on its pure functions (`u51`: empty cells, empty columns, paging, grouping)
  and by its types, not by a rendered table. The first page moved onto it adds that check.
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
