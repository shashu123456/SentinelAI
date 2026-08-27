# SentinelAI — Architecture Documentation

## System Overview

SentinelAI is an Enterprise AI-Powered Application Security Platform built with clean architecture principles: clear separation between API layer, business logic, data access, and infrastructure.

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ React UI │  │ REST API │  │WebSocket │  │ CLI      │            │
│  │ (Vite)   │  │ Client   │  │ Client   │  │ Client   │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
└───────┼──────────────┼──────────────┼──────────────┼─────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                              │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  Nginx (rate limiting, security headers, gzip, WebSocket)  │     │
│  └─────────────────────────┬───────────────────────────────────┘     │
│                            │                                         │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  FastAPI Application                                        │     │
│  │  ├── CORS Middleware                                        │     │
│  │  ├── Request ID Middleware                                  │     │
│  │  ├── Security Headers Middleware                            │     │
│  │  ├── Logging Middleware (structured JSON)                   │     │
│  │  ├── Rate Limiting (per-user + per-IP)                      │     │
│  │  ├── Envelope Middleware                                    │     │
│  │  └── Exception Handlers                                    │     │
│  └─────────────────────────┬───────────────────────────────────┘     │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                                │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │Auth Routes│  │Scan Routes│  │Security  │  │Audit     │           │
│  │          │  │          │  │Routes    │  │Routes    │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │              │              │                  │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Service Layer                                            │       │
│  │  ├── ScanService (orchestrate scans, risk, AI)           │       │
│  │  ├── AuditService (record + classify events)             │       │
│  │  └── RiskEngine (composite scoring + grading)            │       │
│  └──────────────────────────────┬───────────────────────────┘       │
│                                 │                                    │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Core Engines                                             │       │
│  │  ├── Security Engine (API Scanner)                        │       │
│  │  │   ├── OpenAPI Parser (3.x + Swagger 2.0)              │       │
│  │  │   └── OWASP Scanner (10 independent checks)           │       │
│  │  ├── SAST Engine (40+ rules, Python/JS/Java)             │       │
│  │  ├── Dependency Scanner (CVE database, 70+ entries)       │       │
│  │  ├── Risk Intelligence Engine (scoring + grading)         │       │
│  │  ├── AI Engine (Ollama + rule-based fallback)             │       │
│  │  └── Security Copilot (context-aware reasoning)           │       │
│  └──────────────────────────────┬───────────────────────────┘       │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Repository Layer (BaseRepository + Domain Repos)         │       │
│  │  ├── UserRepository, ScanRepository, FindingRepository    │       │
│  │  ├── AuditLogRepository, OrganizationRepository           │       │
│  │  ├── ProjectRepository, ReportRepository                  │       │
│  │  └── RefreshTokenRepository, PasswordResetTokenRepo       │       │
│  └──────────────────────────────┬───────────────────────────┘       │
│                                 │                                    │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  SQLAlchemy ORM (13 tables, Alembic migrations)           │       │
│  └──────────────────────────────┬───────────────────────────┘       │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER                              │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │PostgreSQL│  │  Redis   │  │Prometheus│  │ Grafana  │           │
│  │  (Data)  │  │ (Cache + │  │(Metrics) │  │(Dashboards)│         │
│  │          │  │ Blacklist)│  │          │  │          │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │
│  │  Sentry  │  │  Ollama  │  │  Docker  │                         │
│  │ (Errors) │  │  (AI)    │  │(Deploy)  │                         │
│  └──────────┘  └──────────┘  └──────────┘                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
sentinelai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/              # API endpoint handlers
│   │   │   │   ├── auth.py          # Authentication (register, login, refresh, logout)
│   │   │   │   ├── scans.py         # Scan CRUD, upload, dashboard, analytics
│   │   │   │   ├── security.py      # SAST, dependency scanning, AI copilot
│   │   │   │   ├── audit.py         # Enterprise audit center (RBAC-protected)
│   │   │   │   ├── organizations.py # Org + project management
│   │   │   │   ├── admin.py         # Admin user management (role, lock, unlock)
│   │   │   │   ├── metrics.py       # Prometheus metrics + health endpoints
│   │   │   │   ├── testimonials.py  # Public testimonials
│   │   │   │   └── websocket.py     # Real-time scan progress WebSocket
│   │   │   ├── v1/                  # Versioned API (envelope + pagination)
│   │   │   │   └── routers/
│   │   │   │       ├── health.py    # /api/v1/health, /ready, /live
│   │   │   │       ├── scans.py
│   │   │   │       ├── findings.py
│   │   │   │       └── dashboard.py
│   │   │   ├── envelope.py          # Response envelope middleware
│   │   │   ├── errors.py            # Centralized exception handlers
│   │   │   └── middleware.py        # Request middleware (envelope wrapping)
│   │   ├── core/                    # Domain-specific engines
│   │   │   ├── security_engine/     # API Security Scanner
│   │   │   │   ├── parser.py        # OpenAPI 3.x / Swagger 2.0 parser
│   │   │   │   └── scanner.py       # OWASP Top 10 checks (10 functions)
│   │   │   ├── risk_engine/         # Risk scoring + grading
│   │   │   ├── ai_engine/           # Ollama integration + fallback
│   │   │   ├── sast_engine/         # Static analysis (Python/JS/Java)
│   │   │   ├── dep_scanner/         # Dependency CVE detection
│   │   │   └── copilot/             # AI Security Copilot
│   │   │       ├── engine.py        # Copilot controller
│   │   │       ├── agent.py         # Intent classification + routing
│   │   │       ├── tools.py         # Database tools (findings, scans, etc.)
│   │   │       └── context_retrieval.py  # Security context builder
│   │   ├── database/
│   │   │   └── database.py          # Engine, session, migrations
│   │   ├── models/                  # SQLAlchemy ORM models (13 tables)
│   │   │   └── models.py
│   │   ├── repositories/            # Data access layer
│   │   │   ├── base.py              # Generic CRUD + pagination
│   │   │   ├── scans.py, findings.py, audit.py, ...
│   │   ├── schemas/                 # Pydantic v2 validation schemas
│   │   │   └── schemas.py
│   │   ├── services/                # Business logic
│   │   │   ├── scan_service.py      # Scan orchestration
│   │   │   ├── audit_service.py     # Audit event recording
│   │   │   └── risk_engine.py       # Risk assessment
│   │   ├── reports/                 # PDF + JSON generation
│   │   ├── utils/                   # Cross-cutting concerns
│   │   │   ├── security.py          # JWT, password hashing, RBAC
│   │   │   ├── logger.py            # Structured JSON logging
│   │   │   ├── cache.py             # Redis + in-memory cache
│   │   │   ├── csrf.py              # CSRF token generation/validation
│   │   │   ├── cookies.py           # Refresh token cookie management
│   │   │   ├── ratelimit.py         # Per-user + per-IP rate limiting
│   │   │   ├── token_blacklist.py   # Redis-backed JTI blacklist
│   │   │   ├── system_metrics.py    # CPU, memory, DB, Redis metrics
│   │   │   └── logger.py            # Structured JSON logger
│   │   ├── config.py                # Pydantic Settings (env-based)
│   │   ├── main.py                  # FastAPI app + middleware stack
│   │   └── tasks.py                 # Background scan task manager
│   ├── alembic/                     # Database migrations
│   ├── tests/                       # 150+ pytest tests
│   ├── Dockerfile                   # Multi-stage production build
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                   # 14 page components
│   │   │   ├── Landing.jsx          # Public landing page
│   │   │   ├── Login.jsx            # Authentication
│   │   │   ├── Dashboard.jsx        # Executive dashboard
│   │   │   ├── NewScan.jsx          # API scanner upload
│   │   │   ├── ScanResult.jsx       # Scan results + findings
│   │   │   ├── ScanLive.jsx         # Real-time WebSocket terminal
│   │   │   ├── SASTScan.jsx         # Static analysis
│   │   │   ├── DepScan.jsx          # Dependency scanning
│   │   │   ├── Copilot.jsx          # AI security copilot
│   │   │   ├── VulnerabilityExplorer.jsx
│   │   │   ├── AuditCenter.jsx      # Enterprise audit log
│   │   │   ├── ReportCenter.jsx     # Report generation
│   │   │   ├── Settings.jsx         # Org, project, profile, API keys
│   │   │   └── SystemHealth.jsx     # Infrastructure monitoring
│   │   ├── components/              # Reusable UI components
│   │   │   ├── Navbar.jsx           # Sidebar navigation
│   │   │   ├── CommandPalette.jsx   # ⌘K command palette
│   │   │   ├── KeyboardShortcuts.jsx
│   │   │   ├── Breadcrumbs.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── Toast.jsx
│   │   │   └── Charts.jsx           # Recharts visualizations
│   │   ├── context/                 # React Context providers
│   │   │   ├── AuthContext.jsx
│   │   │   └── ThemeContext.jsx
│   │   ├── services/
│   │   │   └── api.js               # REST API client
│   │   ├── config.js                # API URL configuration
│   │   └── App.jsx                  # Router + layout
│   ├── nginx.conf                   # Production nginx config
│   ├── Dockerfile                   # Multi-stage build
│   └── package.json
├── deploy/
│   ├── prometheus/prometheus.yml
│   └── grafana/provisioning/
├── scripts/
│   └── smoke-test.sh
├── docs/                            # This documentation
├── samples/                         # Sample OpenAPI specs
├── docker-compose.yml
├── .env.example
├── .github/
│   ├── workflows/ci.yml
│   └── dependabot.yml
├── render.yaml
└── railway.json
```

---

## Security Flow

### Authentication & Authorization

```
Client                    Backend                    Database
  │                          │                          │
  │  POST /auth/register     │                          │
  │  {username, email, pass} │                          │
  │─────────────────────────>│                          │
  │                          │  Check existing user     │
  │                          │─────────────────────────>│
  │                          │  Hash password (bcrypt)  │
  │                          │  Create user             │
  │                          │─────────────────────────>│
  │                          │  Create JWT (sub, jti)   │
  │                          │  Create refresh token    │
  │                          │─────────────────────────>│
  │                          │  Record audit event      │
  │<──── 201 + Token ───────│                          │
  │  Set-Cookie: refresh     │                          │
  │                          │                          │

