#!/usr/bin/env bash
# Run the backend API and the Vite dev server together, with readiness
# checks and a clean shutdown on Ctrl-C.
#
#   bash scripts/dev.sh
#   PORT=8080 FRONTEND_PORT=3000 bash scripts/dev.sh
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"
FRONTEND="$REPO_ROOT/frontend"
# Some CI sandboxes export PORT=0 (an ephemeral-port request); treat that and
# any non-numeric value as "use the documented default".
normalize_port() {
  case "${1:-}" in
    ''|0|*[!0-9]*) echo "$2" ;;
    *) echo "$1" ;;
  esac
}

PORT=$(normalize_port "${PORT:-}" 8000)
FRONTEND_PORT=$(normalize_port "${FRONTEND_PORT:-}" 5173)
LOG_DIR="$REPO_ROOT/.dev-logs"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  BOLD=$(printf '\033[1m'); DIM=$(printf '\033[2m'); CYAN=$(printf '\033[36m')
  GREEN=$(printf '\033[92m'); YELLOW=$(printf '\033[93m'); RED=$(printf '\033[91m')
  RESET=$(printf '\033[0m')
else
  BOLD=""; DIM=""; CYAN=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

if [ -x "$BACKEND/venv/Scripts/python.exe" ]; then
  PY="$BACKEND/venv/Scripts/python.exe"
elif [ -x "$BACKEND/venv/bin/python" ]; then
  PY="$BACKEND/venv/bin/python"
else
  echo -e "${RED}✖ backend/venv not found. Run: make setup${RESET}" >&2
  exit 1
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo -e "${RED}✖ frontend/node_modules missing. Run: make install-frontend${RESET}" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Probe a port on both loopback families: Vite binds "localhost", which can be
# IPv6-only on Windows, while uvicorn binds 127.0.0.1 explicitly.
# Path arguments must not start with a slash: MSYS/Git Bash rewrites "/foo"
# into a Windows path before Python ever sees it.
urllib_ok() {
  "$PY" - "$1" "${2:-}" <<'PY'
import sys, urllib.request
port, path = sys.argv[1], sys.argv[2]
for host in ("127.0.0.1", "[::1]", "localhost"):
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/{path}", timeout=1) as r:
            sys.exit(0 if r.status < 500 else 1)
    except Exception:
        continue
sys.exit(1)
PY
}

port_in_use() {
  "$PY" - "$1" <<'PY'
import socket, sys
s = socket.socket()
s.settimeout(0.3)
sys.exit(0 if s.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)
PY
}

# Kill a child and everything it spawned. `npm run dev` and `uvicorn --reload`
# both fork, so killing only the parent leaves orphaned node/uvicorn processes
# holding the ports.
kill_tree() {
  local pid="${1:-}"
  [ -n "$pid" ] || return 0
  if command -v taskkill >/dev/null 2>&1; then
    taskkill //T //F //PID "$pid" >/dev/null 2>&1 || true
  else
    pkill -TERM -P "$pid" >/dev/null 2>&1 || true
    kill -TERM "$pid" >/dev/null 2>&1 || true
  fi
}

PIDS=()
cleanup() {
  echo ""
  printf "${DIM}shutting down...${RESET}\n"
  for pid in "${PIDS[@]:-}"; do
    kill_tree "$pid"
  done
  wait 2>/dev/null || true
  printf "${GREEN}stopped${RESET}\n"
}
trap cleanup INT TERM EXIT

# ── Backend ─────────────────────────────────────────────────────────
if port_in_use "$PORT"; then
  echo -e "${YELLOW}!${RESET} port $PORT already in use — assuming the API is running"
  BACKEND_STARTED=0
else
  printf "${CYAN}▸${RESET} starting backend on port %s ${DIM}(log: .dev-logs/backend.log)${RESET}\n" "$PORT"
  # Allow the frontend origin actually in use. Custom ports (PORT=8010
  # FRONTEND_PORT=5183) would otherwise be rejected by CORS.
  CORS_ORIGINS="[\"http://localhost:$FRONTEND_PORT\",\"http://127.0.0.1:$FRONTEND_PORT\",\"http://localhost:$PORT\"]"
  ( cd "$BACKEND" && CORS_ORIGINS="$CORS_ORIGINS" \
      "$PY" -m uvicorn app.main:app --reload --port "$PORT" --host 127.0.0.1 \
      >"$BACKEND_LOG" 2>&1 ) &
  PIDS+=("$!")
  BACKEND_STARTED=1

  READY=0
  for _ in $(seq 1 60); do
    if urllib_ok "$PORT" "api/health"; then READY=1; break; fi
    if ! kill -0 "${PIDS[0]}" 2>/dev/null; then break; fi
    sleep 0.5
  done

  if [ "$READY" -ne 1 ]; then
    echo -e "${RED}✖ backend failed to start — last lines:${RESET}"
    tail -n 25 "$BACKEND_LOG" || true
    exit 1
  fi
  printf "  ${GREEN}✔${RESET} backend ready ${DIM}http://localhost:%s${RESET}\n" "$PORT"
fi

# ── Frontend ────────────────────────────────────────────────────────
if port_in_use "$FRONTEND_PORT"; then
  echo -e "${YELLOW}!${RESET} port $FRONTEND_PORT already in use — assuming Vite is running"
else
  printf "${CYAN}▸${RESET} starting frontend on port %s ${DIM}(log: .dev-logs/frontend.log)${RESET}\n" "$FRONTEND_PORT"
  # Vite reads VITE_API_URL from the environment at dev-server start.
  ( cd "$FRONTEND" && VITE_API_URL="http://localhost:$PORT" \
      npm run dev -- --port "$FRONTEND_PORT" --strictPort >"$FRONTEND_LOG" 2>&1 ) &
  PIDS+=("$!")

  READY=0
  for _ in $(seq 1 60); do
    if urllib_ok "$FRONTEND_PORT" ""; then READY=1; break; fi
    sleep 0.5
  done
  if [ "$READY" -ne 1 ]; then
    echo -e "${RED}✖ frontend failed to start — last lines:${RESET}"
    tail -n 25 "$FRONTEND_LOG" || true
    exit 1
  fi
  printf "  ${GREEN}✔${RESET} frontend ready ${DIM}http://localhost:%s${RESET}\n" "$FRONTEND_PORT"
fi

cat <<EOF

  ${BOLD}SentinelAI is running${RESET}
    App        http://localhost:${FRONTEND_PORT}
    API        http://localhost:${PORT}
    API docs   http://localhost:${PORT}/docs
    Health     http://localhost:${PORT}/api/v1/health
    Logs       ${LOG_DIR}/

  ${DIM}Demo login: demo / demo1234   ·   Ctrl-C to stop${RESET}

EOF

# Keep the trap alive until interrupted; reopen logs with `make dev` output.
wait
