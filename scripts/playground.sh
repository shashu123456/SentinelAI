#!/usr/bin/env bash
# Serve the offline API playground on a CORS-allowed local origin.
#
#   make playground
#
# The page needs the API running at http://localhost:8000 (`make dev-backend`).
# It is served from http://localhost:8080 because that origin is in the default
# CORS_ORIGINS list; opening the file:// path directly would be blocked.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PLAYGROUND_PORT:-8080}"
URL="http://localhost:${PORT}/api-playground.html"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  BOLD=$(printf '\033[1m'); DIM=$(printf '\033[2m'); CYAN=$(printf '\033[36m'); RESET=$(printf '\033[0m')
else
  BOLD=""; DIM=""; CYAN=""; RESET=""
fi

if [ -x "$REPO_ROOT/backend/venv/Scripts/python.exe" ]; then PY="$REPO_ROOT/backend/venv/Scripts/python.exe"
elif [ -x "$REPO_ROOT/backend/venv/bin/python" ]; then PY="$REPO_ROOT/backend/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else PY="python"; fi

printf "\n${BOLD}API playground${RESET}\n"
printf "  %s\n" "$URL"
printf "  ${DIM}API expected at http://localhost:8000 (override in the header)${RESET}\n"
printf "  ${DIM}Ctrl-C to stop the static server${RESET}\n\n"

open_browser() {
  sleep 1
  case "$(uname -s)" in
    Darwin) open "$URL" 2>/dev/null || true ;;
    MINGW*|MSYS*|CYGWIN*) start "" "$URL" 2>/dev/null || true ;;
    *) xdg-open "$URL" 2>/dev/null || true ;;
  esac
}
open_browser &

# Start the static server in the background
# (don't use exec so the shell stays alive and trap cleanup works)"$PY" -m http.server "$PORT" --bind 127.0.0.1 --directory "$REPO_ROOT/docs" &
HTTP_PID=$!

# Wait for the server process; on exit kill the http server
wait $HTTP_PID 2>/dev/null || true
