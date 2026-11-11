# SentinelAI

### AI-Powered Application Security Platform

<p align="center">
  <strong>Discover, analyze, prioritize, and remediate application security risks<br/>across the entire Software Development Lifecycle.</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#platform-capabilities">Capabilities</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#api-reference">API</a> ·
  <a href="#deployment">Deploy</a> ·
  <a href="#documentation">Docs</a>
</p>

<p align="center">
  <a href="https://github.com/your-org/sentinelai/actions"><img src="https://github.com/your-org/sentinelai/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="#"><img src="https://img.shields.io/badge/react-18-61DAFB.svg" alt="React 18"></a>
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License"></a>
</p>

---

## Why SentinelAI

Modern applications expose 90%+ of their surface area through APIs. SentinelAI is not a dashboard — it's a **production-inspired AI-powered security platform** that combines four integrated security engines with enterprise multi-tenancy, 6-tier RBAC, and real-time threat intelligence into one intelligent platform.

| Capability | What It Does | Depth |
|-----------|-------------|-------|
| **OWASP API Scanner** | Analyzes OpenAPI/Swagger specs against OWASP Top 10 | 21 independent checks, CWE-mapped, CVSS scored |
| **SAST Engine** | Static analysis of Python, JavaScript, Java source code | 48 security rules, line-level evidence |
| **Dependency Scanner** | Checks packages against known CVE databases | 70+ curated CVEs, fix version guidance |
| **AI Security Copilot** | Context-aware security reasoning over findings | Intent classification, remediation plans, executive summaries |
| **Enterprise Multi-Tenancy** | Organizations, teams, projects, invitations, API keys | 6-tier RBAC, scan isolation, org analytics |
| **Security Hardening** | XSS, SSRF, CSRF, brute force detection, threat intelligence | 86 security tests, 13 security headers |

---

## Platform Capabilities

### Security Intelligence

- **OWASP API Security Top 10** — 21 checks covering API1 through API10
- **SAST Rules** — 48 rules across Python, JavaScript, and Java
- **Dependency CVE Detection** — 70+ curated vulnerability entries
- **Risk Scoring** — Severity-weighted CVSS scoring with floor rules
- **AI Copilot** — Intent classification, context retrieval, rule-based + LLM fallback
- **Compliance Mapping** — OWASP, CWE, CVSS, PCI DSS, SOC2 references

### Enterprise Features

- **Organizations** — Multi-tenant workspace with billing tiers
- **Teams** — Group members by function (security, dev, ops)
- **Projects** — Scoped scan isolation within organizations
- **6-Tier RBAC** — owner → admin → security_engineer → developer → viewer
- **Invitations** — Email-based with token authentication
- **API Keys** — Scoped, hashed, prefix-based key management
- **Audit Logging** — Append-only, risk-classified audit trail
- **Security Events Dashboard** — Real-time threat monitoring

### Production Infrastructure

- **93 API Endpoints** — RESTful with envelope responses
- **17 Database Tables** — PostgreSQL 16 with 26+ indexes
- **Redis Caching** — Token blacklist, dashboard cache, session storage
- **Prometheus Metrics** — 30+ custom metrics
- **Grafana Dashboards** — System health, API performance, scanner analytics
- **Loki Logging** — Structured JSON logs with correlation IDs
- **Alertmanager** — 12 pre-configured alert rules
- **Terraform** — AWS deployment module (VPC, RDS, ECS, ALB)

### Developer Experience

