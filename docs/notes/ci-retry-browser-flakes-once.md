# ci-retry-browser-flakes-once

Nimish, 2026-10-23: "can we ensure that we don't run the full tests again in case of such one-off failures that you know aren't going to impact the product". A CI chore outside the W1–W3 gates (no workflow code, prompt, migration or screen). Decision: ADR 0094.

## Verified

| Claim | Command | Last output |
|---|---|---|
| CI retries a failed browser test once, a laptop never | `cd apps/web && npx playwright test tests/p5-ci-retries-once.spec.ts` (runs in the browser job) | not run locally (needs the CI database); its helper is checked by the gate test below and the spec is listed under both `CI=1` and unset by `playwright test --list` |
| The config, the CI step and the summary script are wired, and a later edit cannot undo it | `cd packages/engine && .venv/bin/python -m pytest -q tests/test_gates.py` | 8 passed; with the config and ci.yml reverted the new test fails (1 failed, 7 passed) |
| A retried-then-passed test is `flaky`, a twice-failed one is `unexpected`, and the summary lists only the first | probe of two tests and a throwaway config under `CI=1`, then `bin/ci-flaky-summary <results.json>` | stats `expected 1, unexpected 1, flaky 1`; summary: "1 flaky browser test … `probe.spec.ts:2` flips once (2 attempts)" |
| The "no test skipped or left unrun" step still fails on `skipped` and `unexpected`; only `flaky` no longer fails it | `test_gates.py::test_a_browser_test_that_fails_is_run_once_more_in_ci_and_flaky_ones_are_listed` | passed |
| The code still sits on the map; lint | `bin/check` | 30 passed |
| The browser job on this PR | the PR's `browser` check | see the PR |

u50's setup: the capture now waits for the page to load, its fonts to be laid out and two painted frames. The cause of the run 39921528802 failure ("Unable to capture screenshot") was not reproduced; this is the likeliest cause (a capture before the first paint), not a proven one. If it recurs it will show as flaky in the summary, naming this test.

## Handoff

- Live: nothing; this is CI only, no deploy.
- Next: after merge, read a few runs' summaries. A test listed as flaky more than once is a real bug to find, not to retry.
- Not done on purpose: no limit on how often one test may be flaky (Nimish: visibility is enough for now).
