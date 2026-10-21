#!/usr/bin/env bash
# The engine takes new code without going away (goals/l8-deploy-without-downtime.yaml). deploy-engine.yml runs this on
# the server, from deploy/, as root, once the commit's code is in place. Every deploy to 21 Oct 2026 stopped the engine
# and only then started the new one: 23–31 seconds in which every request failed ("The engine refused (502)").
#
#   1. The new image is built while the engine serves on.
#   2. A standby from it starts on 8001 and must answer /health. If it never does it is removed, and the engine on 8000
#      is never touched: the deploy fails with the old code still serving.
#   3. The engine on 8000 is replaced. Caddy (Caddyfile) sends every request to the standby meanwhile.
#   4. Once the new engine on 8000 answers /health, and Caddy has seen it, the standby finishes what it was doing and
#      goes. If the new engine never answers, the standby, on the same new code, serves on and the deploy fails.
set -euo pipefail

STANDBY=deploy-engine-standby
TRIES=${TRIES:-90}  # × 2 s: the engine took 13 s to answer after a start on every deploy measured

compose() { docker compose -f compose.server.yml "$@"; }

answers() {  # port → succeeds once the engine there answers /health
  for _ in $(seq "$TRIES"); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$1/health")" = 200 ] && return 0
    sleep 2
  done
  return 1
}

compose build engine

# Caddy reads its file once, at its start, from the folder the deploy has just replaced: a changed file is read only
# by a new Caddy. Restarting it holds the door shut for about a second, and only on a deploy that changes it.
if ! docker exec deploy-caddy-1 cat /etc/caddy/Caddyfile 2>/dev/null | cmp -s - Caddyfile; then
  compose up -d --no-deps --force-recreate caddy
fi

docker rm -f "$STANDBY" >/dev/null 2>&1 || true
# ENGINE_STANDBY: the runs marked "running" are the serving engine's, still going; the standby leaves them alone
compose run -d --no-deps --name "$STANDBY" -p 127.0.0.1:8001:8000 -e ENGINE_STANDBY=1 engine
if ! answers 8001; then
  docker logs --tail 50 "$STANDBY" 2>&1 || true
  docker rm -f "$STANDBY"
  echo "::error::the new engine never answered /health; the engine serving before this deploy serves on, unchanged"
  exit 1
fi
echo "the standby answers on 8001"

# always replaced, even on an image the build left as it was: its seed folder is mounted from the folder just replaced
compose up -d --no-deps --no-build --force-recreate engine
if ! answers 8000; then
  echo "::error::the new engine on 8000 never answered /health; the standby, on the same code, serves on 8001"
  exit 1
fi
sleep 6  # Caddy asks every 2 s: it has seen 8000 answer before the standby stops taking requests
# What the standby was doing when it is told to stop, it finishes; nothing new reaches it.
docker stop --time 900 "$STANDBY" >/dev/null
docker rm "$STANDBY" >/dev/null
echo "the engine answers on 8000 on the new code; the standby is gone"
