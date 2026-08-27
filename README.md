# SentinelAI

> **AI-Powered Application Security Intelligence Platform**

<p align="center">
  <strong>Automated API security, static analysis, dependency scanning, and AI-powered security intelligence</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> · 
  <a href="#platform-capabilities">Capabilities</a> · 
  <a href="#architecture">Architecture</a> · 
  <a href="#api-endpoints">API</a> ·
  <a href="#design-system">Design</a>
</p>

---

## Why SentinelAI

Modern applications expose 90%+ of their surface area through APIs. SentinelAI provides a comprehensive security intelligence platform that goes beyond simple scanning — it analyzes, prioritizes, and explains security risks across your entire application stack.

**Four integrated security engines:**

| Engine | What It Does | Output |
|--------|-------------|--------|
| **API Security Scanner** | Analyzes OpenAPI/Swagger specs against OWASP Top 10 | CWE-mapped findings with confidence scores |
| **SAST Engine** | Static analysis of Python, JavaScript, Java source code | Line-level vulnerability detection |
| **Dependency Scanner** | Checks packages against known CVE databases | Vulnerable package identification with fix versions |
| **AI Security Copilot** | Context-aware security reasoning over findings | Remediation plans, executive summaries, attack analysis |

---

## Platform Capabilities

### API Security Intelligence
- OWASP API Security Top 10 (API1-API10) analysis
- 10 independent security checks with CWE mapping
- Per-finding confidence scores (40-95%)
- Detection reasons explaining what triggered each finding
- Risk scoring with severity-weighted algorithm and floor rules

### Static Application Security Testing (SAST)
- 40+ security rules across Python, JavaScript, and Java
- SQL injection, command injection, hardcoded secrets detection
- Unsafe deserialization, weak cryptography, path traversal
- XSS, SSRF, XXE vulnerability patterns
- Line-level evidence with remediation guidance

### Dependency Security Analysis
- Parse requirements.txt, package.json, pom.xml
- Cross-reference against curated CVE database (70+ known vulnerabilities)
- Covers critical packages: Django, Flask, requests, lodash, axios, Spring, etc.
- Severity scoring with CVSS, fix version guidance

### AI Security Copilot
- Context-aware security reasoning (not a generic chatbot)
- Understands scan findings, severity, CWE, OWASP mappings
- Generates: executive summaries, remediation plans, attack path analysis
- Maps findings to compliance frameworks
- Rule-based fallback when AI model unavailable

### Enterprise Reporting
- Professional PDF reports with circular risk gauge, severity distribution
- Finding cards with CWE badges, evidence, remediation
- Executive summary with metric cards
- JSON report export for programmatic consumption

### Real-Time Scan Progress
- WebSocket-based live terminal with ASCII art banner
- Color-coded severity output per finding
- OWASP check progress with percentage tracking
- Completion summary with risk score

---

## Architecture

