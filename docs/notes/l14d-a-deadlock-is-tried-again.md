# L14d — a migration caught in a deadlock with live's readers is tried again (goals/l14-migrations-wait-for-locks.yaml)

## Verified

- **The cause, from migrate live's own log** (run 39823627039, job 119981033514, 2026-10-22 17:32 UTC, read through the
  GitHub API; nothing run on live): applying `20261201090000_the_rung_folded_into_the_skill.sql` (B4), at statement 12,
  `alter table item drop constraint if exists item_tenant_id_rung_code_fkey`: "ERROR: deadlock detected (SQLSTATE
  40P01) — Process 3691309 waits for AccessExclusiveLock on relation 17858; blocked by process 3691293. Process 3691293
  waits for AccessShareLock on relation 18427; blocked by process 3691309." The migration held one table's lock and
  waited on another that a reader of live held while the reader waited on it. Postgres rolled the migration back whole
  (it runs in one transaction with its history row), so live is unchanged and the website stayed held ("live's
  migration failed; the website stays as it was"). `bin/push-migrations` tried again only on 55P03 and stopped.
- **Fix:** a 40P01 is tried again the same way as a 55P03 (six tries, 20 s apart); any other failure still stops at once.
- **Tests:** `tests/test_deploy.py::test_a_migration_caught_in_a_deadlock_tries_again_by_itself` failed before the
  change (one push, then stop) and passes after; `tests/test_deploy.py`: 27 passed. `bin/check`: 30 passed.

## Handoff

- **Live:** B4's migration is not on live. After this merges, its own `migrate live` run pushes what live lacks, B4's
  included, and tries again on a deadlock.
- **Not done:** which reader of live held the lock is not known (live's Postgres log is not reachable from here).
