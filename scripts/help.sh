#!/usr/bin/env bash
# Grouped task list shared by `make` and `bash scripts/tasks.sh help`.
set -uo pipefail

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  BOLD=$(printf '\033[1m'); DIM=$(printf '\033[2m'); CYAN=$(printf '\033[36m'); RESET=$(printf '\033[0m')
else
  BOLD=""; DIM=""; CYAN=""; RESET=""
fi

row() { printf "    ${CYAN}%-16s${RESET} %s\n" "$1" "$2"; }

printf "\n  ${BOLD}SentinelAI — developer commands${RESET}\n"

printf "\n  ${CYAN}Getting started${RESET}\n"
row setup          "One command onboarding: venv, deps, .env, DB, demo data"
row doctor         "Diagnose your local environment"
row dev            "Run backend + frontend together"
row demo           "Seed the demo user, org, project, and scans"
row scan           "Scan a spec locally (default: samples/vulnerable_api.yaml)"

printf "\n  ${CYAN}Quality${RESET}\n"
row test           "Backend + frontend test suites"
row test-fast      "Fast backend subset (~20s)"
row test-backend   "Backend pytest"
row test-frontend  "Vitest"
row coverage       "Backend coverage (term + htmlcov)"
row lint-changed   "Lint only the files you changed"
row lint           "Lint everything (reports pre-existing debt)"
row fmt            "Format backend + tooling"
row typecheck      "mypy"
row check          "Gate your changes: lint-changed, types, fast tests"
row hooks          "Install and run pre-commit hooks"

printf "\n  ${CYAN}Data & tooling${RESET}\n"
row migrate        "Apply database migrations"
row migration      "Create a migration: migration \"add column x\""
row reset-db       "Drop and recreate the local SQLite database"
row cli            "Run the sentinel CLI with arguments"
row playground     "Serve the offline API playground on :8080"
row mocks          "Mock Ollama + SMTP + webhook services"
row datasets       "Regenerate samples/datasets/*.json"
row generate       "Scaffold code: route | page | component | plugin | fixture"
row bench          "Performance benchmarks"
row stats          "Repository size summary"
row secrets        "Generate deployment secrets"

printf "\n  ${CYAN}Docker & cleanup${RESET}\n"
row docker-dev     "Start the stack in Docker"
row docker-prod    "Start with observability profile"
row docker-down    "Stop the stack"
row clean          "Remove caches and build artifacts"
row clean-all      "Also remove venv, node_modules, local database"

printf "\n  ${DIM}make <task>   ·   bash scripts/tasks.sh <task>   ·   PORT=8001 make dev${RESET}\n\n"
