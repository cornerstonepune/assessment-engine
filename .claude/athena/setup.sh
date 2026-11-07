#!/usr/bin/env bash
# Installs what this repo needs before its fast checks and acceptance proofs can run (used by CI).
# Athena writes this once and never overwrites it: edit it for this repo.
set -euo pipefail
cd "$(dirname "$0")/../.."
command -v uv >/dev/null || python3 -m pip install --quiet uv
(cd packages/engine && uv sync --extra dev)
(cd apps/web && npm ci)
