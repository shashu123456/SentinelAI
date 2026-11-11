# ═══════════════════════════════════════════════════════════════════
# SentinelAI — Developer Makefile
# ═══════════════════════════════════════════════════════════════════
# Run `make` (or `make help`) to list every task.
#
# New here? `make setup` then `make dev`.
#
# No `make` on your machine (common on Windows)? Every task is implemented
# in scripts/tasks.sh, so use the identical names:
#
#   bash scripts/tasks.sh setup
#   bash scripts/tasks.sh dev
#
# Every target is a one-line wrapper so the Makefile and the scripts can never
# drift apart.
# ═══════════════════════════════════════════════════════════════════

SHELL := /bin/bash
.DEFAULT_GOAL := help

TASKS := bash scripts/tasks.sh

# Arguments for `cli`, `scan`, `generate`, `migration` etc.
ARGS ?=

.PHONY: help setup doctor dev dev-backend dev-frontend \
        install install-backend install-frontend \
        test test-backend test-frontend test-fast test-watch coverage bench \
        lint lint-changed lint-fix fmt typecheck check hooks \
        migrate migration seed demo reset-db \
        cli scan playground mocks datasets stats secrets generate \
        docker-dev docker-prod docker-down clean clean-all

help: ## Show this help
	@$(TASKS) help

setup: ## One-command onboarding: venv, deps, .env, DB, demo data
	@$(TASKS) setup

doctor: ## Diagnose your local environment
	@$(TASKS) doctor

dev: ## Run backend + frontend together (Ctrl-C stops both)
	@$(TASKS) dev

dev-backend: ## Run the API with hot reload
	@$(TASKS) dev-backend

dev-frontend: ## Run the Vite dev server
	@$(TASKS) dev-frontend

install: ## Install all dependencies
	@$(TASKS) install

install-backend: ## Create the venv and install Python dependencies
	@$(TASKS) install-backend

install-frontend: ## Install frontend dependencies
	@$(TASKS) install-frontend

test: ## Run every test suite
	@$(TASKS) test

test-backend: ## Run backend tests
	@$(TASKS) test-backend

test-frontend: ## Run frontend tests
	@$(TASKS) test-frontend

test-fast: ## Run the fast backend subset (no slow/benchmark tests)
	@$(TASKS) test-fast

test-watch: ## Re-run frontend tests on change
	@$(TASKS) test-watch

coverage: ## Backend coverage report (term + htmlcov)
	@$(TASKS) coverage

lint: ## Lint everything (reports pre-existing debt)
	@$(TASKS) lint

lint-changed: ## Lint only the Python files you changed
	@$(TASKS) lint-changed

lint-fix: ## Auto-fix lint issues
	@$(TASKS) lint-fix

fmt: ## Format backend + tooling code
	@$(TASKS) fmt

typecheck: ## Type-check the backend
	@$(TASKS) typecheck

check: ## Gate your changes: lint-changed, typecheck, fast tests
	@$(TASKS) check

hooks: ## Install git pre-commit hooks
	@$(TASKS) hooks

migrate: ## Apply database migrations
	@$(TASKS) migrate

migration: ## Create a migration (ARGS="describe change")
	@$(TASKS) migration "$(ARGS)"

seed: ## Seed demo user, org, project, and scans
	@$(TASKS) seed

demo: ## Alias for `seed`
	@$(TASKS) demo

reset-db: ## Drop and recreate the local SQLite database
	@$(TASKS) reset-db

cli: ## Run the CLI (ARGS="scan samples/vulnerable_api.yaml")
	@$(TASKS) cli $(ARGS)

scan: ## Scan a spec locally (ARGS="samples/secure_api.yaml --all")
	@$(TASKS) scan $(ARGS)

playground: ## Serve the offline API playground on :8080
	@$(TASKS) playground

mocks: ## Run mock Ollama + SMTP + webhook services
	@$(TASKS) mocks

datasets: ## Regenerate samples/datasets/*.json from samples/*.yaml
	@$(TASKS) datasets

stats: ## Show repository size and file counts
	@$(TASKS) stats

secrets: ## Generate deployment secrets (ARGS="--env")
	@$(TASKS) secrets $(ARGS)

generate: ## Scaffold code (ARGS="route webhooks")
	@$(TASKS) generate $(ARGS)

bench: ## Run performance benchmarks
	@$(TASKS) bench

docker-dev: ## Start the full stack in Docker
	@$(TASKS) docker-dev

docker-prod: ## Start the production profile (with observability)
	@$(TASKS) docker-prod

docker-down: ## Stop the Docker stack
	@$(TASKS) docker-down

clean: ## Remove caches and build artifacts
	@$(TASKS) clean

clean-all: ## Also remove venv, node_modules, and the local database
	@$(TASKS) clean-all
