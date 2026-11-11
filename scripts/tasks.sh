#!/usr/bin/env bash
# SentinelAI developer task runner.
#
# This is the single implementation behind `make <task>`. Run it directly when
# `make` is unavailable (common on Windows):
#
#   bash scripts/tasks.sh setup
#   bash scripts/tasks.sh dev
#   bash scripts/tasks.sh cli scan samples/vulnerable_api.yaml
#   bash scripts/tasks.sh help
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

BACKEND="$REPO_ROOT/backend"
FRONTEND="$REPO_ROOT/frontend"
# Treat PORT=0 (ephemeral request) or a non-numeric value as the default.
normalize_port() {
  case "${1:-}" in
    ''|0|*[!0-9]*) echo "$2" ;;
    *) echo "$1" ;;
  esac
}

PORT=$(normalize_port "${PORT:-}" 8000)
FRONTEND_PORT=$(normalize_port "${FRONTEND_PORT:-}" 5173)

if [ -x "$BACKEND/venv/Scripts/python.exe" ]; then PY="$BACKEND/venv/Scripts/python.exe"
elif [ -x "$BACKEND/venv/bin/python" ]; then PY="$BACKEND/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else PY="python"; fi

TASK="${1:-help}"
shift || true

case "$TASK" in
  # ── Onboarding ─────────────────────────────────────────────────────
  setup)        exec bash scripts/setup.sh "$@" ;;
  doctor)       exec bash scripts/doctor.sh "$@" ;;
  dev)          exec bash scripts/dev.sh "$@" ;;
  dev-backend)  cd "$BACKEND" && exec "$PY" -m uvicorn app.main:app --reload --port "$PORT" ;;
  dev-frontend) cd "$FRONTEND" && exec npm run dev -- --port "$FRONTEND_PORT" ;;

  install)            exec bash scripts/setup.sh ;;
  install-backend)    exec bash scripts/setup.sh --backend-only ;;
  install-frontend)   cd "$FRONTEND" && exec npm install ;;

  # ── Quality ────────────────────────────────────────────────────────
  test)          cd "$BACKEND" && "$PY" -m pytest -q && cd "$FRONTEND" && npm test ;;
  test-backend)  cd "$BACKEND" && exec "$PY" -m pytest -q ;;
  test-frontend) cd "$FRONTEND" && exec npm test ;;
  test-fast)     cd "$BACKEND" && exec "$PY" -m pytest -q -m "not slow" -x ;;
  test-watch)    cd "$FRONTEND" && exec npm run test:watch ;;
  coverage)      cd "$BACKEND" && exec "$PY" -m pytest -q --cov=app \
                   --cov-report=term-missing --cov-report=html ;;
  bench)         cd "$BACKEND" && exec "$PY" -m pytest tests/test_performance_benchmarks.py -q -s ;;

  lint)          cd "$BACKEND" && "$PY" -m ruff check app tests; \
                 cd "$BACKEND" && "$PY" -m ruff check ../tools; \
                 cd "$FRONTEND" && npm run lint --if-present ;;
  lint-changed)  exec bash scripts/lint-changed.sh "$@" ;;
  lint-fix)      cd "$BACKEND" && "$PY" -m ruff check --fix app tests ../tools ;;
  fmt)           cd "$BACKEND" && "$PY" -m black app tests; \
                 cd "$BACKEND" && "$PY" -m ruff check --fix --select I app tests; \
                 cd "$BACKEND" && "$PY" -m ruff format ../tools ;;
  typecheck)     cd "$BACKEND" && exec "$PY" -m mypy app --ignore-missing-imports ;;
  check)         bash scripts/lint-changed.sh || exit 1
                 ( cd "$BACKEND" && "$PY" -m mypy app --ignore-missing-imports ) || exit 1
                 cd "$BACKEND" && exec "$PY" -m pytest -q -m "not slow" -x ;;
  hooks)         cd "$BACKEND" && "$PY" -m pre_commit install && exec "$PY" -m pre_commit run --all-files ;;

  # ── Data ───────────────────────────────────────────────────────────
  migrate)    cd "$BACKEND" && exec "$PY" -m alembic upgrade head ;;
  migration)  [ -n "${1:-}" ] || { echo "Usage: tasks.sh migration \"describe change\"" >&2; exit 1; }
              cd "$BACKEND" && exec "$PY" -m alembic revision --autogenerate -m "$1" ;;
  seed|demo)  exec "$PY" -m tools.sentinel_cli demo ;;
  reset-db)   exec bash scripts/setup.sh --reset-db ;;

  # ── Tooling ────────────────────────────────────────────────────────
  cli)        exec "$PY" -m tools.sentinel_cli "$@" ;;
  scan)       if [ "$#" -eq 0 ]; then set -- samples/vulnerable_api.yaml; fi
              exec "$PY" -m tools.sentinel_cli scan "$@" ;;
  playground) exec bash scripts/playground.sh ;;
  mocks)      exec "$PY" tools/mocks/mock_services.py ;;
  datasets)   exec bash scripts/gen-datasets.sh ;;
  stats)      exec bash scripts/doctor.sh --stats ;;
  secrets)    exec bash scripts/gen-secrets.sh "$@" ;;
  generate)   exec "$PY" tools/generate.py "$@" ;;

  # ── Docker ─────────────────────────────────────────────────────────
  docker-dev)  exec docker compose up -d --build ;;
  docker-prod) exec docker compose --profile full up -d --build ;;
  docker-down) exec docker compose down ;;

  # ── Cleanup ────────────────────────────────────────────────────────
  clean)      exec bash scripts/clean.sh ;;
  clean-all)  exec bash scripts/clean.sh --all ;;

  help|-h|--help) bash scripts/help.sh ;;
  *)
    echo "Unknown task: $TASK" >&2
    echo "Run: bash scripts/tasks.sh help" >&2
    exit 2
    ;;
esac
