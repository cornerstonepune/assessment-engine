# s7-across-classes: the page across every class

Slice S7 of the scope Nimish locked on 2026-10-22 (`BUILD-ORDER.md` on #269, "the locked scope of 22 Oct"), built beside
the C slices because it needs no new table. Goal: `goals/s7-across-classes.yaml`.

## Verified

- `s43-across-classes.spec.ts` failed on main's code first (no "Across every class" link: 1 failed, 3 did not run),
  2026-10-22, on a local copy built by `bin/testdb fresh`; passes on this branch: 4 passed.
- `bin/engine load --check`: every code referenced resolves, unchanged on a second run; `threshold` 61 rows (59 + 2).
- `bin/check`: 30 passed.
- Neighbouring specs (u9, u25, u35, u37, u43, u47, u49, screens): 53 passed, 1 failed: u47 "one main action" on
  `/library` ("Remove from the bank | Keep it", bank proposals other runs left on this copy). It fails the same on main's
  code on this copy; S7 does not touch the library. CI's fresh copy decides.

## Handoff

- **Live:** nothing until merged and deployed. No migration, no new table: two threshold rows in
  `supabase/seed/thresholds.json` (`across.papers_missing_days` 3, `across.check_overdue_hours` 48), loaded by
  `engine load` as every other.
- **What changed:** `/across`, "Across every class" at the foot of the menu (it lights the Children tab): each class and subject's newest
  assessment and where its papers stand; answers waiting for a person over 48 hours, by class; children's papers given
  (or printed, where no one said the day) over 3 days ago and not back, a child said to be away left out; children who
  need help in two or more subjects. `papersCte` is now exported from `lib/queries-papers.ts` so the page counts stages
  as Assessments does.
- **Reads S2's rows when they exist:** "given" and "absent" are `flow_run` rows S2 (#274) writes; before it merges there
  are none, and the day printed stands in.
- **Today only Maths has results**, so "two or more subjects" names no one and says so; the test makes a second subject
  for a moment to prove it counts.
