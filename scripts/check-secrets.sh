#!/usr/bin/env bash
# Block accidental credential commits. Fast, dependency-free, offline.
#
#   bash scripts/check-secrets.sh            # scan the working tree
#   bash scripts/check-secrets.sh --staged   # scan only staged changes (pre-commit)
#
# Allow an intentional match by adding `pragma: allowlist secret` to the line.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

EXCLUDES=(
  ":(exclude)node_modules" ":(exclude)venv" ":(exclude)dist" ":(exclude).git"
  ":(exclude)*.lock" ":(exclude)package-lock.json" ":(exclude)*.min.js"
  ":(exclude)docs/*.md" ":(exclude)*.example" ":(exclude).env.example"
  ":(exclude)backend/.env.example" ":(exclude)scripts/check-secrets.sh"
)

# name|regex
PATTERNS=(
  'AWS access key|AKIA[0-9A-Z]{16}'
  'AWS secret key|aws_secret_access_key\s*=\s*["'"'"'][A-Za-z0-9/+=]{40}'
  'GitHub token|gh[pousr]_[A-Za-z0-9]{36,}'
  'Slack token|xox[baprs]-[A-Za-z0-9-]{10,}'
  'Google API key|AIza[0-9A-Za-z_-]{35}'
  'Stripe secret key|sk_(live|test)_[A-Za-z0-9]{24,}'
  'Private key block|-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----'
  'OpenAI-style key|sk-[A-Za-z0-9]{32,}'
  'JWT secret literal|SECRET_KEY\s*=\s*["'"'"'][A-Za-z0-9_-]{24,}["'"'"']'
  'Hardcoded password|(password|passwd|pwd)\s*[:=]\s*["'"'"'][^"'"'"'${}]{8,}["'"'"']'
)

if [ "${1:-}" = "--staged" ]; then
  FILES=$(git diff --cached --name-only --diff-filter=ACMR || true)
  SEARCH_CMD=(git diff --cached --unified=0)
else
  FILES=$(git ls-files || true)
  SEARCH_CMD=(git grep -n -I -E)
fi

if [ -z "$FILES" ]; then
  echo "✔ check-secrets: nothing to scan"
  exit 0
fi

FOUND=0
for entry in "${PATTERNS[@]}"; do
  name="${entry%%|*}"
  regex="${entry#*|}"

  if [ "${1:-}" = "--staged" ]; then
    matches=$(git diff --cached --unified=0 --diff-filter=ACMR | grep -E '^\+' | grep -Ev '^\+\+\+' \
      | grep -Ev 'pragma: allowlist secret' | grep -E "$regex" || true)
  else
    matches=$(git grep -n -I -E --color=never "$regex" -- . "${EXCLUDES[@]}" 2>/dev/null \
      | grep -v 'pragma: allowlist secret' || true)
  fi

  if [ -n "$matches" ]; then
    FOUND=1
    echo "✖ possible $name detected:"
    echo "$matches" | head -5 | sed 's/^/    /'
    echo ""
  fi
done

if [ "$FOUND" -eq 1 ]; then
  echo "Remove the secret, load it from the environment, or annotate the line"
  echo "with 'pragma: allowlist secret' when it is a documented dummy value."
  exit 1
fi

echo "✔ check-secrets: no credentials found"
exit 0
