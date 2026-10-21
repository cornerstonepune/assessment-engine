# The rehearsal compares live and its copy in one snapshot (W1, gate 3)

Goal: `goals/rehearsal-same-snapshot.yaml`, proved by `bin/engine done rehearsal-same-snapshot`.

## The problem

`rehearse update-live` dumped live with `pg_dump`, then counted each live table with a fresh query a few minutes
later and required the copy's counts to equal those. In school hours educators make papers in that gap: run
39562277664 on #234 (B1) failed twice, `sheet_template` 7982 on the copy against 7995 on live, before the rehearsal
tested anything. Every backend step (B0–B4) would meet the same wall.

## The fix

`engine live copy` (`engine/checks/live_copy.py`) does the step the workflow did in shell: it opens one read-only,
repeatable-read transaction on live, exports its snapshot (`pg_export_snapshot`), dumps with `pg_dump --snapshot`,
and counts live's tables inside that same transaction, so live's counts are exactly the dump's. The copy is restored
and counted; any table whose count differs fails the step, as before. Live is only read; no address is printed (a
failing `pg_dump` reports its own error, never its command line). Rejected: counting the dump file itself, which
would compare the copy with the dump and no longer with live.

## Verified

Run 2026-10-21 on Postgres 16 in this session's container, two scratch databases standing in for live and its copy.

- The drift no longer fails the step: `bin/engine done rehearsal-same-snapshot` → all four tests PROVED,
  `tests/test_live_copy.py` 4 passed, `bin/check` 28 passed. It ends "NOT DONE" only for "not on main yet" and
  "the live database did not answer from here", which this container cannot change.
- The test reproduces the bug: with live counted by a fresh query after the restore (the old order),
  `test_a_paper_made_while_the_copy_is_made_does_not_fail_it` fails `assert 6 == 5`, as run 39562277664 did.
- The command end to end: `LIVE=… COPY=… bin/engine live copy` on 7982 rows → "copied: 2 tables, 7982 rows, every
  count equal to live's snapshot", exit 0.
- Not run here: `tests/test_cli.py` needs a database built by `bin/testdb fresh` (3 fail on "relation does not
  exist" in this empty container); CI builds one.

## Handoff

- Live: nothing; the workflow changes when this merges.
- Next: after merge, bring main into #234's branch and run Actions → rehearse update-live on it, in school hours
  (the goal's `manual` line).
- Blocked: nothing.
