# CI: a pull request starts only the jobs its change can break (not a workflow gate: a CI chore)

Goal: `goals/ci-fast-paths.yaml`, proved by `bin/engine done ci-fast-paths`. Tier 3 (`.github/`), scope approved by Nimish in chat 2026-11-05.

## Verified

### Why the queue formed (measured 2026-11-05, from GitHub's API)

| claim | command | result |
|---|---|---|
| a pull request's ci run starts 19 jobs (not ~16) | `gh api repos/cornerstonepune/cornerstone-platform/actions/runs/41972429785/jobs` | 19 jobs: engine-checks, 12 engine shards, engine, web, 3 browser shards, browser |
| the jobs ran for minutes and waited for tens of minutes | same, `started_at - created_at` against `completed_at - started_at`, runs 41972429785 and 41971536993 | longest job 16–17 min; average wait **39 and 29 min**, longest wait **82 and 51 min**; 175–196 job-minutes per run |
| the cause is GitHub's cap on jobs running at once, not slow tests | every job of the last 40 runs (269 finished, not cancelled), the number running at each start while another waited | **median 20, maximum 20** running whenever anything waited; never above 20 |
| most pushes were wasted | `actions/runs?event=pull_request`, the 30 newest ci runs | 16 cancelled, 8 queued or running, 6 succeeded |
| every open draft is an engine pull request | `bin/ci-plan decide` over the files of the 10 open pull requests | all 10 touch `packages/engine/` or `bin/` |

The cap is 20 (the figure ci.yml's own comment gives for the free plan); I could not read the plan itself (the organisation endpoint is
closed to this session), so 20 is what the runs show, not what the plan states.

### Jobs started per change, before and after (counted from `bin/ci-plan`; "light" = seconds, no checkout of the suite)

| change | before | after |
|---|---|---|
| a draft, any change | 19 | plan + engine-checks + engine + browser (2 light) = 4; plus web when more than documents changed = 5 |
| ready, documents alone | 19 | 4 (the same) |
| ready, the website alone | 19 | 9: plan, engine-checks, web, 3 browser shards, browser, engine (light), 1 runner for the engine tests that read the website |
| ready, anything else; main; the nightly run | 19 | 20 (the 19 and `plan`) |

### The decision, held without GitHub

`cd packages/engine && uv run pytest -q tests/test_ci_plan.py` — 79 passed: each of the five rules for sample changed-file lists, the
workflow's `if` read against each plan, the names the gates wait on, and a docs list that nothing reads.

## Decisions to know about

- **A draft beats rule 5.** The scope says drafts run only the fast checks, and that a change under the engine, schema, seed, map,
  gates "always runs everything". All 10 open drafts touch the engine, so letting rule 5 win inside a draft changes nothing for any of
  them. Rule 5 therefore applies to a ready pull request and to main. One line to flip: the order of the two checks in `decide()`.
- **Documents.** The docs-only list is explicit (`DOCS_PREFIXES`, `DOCS_FILES` in `bin/ci-plan`). Tests read more documents than
  expected (`BUILD-ORDER.md`, `DECISIONS-LOG.md`, `docs/design/`, `docs/sources/*.md`, `docs/crosswalk/`, `docs/spine/`,
  `docs/ux-rules.md`, `docs/md-taxonomy.md`, and three notes), so those, and those notes, are off the list; the test fails the day
  a test starts reading a listed file.
- **The website alone** still runs the engine test files that read (27 on 2026-11-05) `apps/web` (87 of their tests need the database), on one runner:
  skipping them would let a website change break the UX rules or the sign-in gate unseen.
- **Fast checks** now include `bin/check` (the map, the promises, types, contract, lint), run by engine-checks on every change.
- **Nightly.** `schedule` is in ci.yml. migrate live and deploy engine start from any ci run on main that succeeds, so the nightly run
  triggers both; each is idempotent (db push applies what live lacks, deploy skips when nothing it runs changed).
- **No required checks are set** on this repository (`branches/main/protection` answers "Branch not protected"; `rulesets` is `[]`).
  Names are unchanged regardless: `engine`, `web`, `browser`, `engine-checks`, `engine shard N`, `browser shard N`.
- `actionlint` could not be fetched in this session, so the workflow's syntax is checked by GitHub's own parsing of the pull request run.

## Handoff

- Live: nothing; the workflow takes effect on the pull request that carries it.
- In flight: pull request from branch `ci-fast-paths` (draft), then a docs-only draft to show the quick path.
- Next: after merge, watch the first week's queue (`gh api …/actions/runs`); if the cap still binds, the next lever is fewer shards, not more rules.
- Blocked: nothing.
