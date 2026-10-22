# L14c — every path to live pushes through one step, on the CLI that was rehearsed

Goal: `goals/l14-migrations-wait-for-locks.yaml` (L14, its third slice). Starts from L14b (PR #261).

## Verified

**What was open after L14b.** `bin/update-live`, run by a person, ran `supabase db push` itself, without the
lock_timeout 3s / statement_timeout 10min lines, so a hand update could still queue educators' pages behind a lock.
And migrate live installed `supabase/setup-cli` `version: latest`, though the in-band settings rely on the CLI running
a migration's statements and its history row as one batch, which was rehearsed on 2.121.0 only.

**The fix.**
- `bin/push-migrations` is the one step that pushes to live: it writes the settings and their check as the first line
  of each migration, in a folder of its own (never the checkout: on a person's machine that is main, which the next
  `git pull --ff-only` must find unchanged), runs `supabase db push --workdir` on it, and tries a lock again six times
  20 s apart. migrate live's "apply what live is missing" step and `bin/update-live` step 2 both run it.
- migrate live pins the CLI at 2.121.0.
- `rehearse-update-live.yml` does not push to live: it reads live and applies migrations to its copy with psql, so it
  is unchanged. `bin/testdb` pushes only to the local copy, and the test names it as the one other push.

**Rehearsed on this machine, never on live** (Postgres 16, supabase CLI 2.121.0, PGOPTIONS unset, a session holding
`select * from v` for 15 s, a migration `create or replace view v`, run as `LIVE=<local> bin/push-migrations`):

| | result |
|---|---|
| try 1, the reader holding `v` | "canceling statement due to lock timeout (SQLSTATE 55P03) At statement: 3", then "try 1 of 6 … trying again in 20 s" |
| try 2, the reader gone | "Finished supabase db push.", 26 s in all |
| `schema_migrations` | one row; its first statement is `set lock_timeout = '3s'` |
| the checkout's migration | unchanged; no `supabase/.temp` left in it |

- `cd packages/engine && uv run pytest -q tests/test_deploy.py`: 25 passed. The same tests on L14b's `migrate.yml` and
  `bin/update-live`, without `bin/push-migrations`: 10 failed, 15 passed.
- `bin/check`: 29 passed, 1 skipped.
- `bin/engine done l14-migrations-wait-for-locks`: all 9 sentences PROVED, all 3 criteria PASSED; NOT DONE only for
  "not on main yet" and "the live database did not answer from here".

## Handoff

- Live: nothing yet. Merging after #261 re-runs migrate live through `bin/push-migrations`.
- A person's own CLI is not pinned: `bin/update-live` uses whatever `supabase` they have. If a future CLI stopped
  running a migration as one batch, the migration's own check raises before any change, so it fails safe, never silent.
- Next: the first merge with a migration proves the rest (the manual line in the goal).
