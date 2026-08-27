# SentinelAI — Architecture

> Enterprise AI-Powered Application Security Platform

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Principles](#architecture-principles)
- [System Architecture](#system-architecture)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Database Architecture](#database-architecture)
- [Security Architecture](#security-architecture)
- [AI Architecture](#ai-architecture)
- [Scanner Architecture](#scanner-architecture)
- [Data Flow](#data-flow)
- [Deployment Architecture](#deployment-architecture)
- [Scalability](#scalability)

---

## System Overview

SentinelAI is a production-inspired AI-powered Application Security Platform that helps organizations discover, analyze, prioritize, and remediate application security risks throughout the SDLC.

### High-Level System Diagram

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["Web Browser"]
        CLI["CLI / API Client"]
    end

    subgraph Gateway["Gateway Layer"]
        Nginx["Nginx Reverse Proxy<br/>TLS Termination<br/>Rate Limiting<br/>Static Assets"]
    end

    subgraph Application["Application Layer"]
        Backend["FastAPI Backend<br/>93 Endpoints<br/>RBAC + Audit"]
        Worker["Background Worker<br/>Async Scans<br/>AI Analysis"]
        Frontend["React SPA<br/>19 Pages<br/>Dark/Light Theme"]
    end

    subgraph Intelligence["Intelligence Layer"]
        OWASP["OWASP Scanner<br/>21 Checks"]
        SAST["SAST Engine<br/>48 Rules"]
        DepScan["Dependency Scanner<br/>70+ CVEs"]
        RiskEngine["Risk Intelligence<br/>CVSS + Grading"]
        AICopilot["AI Copilot<br/>Ollama + Rules"]
    end

    subgraph Data["Data Layer"]
        Postgres["PostgreSQL 16<br/>17 Tables"]
        Redis["Redis 7<br/>Cache + Sessions"]
    end

    subgraph Observability["Observability Layer"]
        Prometheus["Prometheus<br/>Metrics"]
        Grafana["Grafana<br/>Dashboards"]
        Loki["Loki<br/>Logs"]
        Alertmanager["Alertmanager<br/>Alerts"]
    end

    Browser --> Nginx
    CLI --> Backend
    Nginx --> Frontend
    Nginx --> Backend
    Backend --> Postgres
    Backend --> Redis
    Backend --> OWASP
    Backend --> SAST
    Backend --> DepScan
    Backend --> RiskEngine
    Backend --> AICopilot
    Worker --> Postgres
    Worker --> OWASP
    Backend --> Prometheus
    Prometheus --> Grafana
    Prometheus --> Alertmanager
```

---

## Architecture Principles

| Principle | Description |
|-----------|-------------|
| **Layered Architecture** | Clear separation: Gateway → Application → Intelligence → Data |
| **Domain-Driven Design** | Each module owns its domain (auth, scanning, AI, audit) |
| **Repository Pattern** | All data access through repositories, never direct ORM in routes |
| **Dependency Injection** | FastAPI `Depends()` for all service/repository wiring |
| **API-First** | OpenAPI spec drives both backend and frontend contracts |
| **Security by Design** | RBAC, audit logging, input validation at every layer |
| **Defense in Depth** | Multiple overlapping security controls |
| **Observable** | Structured logging, metrics, tracing at every boundary |
| **Testable** | Every layer independently testable with dependency overrides |
| **Stateless** | No server-side session state; JWT + refresh tokens |

---

## System Architecture

### Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant N as Nginx
    participant A as FastAPI
    participant R as Redis
    participant D as PostgreSQL
    participant S as Scanner Engine

    C->>N: HTTP Request
    N->>N: Rate Limit Check
    N->>N: Security Headers
    N->>A: Proxy Pass

    A->>A: JWT Validation
    A->>A: RBAC Check
    A->>A: Input Validation
    A->>R: Check Cache

    alt Cache Hit
        R-->>A: Cached Response
        A-->>N: JSON Response
    else Cache Miss
        A->>D: Query Database
        D-->>A: Results
        A->>R: Store in Cache
        A-->>N: JSON Response
    end

    N-->>C: HTTP Response
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth API
    participant D as Database
    participant T as Token Blacklist
    participant Audit as Audit Log

    Note over C,A: Login Flow
    C->>A: POST /api/auth/login
    A->>A: Check IP Reputation
    A->>A: Rate Limit Check
    A->>D: Lookup User
    A->>A: Verify Password (bcrypt)
    A->>A: Assess Threat Level
    A->>D: Create Refresh Token
    A->>A: Generate JWT Access Token
    A->>A: Set CSRF Cookie
    A->>Audit: Record Login Event
    A-->>C: Token + User + Set-Cookie

    Note over C,A: Token Refresh Flow
    C->>A: POST /api/auth/refresh
    A->>A: Validate CSRF Header
    A->>A: Extract Refresh Token from Cookie
    A->>D: Lookup Token Hash
    A->>A: Check if Token Reused (theft detection)
    A->>D: Revoke Old Token
    A->>D: Create New Refresh Token
    A->>A: Generate New JWT
    A-->>C: New Token + Set-Cookie

    Note over C,A: Logout Flow
    C->>A: POST /api/auth/logout
    A->>A: Extract JWT JTI
    A->>T: Add JTI to Blacklist
    A->>D: Revoke Refresh Token
    A->>Audit: Record Logout Event
    A-->>C: 204 No Content
```

---

## Backend Architecture

### Layered Design

```
┌─────────────────────────────────────────────┐
│                 API Routes                   │
│  auth | scans | organizations | teams | ...  │
├─────────────────────────────────────────────┤
│              Middleware Layer                 │
│  CORS | Security Headers | Envelope | Audit  │
├─────────────────────────────────────────────┤
│              Service Layer                   │
│  scan_service | team_service | threat_det... │
├─────────────────────────────────────────────┤
│            Repository Layer                  │
│  scans | findings | orgs | audit | users     │
├─────────────────────────────────────────────┤
│              Model Layer                     │
│  SQLAlchemy ORM + Alembic Migrations         │
├─────────────────────────────────────────────┤
│            Database Layer                    │
│  PostgreSQL (prod) | SQLite (dev/test)       │
└─────────────────────────────────────────────┘
```

### Module Structure

```
backend/app/
├── api/
│   ├── routes/          # 12 route modules (93 endpoints)
│   │   ├── auth.py      # Authentication & session management
│   │   ├── scans.py     # Scan CRUD, upload, reports
│   │   ├── organizations.py  # Enterprise org management
│   │   ├── teams.py     # Team management
│   │   ├── invitations.py    # User invitations
│   │   ├── api_keys.py  # API key management
│   │   ├── audit.py     # Enterprise audit center
│   │   ├── security_events.py  # Threat detection dashboard
│   │   ├── metrics.py   # Prometheus metrics
│   │   ├── websocket.py # Real-time scan streaming
│   │   ├── admin.py     # Admin operations
│   │   └── security.py  # SAST, deps, AI copilot
│   ├── v1/              # Versioned API (envelope middleware)
│   ├── middleware.py     # Response envelope wrapping
│   ├── envelope.py      # Standard response format
│   └── errors.py        # Exception handlers
├── core/                # Domain engines
│   ├── security_engine/ # OWASP scanner (21 checks)
│   ├── sast_engine/     # Static analysis (48 rules)
│   ├── dep_scanner/     # Dependency CVE detection
│   ├── risk_engine/     # CVSS scoring + grading
│   ├── ai_engine/       # Vulnerability analysis
│   └── copilot/         # AI security assistant
├── models/              # SQLAlchemy models (17 tables)
├── schemas/             # Pydantic request/response
├── repositories/        # Data access layer (10 repos)
├── services/            # Business logic (6 services)
├── utils/               # Cross-cutting concerns
│   ├── security.py      # JWT, passwords, tokens
│   ├── rbac.py          # Enterprise RBAC
│   ├── sanitization.py  # XSS, SQLi protection
│   ├── ssrf_protection.py  # URL safety validation
│   ├── threat_detection.py  # Login analysis, IP rep
│   ├── cache.py         # Redis + memory cache
│   ├── performance.py   # Request metrics, memory
│   ├── logger.py        # Structured JSON logging
│   └── ratelimit.py     # Slowapi rate limiting
├── reports/             # PDF/JSON report generation
├── tasks.py             # Background scan execution
├── config.py            # Pydantic settings
├── main.py              # FastAPI application
└── database.py          # Engine, sessions, migrations
```

### Dependency Injection

```python
# Example: Organization-scoped endpoint with RBAC
@router.get("/{org_id}/dashboard")
def get_org_dashboard(
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    return get_organization_dashboard(db, org_ctx.organization.id)

# RBAC dependency chain:
# 1. get_current_user() → validates JWT, returns User
# 2. require_org_role("viewer") → checks org membership + role level
# 3. Returns OrgContext with org, role, level, user_id
```

---

## Frontend Architecture

### Component Hierarchy

```
App
├── ErrorBoundary
├── ThemeProvider (dark/light)
├── AuthProvider (JWT + refresh)
├── OrgProvider (org/project context)
├── ToastProvider
├── BrowserRouter
│   ├── KeyboardShortcutsProvider
│   ├── CommandPalette (⌘K)
│   ├── PublicRoute → Login, Landing
│   └── ProtectedRoute → AppLayout
│       ├── Navbar (sidebar + org switcher)
│       ├── Breadcrumbs
│       └── Lazy Pages (19 routes)
│           ├── Dashboard, OrgDashboard
│           ├── NewScan, ScanResult, ScanLive
│           ├── SASTScan, DepScan
│           ├── Copilot (AI)
│           ├── VulnerabilityExplorer
│           ├── TeamManagement, Invitations
│           ├── ApiKeys, OrgSettings
│           ├── AuditCenter, SecurityEvents
│           ├── ReportCenter, Settings
│           └── SystemHealth
```

### State Management

| Context | Scope | Persistence |
|---------|-------|-------------|
| `AuthContext` | User session, JWT | localStorage |
| `OrgContext` | Current org/project | localStorage |
| `ThemeContext` | Dark/light mode | localStorage |
| `ToastContext` | Notifications | In-memory |

### Data Flow

```mermaid
graph LR
    A[Component] --> B[useEffect]
    B --> C[API Service]
    C --> D[request.js]
    D --> E[JWT Header]
    D --> F[Refresh on 401]
    D --> G[CSRF Cookie]
    D --> H[Envelope Unwrap]
    H --> A
```

---

## Database Architecture

### Entity Relationship Diagram

```mermaid
erDiagram
    users {
        int id PK
        string username UK
        string email UK
        string hashed_password
        string role
        boolean is_active
        int failed_login_attempts
        datetime locked_until
        datetime created_at
    }

    organizations {
        int id PK
        string name
        string slug UK
        text description
        int owner_id FK
        string subscription_tier
        int max_members
        int max_projects
        int max_scans_per_month
        boolean enforce_sso
        datetime created_at
    }

    organization_members {
        int id PK
        int organization_id FK
        int user_id FK
        string role
        int invited_by FK
        datetime joined_at
    }

    projects {
        int id PK
        int organization_id FK
        string name
        string slug
        text description
        int owner_id FK
        boolean is_active
        datetime created_at
    }

    project_members {
        int id PK
        int project_id FK
        int user_id FK
        string role
        int added_by FK
        datetime added_at
    }

    teams {
        int id PK
        int organization_id FK
        string name
        string slug
        text description
        datetime created_at
    }

    team_members {
        int id PK
        int team_id FK
        int user_id FK
        string role
        int added_by FK
        datetime added_at
    }

    scans {
        int id PK
        int user_id FK
        int organization_id FK
        int project_id FK
        string api_name
        string api_title
        int total_endpoints
        int total_vulnerabilities
        int risk_score
        string risk_level
        string status
        datetime created_at
        datetime completed_at
    }

    findings {
        int id PK
        int scan_id FK
        string vulnerability_name
        string owasp_category
        string cwe_id
        string severity
        int confidence
        text description
        float cvss_score
        string affected_endpoint
    }

    ai_analysis {
        int id PK
        int scan_id FK
        text executive_summary
        text technical_explanation
        text business_impact
        datetime created_at
    }

    invitations {
        int id PK
        int organization_id FK
        string email
        string role
        string token UK
        int invited_by FK
        string status
        datetime expires_at
    }

    api_keys {
        int id PK
        int organization_id FK
        int user_id FK
        string name
        string key_prefix UK
        string key_hash UK
        json scopes
        boolean is_active
        datetime created_at
    }

    audit_logs {
        int id PK
        int user_id FK
        string action
        string module
        string entity_type
        string risk_level
        string ip_address
        datetime created_at
    }

    refresh_tokens {
        int id PK
        int user_id FK
        string token_hash UK
        datetime expires_at
        string ip_address
        datetime revoked_at
    }

    reports {
        int id PK
        int scan_id FK
        string format
        binary content
        datetime created_at
    }

    testimonials {
        int id PK
        text quote
        string author_name
        string author_role
        boolean is_active
        int display_order
    }

    users ||--o{ organization_members : "belongs to"
    users ||--o{ organizations : "owns"
    users ||--o{ projects : "owns"
    users ||--o{ scans : "creates"
    users ||--o{ audit_logs : "generates"
    users ||--o{ refresh_tokens : "has"
    users ||--o{ api_keys : "creates"
    users ||--o{ invitations : "sends"

    organizations ||--o{ organization_members : "has"
    organizations ||--o{ projects : "contains"
    organizations ||--o{ teams : "has"
    organizations ||--o{ invitations : "sends"
    organizations ||--o{ api_keys : "issues"
    organizations ||--o{ scans : "scopes"

    projects ||--o{ project_members : "has"
    projects ||--o{ scans : "contains"

    teams ||--o{ team_members : "has"

    scans ||--o{ findings : "produces"
    scans ||--o| ai_analysis : "analyzes"
    scans ||--o{ reports : "generates"
```

### Database Statistics

| Metric | Value |
|--------|-------|
| Tables | 17 |
| Columns | 121+ |
| Indexes | 26+ |
| Foreign Keys | 20+ |
| Unique Constraints | 8+ |

---

## Security Architecture

### Defense-in-Depth Layers

```mermaid
graph TB
    subgraph L1["Layer 1: Network"]
        WAF["WAF / CDN"]
        TLS["TLS Termination"]
        RateLimit["Rate Limiting"]
    end

    subgraph L2["Layer 2: Application"]
        CORS["CORS Policy"]
        CSP["Content Security Policy"]
        Headers["Security Headers"]
        CSRF["CSRF Protection"]
    end

    subgraph L3["Layer 3: Authentication"]
        JWT["JWT + Refresh Rotation"]
        Password["bcrypt Hashing"]
        Lockout["Account Lockout"]
        Session["Session Monitoring"]
    end

    subgraph L4["Layer 4: Authorization"]
        RBAC["6-Tier RBAC"]
        OrgScope["Organization Scoping"]
        ProjectScope["Project Scoping"]
        Audit["Audit Logging"]
    end

    subgraph L5["Layer 5: Input"]
        Sanitize["XSS Sanitization"]
        SQLi["SQL Injection Detection"]
        SSRF["SSRF Protection"]
        FileUpload["File Upload Validation"]
    end

    subgraph L6["Layer 6: Threat"]
        IPRep["IP Reputation"]
        BruteForce["Brute Force Detection"]
        Suspicious["Suspicious Login Detection"]
        GeoAnomaly["Geo Anomaly Detection"]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6
```

### RBAC Permission Matrix

| Action | Viewer | Developer | Security Eng | Admin | Owner |
|--------|--------|-----------|-------------|-------|-------|
| View org | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create project | ❌ | ✅ | ✅ | ✅ | ✅ |
| Run scans | ✅ | ✅ | ✅ | ✅ | ✅ |
| View audit logs | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invite members | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage teams | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create API keys | ❌ | ❌ | ❌ | ✅ | ✅ |
| Update org settings | ❌ | ❌ | ❌ | ❌ | ✅ |
| Change member roles | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## AI Architecture

### AI Copilot Flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as Copilot API
    participant Intent as Intent Classifier
    participant CTX as Context Retriever
    participant LLM as Ollama/Mistral
    participant Rules as Rule Engine

    U->>API: Chat message
    API->>Intent: Classify intent
    Intent-->>API: intent + entities

    alt Has scan context
        API->>CTX: Load scan findings
        CTX-->>API: findings + risk data
    end

    API->>Rules: Check rule-based response
    alt Rule match
        Rules-->>API: structured response
    else No rule match
        API->>LLM: Prompt + context
        LLM-->>API: AI response
    end

    API->>API: Safety validation
    API-->>U: Response + sources
```

### Intent Categories

| Intent | Description | Example |
|--------|-------------|---------|
| `explain_vulnerability` | Explain a specific finding | "What is BOLA?" |
| `remediate` | Generate fix code | "How do I fix API1?" |
| `executive_summary` | Business-level summary | "Summarize for CISO" |
| `attack_scenario` | Explain attack vectors | "How would someone exploit this?" |
| `compliance` | Map to standards | "Show PCI DSS impact" |
| `threat_model` | Architecture review | "Review my API design" |
| `general` | General security questions | "What is OWASP Top 10?" |

---

## Scanner Architecture

### OWASP Scanner Pipeline

```mermaid
graph LR
    A[OpenAPI Spec] --> B[Parser]
    B --> C[Endpoint Extractor]
    C --> D[Security Scheme Analyzer]
    D --> E[21 OWASP Checks]
    E --> F[Finding Builder]
    F --> G[Risk Engine]
    G --> H[CVSS Scorer]
    H --> I[AI Analyzer]
    I --> J[Report Generator]
```

### Check Registry

| ID | OWASP Category | Check Name |
|----|---------------|------------|
| SA-01 | API1 | Broken Object Level Authorization (BOLA) |
| SA-02 | API2 | Unauthenticated Endpoint |
| SA-03 | API2 | Weak Authentication Scheme |
| SA-04 | API3 | Exposed Sensitive Properties |
| SA-05 | API3 | Sensitive Query Parameters |
| SA-06 | API3 | Sensitive Response Fields |
| SA-07 | API4 | No Pagination / Rate Limiting |
| SA-08 | API4 | Auth Endpoint Missing Rate Limit |
| SA-09 | API4 | Unbounded Request Body |
| SA-10 | API5 | Admin Endpoint Without Auth |
| SA-11 | API5 | Exposed Debug Endpoint |
| SA-12 | API6 | Unprotected Business Flow |
| SA-13 | API7 | SSRF via URL Parameter |
| SA-14 | API7 | Open Redirect |
| SA-15 | API8 | No Security Schemes |
| SA-16 | API8 | No Global Security |
| SA-17 | API8 | Insecure Transport |
| SA-18 | API9 | Multiple API Versions |
| SA-19 | API9 | Deprecated Endpoints |
| SA-20 | API10 | Unsafe API Consumption |
| SA-21 | API2 | API Key in Query String |

---

## Deployment Architecture

### Docker Compose Topology

```mermaid
graph TB
    subgraph External["External"]
        User["User"]
        Internet["Internet"]
    end

    subgraph Docker["Docker Network: 172.28.0.0/16"]
        subgraph Frontend["Frontend"]
            Nginx["nginx:1.25<br/>Port 80"]
        end

        subgraph Backend["Backend"]
            API["FastAPI<br/>Port 8000"]
        end

        subgraph Data["Data"]
            PG["PostgreSQL 16<br/>Port 5432"]
            Redis["Redis 7<br/>Port 6379"]
        end

        subgraph Obs["Observability"]
            Prom["Prometheus<br/>Port 9090"]
            GF["Grafana<br/>Port 3001"]
            Loki2["Loki<br/>Port 3100"]
            AM["Alertmanager<br/>Port 9093"]
        end

        subgraph AI["AI"]
            Ollama2["Ollama<br/>Port 11434"]
        end
    end

    User --> Internet
    Internet --> Nginx
    Nginx --> API
    API --> PG
    API --> Redis
    API --> Ollama2
    API --> Prom
    Prom --> GF
    Prom --> AM
```

---

## Scalability

### Scaling Path

| Users | Architecture | Resources |
|-------|-------------|-----------|
| 1-100 | Single server Docker | 2 vCPU, 4GB RAM |
| 100-1K | Multi-container | 4 vCPU, 8GB RAM |
| 1K-10K | ECS/EKS | Auto-scaling, RDS, ElastiCache |
| 10K-100K | Multi-region | Load balancer, read replicas, CDN |
| 100K+ | Microservices | Kubernetes, service mesh |

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Response (p50) | <100ms | ~45ms |
| API Response (p95) | <500ms | ~180ms |
| Scan Completion | <30s | ~15s |
| Dashboard Load | <2s | ~1.2s |
| Concurrent Scans | 50+ | Tested |
| Database Queries | <50ms avg | ~12ms |
