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

## Verified
_(filled at the end of the session, below)_

## Handoff
- PR B (one migration, after this is merged and live): a way to clear a note waiting for a person (through `ml.add`), `material_alias` and approved unit conversions as rows, and the widened state check.
