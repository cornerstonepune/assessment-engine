---
globs: ["**/auth/**", "**/*auth*.py", "**/middleware/**", "**/api/**", "**/.env*", "**/config.py"]
---
# Auth, secrets & integration guardrails

Applies to every project with users, an API, or third-party services.

## Secrets — never in code, never in client
- No secret (API key, DB password, token, service_role key) in source, git history, or a committed `.env`.
  `.env` is always gitignored; commit only a `.env.example` with empty values.
- No `NEXT_PUBLIC_` / client-exposed prefix on any secret. Client gets the anon/publishable key only.
- Supabase `service_role` key is server-side only.
- DB passwords live in a secrets manager / env — never in a `create-*.sh` / `verify-*.sh` script.
- If a secret is ever printed, committed, or shared: rotate it at the provider, then purge the literal.

## Auth
- Every authenticated route checks identity server-side. Never trust a client-supplied user id.
- Sessions: httpOnly, secure cookies; short-lived access + refresh. No tokens in localStorage.
- Auth middleware is ON in production. A disabled/bypassed auth gate is a ship blocker, not a TODO.

## RLS (Supabase)
- RLS ON for every table — no exceptions. A table without RLS does not ship.
- Least-privilege policies: a user reads/writes only their own rows. PMS/client data is row-isolated.
- Verify with the supabase `get_advisors` (security) check before calling a schema change done.

## Integrations (third-party APIs)
- Keys in env; rotate on a schedule; one key per environment (dev/prod never share).
- Wrap external calls behind a trust boundary — validate/escape anything from an external response that
  flows into a query, prompt, or shell. (gstack /review checks this.)
- Rate-limit and time-out every outbound call; never let a third party hang a request path.
