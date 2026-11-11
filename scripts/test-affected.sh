#!/usr/bin/env bash
# Run Vitest for the frontend files touched by this commit.
#
# Falls back to a no-op when node_modules is missing (fresh clone, CI cache
# miss) so commits are never blocked by an environment problem.
#
#   bash scripts/test-affected.sh src/pages/Dashboard.jsx
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$REPO_ROOT/frontend"

[ -d "$FRONTEND/node_modules" ] || { echo "· frontend deps missing — skipping"; exit 0; }

# Only files that have (or could have) a sibling test warrant a run.
TARGETS=()
for file in "$@"; do
  case "$file" in
    *.test.jsx|*.test.js) TARGETS+=("$file") ;;
    *.jsx|*.js)
      base="${file%.*}"
      [ -f "$REPO_ROOT/${base}.test.jsx" ] && TARGETS+=("${base}.test.jsx")
      [ -f "$REPO_ROOT/${base}.test.js" ] && TARGETS+=("${base}.test.js")
      ;;
  esac
done

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "· no related frontend tests — skipping"
  exit 0
fi

RELATIVE=()
for target in "${TARGETS[@]}"; do
  RELATIVE+=("${target#"$FRONTEND"/}")
done

echo "▸ vitest ${RELATIVE[*]}"
cd "$FRONTEND" || exit 1
npm test --silent -- "${RELATIVE[@]}" || {
  echo "✖ frontend tests failed. Fix them, or run \`make test-frontend\`." >&2
  exit 1
}
