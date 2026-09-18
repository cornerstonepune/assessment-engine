# HANDOFF — for the next session

Read `STATE.md` for what is verified and how. This file is what the last session left.

## Where things stand, 2026-09-19

**The architecture changed, not just the Growth screen.** Nimish pushed back hard on 2026-09-19:
the system had been built and run entirely by hand-typed CLI commands, against
`ARCHITECTURE.md`'s own stated design of an engine-as-a-service orchestrated by n8n. That gap is
what produced the double import (below) — nothing could tell a command it had already run. The
plan to close it is `docs/superpowers/plans/2026-09-18-spine.md`, seven chunks; ADRs 0007–0009
record the decisions. **Chunk 1 shipped this session**; chunks 2–7 (the FastAPI surface, n8n
itself, read validation, subject plugins, the reading-profile loop, CI/deploy) are next.

**Chunk 1, done:** `capture` is idempotent on content hash — `engine legacy import` of a file
already read for that child returns the existing capture and asks the model nothing; a prior
errored attempt retries into the same row. `engine legacy dedupe` fixed the historical mess: 28
captures hashed, 16 superseded (nothing deleted — rule 4), live confirmed evidence dropped from
218 to 133 real answers. The three active read prompts (`read_cells`, `read_page`,
`legacy_extract` v2) moved from `claude-sonnet-5` to `claude-haiku-4-5` — the $10 burn's actual
cause. `llm.generate()` now refuses a call before making it once today's spend reaches the
`llm.daily_budget_inr` threshold row (₹150 to start), and prefers a `prompt.subject`-scoped row
over the shared one for the same purpose (ADR 0009's seam for a second subject). PyMuPDF replaced
the `pdftoppm` subprocess — the transient failures that left 13 of 28 captures `status='error'`
cannot recur because there is no subprocess to fail. New tables `subject` (seeded: `NUM`),
`read_correction`, `child_reading_profile` exist but are empty — chunks 3 and 6 write them.

146 engine tests pass, 17 web screen tests pass, `engine load --check` is clean.

## Start here — chunk 2: the engine as a service

Per the plan: `packages/engine/engine/api/` (FastAPI), one route per existing engine function
(`/ingest`, `/read`, `/mark`, `/commit`, `/graph/rebuild`, `/bank/fill`, …), every route keyed by
`X-Engine-Key` and accepting `Idempotency-Key`, a `Dockerfile`, `deploy/compose.yml` with the
engine and n8n services. Then chunk 3 (validate the read, grow `gold`), chunk 4 (the first real
n8n workflow — F3 read-and-respond, on a local inbox folder, not Drive yet). **n8n MCP tools
became available mid-session** (user: "n8n mcp is connected now") but were not visible to this
session (`ToolSearch` for `n8n` found nothing) — check again at the start of chunk 4; if still
absent, build workflows as JSON and use `n8n import:workflow` from the CLI instead, which needs no
login (Nimish creates the n8n owner account once, per the plan's "What Nimish provides" table).

## Blocked on Nimish

- **The n8n owner account**, once chunk 4 starts a container — one-time, ~1 minute, see the plan's
  "What Nimish provides" table. Nothing else is needed to start chunk 4's local-folder trigger.
- `AUTH_SECRET` on Vercel if not yet set; **rotate the database password** (typed into a chat
  earlier, printed into a build log); re-copy or delete `SUPABASE_SERVICE_ROLE_KEY` (401s).
- The two Haiku 4.5 prices in `config.llm.prices` are an estimate (₹88 in / ₹440 out per million
  tokens) pending a verified figure at anthropic.com/pricing — the row's own `description` says
  so; correct it there when confirmed, nothing else changes.
- Achal's and Neha's emails for `app.staff`; consent text; parent-note channel; whether the
  Olympiad papers count; Kiyaan's missing Week 1; the VPS decision (D8 in the plan) before any
  teacher-facing run.

## Traps this session fell into, or found and fixed — do not repeat

- **A person as the orchestrator is not a stage of the architecture, it is a bug waiting to
  happen.** Every "run this by hand" step is a step nothing can make idempotent. Chunk 2 exists
  to remove the remaining ones; do not add a new CLI-only step without either an idempotency key
  or a stated reason n8n doesn't own it yet.
- **A partial unique index that guards "no two live rows share this value" also blocks a backfill
  that would momentarily create that state.** `dedupe()`'s first draft hashed one row at a time
  and wrote it immediately — the second of two identical files collided with the first's freshly
  written hash before either was marked superseded. Fixed by hashing everything in Python first,
  then writing a voided row's `file_sha256` and `superseded_by` in one statement, so it is never
  observed live-and-duplicate. If a future migration adds another such index, check whether the
  backfill that populates it needs the same treatment.
- **Changing a table's unique constraint breaks every hand-written `ON CONFLICT (columns)` that
  named the old column list** — `loaders.py`'s prompt upsert failed with "no unique or exclusion
  constraint matching" until its `ON CONFLICT` target was rewritten to match the new index
  exactly (`coalesce(subject, '')` included). Grep for `on conflict` against any table whose
  unique index changes.
- **A test that calls a tenant-wide admin function (here, `dedupe()`) against the shared live
  database cannot assert exact counts** — ambient production rows get swept up inside the same
  rolled-back transaction. Assert the effect on rows the test itself created; use `>=` or a
  membership check for anything touching the whole table.
- Never assemble a connection string with shell substitution; never run a migration while a fill
  is writing; the e2e suite writes to the live database; `roster` has been an unused import in
  `engine/legacy.py` since before this session — left alone rather than deleted in an unrelated
  diff (CLAUDE.md: pre-existing dead code is mentioned, not deleted).
