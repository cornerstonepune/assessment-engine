# M1-10 — the K2 educator's materials list (engine side)

**Gate:** W2, step N4 (files added to the step, no thirteenth step; the orchestrator agreed, 4 Nov). Goal: `goals/m1-10-materials-list.yaml`.
Screens are 4b's; this branch is the migration, the engine and its routes. Everything is behind `educator.timetable_enabled` (default off, M1-06's row, #379; read only here).

## Verified (4 Nov, on a database built from the migrations alone, M1-11's included)
- `bin/check` → `34 passed`.
- 61 materials tests plus `tests/test_rules.py` → `64 passed`. Written first and seen failing (import errors) before the code.
- 12 shards, each on its own clone of the fresh database, 3495 tests (`bin/ci-shard pick`): shards 1-11 green; shard 12: `2 failed, 445 passed`, both `tests/test_spine_provenance.py`, which download NCERT PDFs and fail TLS verification in this container (`CERTIFICATE_VERIFY_FAILED`). Not this change; CI runs them.
- `/code-review` (medium): 9 findings, all fixed with a test each. `/simplify` (4 angles): applied; skipped batching of the line/source inserts (lists are tens of lines) and one shared tenant lookup (about eight other modules repeat it; outside this diff).
- NOT verified: rehearse-update-live (runs on the pushed branch; the orchestrator dispatches it, `states_may_change=false`); the FN10 scenario S-M1-10 (nothing yet writes sessions or maps planner lines to activities, so the real list cannot be built; the tests use placeholder rows, and no walkthrough on the real FN10 list was possible); a real WhatsApp send; the email route (the engine has no mail sender: it records "not configured", and nothing is sent).

## Handoff
- **Box timer** (counts only, sends nothing; the educator sees reminders in her inbox):
    30 2 * * * docker exec deploy-engine-1 engine reminders --due >> /var/log/materials-reminders.log 2>&1
- Open: Nimish names the materials team's number (`materials.whatsapp_to`); until then the link opens WhatsApp with nobody chosen. A new catalogue item waits on `material_item_proposal` (state `needs_person`), not on M1-11's proposal ledger (the orchestrator's call, 4 Nov).
- The goal's quotations are the orchestrator's relay of D-070/D-071, not re-read in teacher-os.
