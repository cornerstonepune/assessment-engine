# L8 — a deploy does not take the engine down

Goal: `goals/l8-deploy-without-downtime.yaml`. ADR 0089. Nimish, 2026-10-21: "start L8".

## Verified

**Measured first, on live's own record** (the deploy engine workflow's job logs, read with `gh api`; nothing run on the
server). From "Container deploy-engine-1 Recreate" to the first 200 from the public `/health`:

| run | when (UTC) | build | stop old | unreachable |
|---|---|---|---|---|
| 38851584813 | 16 Oct 04:37 | 210 s | 10 s | 23 s |
| 38858327760 | 16 Oct 05:55 | 211 s | 13 s | 26 s |
| 38907244418 | 16 Oct 13:21 | 244 s | 12 s | 26 s |
| 38929617532 | 16 Oct 16:08 | 227 s | 13 s | 26 s |
| 39466742303 | 20 Oct 17:30 | 202 s | 11 s | 25 s |
| 39481147462 | 20 Oct 19:10 | 195 s | 13 s | 26 s |
| 39530706180 | 21 Oct 02:01 | 185 s | 12 s | 25 s |
| 39540716172 | 21 Oct 03:49 | 201 s | 12 s | 26 s |
| 39555545977 | 21 Oct 06:27 | 371 s | 18 s | 31 s |

The health poll was every 5 s, so each gap may be up to 5 s longer. Causes found:
1. **Stop, then start.** `up -d --build` stops the engine and only then starts the new one: 23–31 s with nothing on
   8000. The "stop old" column is Docker waiting most of its 10 s before killing the old engine.
2. **Caddy had one upstream and no retry**, so each request in the gap got 502 at once: "The engine refused (502)".
3. **The Dockerfile copied the engine above Chromium and the reader's models**, so every code change fetched both
   again: on 21 Oct 03:49, 57 s Chromium + 37 s models + 52 s writing the layers, of a 201 s build.
4. **The website said "The engine refused (502)"**, or "not answering on <the engine's address>".
5. **A running Caddy never reads a new Caddyfile.** It is mounted as one file from the folder each deploy replaces, so
   Caddy keeps the file it started with. `deploy/switch.sh` restarts Caddy when the file differs.
6. **An engine marks every running run dead when it starts** (`runs.orphaned`), right only when no other engine runs.
   A standby beside a serving engine would have marked a scan being read as dead.

Ruled out: the deploy deletes the code folder (with the seed the engine mounts) before the build; the engine's
request paths read settings from the database, not from those files. The 16 Oct HANDOFF line says the engine
"restarted 04:38–04:42"; that is the deploy step's span. The log shows the build 04:38–04:41, the switch at 04:41:48 and
the engine back at 04:42:12. I am not certain the engine also failed during the build, and I have no record either way.

**Rehearsed on this machine, never on live:** Docker, the real engine image, a throwaway Postgres, this branch's
`deploy/` files; a request through Caddy to `/health` every 0.1 s during the switch.

| what was rehearsed | answered 200 | not 200 |
|---|---|---|
| the old way: old Caddyfile, `up -d --build`, a code change | 57 | 13 × 502 |
| `switch.sh`, a code change | 226 | 0 |
| `switch.sh`, a new engine that crashes on start: exit 1, the old image still serving | 184 | 0 |
| `switch.sh` on the first deploy after merging (Caddy restarts once for its new file) | 187 | 2 refused, ~0.2 s |

- The layer order, `docker build` of the engine before and after one changed line of code (this machine, 4 CPUs):
  old Dockerfile 119 s, rebuilding Chromium and the models; new Dockerfile 2 s, both CACHED.
- `caddy adapt --validate` (caddy:2 image) on `deploy/Caddyfile`: exit 0; upstreams 127.0.0.1:8000 and :8001, policy
  `first`, try_duration 30 s, health `/health` every 2 s.
- `cd packages/engine && uv run pytest -q tests/test_deploy.py`: 15 passed. The 8 new tests fail on main's
  Dockerfile, Caddyfile, deploy workflow and app.py (8 failed, 7 passed), and pass on this branch.
- `apps/web/tests/p3-the-engine-restarting.spec.ts` under the website's own Playwright config: 3 passed. On main's
  `lib/engine.ts`: 2 failed, 1 passed. (First named `l8-…`, which matches no project in `playwright.config.ts`, so CI
  ran none of it; renamed `p3-…`, the platform tests' prefix.)
- CI's full engine suite on 2cc3231: 1 failed, 2590 passed. `test_legacy.py::test_a_deploy_enters_every_paper_again_as_its_file_now_says`
  found the engine's start by `docker compose` in its step, which is now `bash switch.sh`; it finds that instead
  (reproduced failing, then passing). The 178 failures of a local run were this sandbox's (no browser for Playwright).
- `bin/check`: 28 passed.

## Handoff

- **Live:** nothing. Not deployed; the deploy workflow was not run.
- **In flight:** the PR "L8: a deploy does not take the engine down".
- **On the first deploy after merging, watch** the "start the engine" step. It should print "the standby answers on
  8001", then "the engine answers on 8000 on the new code; the standby is gone". Caddy restarts once on that deploy,
  because its file changed. Rehearsed, that refused requests for about 0.2 s.
- **Risk to watch:** the server has 1.9 GB and two CPUs. For about 30 s two engines run (≈176 MB each, measured
  16 Oct). With the new layer order a code-only build no longer loads the reader's models (~600 MB), so it should use
  less memory than before. A deploy that changes the dependencies still builds everything.
- **Not certain:** on the server, "Recreate" took 10–13 s, which includes stopping, removing and creating the
  container. Here the real image, with no request in flight, stopped in 0.9 s (`docker stop --time 900`). The standby
  is given up to 15 minutes to finish its work. If it does not stop on the server, the deploy step waits that long.
- **Blocked:** none. Nimish has no sentence of his own about this; `says` quotes HANDOFF's record of what he saw. The
  PR asks him for one.