Client                    Backend                    Redis
  │                          │                          │
  │  POST /auth/login        │                          │
  │  {username, password}    │                          │
  │─────────────────────────>│                          │
  │                          │  Lookup user             │
  │                          │  Verify password         │
  │                          │  Check lockout           │
  │                          │  Reset failed attempts   │
  │                          │  Create access JWT       │
  │                          │  Create refresh token    │
  │<──── 200 + Token ───────│                          │
  │                          │                          │

Client                    Backend                    Redis
  │                          │                          │
  │  POST /auth/refresh      │                          │
  │  Cookie: refresh_token   │                          │
  │  Header: x-csrf-token    │                          │
  │─────────────────────────>│                          │
  │                          │  Validate CSRF token     │
  │                          │  Rotate refresh token    │
  │                          │  Revoke old refresh      │
  │                          │  Create new access JWT   │
  │<──── 200 + New Token ───│                          │
  │                          │                          │

Client                    Backend                    Redis
  │                          │                          │
  │  POST /auth/logout       │                          │
  │  Header: Bearer <token>  │                          │
  │─────────────────────────>│                          │
  │                          │  Extract JTI from JWT    │
  │                          │  Add JTI to blacklist    │
  │                          │─────────────────────────>│
  │                          │  Revoke refresh token    │
  │<──── 204 No Content ────│                          │
