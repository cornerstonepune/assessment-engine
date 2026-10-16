#!/usr/bin/env bash
# Installs what this repo needs before its acceptance proofs can run (used by CI).
# Athena writes this once and never overwrites it: edit it for this repo.
set -euo pipefail
cd "$(dirname "$0")/../.."
if [ -f package-lock.json ]; then npm ci
elif [ -f pnpm-lock.yaml ]; then corepack enable && pnpm install --frozen-lockfile
elif [ -f yarn.lock ]; then corepack enable && yarn install --frozen-lockfile
elif [ -f package.json ]; then npm install
fi
if [ -f requirements.txt ]; then python3 -m pip install -r requirements.txt
elif [ -f pyproject.toml ]; then python3 -m pip install -e . || python3 -m pip install .
fi
if [ -f requirements-dev.txt ]; then python3 -m pip install -r requirements-dev.txt; fi
