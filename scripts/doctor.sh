#!/usr/bin/env bash
# Environment diagnostics — delegates to `python -m tools.sentinel_cli doctor`.
#
#   bash scripts/doctor.sh
#   bash scripts/doctor.sh --stats
#
# Exit code 0 means nothing is broken; 1 means something must be fixed.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/backend/venv"

if [ -x "$VENV/Scripts/python.exe" ]; then
  PY="$VENV/Scripts/python.exe"
elif [ -x "$VENV/bin/python" ]; then
  PY="$VENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "✖ Python is not installed. Install Python 3.11+ from https://python.org" >&2
  exit 1
fi

if [ "${1:-}" = "--stats" ]; then
  cd "$REPO_ROOT" && "$PY" -m tools.sentinel_cli doctor --stats 2>/dev/null \
    || "$PY" -m tools.sentinel_cli doctor
else
  cd "$REPO_ROOT" && "$PY" -m tools.sentinel_cli doctor
fi