```

### RBAC (Role-Based Access Control)

```
Request → get_current_user() → require_roles("admin")
                                    │
                              ┌─────┴─────┐
                              │ user.role  │
                              └─────┬─────┘
                                    │
                         ┌──────────┼──────────┐
                         │          │          │
                      "admin"    "user"    "viewer"
                         │          │          │
                    Full access  Read +    Read-only
                    (admin,      Write      (dashboard,
                    settings,    (scans,    reports)
                    audit)       copilot)
```

---

## Scanner Flow

### API Security Scan (Sync)

```
Upload File                    Parse OpenAPI Spec
    │                              │
    │  Validate file type/size     │
    │  Extract content             │
    │  YAML/JSON parse             │
    │  Resolve $ref pointers       │
    │  Extract endpoints, methods, │
    │  parameters, security schemes│
    │                              ▼
    │                         10 OWASP Checks
    │                         ┌──────────────┐
    │                         │ API1: BOLA    │
    │                         │ API2: Auth    │
    │                         │ API3: Props   │
    │                         │ API4: Rate    │
    │                         │ API5: Func    │
    │                         │ API6: Biz     │
    │                         │ API7: SSRF    │
    │                         │ API8: Config  │
    │                         │ API9: Inv     │
    │                         │ API10: Unsafe │
    │                         └──────┬───────┘
    │                                │
    │                         Risk Scoring
    │                         ┌──────────────┐
    │                         │ Weights:      │
    │                         │ Critical: 25  │
    │                         │ High: 15      │
    │                         │ Medium: 8     │
    │                         │ Low: 3        │
    │                         │ Info: 1       │
    │                         │ Floor rules   │
    │                         │ Normalize 0-100│
    │                         └──────┬───────┘
    │                                │
    │                         AI Analysis
    │                         ┌──────────────┐
    │                         │ Ollama →      │
    │                         │ Executive sum │
    │                         │ Tech analysis │
    │                         │ Business impact│
    │                         │ Attack scenario│
    │                         │ Mitigations   │
    │                         │ OR fallback   │
    │                         └──────┬───────┘
    │                                │
    │                         Save to DB
    │                         ┌──────────────┐
    │                         │ Scan record   │
    │                         │ Findings      │
    │                         │ AI Analysis   │
    │                         │ Audit log     │
    │                         └──────────────┘
    │                                │
    ◄──── Response with all data ────┘
