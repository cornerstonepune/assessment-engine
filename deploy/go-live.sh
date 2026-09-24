#!/usr/bin/env bash
# Put the engine online, on the school's own server, and point the website at it. One command, from
# any directory:  ~/cornerstone/assessment-engine/deploy/go-live.sh
#
# Safe to run again: every step checks what already exists. What it moves, and nothing more:
#   the committed code (git archive of HEAD — never the working folder, never .env as a whole);
#   two settings, DATABASE_URL and ENGINE_KEY — no AWS keys, no Supabase admin token, no model keys:
#     the server only shows scans and marks corrections; reading new papers stays on this Mac;
#   the scans the engine has actually read, by their capture paths — not the roster, not the reports;
#   and the printed packs that sheet rows point at, for the question-bank screens.
#
# Needs: the AWS profile `cornerstone` allowed `lightsail:*` (Nimish, IAM inline policy
# `run-the-engine`), ssh and tar, and the Vercel CLI logged in (npx vercel).
set -euo pipefail

# Everything runs inside main, called on the last line: bash then reads the whole file before it
# acts. It reads a script as it goes otherwise, and an edit made while a run was waiting broke it
# with 'unexpected EOF' — a run half-reading a different version of itself.
main() {

REPO="$(cd "$(dirname "$0")/.." && pwd)"
NAME=cornerstone-engine
REGION=ap-south-1
AWS=(aws --profile cornerstone --region "$REGION")
say() { printf '\n==> %s\n' "$*"; }

say "1/7 the server"
# Only "it does not exist" creates a server. Any other failure — Amazon unreachable, a broken TLS connection, an
# expired key — stops here: taken for "not found", it once led straight to creating a second, paid server.
exists() { # $1 the get- command, $2… its arguments: 0 found, 1 not found, stops on anything else
  local out
  if out=$("${AWS[@]}" lightsail "$@" 2>&1 >/dev/null); then return 0; fi
  if grep -q "NotFoundException\|DoesNotExist" <<<"$out"; then return 1; fi
  echo "Amazon did not answer ($1): $out" >&2
  echo "Nothing was changed. Check the network (a VPN or firewall can cut the connection) and run this again." >&2
  exit 1
}
if ! exists get-instance --instance-name "$NAME"; then
  BUNDLE=$("${AWS[@]}" lightsail get-bundles --output text \
    --query "bundles[?isActive && ramSizeInGb==\`2.0\` && contains(supportedPlatforms,'LINUX_UNIX') && !contains(bundleId,'ipv6')].bundleId | [0]")
  BLUEPRINT=$("${AWS[@]}" lightsail get-blueprints --output text \
    --query "blueprints[?platform=='LINUX_UNIX' && starts_with(blueprintId,'ubuntu_24')].blueprintId | [0]")
  echo "creating $NAME ($BUNDLE, $BLUEPRINT) in ${REGION}a"
  "${AWS[@]}" lightsail create-instances --instance-names "$NAME" --availability-zone "${REGION}a" \
    --bundle-id "$BUNDLE" --blueprint-id "$BLUEPRINT" >/dev/null
fi
until [ "$("${AWS[@]}" lightsail get-instance-state --instance-name "$NAME" --query state.name --output text)" = running ]; do
  sleep 5
done
if ! exists get-static-ip --static-ip-name "$NAME-ip"; then
  "${AWS[@]}" lightsail allocate-static-ip --static-ip-name "$NAME-ip" >/dev/null
  "${AWS[@]}" lightsail attach-static-ip --static-ip-name "$NAME-ip" --instance-name "$NAME" >/dev/null
fi
"${AWS[@]}" lightsail open-instance-public-ports --instance-name "$NAME" --port-info fromPort=80,toPort=80,protocol=tcp >/dev/null
"${AWS[@]}" lightsail open-instance-public-ports --instance-name "$NAME" --port-info fromPort=443,toPort=443,protocol=tcp >/dev/null
IP=$("${AWS[@]}" lightsail get-static-ip --static-ip-name "$NAME-ip" --query staticIp.ipAddress --output text)
HOST="${IP//./-}.sslip.io"
echo "server $IP, public address https://$HOST"

say "2/7 a way in"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
"${AWS[@]}" lightsail download-default-key-pair --query privateKeyBase64 --output text > "$WORK/key"
chmod 600 "$WORK/key"
SSH=(ssh -i "$WORK/key" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 "ubuntu@$IP")
until "${SSH[@]}" true 2>/dev/null; do sleep 5; done

say "3/7 docker"
"${SSH[@]}" 'command -v docker >/dev/null || (sudo apt-get update -q && sudo apt-get install -y -q docker.io docker-compose-v2 rsync)'

say "4/7 the code, exactly as committed ($(git -C "$REPO" rev-parse --short HEAD))"
"${SSH[@]}" 'rm -rf ~/assessment-engine.new && mkdir -p ~/assessment-engine.new'
git -C "$REPO" archive --format=tar HEAD | "${SSH[@]}" 'tar -x -C ~/assessment-engine.new'
"${SSH[@]}" 'rm -rf ~/assessment-engine && mv ~/assessment-engine.new ~/assessment-engine'

say "5/7 the two settings, and the scans the engine has read"
# scp and tar, never rsync: macOS ships openrsync, which refuses --chmod and more besides. And tar
# without Apple's extras: macOS tar otherwise sends a "._" companion per file for its quarantine and
# download tags — the first run landed 142 files for 71 scans, and a warning for each on the server.
grep -E '^(DATABASE_URL|ENGINE_KEY|TENANT_SLUG)=' "$REPO/.env" > "$WORK/env"
"${SSH[@]}" 'umask 077 && cat > ~/assessment-engine/.env' < "$WORK/env"
"$REPO/packages/engine/.venv/bin/python" - > "$WORK/scans" <<'PY'
import os, sys
from engine.core import db
home = os.path.expanduser("~/cornerstone/assessments")
with db.connect() as conn:
    for r in conn.execute("select distinct path from capture where superseded_by is null"):
        rel = os.path.relpath(os.path.expanduser(r["path"]), home)
        if rel.startswith(".."):  # the server mounts only ~/cornerstone/assessments: this one cannot be shown there
            print(f"not sent, it is outside ~/cornerstone/assessments: {r['path']}", file=sys.stderr)
        elif os.path.exists(os.path.join(home, rel)):
            print(rel)
PY
echo "$(wc -l < "$WORK/scans" | tr -d ' ') scans"
COPYFILE_DISABLE=1 tar --no-xattrs -C ~/cornerstone/assessments -cf - -T "$WORK/scans" \
  | "${SSH[@]}" 'mkdir -p ~/cornerstone/assessments && tar -x -C ~/cornerstone/assessments'
"${SSH[@]}" 'echo "on the server: $(find ~/cornerstone/assessments -type f | wc -l) scans"'
# and the printed packs the question-bank screens show, by the paths their rows record
"$REPO/packages/engine/.venv/bin/python" - "$REPO/data/packs" > "$WORK/packs" <<'PACKS'
import os, sys
from engine.core import db
with db.connect() as conn:
    for r in conn.execute("select pdf_path from sheet_instance where pdf_path is not null"):
        if r["pdf_path"].startswith(sys.argv[1]) and os.path.exists(r["pdf_path"]):
            print(os.path.relpath(r["pdf_path"], sys.argv[1]))
PACKS
if [ -s "$WORK/packs" ]; then
  COPYFILE_DISABLE=1 tar --no-xattrs -C "$REPO/data/packs" -cf - -T "$WORK/packs" \
    | "${SSH[@]}" 'mkdir -p ~/cornerstone/packs && tar -x -C ~/cornerstone/packs'
fi
echo "$(wc -l < "$WORK/packs" | tr -d ' ') printed sheets"

say "6/7 start the engine"
"${SSH[@]}" "cd ~/assessment-engine/deploy && sudo ENGINE_HOST=$HOST HOME=/home/ubuntu PACKS_AS_RECORDED='$REPO/data/packs' docker compose -f compose.server.yml up -d --build"
printf 'waiting for https://%s/health ' "$HOST"
for _ in $(seq 60); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "https://$HOST/health")" = 200 ]; then echo " up"; break; fi
  printf '.'; sleep 5
done
[ "$(curl -s -o /dev/null -w '%{http_code}' "https://$HOST/health")" = 200 ] || { echo "the engine did not come up"; exit 1; }

say "7/7 point the website at it"
KEY_VALUE=$(grep -E '^ENGINE_KEY=' "$REPO/.env" | cut -d= -f2- | tr -d "\"'")
cd "$REPO"
for var in ENGINE_URL ENGINE_KEY; do npx --yes vercel env rm "$var" production --yes >/dev/null 2>&1 || true; done
printf '%s' "https://$HOST" | npx --yes vercel env add ENGINE_URL production >/dev/null
printf '%s' "$KEY_VALUE" | npx --yes vercel env add ENGINE_KEY production >/dev/null
echo "website settings: ENGINE_URL=https://$HOST, ENGINE_KEY set"

say "done — the engine is online at https://$HOST"
echo "The website picks this up on its next deployment: merging the pull request into main triggers it."
}

main "$@"
