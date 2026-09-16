# Cornerstone Assessment Engine

Worksheets in, per-child skill understanding out. Grades 1–4 addition and subtraction first.

- `SPEC.md` — the design: tables, flows, how a worksheet is parsed, what comes out.
- `CLAUDE.md` — how this repository is built; binding for every session.
- `STATE.md` — what is verified true, with the command that proves it.
- `docs/adr/` — why each alternative was rejected.

Layout: `packages/engine` (Python), `apps/web` (Next.js), `supabase/` (schema and seeds),
`n8n/` (workflows). Raw scans and renders live in `data/` and never in git.
