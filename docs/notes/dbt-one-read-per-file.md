# dbt-one-read-per-file — "Read again" pressed several times stopped every reading but one (fault fix, no gate moved)

Nimish, 2026-10-26, on Mark / Upload: one 23-page file, "Read again" pressed several times; several lines of the same
file said "reading stopped … QueryCanceled: canceling statement due to statement timeout CONTEXT: while inserting index
tuple (14,44) in relation "sheet_instance""; one earlier line of it read 11 copies. Goal: `goals/dbt_one_read_per_file.yaml`.

## Verified

Local only (this container's Postgres 16, `bin/testdb fresh`). The live database and its logs were not reachable.

| Claim | Command | Last output |
|---|---|---|
| The live message is a wait on another transaction's open row with the same `qr_code`, not on a migration | two `psql` sessions: A runs the reading's own `insert into sheet_instance … on conflict (tenant_id, qr_code) do update` and holds it open; B runs it with `statement_timeout = '2s'` | `ERROR: canceling statement due to statement timeout` / `CONTEXT: while inserting index tuple (0,15) in relation "sheet_instance"` |
| A table lock (what a migration takes) gives no such context | A: `lock table … in access exclusive mode`; B as above | `ERROR: canceling statement due to statement timeout` (no CONTEXT line) |
| No migration or deploy overlapped 07:16–07:17 UTC | GitHub Actions `migrate.yml`, `deploy-engine.yml` | migrate 05:28–05:29 and 07:48–07:49; deploy 05:28–05:37 and 07:48–07:52 UTC |
| A second reading of a file being read is refused, on any line of it, and two presses at once start one | `cd packages/engine && uv run pytest -q -o addopts= tests/test_one_read_per_file.py` | `6 passed` (5 failed before the fix) |
| A file read again is one line, its other readings inside; no "Read again" while it reads | `cd apps/web && npx playwright test tests/u64-a-file-read-again-is-one-line.spec.ts` | `2 passed` (failed before: 4 lines for the file) |

**Cause.** `inbox.read` reads a whole file on one connection in one transaction (`copies.read`, committed only when every
copy is read, minutes for 23 pages), and each copy's `legacy.import_scan` upserts that copy's `sheet_instance` row by its
code. "Read again" (`inbox.again`) refused only if the line pressed was still reading; the screen hides the button on
that line only. Pressed on an earlier line of the same file, a second reading started, reached the first copy, and waited
on the first reading's uncommitted row until the statement timeout cancelled it. Each further press did the same. The
reading that was already going on finished (the 11-copy line).

**Fix.** `inbox.start` (every route that starts a reading: a Drive link, an upload, "Read again") and `inbox.give` refuse
a file another run is reading ("this scan is already being read …"), under an advisory lock on the file's name so the
look and the insert are one step. `lastScans` folds a file's runs into one line: the reading going on, else the newest
that finished, else the newest; the others inside it.

**Not certain.** The live statement timeout is assumed to be about 2 minutes (ADR 0024 measured `show statement_timeout`
→ `2min` through the pooler); not re-measured. A reading still holds every copy's row until the whole file is read.
Besides a second reading, the only other writer of an existing copy's row is printing (`handout.py`, `pack.py` mark it
printed); printing a copy whose file is being read at that moment would wait for the reading. Not seen, not fixed here:
committing copy by copy changes what a stopped reading leaves behind (copies kept that its line does not count), which is
a change of its own.

## Handoff

- Live: nothing until merged; no migration.
- Next: after the deploy, tap Read again once on the 24 Oct file and let it finish.
- Blocked: nothing.
