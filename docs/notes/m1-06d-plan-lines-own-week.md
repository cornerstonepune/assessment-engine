# m1-06d: a period shows its own week's planner lines (W2, gate N4)

## Verified
- `DATABASE_URL=…/cs_plan TEST_DATABASE_URL=…/cs_plan pytest -q tests/test_k2_day.py` on a database built by `bin/testdb fresh`
  from this branch's migrations → 16 passed. Before the fix, the new test failed: General Awareness gave four lines
  (Insects, lifecycle of a butterfly, twice).
- The same with tests/test_k2_timetable_load.py, test_k2_timetable.py, test_timetable_run_command.py → passed.
- `engine live rules --url <local> --write` → one new rule, `plan_entry_week_code_check`.
- Nothing applied live. No model call.

## The rule
- A fortnight listed under two month headings: week A is planned by the first row, week B by the second (the loader,
  `_parts`). Each line keeps its week in `plan_entry.week_code` ('A' / 'B'); a fortnight listed once leaves it null.
- A period's lines (`k2_day._plan_lines`) are those under its heading, in its fortnight, with the same week_code as
  its own line (null matching null).
- Rows already loaded: the migration reads each half's month from `source` ("… (November block)"). The second row's
  lines are numbered on from the first's under each heading, so the half holding the first line of a heading both
  rows share is week A. If a split fortnight has no shared heading, the migration stops with an error.

## Handoff
- Merges alone, after #398 and #399 (migration order 20270106, 20270107, then this one, 20270108).
