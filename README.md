# SentinelAI

> **AI-Native Application Security Intelligence Platform**

<p align="center">
  <strong>Automated API security, static analysis, dependency scanning, and AI-powered security intelligence</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> · 
  <a href="#platform-capabilities">Capabilities</a> · 
  <a href="#architecture">Architecture</a> · 
  <a href="#api-endpoints">API</a>
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
- Cross-reference against curated CVE database (50+ known vulnerabilities)
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
          │   ├── CVE Database      ── 50+ curated vulnerability entries
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
| **Frontend** | React 18, Vite 6, React Router 6, Lucide Icons |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Pydantic v2 |
| **Auth** | JWT (python-jose), bcrypt (passlib) |
| **AI** | Ollama (Mistral), with rule-based fallback |
| **SAST** | Custom regex-based rules engine (Python/JS/Java) |
| **Dependency Scanning** | Custom parsers + curated CVE database |
| **Reports** | ReportLab (PDF), native JSON |
| **Real-time** | WebSocket (FastAPI native) |
| **Database** | SQLite (dev), PostgreSQL-ready |
| **CLI** | Click framework |
| **CI/CD** | GitHub Actions (test, build, security scan, Docker) |
| **Testing** | pytest (131 tests) |

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

### Docker (Production)

```bash
# Start everything with Docker Compose
docker-compose up --build

# Frontend: http://localhost:80
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

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
# 38 curated CVE entries covering Django, Flask, requests, lodash, etc.
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

### WebSocket
| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws/scan/{task_id}` | Real-time scan progress |

---

## Testing

```bash
cd backend
python -m pytest tests/ -v
# 131 tests covering:
# - OpenAPI parser (10 tests)
# - OWASP scanner (14 tests)
# - Risk engine (14 tests)
# - SAST engine (35 tests)
# - Dependency scanner (24 tests)
# - Security copilot (38 tests)
```

---

## CI/CD

GitHub Actions pipeline with:
1. **Backend Tests** — Python 3.11 + 3.12 matrix
2. **Frontend Build** — Node.js 18 with bundle size check
3. **Security Scan** — Self-analysis with SAST + dependency scanner
4. **Docker Build** — Multi-stage builds for backend + frontend

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
│   │   ├── api/routes/     ── auth, scans, security, websocket
│   │   ├── core/
│   │   │   ├── security_engine/  ── OpenAPI parser + OWASP scanner
│   │   │   ├── risk_engine/      ── Weighted risk scoring
│   │   │   ├── ai_engine/        ── Ollama integration + fallback
│   │   │   ├── sast_engine/      ── Static analysis (Python/JS/Java)
│   │   │   ├── dep_scanner/      ── Dependency CVE detection
│   │   │   └── copilot/          ── AI Security Copilot
│   │   ├── models/         ── SQLAlchemy ORM
│   │   ├── schemas/        ── Pydantic v2 models
│   │   ├── services/       ── Scan orchestration
│   │   ├── reports/        ── PDF + JSON generation
│   │   ├── utils/          ── Security, logging
│   │   ├── cli.py          ── Click CLI
│   │   ├── tasks.py        ── Background task management
│   │   └── main.py         ── FastAPI app
│   ├── tests/              ── 131 pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/          ── Dashboard, SAST, Deps, Copilot, Results, Live
│   │   ├── components/     ── Navbar
│   │   ├── services/       ── API client
│   │   └── context/        ── Auth state
│   └── package.json
├── samples/                ── Vulnerable/secure/banking/ecommerce API specs
├── docs/                   ── Architecture, security engine, API flow
├── .github/workflows/      ── CI/CD pipeline
├── docker-compose.yml
├── render.yaml             ── Render deployment blueprint
├── vercel.json             ── Vercel deployment config
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
