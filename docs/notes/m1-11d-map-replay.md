# m1-11d: read a dev-set run of the mapping agents back from the replies flow_run kept

## Verified
- `cd packages/engine && uv run pytest -q tests/test_map_replay.py tests/test_curriculum_run_command.py tests/test_map_stage.py` → 8 + the others passed (local, fresh database).
- `bin/check` → rc=0 (layout, promises, types, lint, 34 tests).
- A scripted dev-set run, stored as flow_run rows and read back, scores exactly what the run scored
  (`test_a_run_rebuilt_from_its_stored_replies_scores_what_the_run_scored`).
- Not verified: the real run of 2026-11-04. It was made before the activity code was kept on each row, so it is aligned
  by call order. The replay prints the score it rebuilt; it must equal the run's own line (0.857 / 0.953 / 0.28).
- 7 tests in `tests/test_k2_day.py` fail on this machine's fresh database with and without this change (timetable rows
  are not in a database built by `bin/testdb fresh`); not this change's.

## Handoff
- New: `engine curriculum map-replay` (read-only) and a `map_replay` choice in the curriculum run workflow.
- `flow_run.request` now also holds `about` (the activity or page asked about) for every new call.
- Next: dispatch `map_replay` after deploy; read the counts by cause; then decide the smallest change toward 0.90 / 0.60.
- Not built: vendor-enforced structured output (named in M1-11c; needs its own goal and an eval).
