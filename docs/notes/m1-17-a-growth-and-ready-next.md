# M1-17 brick A — growth and ready-next, as pure functions

W3, gate N10 (reading side). Design: `docs/notes/m1-17-design.md` (PR #402). No migration, no model call, no screen.

## What changed
- `engine/w3_read/k2_growth.py` (new, on N9 beside `k2_picture_reads.py` in `workflows.json`):
  - `growth(seen, min_months)`: first seen, last seen, level by month (highest in the month, days seen), a trend
    (up / steady / down / too_few) from the latest two months seen. A gap month is a gap. No score.
  - `ready_next(links, states, done_states)`: skills ready from confirmed links only. Every hard link before it must be
    done; at least one confirmed link before it must be done. It has no "not ready" output.
- `min_months` and `done_states` are parameters; the caller reads them from config rows (brick B). Per the orchestrator,
  5 Nov: only `secure` is done; `secure_to_recheck` is not.

## Verified
- `cd packages/engine && .venv/bin/python -m pytest -q tests/test_k2_growth.py tests/test_layout.py` → 24 passed.
  The growth tests failed first (`ModuleNotFoundError: engine.w3_read.k2_growth`). `ruff check` and `ruff format --check` clean.
- Not run: the whole suite and `bin/check` (needs a database; CI runs them).

## Handoff
Next: brick B extends `POST /k2/child` with `plan`, `ready_next`, `growth` and adds the config rows (seed, no migration).
