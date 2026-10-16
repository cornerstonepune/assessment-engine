#!/usr/bin/env bash
# Athena: set up your Mac from the one master harness (athena-ops). Safe to run again.
#
#   In Terminal, inside any repository with the harness (Atlas, for example):
#     bash .claude/athena/mac-setup.sh
#
# It fetches athena-ops into ~/.athena/ops (or updates it), then runs athena-ops/mac/setup.sh,
# which says step by step what it changes and backs up your current settings first.
set -euo pipefail
OPS="$HOME/.athena/ops"
if [ -d "$OPS/.git" ]; then
  git -C "$OPS" pull -q --ff-only
elif command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  mkdir -p "$HOME/.athena" && gh repo clone nimishshah1989/athena-ops "$OPS" -- -q
else
  mkdir -p "$HOME/.athena" && git clone -q https://github.com/nimishshah1989/athena-ops.git "$OPS"
fi
exec bash "$OPS/mac/setup.sh"