```

### Async Live Scan

```
Client                         Backend                      WebSocket
  │                               │                            │
  │  POST /scans/upload/async     │                            │
  │──────────────────────────────>│                            │
  │                               │  Create ScanTask           │
  │                               │  Spawn asyncio task        │
  │<──── { task_id } ────────────│                            │
  │                               │                            │
  │  WS /ws/scan/{task_id} ──────────────────────────────────>│
  │                               │                            │
  │                               │  publish_progress()        │
  │<──── { progress: 15% } ──────────────────────────────────│
  │<──── { progress: 35% } ──────────────────────────────────│
  │<──── { progress: 74% } ──────────────────────────────────│
  │<──── { progress: 100% } ─────────────────────────────────│
  │                               │                            │
  │  GET /scans/{scan_id}         │                            │
  │──────────────────────────────>│                            │
  │<──── Full scan data ─────────│                            │
```

---

## AI Flow

### Copilot Processing

```
User Message
    │
    ▼
Intent Classification
    │
    ├── "hello" → Greeting
    ├── "security status" → Scan Status
    ├── "highest risk" → Highest Risk
    ├── "explain" → Explain Vuln
    ├── "why critical" → Why Critical
    ├── "how to fix" → Remediation
    ├── "executive summary" → Executive Summary
    ├── "attack" → Attack Path
    ├── "compliance" → Compliance
    └── "general" → General Help
         │
         ▼
Security Context Retrieval
    │
    ├── get_latest_scan()
    ├── get_critical_findings()
    ├── get_all_findings()
    ├── get_risk_summary()
    ├── get_scan_history()
    └── get_findings_by_category()
         │
         ▼
Response Generation
    │
    ├── Rule-based templates
    │   (when Ollama unavailable)
    │
    └── Ollama LLM
        (Mistral model)
        Context + findings →
        Grounded response
         │
         ▼