```
  Frontend (React 18 + Vite 6)
  ├── Dashboard         ── Risk gauge, scan history, severity distribution
  ├── API Scanner       ── OpenAPI/Swagger upload with live/instant modes
  ├── SAST Scanner      ── Source code upload, line-level findings
  ├── Dependency Scanner ── Package manifest analysis, CVE detection
  ├── Security Copilot  ── AI chat interface with context
  ├── Live Terminal     ── Real-time WebSocket scan progress
  ├── Scan Results      ── Finding details, AI analysis, PDF/JSON download
  └── Auth              ── JWT login/register
          │
          │ HTTP / WebSocket
          ▼
  Backend (FastAPI + Python 3.11)
  ├── JWT Auth           ── Registration, login, token validation
  ├── Rate Limiting      ── SlowAPI per-IP rate limits
  └── Security Intelligence Pipeline
          │
          ├── API Security Engine
          │   ├── OpenAPI Parser    ── OpenAPI 3.x / Swagger 2.0
          │   ├── OWASP Scanner     ── 10 independent checks
          │   └── Risk Engine       ── Weighted scoring with floor rules
          │
          ├── SAST Engine
          │   ├── Rules Engine      ── 40+ pattern-based security rules
          │   ├── Code Scanner      ── Python/JS/Java analysis
          │   └── Finding Generator ── CWE-mapped, line-level output
          │
          ├── Dependency Scanner
          │   ├── Manifest Parser   ── requirements.txt, package.json, pom.xml
          │   ├── CVE Database      ── 70+ curated vulnerability entries
          │   └── Version Analyzer  ── Installed vs. fixed version comparison
          │
          ├── AI Engine
          │   ├── Ollama Integration ── Mistral/LLaMA for analysis
          │   ├── Fallback Analyzer  ── Rule-based when AI unavailable
          │   └── Security Copilot   ── Context-aware reasoning system
          │
          └── Report Generation
              ├── PDF Generator     ── ReportLab enterprise reports
              └── JSON Export       ── Structured scan data
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite 6, React Router 6, Recharts, Lucide Icons |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Pydantic v2 |
| **Auth** | JWT (python-jose), bcrypt (passlib), CSRF tokens |
| **AI** | Ollama (Mistral), with rule-based fallback |
| **SAST** | Custom regex-based rules engine (Python/JS/Java) |
| **Dependency Scanning** | Custom parsers + curated CVE database |
| **Reports** | ReportLab (PDF), native JSON |
| **Real-time** | WebSocket (FastAPI native) |
| **Database** | PostgreSQL 16 (prod), SQLite (dev) |
| **Cache** | Redis 7 (token blacklist, dashboard cache) |
| **Monitoring** | Prometheus metrics, Grafana dashboards |
| **Logging** | Structured JSON logs, correlation IDs, Sentry |
| **CI/CD** | GitHub Actions (lint, test, coverage, Docker, CodeQL, Gitleaks) |
| **Deployment** | Docker Compose, Render, Railway |
| **Testing** | pytest (150+ tests), Vitest |

---

## Design System

SentinelAI features a professional cybersecurity design with:

### Visual Identity
- **Dark/Light Mode** — Full theme system with localStorage persistence
- **SIEM Aesthetic** — Neon cyan accents, grid overlays, scanline effects
- **Typography** — Space Grotesk (display), DM Sans (body), JetBrains Mono (code)
- **Threat Radar** — Animated signature element on landing page

### Landing Page
- Hero with animated threat radar visualization
- Feature cards with hover effects and color-coded tags
- How-it-works section with numbered steps
- Animated stat counters with intersection observer
- Dynamic testimonials from database
- CTA section with conversion-optimized design

### Dashboard
- Threat gauge with severity-weighted scoring
- Severity matrix with animated progress bars
- Quick access cards for all security tools
- Recent operations with risk scores
- System status bar with live indicators

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Ollama for AI-enhanced analysis

### Backend

```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173` with API proxying to `http://localhost:8000`.

### Docker Compose (Full Stack)

```bash
# Copy environment template
cp .env.example .env
# Edit .env with your SECRET_KEY and passwords

# Start all services (Postgres, Redis, Backend, Frontend)
docker compose up --build

# With AI engine (Ollama)
docker compose --profile ai up --build

# With monitoring (Prometheus + Grafana)
docker compose --profile observability up --build

# Smoke test
./scripts/smoke-test.sh

# Frontend:    http://localhost:80
# Backend API: http://localhost:8000
# API Docs:    http://localhost:8000/docs
# Prometheus:  http://localhost:9090 (with observability profile)
# Grafana:     http://localhost:3001 (with observability profile)
```

### Cloud Deployment

