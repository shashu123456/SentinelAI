#!/usr/bin/env bash
# Remove build and test artifacts.
#
#   bash scripts/clean.sh          # caches, coverage, build output
#   bash scripts/clean.sh --all    # also venv, node_modules, local database
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

rm -rf frontend/dist \
       backend/htmlcov \
       backend/.coverage \
       backend/.pytest_cache \
       backend/.ruff_cache \
       backend/.mypy_cache \
       .dev-logs

find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

if [ "${1:-}" = "--all" ]; then
  rm -rf backend/venv frontend/node_modules
  rm -f backend/sentinelai.db backend/sentinelai.db-shm backend/sentinelai.db-wal
  echo "✔ removed venv, node_modules, and the local database"
else
  echo "✔ removed caches and build artifacts"
fi
