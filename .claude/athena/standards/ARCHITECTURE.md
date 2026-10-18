# Architecture standard

Open this before designing a new system, module, data model or integration, or any change that adds a moving part. Where the repository's own `ARCHITECTURE.md` or `docs/adr/` is more specific, the repository wins; this file covers what it doesn't say.

## Before you design

1. Read what exists: the repository's `ARCHITECTURE.md`, `docs/adr/` and `docs/decisions/`. Search the code (`graphify query` where the repository has it) before reading files.
2. Adopt before you build. For anything generic (auth, queues, notifications, admin panels, payments, file storage), pick a well-maintained open-source option and say why in the pull request.
3. Write the design down: the problem in two sentences, the parts, how data moves between them, and what you rejected and why. Architecture goes in `docs/adr/`, product decisions in `docs/decisions/`.

## Shape

- One database is the source of truth. Anything derived from it can be thrown away and rebuilt by a script.
- Every outside service (a vendor API, a model, email, storage) sits behind one adapter file. Nothing else names it.
- Modules talk through declared edges. A new import across modules is a design change, not a convenience.
- Numbers that encode a method or a policy (weights, thresholds, bands, rates) live in a table or a config file, never in code.
- The schema changes only through numbered migrations. No hand-made changes on any environment.
- A model proposes and code decides: see `AI-AGENTS.md`.
- Boring technology first: Postgres, the standard library, the platform's own features (ponytail).
- Every scheduled job is safe to run twice and logs its row counts before and after.

## Money, time and data

- Money is `Decimal` (`Numeric(20,4)` in the database), never float. Shown with ₹ and lakh/crore.
- Datetimes are timezone-aware and shown in IST, or in the market's own zone where the product says so.
- Every number a person sees traces to its source, its date (`data_as_of`) and its freshness.
- No synthetic, placeholder or default number ever stands in for a computed one.

## Security by default

- Secrets live in environment variables or a secrets manager, one key per environment.
- Every table has row-level access control; every route checks identity on the server.
- Client data (names, PANs, holdings, children's records) stays in production systems: never in logs, fixtures, screenshots or prompts to a vendor the client hasn't approved.

## Domain rules

The detailed conventions shared with Nimish's Mac are in `rules/`: `python-backend.md`, `database.md`, `data-engineering.md`, `auth.md`, `financial-domain.md`, `testing.md` and `frontend-viz.md`. Open the ones your change touches. Where the repository's own `CLAUDE.md` names a different stack (Supabase migrations instead of Alembic, say), the repository wins.

## Show it

When a change adds or moves a part, draw it for Nimish with the `archify` skill: one focused diagram of 10 to 20 parts, built only from evidence in the repository, attached to the pull request. For a before-and-after, use archify's diff of two snapshots. `graphify` answers the agent's questions about the code; `archify` draws the picture for a person.
