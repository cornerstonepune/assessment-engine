# ux10-declutter: the educator's pages say what to do and nothing else

Nimish, 2026-10-22, on the live site: "Look at the clutter"; "The current frontend is extremely confusing to me ... make
it much, much cleaner." Goal: `goals/ux10-declutter.yaml`. Gate: the 22 Oct locked scope, screens only (S1 follow-on);
no migration, no table. Assessments (`/papers`, `/capture`) is S2's (PR #274) and is untouched.

## What changed

- **Menu:** only Today carries a count (`components/shell.tsx`).
- **Children (`/growth`):** a short "Children who need you" list leads (needs help or answers waiting, at most 8, then
  "and N more"). A class's table shows only the columns with something in them; a nought or a dash is left blank. The
  topic chips and the second find box are gone (`finder.tsx` deleted; the bar at the top finds a child). "Against every
  skill" is a small grey link under the table. The reading of the table and the colour key sit behind "Details".
  One line under the title.
- **Curriculum (`/`):** grades → topics → skills, each skill with what its levels ask. Counts, worksheets by level, children
  assessed, and the two doors into the bank are behind a link, "Question bank details" (`/?details=1`). The two big
  "Not taught yet" / "Taught" sections are one closed fold, "Taught in each class"; a topic not taught yet is still a
  word on its row, with its button. Links that point at it (Today, a skill page, the switch's redirect) add `?taught=1`
  so the fold is open when they land.
- The door "Read the same worksheets by the taxonomy" is now worded "Every case, with its worksheets", per the
  plain-words rule.

## Verified

- Red first, on main's code: `cd apps/web && npx playwright test tests/u50-declutter.spec.ts` → 6 failed.
  Green on this branch → 6 passed.
- Whole browser suite, on a database built from the repository (`bin/testdb fresh`): 322 passed (16.5 min).
- `bin/check` → 30 passed, ruff clean.
- `bin/engine done ux10-declutter` on a fresh database: all 5 of Nimish's sentences PROVED; criteria PASSED (322 browser
  tests in 16.3 min; `bin/check` 30 passed). It still prints NOT DONE only because the live database did not answer from the
  build container (ConnectionTimeout), so live migrations are unchecked; this change adds none.
- Three older goals (`ui1`, `ui4a`, `ui4b2`) pointed at specs whose claim this change reverses; each is re-pointed at the
  spec that proves what survives, with a dated comment.
- Before and after screenshots, desktop and phone, as an educator of two classes with fake children (Asha, Bina, Cara, Dev):
  in a private page: https://claude.ai/artifact/1LcGje1iAZGp4fL9DaFiG5 . PNGs are ignored by `.gitignore` (children's work never in git), so they are not committed.

## Existing specs changed, and why

Each said the old layout; each now says the new one. Where the claim itself reversed, the title says so.
- Menu counts (u15, u32): the tabs carry no count; Today's count is still every tab's.
- Topic chips on Children (u21, u31): gone; u21's first test now says the list reads every topic whatever the address says.
- Second find box (u18): replaced by "no second box"; finding a child is s41's test of the bar.
- Counts and columns on Curriculum (u5, u12, u19, u30, u33, u34, u42, u44, e2e): read at `/?details=1`.
- "Not taught yet" / "Taught" (u13, u17, u18, u30, u31): read at `/?taught=1`.
- Children columns (u8, u35), colour key (u11, u35), a name's colour (u46): follow the columns shown and the Details fold.

## Handoff

- **Live:** nothing until merged and deployed.
- **Observed, not fixed:** u15's second test ("Today lists everything that waits...") fails on a database that earlier
  specs have used (Today's list of class papers to approve cuts off the test's own class once enough classes have a pack
  waiting) and passes on a fresh one, with or without this change. Run the suite on `bin/testdb fresh`.
- **Not touched, on purpose:** the taxonomy page's own title still says "taxonomy"; Assessments (S2); a topic row's
  "Say it is taught" control still shows on each untaught topic row (the feature, kept).
- **For Nimish:** the Curriculum page still has one button per untaught topic. If that is still too much, the next step is
  moving it behind the same fold; say so.
