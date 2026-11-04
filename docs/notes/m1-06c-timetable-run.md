# M1-06c — the timetable reaches live by a logged command

Follow-up to #379 (merged ad8aa1a). Goal: `goals/m1-06c-timetable-run.yaml`. W2 step N4, files only.

- `.github/workflows/timetable-run.yml` (manual, `workflow_dispatch`, choice `dry` | `apply`) and `.github/timetable/command.py`
  (the fixed commands; same pattern as the curriculum run: contents read, one run at a time, no `${{ }}` inside a script, the
  person from the repository variable CURRICULUM_STAFF, checked by the curriculum script's own `person()`; an apply needs one).
- `dry` = `engine timetable load` on the committed exports in `supabase/seed/k2_tabs_2026_11_04/` (the engine container mounts
  `supabase/seed` at `/app/supabase/seed`), K2 section A, Mon 7 Dec undecided; it rolls back. `apply` = the same with `--apply`, twice.
- `engine timetable load` now prints, per table, planned / added / before / after (before = after − added, the same transaction).
  Expected after an apply on live: fortnight 8, school_day 80, period 15, timetable_slot 150, plan_entry 375, session 1,049; the
  second apply adds 0 everywhere.
- Needs on the server: this commit's `supabase/seed` and the seed loaded (`engine load`), because the command reads the vocabulary
  from the `timetable.vocabulary` row (it says "run `engine load`" if the row is older than the code).

Proof: `pytest tests/test_timetable_run_command.py tests/test_k2_timetable_load.py` and `bin/check`.
Not claimed: the run on the server; that is the orchestrator's dispatch.
