# L14b — a migration's timeouts travel inside the migration

Goal: `goals/l14-migrations-wait-for-locks.yaml` (L14, its second slice).

## Verified

**What happened, from migrate live's own logs** (read with the GitHub API; nothing run on live).

- Run 39709016021 (commit 1a82d28), attempt 1 at 02:01:17 UTC and attempt 2 at 02:09:39: "live's connection ignores
  PGOPTIONS, so a migration would wait on educators' locks again", 1.6 s after the step began, both times. Each then set
  `live database` to failure on 1a82d28, and Vercel's Deployment Check held the website (Vercel: failure, 02:01:20).
- Run 39708927072 at 02:00 did **not** pass the check: it was CI's run for 3ea0b00, and its job stopped at "main has
  moved on to 1a82d28" without touching live. So the check is not flaky. It ran twice ever (L14 merged at 01:05) and
  failed twice.
- `db push` had nothing to apply (B2, B3 are not merged), so the website was held over a check, not a change.

**Why.** PGOPTIONS travels as the connection's startup `options`. Live is reached through Supabase's pooler, not the
database directly:
- the repository records `DATABASE_URL`, which `LIVE_DATABASE_URL` copies (`migrate.yml`'s header), as
  `aws-0-ap-south-1.pooler.supabase.com:5432`, the session pooler (`docs/superpowers/plans/2026-09-17-phase-0-foundations.md`);
- ADR 0024 measured the pooler dropping `options=-c statement_timeout=…` (`show statement_timeout` → `2min`).

I could not read the secret itself (GitHub does not return secret values), so its host and port are as recorded, not
as read. Supabase's timeouts guide (supabase.com/docs/guides/database/postgres/timeouts) says a session-level `set`
works through the session pooler (5432) or a direct connection, and a transaction-level setting works in either
pooler mode. The L14 rehearsal passed because it connected to Postgres directly, which honours startup options.

**The fix.** The push step writes `set lock_timeout = '3s'; set statement_timeout = '10min';` and a check (`do $$ …
raise exception … $$`) as the first line of each migration in its own checkout before `db push`. The CLI runs a
migration's statements and its history row as one batch, so the settings and the check run in the migration's own
transaction, on the backend that runs it, in either pooler mode. The second-connection psql check and PGOPTIONS are
gone. With nothing to apply, nothing runs, so nothing can fail.

**Rehearsed on this machine, never on live** (Postgres 17, supabase CLI 2.121.0, PGOPTIONS unset, a session holding
`select * from v` for 15 s, a migration `create or replace view v`, the files rewritten by the step's own lines):

| | result |
|---|---|
| first push, the reader holding `v` | 5 s, "canceling statement due to lock timeout (SQLSTATE 55P03) At statement: 3" |
| `schema_migrations` after it | 0 rows: the settings, the check, the view and the history row rolled back together |
| second push, the reader gone | applied; its recorded statements start with the two `set`s and the check |
| the check alone, without the `set`s | `ERROR: this migration's session did not take lock_timeout 3s and statement_timeout 10min` |

- `cd packages/engine && uv run pytest -q tests/test_deploy.py`: 22 passed. With main's `migrate.yml` and these tests:
  6 failed, 16 passed.
- `bin/check`: see the PR.

## Handoff

- Live: nothing yet. Merging this re-runs migrate live; with nothing to apply it sets `live database` green on its
  commit and Vercel releases that build.
- The first merge with a migration proves the rest: its `schema_migrations` row on live starts with the two `set`s.
- Not changed: `bin/update-live` still runs `db push` by hand without these settings; migrate live uses
  `supabase/setup-cli` `version: latest`, so a CLI that stopped running a migration as one batch would be caught only
  by the check raising (it fails before any change, never silently).