Conversation History Update
```

---

## Database ER Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      users       │     │ organizations   │     │    projects      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id          PK  │◄─┐  │ id          PK  │◄─┐  │ id          PK  │◄─┐
│ username    UQ  │  │  │ name            │  │  │ organization_id │──┤
│ email       UQ  │  │  │ slug        UQ  │  │  │ name            │  │
│ hashed_password │  │  │ description     │  │  │ slug            │  │
│ role            │  │  │ owner_id    FK──┼──┘  │ description     │  │
│ is_active       │  │  │ created_at      │     │ owner_id    FK──┼──┘
│ failed_attempts │  │  │ updated_at      │     │ is_active       │
│ locked_until    │  │  └────────┬────────┘     │ created_at      │
│ created_at      │  │           │               │ updated_at      │
└────────┬────────┘  │  ┌────────┴────────┐     └────────┬────────┘
         │           │  │ organization_   │              │
         │           │  │    members      │              │
         │           │  ├─────────────────┤              │
         │           │  │ id          PK  │              │
         │           │  │ organization_id │              │
         │           │  │ user_id     FK──┼──┐           │
         │           │  │ role            │  │           │
         │           │  │ joined_at       │  │           │
         │           │  └─────────────────┘  │           │
         │           │                       │           │
         │  ┌────────┴────────────────────┐  │           │
         │  │          scans              │  │           │
         │  ├─────────────────────────────┤  │           │
         │  │ id                     PK   │◄─┘           │
         ├──┤ user_id                FK   │              │
         │  │ project_id             FK   │◄─────────────┘
         │  │ api_name                    │
         │  │ api_title                   │
         │  │ api_version                 │
         │  │ total_endpoints             │
         │  │ total_vulnerabilities       │
         │  │ risk_score                  │
         │  │ risk_level                  │
         │  │ status                      │
         │  │ source_spec            JSON │
         │  │ created_at                  │
         │  │ completed_at                │
         │  │ deleted_at                  │
         │  └─────────────┬───────────────┘
         │                │
         │  ┌─────────────┴───────────────┐
         │  │        findings             │
         │  ├─────────────────────────────┤
         │  │ id                     PK   │
         │  │ scan_id                FK   │
         │  │ vulnerability_name          │
         │  │ owasp_category              │
         │  │ cwe_id                      │
         │  │ severity                    │
         │  │ confidence                  │
         │  │ description                 │
         │  │ evidence                    │
         │  │ impact                      │
         │  │ remediation                 │
         │  │ technical_impact            │
         │  │ business_impact             │
         │  │ request_example             │
         │  │ response_example            │
         │  │ fix_recommendation          │
         │  │ references             JSON │
         │  │ cvss_score                  │
         │  │ cvss_vector                 │
         │  │ affected_endpoint           │
         │  │ affected_method             │
         │  │ detection_reason            │
         │  │ false_positive_note         │
         │  └─────────────────────────────┘
         │
         │  ┌─────────────────────────────┐
         │  │       ai_analysis           │
         │  ├─────────────────────────────┤
         │  │ id                     PK   │
         │  │ scan_id          FK + UQ    │
         │  │ executive_summary           │
         │  │ technical_explanation       │
         │  │ business_impact             │
         │  │ attack_scenario             │
         │  │ recommended_mitigation      │
         │  │ created_at                  │
         │  └─────────────────────────────┘
         │
         │  ┌─────────────────────────────┐
         │  │        audit_logs           │
         │  ├─────────────────────────────┤
         │  │ id                     PK   │
         ├──┤ user_id                FK   │
         │  │ username                    │
         │  │ action                      │
         │  │ module                      │
         │  │ entity_type                 │
         │  │ entity_id                   │
         │  │ resource                    │
         │  │ old_value              JSON │
         │  │ new_value              JSON │
         │  │ detail                 JSON │
         │  │ ip_address                  │
         │  │ user_agent                  │
         │  │ request_id                  │
         │  │ status                      │
         │  │ risk_level                  │
         │  │ created_at                  │
         │  └─────────────────────────────┘
         │
         │  ┌─────────────────────────────┐
         │  │     refresh_tokens          │
         │  ├─────────────────────────────┤
         │  │ id                     PK   │
         ├──┤ user_id                FK   │
         │  │ token_hash           UQ     │
         │  │ expires_at                  │
         │  │ created_at                  │
         │  │ revoked_at                  │
         │  │ replaced_by                 │
         │  │ ip_address                  │
         │  └─────────────────────────────┘
         │
         │  ┌─────────────────────────────┐
         │  │   password_reset_tokens     │
         │  ├─────────────────────────────┤
         │  │ id                     PK   │
         ├──┤ user_id                FK   │
         │  │ token_hash           UQ     │
         │  │ expires_at                  │
         │  │ created_at                  │
         │  │ used_at                     │
         │  └─────────────────────────────┘
         │
         │  ┌─────────────────────────────┐
         │  │         reports             │
         │  ├─────────────────────────────┤
         │  │ id                     PK   │
         │  │ scan_id                FK   │
         │  │ format                     UQ│
         │  │ content             LargeBin │
         │  │ created_at                  │
         │  └─────────────────────────────┘
         │
         │  ┌─────────────────────────────┐
         │  │       testimonials          │
         │  ├─────────────────────────────┤
         │  │ id                     PK   │
         │  │ quote                       │
         │  │ author_name                 │
         │  │ author_role                 │
         │  │ author_company              │
         │  │ avatar_letter               │
         │  │ is_active                   │
         │  │ display_order               │
         │  │ created_at                  │
         │  └─────────────────────────────┘
```
