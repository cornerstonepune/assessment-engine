# M1-03 — the K2 screens' read calls

W3, step N9 (the voice notes' reader). No migration: queries in code. Part A is built; Part B waits on #364.

## Verified

- `cd packages/engine && uv run pytest -q tests/test_k2_reads.py tests/api/test_k2_routes.py` → 13 passed, on a local
  database built from every migration (`bin/testdb fresh`), placeholder rows only.
- `bin/engine done m1-03-k2-reads` → both of Nimish's sentences PROVED, all three criteria PASSED, "NOT DONE": not on
  main; Part B manual; the live database does not answer from the build container.
- `bin/check` → 33 passed. Neighbouring suites (voice intake, confirm, tables, cli, routes, loaders) → 56 passed.
- Routes `POST /k2/todo` and `POST /k2/coordinator` (JSON, engine key, `actor` = her email), 403 while
  `voice.screens_enabled` is off. `apps/web/lib/engine-routes.ts` regenerated with `bin/engine contract`.
- Query counts: todo 5, coordinator 8, the same for 3 notes or 43. Both well under 1 s (asserted, not loosened).

## Decisions made without an answer (the orchestrator was asked)

- **Late** = confirmations (not children) made on a later school day than the activity, since the week began.
- **Unplanned** = null with the reason in words. No plan or session table exists and no migration is allowed.
- **No notes this week** = two counts: children with no observation, and weekday class-days with no note received.
  School holidays are not known, so a holiday counts as a day with no note. Needs a calendar to be exact.
- Who may ask for the coordinator's list, which grades, how far back rows reach, week start: one config row `k2.reads`
  (seed only). It is added by `bin/engine load`, which must run on live before the routes are used.
- A note older than 48 hours is "left unconfirmed" by time, whether or not the hourly job has run yet.
- `voice_intake.resolve` takes optional lookups so a list uses the Confirm page's one rule without a query per note.

## Not verified / open

- Part B (class picture, child page): not started.
- On live: nothing run; the `k2.reads` row is not there until the seed loads.
- Test fixtures: two K2 classes must have different activity numbers (a number names one activity on the school's list).

## Handoff

- In flight: Part A in review. Next: Part B contract tests on fixture rows, then the real table after #364.