- **Command Palette** (⌘K) — Keyboard-driven navigation
- **Dark/Light Mode** — Full theme system with persistence
- **Error Boundaries** — Graceful failure handling
- **Skeleton Loading** — Per-page skeleton states
- **Toast Notifications** — Real-time feedback
- **Keyboard Shortcuts** — Global navigation shortcuts
- **Swagger UI** — Interactive API documentation at `/docs`

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│   React 18 SPA · Vite 6 · React Router 6 · Recharts · Lucide   │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP / WebSocket
┌────────────────────────────▼─────────────────────────────────────┐
│                         GATEWAY LAYER                             │
│   Nginx 1.25 · TLS Termination · Rate Limiting · Static Assets  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                       APPLICATION LAYER                           │
│   FastAPI 0.115 · Python 3.11 · SQLAlchemy 2.0 · Pydantic v2   │
│                                                                    │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│   │ Auth     │ │ Scans    │ │ Orgs     │ │ Security Events  │   │
│   │ JWT+CSRF │ │ Upload   │ │ Teams    │ │ Threat Detection │   │
│   │ RBAC     │ │ Reports  │ │ Invites  │ │ IP Reputation    │   │
│   │ Lockout  │ │ Analytics│ │ API Keys │ │ Session Monitor  │   │
│   └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                     INTELLIGENCE LAYER                            │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│   │ OWASP    │ │ SAST     │ │ Dep Scan │ │ AI Copilot       │   │
│   │ 21 Rules │ │ 48 Rules │ │ 70+ CVEs │ │ Ollama + Rules   │   │
│   │ CWE Maps │ │ Line Lvl │ │ Fix Ver  │ │ Intent Classify  │   │
│   │ CVSS     │ │ Python   │ │ 3 Formats│ │ Context Retrieval│   │
│   │          │ │ JS/Java  │ │ SBOM     │ │ Executive Summ   │   │
│   └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                        DATA LAYER                                 │
│   PostgreSQL 16 (17 tables) · Redis 7 (cache + sessions)         │
│   26+ Indexes · Connection Pooling · WAL Mode · Alembic Migrate  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                             │
│   Prometheus (metrics) · Grafana (dashboards) · Loki (logs)      │
│   Alertmanager (alerts) · Sentry (errors) · Smoke Tests          │
└──────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React 18, Vite 6, React Router 6 | Fast SPA, code splitting, modern DX |
| **UI** | Recharts, Lucide Icons, CSS Modules | Professional charts, consistent icons |
| **Backend** | FastAPI, Python 3.11, Pydantic v2 | Async, type-safe, auto OpenAPI |
| **ORM** | SQLAlchemy 2.0, Alembic | Production ORM, safe migrations |
| **Auth** | JWT (python-jose), bcrypt, CSRF | Stateless auth with token rotation |
| **Database** | PostgreSQL 16 (prod), SQLite (dev) | ACID, JSON support, full-text search |
| **Cache** | Redis 7 | Token blacklist, dashboard cache |
| **AI** | Ollama (Mistral) + rule-based fallback | Local inference, no API costs |
| **Reports** | ReportLab (PDF) | Enterprise-quality PDF generation |
| **Real-time** | WebSocket (FastAPI native) | Live scan streaming |
| **Monitoring** | Prometheus + Grafana + Loki | Full observability stack |
| **CI/CD** | GitHub Actions | Lint, test, Docker, CodeQL, Gitleaks |
| **Deployment** | Docker Compose, Render, Railway, Terraform | One-click to enterprise |

---

## Quick Start

### Option 1: Local development (< 15 minutes)

```bash
git clone https://github.com/your-org/sentinelai.git
cd sentinelai
make setup     # venv, deps, .env, migrations, demo data
make dev       # backend :8000 + frontend :5173
```

Then sign in with **demo / demo1234**. Run `make doctor` if anything looks off,
and see [docs/DEVELOPER-ONBOARDING.md](docs/DEVELOPER-ONBOARDING.md) for the
15-minute tour.

No server needed to try the scanner:

```bash
make scan                                              # bundled vulnerable spec
make cli ARGS="scan samples/secure_api.yaml --all"      # any spec
make cli ARGS="scan openapi.yaml --format sarif -o results.sarif --fail-on high"
```

### Option 2: Docker

```bash
git clone https://github.com/your-org/sentinelai.git
cd sentinelai
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:80 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

### Option 3: Manual Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Demo Credentials (created by `make seed`)

| Field | Value |
|-------|-------|
| Username | `demo` |
| Password | `demo1234` |
| Backend | http://localhost:8000 |
| Frontend | http://localhost:5173 |

### Verify

```bash
make doctor                            # environment diagnostics
curl http://localhost:8000/api/health  # health check
./scripts/smoke-test.sh                # smoke test

# CLI (local scan, no server required)
make scan

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT + refresh token |
| POST | `/api/auth/refresh` | Rotate refresh token |
| POST | `/api/auth/logout` | Revoke tokens |
| GET | `/api/auth/me` | Current user profile |

