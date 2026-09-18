-- Chunk 2 of the spine (docs/superpowers/plans/2026-09-18-spine.md): the HTTP idempotency wrapper
-- needs somewhere to put a route's response so a repeat with the same Idempotency-Key can return
-- it without running the operation again. `request` (added in service_foundations) holds the ids
-- going in; `result` holds the ids and counts coming out — never a name or an image (rule 6).

alter table flow_run add column result jsonb not null default '{}'::jsonb;
