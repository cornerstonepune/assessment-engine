# M1-16 brick 1 — the month build, the cost report, no empty builds (PR A, no migration)

**Gate:** W2, step N4 (files and commands added to the step in `workflows.json`). Goal: `goals/m1-16-materials-consolidated.yaml` (same goal; this is its first follow-on brick). Decided by the orchestrator, 4 Nov. **No migration, no model call, no spend.**

## What it does
- **`engine materials month --from D --to D`** (and the coordinator's Build route): builds a list for each class and each fortnight the class has a planned session of a mapped activity in, then the school's list, and names the classes it is short of: `no_plan` (a class whose grade has activities and whose school year the month touches, with no planned session to build from) and `no_materials` (a plan that asks for no materials). A class of a grade with no activities is not expected to have a plan. Nothing is built for a class with no plan.
- **The text sent to the inventory person** gains a line per kind of shortness ("Not included: K2 A (no plan yet)"), so the list says what it is short of instead of looking complete.
- **`engine materials cost`**: this month's calls, failed calls, tokens, rupees and dollars against the campaign `m1-16`'s cap, and the average tokens per call, read from `flow_run`. It never calls a model. `llm_budget.window_start` is now public for it.
- **An identical build is not stored.** A build with the same lines, sources and skipped lists as the last makes no new build and no rows, so the school list's "what changed" is the last real change, not an empty one.

## Limits (plainly)
- A planned session on a day that no `fortnight` row covers cannot be built into a list (a list is for a fortnight) and is not named. Not seen on any real data yet.
- The shortness is computed now, from today's plans, when the text is sent; it is not stored with the build.
- Needs real sessions (M1-06 part 2) and mapped planner lines (M1-05) to have anything to build from; with none, every class is `no_plan`, which is the true answer.

## Verified (4 Nov, on a database built from the migrations alone; this brick adds no migration)
- Tests written first and seen failing (import errors; the identical-build and command-exists tests failed on behaviour), then passing: the month build, the cost report, the identical-build skip, the "Not included" footer, the range cap, the route. 71 tests across the files touched. `bin/check` → 34 passed. Ruff and pyright clean.
- `/code-review` (medium): 8 findings. Fixed with a test each: the footer was worked out from today's plans while the lines came from the stored build (it now reads the stored build); sessions on days no fortnight covers were called "plan asks for no materials" (own bucket `no_fortnight`); the cost report counted a running call as failed and hid unknown spend (it now mirrors the gate); no cap on the range of a month build (setting `materials.month_build_max_days`, 62). **Not fixed, with reasons:** `engine materials cost` is not behind `educator.timetable_enabled` (it only reads, and an operator should see spend even with the screens off); a month build refreshes lists already sent (carrying later changes into the school list is the requirement, and the sent text stays recorded); the changes of the latest build stay visible after an identical rebuild (by design).
- `/simplify`: applied. The class-coverage helpers moved out of `materials_consolidate` into `materials_coverage`; the school list's shortness is read from the stored build (no second gather); the route returns every shortness; the reasons live beside the buckets (`WHY`); the cost report finds its campaign by purpose (`llm_budget.campaign_for`). **Not done:** merging `_stored_shape` into `_totals` (risk to the change-noting code for little gain); a shared SQL fragment for the planned-session join (the two uses need different columns); a tenant helper for the CLI (about eight modules inline it).
- Whole suite in 12 shards: see the PR.

## Handoff
- PR B (one migration, after this is merged and live): a way to clear a note waiting for a person (through `ml.add`), `material_alias` and approved unit conversions as rows, and the widened state check.
