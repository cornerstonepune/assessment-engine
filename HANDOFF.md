# HANDOFF — for the next session

Read `STATE.md` for what is verified and how. This file is what the last session left.

## Where things stand, 2026-09-19, evening

Nimish pushed back hard this session on how the system had been built: entirely by hand-typed CLI
commands against `ARCHITECTURE.md`'s own stated design of an engine-as-a-service orchestrated by
n8n — which is what caused the double import. The plan closing that gap is
`docs/superpowers/plans/2026-09-18-spine.md` (seven chunks; ADRs 0007–0009). **Chunks 1 and 2 are
done this session.**

**Chunk 1** (idempotent capture, Haiku reads, a spend budget) shipped earlier today — see
STATE.md's N3.1 section if you need the detail; the historical double-import damage is fixed
(133 real answers, not 218) and cannot recur on a re-run of the same command.

**Chunk 2, the engine as a service, is done and genuinely verified — not just unit-tested.**
`packages/engine/engine/api/` is a real FastAPI app: `/health`, `/runs/{id}`, `/children/find`,
`/ingest`, `/mark`, `/commit`, `/graph/rebuild`, `/bank/fill`, every write route wrapped in
`run_idempotent` (claims a `flow_run` row via the real partial unique index, retries a previous
failure, refuses a genuine concurrent duplicate with 409 rather than double-running). Built,
containerized (`Dockerfile`, `deploy/compose.yml`), and proven against the real database from
*inside the running container* — not mocked: `/health` → `{"ok": true}`; `POST /graph/rebuild` →
`{"states": 26}` and a real `flow_run` row; the same call repeated with the same
`Idempotency-Key` → `already: true`, confirmed exactly one row exists. 182 engine tests pass
(41 of them new, in `tests/api/`), `tsc` clean on the web app.

**Two things this session's insistence on real verification actually caught**, worth naming
because they're the reason "build it and test it against the real thing" mattered more than usual
here:
1. `db.py`'s `REPO_ROOT = Path(__file__).resolve().parents[3]` assumed the monorepo's directory
   depth and crashed the whole container at import time — Docker copies only `engine/`, so the
   file has nothing four levels above it inside the image. No unit test would have found this;
   only an actual `docker build` + a real container start did. Fixed, and now unit-tested as a
   pure function (`_repo_root_for`) so the fix itself is provable, not just "seems to work now."
2. A `RuntimeError` subclass (`InProgress`, raised on a genuine concurrent duplicate request) was
   never translated to an HTTP response — it would have reached a real caller as an unhandled 500
   with a stack trace. `test_idempotency.py` proved the *Python exception* was raised; that test
   alone gave false confidence. Only a *second*, separate test that hit the same scenario through
   a real HTTP call surfaced that it was never caught. Both kinds of test are now in the suite for
   this and should be the pattern for anything chunk 3+ adds that raises a custom exception.

**Two scope decisions made mid-chunk, not in the original plan text**, both explained in
`docs/superpowers/plans/2026-09-18-spine.md`'s chunk 2 section: `/ingest` was not split into
`/ingest` + `/read` (nothing consumes the split yet — building it now would be a guess, not a
design); `/prescribe`, `/assemble`, `/render` were not built (they need an answer to "where does a
rendered PDF live in a container" that nothing yet needs).

## Start here — chunk 3: validate the read, capture corrections, grow gold

Per the plan: a `validate_read` prompt (Haiku) that checks a transcription against the page it
came from; `read_correction` and `gold` rows written from the settle flow (`resolve_result` needs
a `p_read` parameter it doesn't have yet); `engine eval legacy_extract|read_cells` scoring a
prompt version against accumulated gold, refusing to activate a version that scores worse. The
Growth page's settle form (`apps/web/app/(app)/growth/[id]/actions.ts`) needs a "what the child
actually wrote" field alongside its right/wrong/blank buttons — right now a settle only records a
status, never a corrected value, so `read_correction` has nothing to write from the UI yet.

n8n MCP tools were reported connected mid-session ("n8n mcp is connected now") but were not
visible to this session (`ToolSearch` for `n8n` found nothing) — check again at the start of
chunk 4; if still absent, build workflows as JSON and use `n8n import:workflow` from the CLI,
which needs no login.

## Blocked on Nimish

- The n8n owner account, once chunk 4 starts the n8n container — one-time, ~1 minute (see the
  plan's "What Nimish provides" table). Nothing else is needed to start chunk 4.
- The Haiku 4.5 prices in `config.llm.prices` (₹88 in / ₹440 out per million tokens) are an
  estimate pending a verified figure at anthropic.com/pricing — the row's own `description` says
  so; correct it there when confirmed.
- `AUTH_SECRET` on Vercel if not yet set; rotate the database password (typed into a chat earlier,
  printed into a build log); re-copy or delete `SUPABASE_SERVICE_ROLE_KEY` (returns 401).
- Voiding vs. deleting the pre-chunk-1 duplicate captures' *evidence_event* rows specifically —
  chunk 1 made them stop counting; whether to also mark them in some more visible way is Nimish's
  call, not a technical one.
- Achal's and Neha's emails for `app.staff`; consent text; parent-note channel; whether the
  Olympiad papers count; Kiyaan's missing Week 1; the VPS decision before any teacher-facing run.

## Traps this session fell into, or found and fixed — do not repeat

- **"The exception is raised" and "the caller gets a sensible response" are different claims.**
  Test both, separately, for any custom exception a route can raise. See point 2 above.
- **A migration's new partial unique index can make its own backfill fail** if the backfill writes
  the indexed value one row at a time — two rows converging on the same value both still "live"
  between statements collides with the index they're being backfilled to satisfy. `legacy.dedupe`
  (chunk 1) hits this; fixed by computing everything in Python first, then writing a superseded
  row's new value and its supersession in one statement, never two.
- **Docker credential-helper hangs on macOS from a non-interactive session look exactly like a
  network block** (silent, no error, no timeout) but are not one — `docker pull` directly (not
  through `compose`/`buildx bake`) surfaces the real "error getting credentials" message in
  seconds. Diagnosed via: raw `curl` to the registry (fast, proves network is fine) →
  `docker pull` directly (reveals the credential-helper error) → a scoped `DOCKER_CONFIG` +
  `DOCKER_HOST` pointed at the real socket (`~/.docker/run/docker.sock`), not a global config
  edit. Don't spend time on network-block theories before ruling this out first.
- **A route's build context needs a `.dockerignore`** as much as the image needs multi-stage
  builds — `packages/engine/.venv` is 417 MB and was about to ship into every build's context
  before one was added.
- **An idempotency key derived from a request body is not private to a test.** A manual smoke test
  against the real database using an empty/generic body (`{}`, no explicit key) leaves a real
  `flow_run` row that a *later automated test* with an equivalent body will legitimately treat as
  "already done" — because it is, by the same rule that makes idempotency work at all. This isn't
  a bug in the wrapper; it means a test whose body is realistic/generic (an empty "rebuild
  everyone" call, say) should pass its own explicit `Idempotency-Key` rather than lean on the
  derived one, precisely because the derived one is *supposed* to collide with a real repeat.
- Never assemble a connection string with shell substitution; never run a migration while a fill
  is writing; the e2e suite writes to the live database; `roster` has been an unused import in
  `engine/legacy.py` since before chunk 1 — left alone rather than deleted in an unrelated diff.
