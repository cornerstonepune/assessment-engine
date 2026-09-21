# 0025 — Tests and goal runs use a local copy of the database, never the live one

Date: 2026-09-21
Status: accepted (step 1 of the five, `BUILD-ORDER.md`)

## Context

Until today the engine's test suite, the Playwright end-to-end tests and every `engine goal` run
wrote to the one live database that the website and the school's engine server read. Since
2026-09-17 that database has taken 1.27 million `activity` inserts, 1 million `learning_objective`
inserts and 10,776 `child` inserts — the loader and fixtures run again and again by tests. On
2026-09-21 its checkpoints took 127–203 seconds to write under 1 MB, hour after hour, on the free
tier's small disk allowance, and the live website timed out while suites ran (`STATE.md`, 13:05 IST).
A test is also a risk to the data itself: the approval e2e test once left `approved_by` on nine
real sheets.

## Decision

A copy of the live database on this Mac — Supabase's own Postgres image in Docker, built from this
repository's migrations (`supabase db start`, port 54322), holding the live rows (`bin/testdb`,
~10 s, every table's row count compared with live). `TEST_DATABASE_URL` names it.

- `packages/engine/tests/conftest.py` points every test at `TEST_DATABASE_URL` before any test
  connects, and refuses to run at all if that address is not this machine.
- Playwright starts its own production build and its own engine against the copy.
- `engine goal` runs its scenarios against the copy.

The live database sees the website, the engine server, and deliberate jobs (a bank fill, the
worksheet build, a re-read) — each run on purpose and recorded in `STATE.md`.

## Rejected

- **A second Supabase project for tests.** It changes the account and may cost money, and it would
  still be a remote database with the same small disk allowance.
- **Keep sharing, run tests less often.** The damage is per run, and a goal is meant to be run until
  it is green.
- **An empty test database with seeds only.** The bank's 12,567 questions and the 867 read answers
  are the data the tests reason about; the reads cannot be regenerated for free. The copy is the
  live rows.
