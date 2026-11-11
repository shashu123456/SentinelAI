# Developer Onboarding — Zero to Running in 15 Minutes

> Target: a new developer goes from `git clone` to a signed-in app, running a
> real scan, with tests passing — in under 15 minutes.

---

## 0 · What you need (2 minutes)

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.11+ | Backend API and scanners |
| Node.js | 18+ (with npm) | React frontend |
| Git | any recent | Version control |

Everything else (PostgreSQL, Redis, Ollama, SMTP) is **optional** for local
development — the app falls back to SQLite, an in-memory cache, rule-based AI
analysis, and a mock mail server.

Check what you have:

```bash
make doctor
```

`make doctor` prints a table of every requirement with a fix hint for each
problem. Warnings are fine; a red ✖ means fix it first.

---

## 1 · One command (3–8 minutes, mostly downloads)

```bash
git clone <repository-url> sentinelai
cd sentinelai
make setup
```

`make setup` is idempotent and does exactly this:

1. verifies Python 3.11+ and npm
2. creates `backend/venv` and installs `requirements-dev.txt`
3. writes `backend/.env` with a freshly generated `SECRET_KEY`
4. applies database migrations (falls back to `create_all`)
5. installs frontend dependencies
6. seeds a demo workspace with real scans
7. prints the next steps

Useful variants:

| Command | Effect |
|---------|--------|
| `make setup -- --skip-demo` | skip demo data |
| `make setup -- --backend-only` | no `npm install` |
| `make setup -- --reset-db` | drop and recreate the database |
| `make install` | dependencies only |

---

## 2 · Run it (1 minute)

```bash
make dev
```

```
  SentinelAI is running
    App        http://localhost:5173
    API        http://localhost:8000
    API docs   http://localhost:8000/docs
    Health     http://localhost:8000/api/v1/health
    Logs       .dev-logs/

  Demo login: demo / demo1234   ·   Ctrl-C to stop
```

`make dev` starts both servers, waits until each answers HTTP, and stops both on
Ctrl-C. If a port is already taken by a healthy instance, it reuses it instead
of failing.

Sign in with **demo / demo1234**. The demo workspace has three scanned APIs, an
organization, and a project, so the dashboard is populated on first load.

---

## 3 · Scan something without a server (1 minute)

The fastest loop in the project — no API, no database, no network:

```bash
make scan                                   # samples/vulnerable_api.yaml
make cli ARGS="scan samples/secure_api.yaml --all"
make cli ARGS="scan samples/*.yaml --format markdown -o report.md"
make cli ARGS="scan samples/vulnerable_api.yaml --format sarif -o results.sarif"
```

This runs the real engines (`parse → 21 OWASP checks → risk scoring`) in-process
and prints findings in ~300ms. `--fail-on high` makes it usable as a CI gate.

---

## 4 · Know the loop (2 minutes)

| Command | What it does |
|---------|--------------|
| `make dev` | backend + frontend with hot reload |
| `make test-fast` | quick backend suite (~20s) |
| `make test` | backend + frontend suites |
| `make lint-changed` | ruff on the files you changed (the default gate) |
| `make lint` | ruff on the whole backend — reports pre-existing debt |
| `make fmt` | black + ruff import sorting |
| `make typecheck` | mypy |
| `make check` | lint-changed + typecheck + fast tests |
| `make hooks` | install pre-commit hooks |
| `make seed` | (re)seed demo data |
| `make mocks` | mock Ollama + SMTP + webhook |
| `make playground` | offline API playground |
| `make datasets` | regenerate `samples/datasets/*.json` |

Run `make` alone to see the full, grouped list.

---

## 5 · Where things live (2 minutes)

```
backend/
  app/
    api/routes/        HTTP routers (one file per domain)
    api/v1/routers/    versioned API with response envelopes
    core/              security engines: security_engine, sast_engine,
                       dep_scanner, risk_engine, copilot, ai_platform
    models/            SQLAlchemy models
    repositories/      query layer (no business logic)
    services/          orchestration + transactions
    schemas/           Pydantic request/response models
    utils/             security, rbac, cache, ratelimit, logging
  tests/               pytest suites + tests/helpers
  alembic/             migrations
frontend/
  src/pages/           route-level screens
  src/components/      reusable UI
  src/services/api.js  the only place that talks to the API
  src/test/helpers.jsx shared test utilities
tools/
  sentinel_cli/        the `sentinel` CLI
  generate.py          scaffolders
  mocks/               mock external services
samples/               OpenAPI specs + captured scan datasets
docs/                  this guide, CLI.md, API.md, architecture, runbooks
```

---

## 6 · Create something (1 minute)

Do not hand-copy boilerplate — generate it:

```bash
python tools/generate.py route webhooks        # router + tests
python tools/generate.py page ReportBuilder    # page + css + tests
python tools/generate.py component SeverityBadge
python tools/generate.py plugin saml_login     # scanner plugin + tests
python tools/generate.py fixture findings      # reusable test data
```

Each generator prints the one line you need to register the new module.

---

## 7 · Work offline

| Need | Without internet |
|------|------------------|
| AI analysis | `make mocks` → set `OLLAMA_URL=http://localhost:11434/api/generate` |
| Password reset email | mock SMTP on `localhost:1025` (`SMTP_USE_TLS=false`) |
| Webhook targets | mock receiver on `localhost:8099`, inspect `/_requests` |
| API exploration | `make playground` → http://localhost:8080/api-playground.html |
| Fixtures | `samples/datasets/*-scan.json` (real engine output) |

---

## 8 · Commit cleanly

```bash
make hooks          # once per clone
git commit -m "feat(scan): export findings as SARIF"
```

Hooks run in under two seconds: whitespace/JSON/YAML hygiene, a secret scan
(AWS keys, private keys, JWTs, hardcoded passwords), ruff, an import check, and
affected frontend tests. Commit messages must follow Conventional Commits.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `make doctor` shows red | follow the `→` hint on that row |
| `Address already in use` | `PORT=8001 make dev` |
| Login fails with 423 | account lockout — wait 15 min or `make reset-db` |
| Login fails with 401 after seeding | passwords are case-sensitive: `demo1234` |
| Dashboard is empty | `make seed` |
| Slow first request | health checks warm up in ~2s on cold start |
| AI panel empty | expected without Ollama; `make mocks` provides a stand-in |
| `ModuleNotFoundError` in backend | `make install-backend` (venv is stale) |
| Frontend can't reach the API | `.env.local` `VITE_API_URL` must match the backend port |
| Tests fail on a fresh clone | `make install-backend` may still be running |
| `make lint` reports many errors | pre-existing debt, not yours — `make lint-changed` gates only your edits (see [TECHNICAL-DEBT-REPORT.md](TECHNICAL-DEBT-REPORT.md)) |
| Port 8080 taken (playground) | `PLAYGROUND_PORT=8088 make playground` |

Still stuck? Run `make doctor` and read the detail column — it names the exact
missing piece.

---

## The 15-minute checklist

- [ ] `make doctor` → no red rows
- [ ] `make setup` → "Setup complete"
- [ ] `make dev` → both ready, sign in as `demo`
- [ ] `make scan` → findings table in the terminal
- [ ] `make test-fast` → green
- [ ] `make hooks` → hooks installed
- [ ] `python tools/generate.py route demo` → new files, then delete them

Done — you are productive. For depth, read
[developer-guide.md](developer-guide.md), [CLI.md](CLI.md),
[architecture.md](architecture.md), and [API.md](API.md).
