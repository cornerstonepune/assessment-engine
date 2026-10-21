# ux6-curriculum-for-the-educator

Nimish, 2026-10-15: "Most of the pages just have a long list for no reason. All these things should be expandable and
collapsible. They should have the right set of columns which are important. It should be teacher-specific." He said
"go" to UX6 and UX7 on 2026-10-21. Same branch and pull request as `ux7-phone-and-words` (#247).

## Verified

- Measured first, as an educator of one Grade 2 class on a fresh `bin/testdb fresh`:
  - Curriculum opened with every grade closed, and "Children assessed" counted every child in the school.
  - The bank listed every taught skill of every grade, in a stock table with four level columns and "removed".
  - Worksheets read every skill of the school (`skillSets()` with no scope).
- `u42-curriculum-for-the-educator.spec.ts`, one test per sentence: failed first ("G2 is open: received false"), now 5
  passed. `cd apps/web && npx playwright test tests/u42-curriculum-for-the-educator.spec.ts`
- `bin/engine done ux6-curriculum-for-the-educator` (2026-10-21): all five of Nimish's sentences PROVED. Criterion
  "the curriculum, bank and worksheet pages still hold": 86 passed. `bin/check`: 28 passed. NOT DONE only because the
  work is not on main or live yet.

## Handoff

- **Live:** nothing yet; #247 waits for review and merge.
- **What changed:**
  - `gradesOf(scope)` in `lib/scope.ts`: the grades of the person's classes, from `class_band`. None for the coordinator.
  - Curriculum opens those grades (`CurriculumTable start`), and counts children assessed in the scope only.
  - The bank's `ItemFilter.grades` and the worksheets' `WorksheetFilter.grades` filter by the level's grade (`level_band`,
    else the skill's).
  - The bank's stock table shows only for `role === "coordinator"`. An educator gets Skill · Kinds of question · Questions.
  - Worksheets are scoped to the person's taught skills.
- **Database:** none. No migration, seed or engine change.
- **Seen, not in this slice:** the bank's "What the bank is" prose still opens the page above the educator's table.
