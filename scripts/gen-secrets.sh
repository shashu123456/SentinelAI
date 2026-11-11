#!/usr/bin/env bash
# Generate the secrets a local or self-hosted deployment needs.
#
#   bash scripts/gen-secrets.sh            # human-readable
#   bash scripts/gen-secrets.sh --env      # copy-paste .env block
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/backend/venv"

if [ -x "$VENV/Scripts/python.exe" ]; then PY="$VENV/Scripts/python.exe"
elif [ -x "$VENV/bin/python" ]; then PY="$VENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else PY="python"; fi

read -r SECRET_KEY POSTGRES_PASSWORD GRAFANA_PASSWORD <<<"$("$PY" - <<'PY'
import secrets
print(secrets.token_urlsafe(48), secrets.token_urlsafe(24), secrets.token_urlsafe(16))
PY
)"

if [ "${1:-}" = "--env" ]; then
  cat <<EOF
SECRET_KEY=$SECRET_KEY
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
GRAFANA_PASSWORD=$GRAFANA_PASSWORD
EOF
  exit 0
fi

cat <<EOF
Generated secrets (store them in your secret manager, never in git):

  SECRET_KEY=$SECRET_KEY
  POSTGRES_PASSWORD=$POSTGRES_PASSWORD
  GRAFANA_PASSWORD=$GRAFANA_PASSWORD

Re-run with --env to print only the .env lines.
EOF
