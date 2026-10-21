# L14 — a migration on live waits briefly for a lock and tries again

Goal: `goals/l14-migrations-wait-for-locks.yaml`. (L9 was taken: `goals/l9-not-taught-is-said-where-it-shows.yaml`.)

## Verified

**The cause, from migrate live's own log** (run 39603041282 attempt 1, job 119232119365, read with `gh api`; nothing
run on live). 12:52:04 UTC "Applying migration 20261126090000_a_check_is_an_answer_a_person_was_shown.sql", 12:54:05
"canceling statement due to statement timeout (SQLSTATE 57014)", at statement 0: `create or replace view
answer_checked`. Replacing a view changes the catalogue only, milliseconds of work; the 121 s were spent waiting for
the view's exclusive lock while live's readers of `answer_checked` held theirs, until live's 2-minute statement
timeout fired. A waiting exclusive lock also queues every later reader of the view behind it, so educators' pages on
it waited too. Attempt 2 (13:25:28–13:25:42) applied it. I could not read live's Postgres log: the only Supabase project
this session reaches is another organisation's, so which query held the lock is not known.

**Rehearsed on this machine, never on live** (Postgres 16, supabase CLI 2.121.0, a view, one session holding
`select * from v` open for 20 s, a migration `create or replace view v`):

| | result |
|---|---|
| `PGOPTIONS="-c lock_timeout=3s -c statement_timeout=10min" supabase db push` | exit 1 after 5 s, "canceling statement due to lock timeout (SQLSTATE 55P03)" |
| `supabase_migrations.schema_migrations` after it | 0 rows, view unchanged: the failed migration rolled back whole |
| the same push once the reader finished | applied, version recorded |

The CLI runs `RESET ALL` before each migration (`pkg/migration/apply.go`); a setting given at connection start
survives it, as the 55P03 shows.

- `cd packages/engine && uv run pytest -q tests/test_deploy.py`: 20 passed. On main's `migrate.yml` the 5 new tests
  fail (5 failed, 15 passed).
- `bin/check`: 28 passed, lint clean.

**A second way migrate live fails: a migration older than live's newest.** `supabase db push` compares the local
files with the versions live recorded and, when a local one sorts before the newest recorded, stops with "Found local
migration files to be inserted before the last migration on remote database. Rerun the command with --include-all"
(supabase/cli `apps/cli/src/command-internal/migration-pending.ts` `findPendingMigrations`, and `db-push-core.ts`,
which raises it unless `--include-all`; the Go CLI's `pkg/migration/apply.go` the same). B2 (#240) held
`20261125090000` while live had main's `20261126090000`; the rehearsal applies with psql and cannot see it. B2's is
now `20261126100000`, and `tests/test_migration_order.py` fails any change whose added migration sorts at or before
`origin/main`'s newest, naming the file and a version to rename it to. It runs in `bin/check` and in CI's
`engine-checks` (full-history checkout, so `origin/main` is there; in CI a missing `origin/main` fails, never skips).

- With B2's old migration in the tree: `1 failed, 1 passed`, "supabase/migrations/20261125090000_question_types_are_rows.sql
  sorts before main's newest migration 20261126090000 … e.g. 20261126100000_question_types_are_rows.sql". With B2's
  renamed one: `2 passed`. On this branch: `2 passed`.

## Handoff

- Live: nothing yet. The first merge with a migration proves the one thing this machine could not: that live's
  connection takes PGOPTIONS (the step checks `show lock_timeout` is 3s and pushes nothing otherwise).
- Not changed, by the scope: `bin/update-live` runs the same `supabase db push` on live by hand, without these
  settings. `rehearse-update-live.yml` applies migrations only to its copy, with psql.
