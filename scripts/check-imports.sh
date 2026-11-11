#!/usr/bin/env bash
# Fast guard: the FastAPI app must import cleanly.
#
# Catches syntax errors, circular imports, and broken router wiring before a
# commit lands. Takes ~2s (no database, no server).
#
#   bash scripts/check-imports.sh
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"

if [ -x "$BACKEND/venv/Scripts/python.exe" ]; then PY="$BACKEND/venv/Scripts/python.exe"
elif [ -x "$BACKEND/venv/bin/python" ]; then PY="$BACKEND/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else PY="python"; fi

if ! (cd "$BACKEND" && "$PY" -c "from app.main import app; print(f'{len(app.routes)} routes')" 2>/tmp/sentinel-import.log); then
  echo "✖ backend failed to import:" >&2
  tail -n 30 /tmp/sentinel-import.log >&2
  exit 1
fi

echo "✔ backend imports cleanly"