### Scanning

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scans/upload` | Upload OpenAPI spec & scan |
| GET | `/api/scans` | List scans (paginated) |
| GET | `/api/scans/{id}` | Scan details + findings |
| GET | `/api/scans/{id}/report` | Download PDF report |
| POST | `/api/copilot/chat` | AI security copilot |

### Enterprise

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/orgs` | Create organization |
| GET | `/api/v1/orgs` | List organizations |
| POST | `/api/v1/orgs/{id}/teams` | Create team |
| POST | `/api/v1/orgs/{id}/invitations` | Invite member |
| POST | `/api/v1/orgs/{id}/api-keys` | Create API key |
| GET | `/api/audit` | Audit log center |
| GET | `/api/v1/security/events` | Security events |

**93 total endpoints** — see [docs/API.md](docs/API.md) for the complete reference.

---

## Security

### Defense in Depth

```
Layer 1: Network      → TLS, Rate Limiting, DDoS Protection
Layer 2: Application  → CSP, CORS, 13 Security Headers
Layer 3: Auth         → JWT + Refresh Rotation, bcrypt, Lockout
Layer 4: AuthZ        → 6-Tier RBAC, Org/Project Scoping
Layer 5: Input        → XSS, SQLi, SSRF, Path Traversal Detection
Layer 6: Monitoring   → Threat Detection, IP Reputation, Session Monitor
```

### OWASP API Top 10 Coverage

| OWASP | Category | Status |
|-------|----------|--------|
| API1 | Broken Object Level Authorization | ✅ Detected |
| API2 | Broken Authentication | ✅ Detected |
| API3 | Broken Object Property Level Authorization | ✅ Detected |
| API4 | Unrestricted Resource Consumption | ✅ Detected |
| API5 | Broken Function Level Authorization | ✅ Detected |
| API6 | Unrestricted Access to Sensitive Business Flows | ✅ Detected |
| API7 | Server Side Request Forgery | ✅ Detected |
| API8 | Security Misconfiguration | ✅ Detected |
| API9 | Improper Inventory Management | ✅ Detected |
| API10 | Unsafe Consumption of APIs | ✅ Detected |

See [docs/SECURITY.md](docs/SECURITY.md) for the complete security documentation.

---

## Testing

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

### Test Coverage

| Suite | Tests | Coverage |
|-------|-------|----------|
| Authentication & RBAC | 42 | JWT, refresh rotation, CSRF, org isolation |
| OWASP Scanner | 18 | 21 security checks, edge cases |
| SAST Engine | 15 | 48 rules, false positive handling |
| Dependency Scanner | 10 | CVE detection, fix versions |
| Security Hardening | 86 | XSS, SQLi, SSRF, threat detection |
| Enterprise Multitenancy | 42 | Teams, invitations, API keys |
| Audit Logging | 26 | Append-only, risk classification |
| System Health | 20 | Prometheus metrics, health checks |
| Other | 30+ | Cache, rate limiting, websockets |
| **Total** | **289+** | **All passing** |

---

## Deployment

### Docker Compose

```bash
# Full stack
docker compose up --build

# With AI engine
docker compose --profile ai up --build

# With monitoring
docker compose --profile observability up --build

# Everything
docker compose --profile full up --build
```

### Cloud Platforms

| Platform | Config | Status |
|----------|--------|--------|
| **Render** | `render.yaml` | ✅ Blueprint ready |
| **Railway** | `railway.json` | ✅ Config ready |
| **Vercel** | `vercel.json` | ✅ Frontend deploy |
| **AWS** | `deploy/terraform/aws/main.tf` | ✅ Terraform module |
| **Docker** | `docker-compose.yml` | ✅ 10 services |

### One-Click Deploy

```bash
# Clone and deploy
git clone https://github.com/your-org/sentinelai.git
cd sentinelai
./scripts/deploy.sh
```

