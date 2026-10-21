# CI: the engine tests in parallel (not a workflow gate: a CI chore)

Goal: `goals/ci-engine-shards.yaml`, proved by `bin/engine done ci-engine-shards`.

## Before: measured 2026-10-21

Main's CI run 737 (merge of #239, `e5bf88a`), read from GitHub's job steps:

| job / step | time |
|---|---|
| **engine, whole job** | **37 min 41 s** |
| set-up (checkout, Postgres, uv, lint, ratchet, Chromium, caches) | 50 s |
| `bin/testdb fresh` | 5 min 37 s |
| `pytest --cov` | 31 min 11 s ("2605 passed, 2 skipped … in 1867.31s") |
| coverage | TOTAL 14389 statements, 2025 missed, **85.93%** (floor 79.5) |
| browser, whole job | 16 min 43 s (its own `bin/testdb fresh` 5 min 46 s, Playwright 9 min 48 s) |
| web | 49 s |

The brief said "about 26 minutes" for the engine and "about 7" for the browser: both were higher on the day.

**Where the database build goes** (this container, Postgres 16, `bash -x bin/testdb fresh`): 6 min 50 s in all, of
which `engine bank refill` 6 min 33 s, single-core Python (user 6 min 24 s). Migrations, `engine load` and
`engine library build` take seconds. The bank is drawn with fresh randomness on purpose
(`docs/notes/bank-fills-every-time.md`), so it is rebuilt on each runner, never cached: a cached bank would stop
CI from drawing a new one each run.

**Collection** of the whole suite: 3.8 s (2607 tests).

## The design

- `engine-checks`: lock, ruff, ratchet; no database, beside the shards.
- `engine shard 1…14`: each builds its own database, started in the background so Chromium and the caches install
  beside it; collects the whole suite; takes its cut (`bin/ci-shard pick`: whole files, slowest first to the least
  loaded runner, from `.github/ci-durations.json`); runs it with coverage, no floor; uploads its report and data.
- `engine` (the name required checks and the deploys know): every shard and the checks green; `bin/ci-shard check`
  (every runner collected the same suite, the cuts are disjoint and cover it, each shard's junit count equals its
  cut); `coverage combine` then `coverage report`, which applies pyproject's `fail_under`.
- The deploys (`migrate.yml`, `deploy-engine.yml`) wait on the workflow `ci` completing, not on a job name, so they
  are unchanged.
- Caching: uv's cache was already on (setup-uv, "Cache hit occurred"). Chromium's install (16 s) now runs beside the
  database build, so caching it would save nothing on the critical path.

## Verified

(filled from the PR's CI run)

## Handoff

- In flight: PR #246.