**Render (one-click):**
1. Push to GitHub
2. Connect repo on [render.com](https://render.com) — `render.yaml` blueprint auto-detected
3. PostgreSQL + Redis provisioned automatically
4. Deploy → live at `https://sentinelai-backend.onrender.com`

**Railway:**
1. Connect repo on [railway.app](https://railway.app)
2. Add PostgreSQL plugin → set `DATABASE_URL`
3. Add Redis plugin → set `REDIS_URL`
4. Set `SECRET_KEY` env var
5. Deploy → `railway.json` configures build + health check

**Vercel (frontend only):**
1. Import repo on [vercel.com](https://vercel.com) → Root: `frontend/`
2. Framework: Vite → auto-detected
3. Set `VITE_API_URL` to your backend URL
4. Deploy → update `vercel.json` rewrite targets

---

## Ollama AI Integration

SentinelAI uses **Ollama** for AI-enhanced security analysis. When Ollama is running, the AI engine provides deeper vulnerability explanations. When it's unavailable, the system falls back to rule-based analysis automatically.

### Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows: download from https://ollama.com/download/windows
```

### Pull the Mistral model

```bash
ollama pull mistral
```

### Start Ollama server

```bash
ollama serve
# Runs on http://localhost:11434 by default
```

### How it works

| When Ollama is running | When Ollama is offline |
|----------------------|----------------------|
| AI analysis uses Mistral for vulnerability explanations | Rule-based fallback generates structured analysis |
| Executive summaries are AI-generated | Executive summaries use template-based generation |
| Copilot can provide contextual AI responses | Copilot uses rule-based intent matching + DB queries |

The backend config (`backend/app/config.py`) points to `http://localhost:11434/api/generate` by default. Override with:

```bash
export OLLAMA_URL=http://localhost:11434/api/generate
export OLLAMA_MODEL=mistral
```

### Verify AI is working

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Run a scan — AI analysis will show in the results if Ollama is up
# In the scan results page, the "AI Security Analysis" section shows AI-generated content
```

---

## Sample Scans

### API Security Scan

```bash
# 1. Open http://localhost:5173
# 2. Register/Login
# 3. Go to API Scanner
# 4. Upload samples/vulnerable_api.yaml
# 5. Select "Live Scan" for real-time progress
# 6. Review findings with CWE mapping
# 7. Download PDF report
```

### Step-by-Step Demo Flow

```
1. Register account        → POST /api/auth/register
2. Login                   → POST /api/auth/login (JWT token)
3. Upload OpenAPI spec     → POST /api/scans/upload/async
4. Watch live terminal     → WebSocket /ws/scan/{task_id}
5. View scan results       → GET /api/scans/{id}
6. Ask AI Analyst          → POST /api/security/copilot/chat
7. Download PDF report     → GET /api/scans/{id}/report/pdf
8. Run SAST scan           → POST /api/security/sast/scan
9. Run dependency scan     → POST /api/security/deps/scan
```

**Vulnerable API:** Risk Score 90/100, 15+ findings across 8 OWASP categories
**Secured API:** Risk Score 10/100, only low-severity informational items

### SAST Scan

```bash
# Upload any .py, .js, or .java file for static analysis
# Detects: SQL injection, command injection, hardcoded secrets,
#           weak crypto, unsafe deserialization, XSS, and more
# 40 rules covering Python, JavaScript, and Java
```

### Dependency Scan

```bash
# Upload requirements.txt, package.json, or pom.xml
# Detects known CVEs with fix versions
# 70 curated CVE entries covering Django, Flask, requests, lodash, etc.
```

### Additional Sample APIs

- `samples/vulnerable_api.yaml` — Intentionally vulnerable e-commerce API (high risk)
- `samples/secure_api.yaml` — Secured version with proper controls (low risk)
- `samples/banking_api.yaml` — Enterprise banking API with MFA, RBAC
- `samples/ecommerce_api.yaml` — Full-featured e-commerce platform API

---

## API Endpoints

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login |
| GET | `/api/auth/me` | Yes | Current user profile |

### API Security Scanning
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/scans/upload` | Yes | Sync scan |
| POST | `/api/scans/upload/async` | Yes | Async scan (WebSocket) |
| GET | `/api/scans/` | Yes | List scans |
| GET | `/api/scans/dashboard` | Yes | Dashboard stats |
| GET | `/api/scans/{id}` | Yes | Scan detail |
| GET | `/api/scans/{id}/report/pdf` | Yes | PDF report |
| GET | `/api/scans/{id}/report/json` | Yes | JSON report |
| DELETE | `/api/scans/{id}` | Yes | Delete scan |

### Security Intelligence
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/security/sast/scan` | Yes | SAST file scan |
| POST | `/api/security/sast/scan/text` | Yes | SAST inline code scan |
| POST | `/api/security/deps/scan` | Yes | Dependency vulnerability scan |
| POST | `/api/security/copilot/chat` | Yes | Chat with Security Copilot |
| POST | `/api/security/copilot/context` | Yes | Load findings into copilot |
| POST | `/api/security/copilot/clear` | Yes | Clear copilot context |
| GET | `/api/security/copilot/commands` | No | List copilot capabilities |

### Organizations & Projects
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/organizations` | Yes | Create organization |
| GET | `/api/organizations` | Yes | List user's organizations |
| GET | `/api/organizations/{id}` | Yes | Get organization details |
| POST | `/api/organizations/{id}/members` | Yes | Add member (admin only) |
| DELETE | `/api/organizations/{id}/members/{user_id}` | Yes | Remove member |
| POST | `/api/organizations/{id}/projects` | Yes | Create project |
| GET | `/api/organizations/{id}/projects` | Yes | List org projects |

### Public Endpoints
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/testimonials` | No | Get active testimonials |
| GET | `/api/metrics` | No | Prometheus metrics |
| GET | `/health/detailed` | No | Detailed health check |

### WebSocket
| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws/scan/{task_id}` | Real-time scan progress |

---

## Testing

```bash
cd backend
python -m pytest tests/ -v
# 150+ tests covering:
# - OpenAPI parser (10 tests)
# - OWASP scanner (14 tests)
# - Risk engine (14 tests)
# - SAST engine (35 tests)
# - Dependency scanner (24 tests)
# - Security copilot (38 tests)
# - Organizations (10 tests)
# - Testimonials (14 tests)
# - Enterprise audit (26 tests)
# - Observability (20 tests)
# - Cache (12 tests)
# - Auth hardening (29 tests)
```

---

## CI/CD

GitHub Actions pipeline with:
1. **Backend Lint** — Black, Ruff, MyPy
2. **Backend Tests** — pytest with coverage report (JUnit XML)
3. **Frontend Build** — npm test + vite build
4. **Docker Build** — Multi-stage builds for backend + frontend (BuildKit cache)
5. **Secret Scanning** — Gitleaks on every PR
6. **CodeQL Analysis** — JavaScript + Python security analysis
7. **Deploy Verification** — Smoke test against live services
8. **Dependabot** — Auto-updates for pip, npm, GitHub Actions, Docker

### Running Locally

```bash
# Full stack with Docker (recommended)
cp .env.example .env && docker compose up --build

# Or manually:
# Terminal 1: Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
# Terminal 2: Frontend
cd frontend && npm install && npm run dev
# Terminal 3: (optional) AI
ollama serve
```

### Smoke Test

```bash
./scripts/smoke-test.sh                    # Test localhost:8000
./scripts/smoke-test.sh https://api.example.com  # Test remote
```

Checks: liveness, readiness, health, auth flow, metrics endpoint.

### Deployment Checklist

- [ ] Copy `.env.example` to `.env` and set `SECRET_KEY`
- [ ] Set `POSTGRES_PASSWORD` to a strong value
- [ ] Set `REFRESH_TOKEN_COOKIE_SECURE=true` (HTTPS required)
- [ ] Set `CORS_ORIGINS` to your frontend domain
- [ ] Configure `SENTRY_DSN` for error tracking
- [ ] Run `alembic upgrade head` to apply migrations
- [ ] Run `./scripts/smoke-test.sh` to verify

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture and design decisions |
| [Security Engine](docs/security-engine.md) | OWASP scanner details and CWE mapping |
| [API Flow](docs/api-flow.md) | Request/response flow documentation |
| [Demo Guide](docs/demo-guide.md) | Step-by-step interview demo workflow |

---

## Project Structure

```
sentinelai/
├── backend/
│   ├── app/
│   │   ├── api/routes/     ── auth, scans, security, audit, organizations
│   │   ├── api/v1/         ── Versioned API (health, scans, findings)
│   │   ├── core/
│   │   │   ├── security_engine/  ── OpenAPI parser + OWASP scanner
│   │   │   ├── risk_engine/      ── Weighted risk scoring
│   │   │   ├── ai_engine/        ── Ollama integration + fallback
│   │   │   ├── sast_engine/      ── Static analysis (Python/JS/Java)
│   │   │   ├── dep_scanner/      ── Dependency CVE detection
│   │   │   └── copilot/          ── AI Security Copilot
│   │   ├── models/         ── SQLAlchemy ORM (13 tables)
│   │   ├── repositories/   ── Repository pattern (Base + domain repos)
│   │   ├── schemas/        ── Pydantic v2 models
│   │   ├── services/       ── Audit, scan orchestration
│   │   ├── reports/        ── PDF + JSON generation
│   │   ├── utils/          ── Security, logging, cache, CSRF, metrics
│   │   └── main.py         ── FastAPI app with middleware stack
│   ├── alembic/            ── Database migrations
│   ├── tests/              ── 150+ pytest tests
│   ├── Dockerfile          ── Multi-stage production build
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/          ── Dashboard, SAST, Deps, Copilot, Audit, Health
│   │   ├── components/     ── Navbar, CommandPalette, ErrorBoundary, Charts
│   │   ├── services/       ── API client (auth, scans, audit, orgs)
│   │   └── context/        ── Auth state, Theme
│   ├── nginx.conf          ── Production nginx config
│   ├── Dockerfile          ── Multi-stage build (node + nginx)
│   └── package.json
├── deploy/
│   ├── prometheus/         ── Prometheus scrape config
│   └── grafana/            ── Grafana datasource provisioning
├── scripts/
│   └── smoke-test.sh       ── Deployment verification script
├── samples/                ── Vulnerable/secure/banking/ecommerce API specs
├── docs/                   ── Architecture, security engine, API flow
├── .github/
│   ├── workflows/ci.yml    ── CI/CD pipeline (lint, test, Docker, CodeQL)
│   └── dependabot.yml      ── Automated dependency updates
├── docker-compose.yml      ── Full stack (Postgres, Redis, Prometheus, Grafana)
├── .env.example            ── Environment variable template
├── render.yaml             ── Render deployment blueprint
├── railway.json            ── Railway deployment config
└── README.md
```

---

## Deployment

### Free Cloud Deployment (Render + Vercel)

**Backend (Render):**

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` blueprint — approve it
5. Set env vars: `CORS_ALLOW_ALL=true`, `SECRET_KEY` (auto-generated)
6. Deploy → your backend is live at `https://sentinelai-backend.onrender.com`

**Frontend (Vercel):**

1. Go to [vercel.com](https://vercel.com) → Import GitHub repo
2. Framework: Vite, Root Directory: `frontend`
3. Deploy → your frontend is live at `https://your-app.vercel.app`
4. Update `vercel.json` with your actual Render backend URL

**Post-Deploy:**
- Update `vercel.json` `destination` URLs with your actual Render URL
- Update Render's `CORS_ORIGINS` or keep `CORS_ALLOW_ALL=true`
- Health check: `GET https://your-backend.onrender.com/api/health`

> **Note:** Render free tier spins down after 15 min of inactivity. First request may take ~30s.

### Docker (Local Production)

```bash
docker-compose up --build
# Frontend: http://localhost:80
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built as a production-inspired security platform for demonstrating<br/>
  full-stack engineering, application security, and AI integration skills.
</p>
