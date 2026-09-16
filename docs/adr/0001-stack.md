# ADR 0001 — Python engine + Supabase Postgres + self-hosted n8n + thin Next.js

Date: 2026-09-16. Status: accepted.

## Decision

The existing Python `assess/` prototype is the engine, wrapped in a small FastAPI. Supabase
Postgres (Mumbai when deployed) is the only store. n8n, self-hosted in Docker, is the control
plane. A Next.js app renders the six screens and reads the database directly.

## Why

- The prototype's generation, rendering, deskew, QR and cell-crop pipeline is ~1,100 lines,
  clean, and already validated end to end (cell geometry agreement 1.0 on the synthetic
  roundtrip). Its only stub is the digit reader, which becomes a vision adapter.
- Image work (OpenCV, Playwright PDF) is native to Python. Rewriting it in TypeScript re-derives
  solved problems and delays the first real result by weeks.
- One Postgres with `tenant_id` and RLS from the first migration is what lets this become the
  shared backend for every later Cornerstone product without a data migration.
- n8n was explicitly requested as the orchestration layer and fits the "trigger → step → human
  confirm → write" pattern; keeping logic out of it is a rule, not a hope.
- Supabase's grain is TypeScript, so the app is TypeScript; server-rendered pages survive
  classroom 4G.

## Rejected

- **All-Python monolith (FastAPI + server-rendered HTML, SQLite).** Fewest parts and fastest to a
  demo, but no orchestration layer, a UI that would not match the approved mockup without much
  more work, and a second store to migrate away from later.
- **TypeScript rewrite per platform-architecture-v1.1's "one toolchain".** Cleanest story, but
  throws away validated code and puts the one genuinely uncertain step (handwriting reading) into
  a language where the image tooling is weaker. That document already anticipated "Python later,
  as one worker"; this is that worker, earlier.

## Consequences

Two runtimes to operate (Python, Node) plus n8n. Accepted because each has exactly one job. If a
second school needs different residency, or three developers work concurrently, the engine's
endpoints are already the seam to split on.
