# ADR 0008 — the engine becomes an HTTP service; n8n arrives now, not at N7

Date: 2026-09-19. Status: accepted.

## Decision

`ARCHITECTURE.md` §8 said n8n arrives at N7, "before that, a CLI run by a person is the honest
tool". That was true through Phase 1's proof-of-concept import; it stopped being true the moment
the same person ran the same CLI command twice over the same file and the graph counted every
paper's answers twice (STATE.md N3, HANDOFF.md 2026-09-18). Superseding a bad chunk 1: n8n now
orchestrates from **F3 read-and-respond** onward (N8/N9/N10), self-hosted in Docker on this
machine for the pilot, a Mumbai VPS before any teacher-facing run (SPEC §14.5). The engine gains a
FastAPI surface — `packages/engine/engine/api/` — matching the endpoints `ARCHITECTURE.md` §5
already named; handlers are plain `def` over the existing synchronous psycopg connection (a
`psycopg_pool.ConnectionPool` under load), not `async def` — a deliberate exception to the house
Python-backend rule (`~/.claude/rules/python-backend.md`), because FastAPI already runs a sync
handler in its own threadpool and the engine's database layer (`engine/db.py`) is synchronous
throughout; making one route async while the rest of the codebase is sync would buy nothing and
cost a second connection-handling convention.

Every route accepts an `Idempotency-Key` and writes it to `flow_run`; a repeat with the same key
returns the stored result. n8n's payloads carry ids and counts only — never a name, a path with a
name in it, or an image (rule 6) — enforced by a lint (`n8n/lint.py`) that also refuses a Code
node or an inline LLM node in any exported workflow, so ADR 0003's "n8n never thinks" stays true
as the workflows grow past three.

## Why

The double import was not a training mistake, it was the predicted failure mode of "a person is
the orchestrator": nothing recorded that the file had already been read, so nothing could refuse
to read it again. An idempotent HTTP endpoint plus a workflow that calls it once per trigger makes
the mistake structurally impossible rather than a discipline problem.

## Rejected

- **Waiting for N7 as originally planned.** Correct sequencing for a system with no repeated,
  unattended, human-in-the-loop trigger yet; wrong once N8/N9 (capture → read → confirm) is the
  actual daily loop, which is now.
- **A cron + a Python job queue, no orchestrator.** ADR 0003 already rejected this for F1–F3; the
  same reasoning applies to F3 read-and-respond, and F3 is the one queue-and-wait workflow that
  most needs a legible run history for a non-developer coordinator.

## Consequences

`ARCHITECTURE.md` §8's table is superseded by this ADR for F3 onward; the file should be updated
at the next full pass over it. Plan and chunk order: `docs/superpowers/plans/2026-09-18-spine.md`.
