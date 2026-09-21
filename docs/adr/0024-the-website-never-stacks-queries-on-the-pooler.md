# 0024 — The website never stacks queries on one pooled connection

Date: 2026-09-21
Status: accepted (step 1 of the five, `BUILD-ORDER.md`)

## Context

On the live website the Question bank never opened: Vercel killed every request at its five-minute
limit (13 of 13 between 14:05 and 14:08 IST), and pages that shared the database queue with them
began to fail too. On this Mac the same page answered in half a second.

The difference is the road to the database. Deployed, `apps/web/lib/db.ts` connects through
Supabase's *transaction* pooler (port 6543) with one connection per function; on this Mac it uses
the *session* pooler (5432). The Question bank asks four questions at once (`Promise.all`), and
postgres.js sends concurrent queries down one connection back to back ("pipelining").

Measured 2026-09-21 with the page's own four queries, and with four `select 1`s, through the
transaction pooler and one connection: the first two answer, the rest never do — 3 runs of 3, and
still with `max: 2`. Through the session pooler: all answer. With `max_pipeline: 0` (a query waits
for the one before it on its connection): seven at once answer in 0.2–0.5 s, on one connection or
four.

## Decision

`db.ts` sets `max_pipeline: 0` everywhere, and allows four connections per serverless function so
a page's queries still run side by side. `apps/web/scripts/check-pooler.ts` runs eight queries at
once through the live pooler with the app's own `db.ts` and is a criterion of goal
`s1-site-answers`: it hung before this change and answers after it.

## Rejected

- **The session pooler for the website.** It works for this bug, but holds a database connection
  per function for the function's life; a burst of pages (the table links pre-loading every page
  behind them did exactly that) runs it out. The transaction pooler is the right road; the bug is
  in how we drove it.
- **More connections alone.** `max: 2` still hung, because a page can ask more questions at once
  than it has connections, and then they stack again. The ceiling has to be on stacking, not on
  connections.
- **A per-connection statement timeout** (`options=-c statement_timeout=…`). Measured: the
  transaction pooler ignores it (`show statement_timeout` → `2min`). The page-level deadline in
  step 1 is what bounds a wait now.
