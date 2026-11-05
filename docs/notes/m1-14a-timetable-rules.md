# M1-14 part a — the timetable's rules as rows, and the screen that edits them

W2, step N4 (files only). Goal: `goals/m1-14a-timetable-rules.yaml`. Screen: `/timetable/rules` (Setup menu, "Timetable rules").

## Verified
- `bin/engine done m1-14a-timetable-rules` — every sentence PROVED, both criteria PASSED (22 tests; `bin/check` 34 passed); verdict
  "NOT DONE" only because it is not on main and the live database was not reachable from here.
- Browser walkthrough on the school's own Fortnight 10 text (K2 class made by the test): block a day + set a weekly limit =
  6 fields/taps, 1.5 s (`npx playwright test tests/m1-14a-timetable-rules.spec.ts --project=steps`, 6 passed).
- Screenshots: `docs/screens/m1-14a/` (empty 1280, rules 1280, rules 390). Token check is in the spec: no hex or rgb in the css.
- The educator switch stays off: the spec asserts it; the staff screens do not read it.

## Handoff
- Needs the migration `20270109090000_timetable_rules.sql` merged alone (three tables: timetable_block, timetable_limit,
  timetable_rule_edit; rules.json updated, 27 rules).
- Known risk for part b: `engine timetable load` identifies periods by (grade, start time). A person who changes a period's start
  here makes a re-run of that load add a second period. Part b should not re-run the load once rules exist, or the loader should key
  periods by `ord`.
- A period belongs to the grade; its change is kept in the history of every class of the grade.
- Fixed-slot "pin" replaces the slot already there (kept in the history); sessions already made from slots are not regenerated until part b.
- Not built here (misalignments, simplest reading): left sidebar and bottom tab bar are a shell-wide change, so this page sits in
  the existing top-bar shell; teacher-os decisions could not be read (adding that repo was refused), so D-075 was taken from the brief.
