#!/usr/bin/env bash
# Lint only the Python files you have touched.
#
# The repository carries pre-existing lint debt (see `make lint`). This script
# gates *your* changes so `make check` stays green on a fresh clone without
# hiding the backlog.
#
#   bash scripts/lint-changed.sh            # changed + new Python files
#   bash scripts/lint-changed.sh --all      # whole backend + tooling
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

if [ -x backend/venv/Scripts/python.exe ]; then PY="$REPO_ROOT/backend/venv/Scripts/python.exe"
elif [ -x backend/venv/bin/python ]; then PY="$REPO_ROOT/backend/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else PY="python"; fi

if ! "$PY" -m ruff --version >/dev/null 2>&1; then
  echo "· ruff not installed — run \`make install-backend\`" >&2
  exit 1
fi

# Ruff resolves `src = ["."]` relative to the working directory, so run it from
# backend/ exactly like CI does; otherwise imports sort differently.
cd "$REPO_ROOT/backend" || exit 1

if [ "${1:-}" = "--all" ]; then
  "$PY" -m ruff check app tests ../tools
  exit $?
fi

# Working-tree changes only: staged, unstaged, and new files. Comparing against
# a branch would include every commit since divergence and defeat the purpose.
FILES=()
while IFS= read -r file; do
  [ -n "$file" ] || continue
  if [[ "$file" == backend/* ]]; then
    FILES+=("${file#backend/}")
  elif [[ "$file" == tools/* ]]; then
    FILES+=("../$file")
  fi
done < <(
  { git -C "$REPO_ROOT" diff --name-only --diff-filter=ACMR;
    git -C "$REPO_ROOT" diff --cached --name-only --diff-filter=ACMR;
    git -C "$REPO_ROOT" ls-files --others --exclude-standard; } \
    | sort -u | grep -E '\.py$' || true
)

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "· no changed Python files — nothing to lint"
  exit 0
fi

echo "▸ ruff check ${#FILES[@]} changed file(s)"
"$PY" -m ruff check "${FILES[@]}"
