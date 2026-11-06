# M1-12m: the held-out score read free, and the proposing run for the 281

## Verified
- `engine curriculum map-replay --stage held_out` (run choice `map_replay_held_out`, free): the activities the held-out
  run reached, how many passed on their own, how many of those were right, each share with its Wilson interval, the
  causes, and `unanswered` for the ones the cap cut off. Counts only; no activity is named (public log).
- `engine curriculum propose --estimate` (in `forecast`): the gaps still to propose and the average price of a proposer call
  already paid. Makes no call.
- `propose` takes `--stage`, `--version`, `--validate-version`, as the held-out eval does. Without them it asks as before.
- Run choice `map_propose` (spends): `propose --stage draft --version 3 --validate-version 2 --apply --by <dispatcher>`.
  It does not activate any prompt; the active version is a person's decision after the held-out bars.
- Tests: `tests/test_map_replay.py` (19), `tests/test_curriculum_run_command.py` (33), against a fresh database.

## Handoff
- Dispatch `map_replay_held_out` (free) first and read the interval; decide on `map_propose` after.
- Links made from proposals are marked `machine` plus the proposal id, not `drafted`; `apply` makes them and they can be reverted by id.
