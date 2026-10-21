# ADR 0089 — A deploy starts a standby before it replaces the engine

**Status:** proposed (2026-10-21).
Goal: goals/l8-deploy-without-downtime.yaml

## What happened

Every deploy ran `docker compose up -d --build`: build the image, stop the engine, start the new one. The deploy
engine workflow's own logs, for every deploy from 16 to 21 Oct 2026, put the engine unreachable for 23–31 seconds
(10–13 of them Docker waiting to kill the old process), after a build of 185–371 seconds that fetched Chromium and the
reader's models again on every code change, because the Dockerfile copied the whole engine in above them. Caddy had one
upstream and no retry, so each request in the gap was answered 502 at once, and the website said "The engine refused
(502)" (HANDOFF.md, 2026-10-16, which Nimish saw).

## Decision

- **A standby, then the switch** (`deploy/switch.sh`). The new image is built while the engine serves; a standby from
  it starts on 8001 (`docker compose run`, so it has the engine's own settings and folders) and must answer `/health`
  before the engine on 8000 is touched. Caddy holds both, sends each request to the first that answered `/health`,
  and holds a request that finds neither for up to 30 seconds. The standby is told to stop only once the new engine on
  8000 answers and Caddy has seen it, and it finishes what it was doing first.
- **The engine keeps its name.** `deploy-engine-1` on 8000 stays the engine; eight workflows `docker exec` into it.
- **A standby leaves the serving engine's runs alone** (`ENGINE_STANDBY`): an engine marks every running run dead when
  it starts, which is right only when no other engine is running.
- **Only the reader's file comes in before the reader's models** in the Dockerfile; the rest of the engine comes last.

## Rejected

- **Caddy's retry alone.** It turns the 502 into a wait of 23–31 seconds; the engine is still down for them.
- **Two named engines, blue and green, taking turns.** The engine's name would change every deploy, and every
  workflow that reaches into it (logs, eval, reports, the reader's ink line, the watcher) would have to find it first.
- **`--scale engine=2` with a range of ports.** Docker gives each copy a port from the range in no fixed order, so
  which one is new is not known without asking; a standby on a named port says so itself.
- **A container orchestrator, or a load balancer in front of the server.** New infrastructure for one server.