See [docs/DEPLOYMENT-GUIDE.md](docs/DEPLOYMENT-GUIDE.md) for platform-specific instructions.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System architecture with Mermaid diagrams |
| [Database](docs/DATABASE.md) | Schema reference, ER diagrams, migrations |
| [API Reference](docs/API.md) | All 93 endpoints with examples |
| [Developer Onboarding](docs/DEVELOPER-ONBOARDING.md) | Zero to running in 15 minutes |
| [Developer Guide](docs/DEVELOPER-GUIDE.md) | Setup, coding standards, testing |
| [CLI](docs/CLI.md) | `sentinel` commands: local scans, uploads, reports |
| [Security](docs/SECURITY.md) | Threat model, OWASP compliance, hardening |
| [Contributing](docs/CONTRIBUTING.md) | PR process, code review, branch strategy |
| [Deployment Guide](docs/DEPLOYMENT-GUIDE.md) | Docker, cloud, Terraform instructions |
| [Phase 10](docs/PHASE-10.md) | Enterprise multi-tenancy implementation |
| [Security Review](docs/SECURITY-REVIEW.md) | OWASP ASVS security assessment |
| [Release Notes](docs/RELEASE-NOTES-v1.0.md) | v1.0 production release notes |
| [CHANGELOG](CHANGELOG.md) | Complete version history |

---

## Project Structure

```
sentinelai/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # 12 route modules (93 endpoints)
│   │   ├── core/             # 6 domain engines
│   │   │   ├── security_engine/   # OWASP scanner (21 checks)
│   │   │   ├── sast_engine/       # Static analysis (48 rules)
│   │   │   ├── dep_scanner/       # Dependency CVE detection
│   │   │   ├── risk_engine/       # CVSS scoring + grading
│   │   │   ├── ai_engine/         # Vulnerability analysis
│   │   │   └── copilot/           # AI security assistant
│   │   ├── models/           # SQLAlchemy ORM (17 tables)
│   │   ├── schemas/          # Pydantic v2 request/response
│   │   ├── repositories/     # Data access layer (10 repos)
│   │   ├── services/         # Business logic (6 services)
│   │   ├── utils/            # 12 utility modules
│   │   ├── reports/          # PDF/JSON report generation
│   │   └── main.py           # FastAPI application
│   ├── alembic/              # Database migrations
│   ├── tests/                # 289+ pytest tests
│   └── Dockerfile            # Multi-stage production build
├── frontend/
│   ├── src/
│   │   ├── pages/            # 19 route pages
│   │   ├── components/       # 9 reusable components
│   │   ├── context/          # Auth, Theme, Org contexts
│   │   └── services/         # API client modules
│   ├── nginx.conf            # Production nginx config
│   └── Dockerfile            # Multi-stage build
├── deploy/
│   ├── terraform/            # AWS infrastructure as code
│   ├── prometheus/           # Metrics + alert rules
│   ├── grafana/              # Dashboard provisioning
│   ├── loki/                 # Log aggregation config
│   └── alertmanager/         # Alert routing config
├── scripts/                  # Deploy, backup, rollback, smoke test
├── docs/                     # 14 documentation files
├── docker-compose.yml        # 10 services, 5 profiles
├── .github/workflows/ci.yml  # CI/CD pipeline
└── render.yaml               # Render deployment blueprint
```

---

## CI/CD Pipeline

```
Push to GitHub
  ├── Lint (Black + Ruff)
  ├── Test (pytest + coverage)
  ├── Build (Vite + FastAPI)
  ├── Docker (multi-stage)
  ├── Security (CodeQL + Gitleaks + Dependabot)
  └── Deploy Verification (smoke test)
```

---

## Version Roadmap

### v1.1.0 — Current

- ✅ Enterprise multi-tenancy (organizations, teams, projects)
- ✅ 6-tier RBAC with org/project scoping
- ✅ Security hardening (XSS, SSRF, threat detection, 13 headers)
- ✅ Performance optimization (connection pooling, caching, query monitoring)
- ✅ 289+ tests, all passing

### v1.5 — Planned

- [ ] TypeScript migration for frontend
- [ ] E2E tests (Playwright)
- [ ] WebSocket authentication hardening
- [ ] RAG-based AI copilot with vector search
- [ ] Compliance center (PCI DSS, SOC2, ISO27001)
- [ ] Attack graph visualization
- [ ] MFA/TOTP support

### v2.0 — Vision

- [ ] Container security scanning
- [ ] Cloud security (AWS, GCP, Azure)
- [ ] IaC security (Terraform, CloudFormation)
- [ ] Secrets detection scanner
- [ ] API discovery and inventory
- [ ] Policy as Code engine
- [ ] Developer coaching and security training
- [ ] Plugin marketplace

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built as a production-inspired enterprise security platform demonstrating<br/>
  full-stack engineering, application security, AI integration, and DevOps excellence.
</p>
