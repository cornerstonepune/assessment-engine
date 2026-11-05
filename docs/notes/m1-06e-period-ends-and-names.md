# m1-06e: the engine says when a period ends and what it is called (W2, gate N4)

## Verified
- `pytest -q tests/test_k2_day.py tests/test_k2_timetable*.py tests/test_timetable_run_command.py` and the materials
  route tests, on a local database built from the migrations → 95 passed. Both new tests failed first (no `name`;
  a period with no end said null mid-day).
- Nothing applied live. No model call. No migration.

## What changed
- `k2_day.days()`: a period with no end gets the next period's start; the day's last keeps none. Day, week and period
  all go through `days()`, so they agree.
- Each period has `name`: a break's `label`, else the frame's own text for the slot (`timetable_slot.text`).
- The calendar PR (M1-09c) reads both and drops its own `withEnds` and `nameOf`.

## Handoff
- Merge before the calendar PR.
