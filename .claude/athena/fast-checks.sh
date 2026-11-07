#!/bin/sh
# Teacher OS's fast checks, run before a session ends and on every pull request (ATH-14):
#  - the engine's tests that need no database, its lint and its code against workflows.json
#    (bin/check: pytest under packages/engine, ruff);
#  - the website's Playwright specs under apps/web, listed, so a spec that no longer loads fails here.
# The full suites, with a database and a browser, run in CI on every pull request (.github/workflows/ci.yml).
set -e
root=$(cd "$(dirname "$0")/../.." && pwd)
"$root/bin/check"
# Listing loads every spec without running one, so it needs no database: the config only asks the address be local.
cd "$root/apps/web" && TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql://127.0.0.1:5432/postgres}" npx --no-install playwright test --list > /dev/null
