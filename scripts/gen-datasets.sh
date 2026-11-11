#!/usr/bin/env bash
# Regenerate samples/datasets/*-scan.json from the specs in samples/.
#
#   make datasets
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -x backend/venv/Scripts/python.exe ]; then PY="backend/venv/Scripts/python.exe"
elif [ -x backend/venv/bin/python ]; then PY="backend/venv/bin/python"
else PY="python"; fi

mkdir -p samples/datasets
count=0
for spec in samples/*.yaml; do
  name=$(basename "$spec" .yaml)
  "$PY" -m tools.sentinel_cli scan "$spec" --format json -o "samples/datasets/${name}-scan.json" >/dev/null
  count=$((count + 1))
done

echo "✔ regenerated ${count} dataset(s) in samples/datasets/"
