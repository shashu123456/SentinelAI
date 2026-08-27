# Changelog

All notable changes to SentinelAI are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [1.1.0] — 2026-08-27

### 🏢 Phase 10 — Enterprise Multi-Tenancy & RBAC

Transformed SentinelAI from a single-user application into a true enterprise SaaS platform.

#### ✨ New Features

**Organization Management**
- Enterprise organization CRUD with RBAC
- Organization settings (SSO enforcement, email domain restrictions)
- Organization dashboard with aggregate metrics across all projects
- Organization analytics with time-series scan activity, risk trends, OWASP distribution

**Role-Based Access Control (RBAC)**
- 6-tier permission hierarchy: super_admin > owner > admin > security_engineer > developer > viewer
- Organization-level RBAC with `require_org_role()` dependency factory
- Project-level RBAC with automatic org-level fallback
- Team-level RBAC with admin and member roles
- Every endpoint enforces permissions; no data leakage across organizations

**Teams**
- Create and manage teams within organizations
- Add/remove team members with role management
- Team CRUD with RBAC enforcement

**User Invitations**
- Send email-based invitations to join organizations
- Token-based acceptance with 7-day expiry
- Revoke pending invitations
- Automatic cleanup of expired invitations

**API Key Management**
- Create programmatic API keys with configurable scopes
- Secure key display (shown only once at creation)
- SHA-256 key hashing with prefix-based lookup
- Key validation, revocation, and expiry

**Billing-Ready Architecture**
- Subscription tier system (free, starter, professional, enterprise)
- Configurable member limits, project limits, and scan quotas
- Monthly scan usage tracking

**Scan Isolation**
- Scans can be associated with organizations and projects
- Organization-scoped scan listing endpoints
- Project-scoped scan listing endpoints
- Cross-org scan access is blocked by RBAC

**Frontend**
- Organization switcher dropdown in sidebar
- Project switcher dropdown in sidebar
- 5 new enterprise pages: OrgDashboard, TeamManagement, Invitations, ApiKeys, OrgSettings
- New "Enterprise" navigation section in sidebar
- OrgContext for global organization/project state management
- localStorage persistence for org/project selection

**New API Endpoints (22+)**
- `/api/organizations/{org_id}/teams/*` — Team CRUD + member management
- `/api/organizations/{org_id}/invitations/*` — Invitation lifecycle
- `/api/organizations/{org_id}/api-keys/*` — API key management
- `/api/organizations/{org_id}/settings` — Organization settings
- `/api/organizations/{org_id}/dashboard` — Org aggregate dashboard
- `/api/organizations/{org_id}/analytics` — Org analytics
- `/api/scans/org/{org_id}` — Org-scanned listing
- `/api/scans/project/{project_id}` — Project-scanned listing

#### 🗄️ Database Changes

**New Tables:**
- `project_members` — Project-level RBAC membership
- `teams` — Organization team grouping
- `team_members` — Team membership
- `invitations` — Email-based user invitations
- `api_keys` — Programmatic API access

**Enhanced Tables:**
- `organizations` — +8 columns: subscription_tier, max_members, max_projects, max_scans_per_month, scans_used_this_month, default_project_visibility, enforce_sso, allowed_email_domains
- `organization_members` — +1 column: invited_by
- `scans` — +1 column: organization_id

**New Indexes:**
- `ix_org_member_org_role` — Org member role lookups
- `ix_project_member_project_role` — Project member role lookups
- `ix_teams_org_id` — Team org lookups
- `ix_team_member_team_role` — Team member role lookups
- `ix_invitations_org_id`, `ix_invitations_email`, `ix_invitations_token`
- `ix_api_keys_org_id`, `ix_api_keys_user_id`
- `ix_scans_org_id`, `ix_scans_org_status`

#### 🧪 Tests

- **42 new enterprise multi-tenancy tests** covering:
  - Organization CRUD with RBAC
  - Member management with role checks
  - Project management with isolation
  - Team CRUD with RBAC
  - Invitation lifecycle
  - API key lifecycle
  - Organization settings
  - Organization dashboard & analytics
  - Scan isolation by organization
  - Cross-org data isolation

---

## [1.0.0] — 2026-08-20

### 🎯 SentinelAI v1.0 — Production Release

Enterprise AI-Powered Application Security Platform.

### ✨ Features

#### Security Scanning
- **API Security Scanner** — OWASP API Security Top 10 analysis (10 independent checks)
- **SAST Engine** — Static analysis for Python, JavaScript, Java (40+ rules)
- **Dependency Scanner** — CVE detection for requirements.txt, package.json, pom.xml (70+ CVEs)
- **Risk Intelligence Engine** — Severity-weighted scoring with floor rules, security grading
- **Risk Score** — 0-100 normalized score with Critical/High/Medium/Low/Risk levels

#### AI Security Copilot
- **Context-Aware Reasoning** — Loads real scan data for grounded responses
- **Intent Classification** — Understands 12+ security intents (explain, remediate, executive, attack, compliance)
- **Ollama Integration** — Local AI with Mistral model, rule-based fallback
- **Security Context** — Database-backed tool system for findings, scans, history

#### Enterprise Features
- **Organizations & Projects** — Multi-tenant organization management with RBAC
- **Role-Based Access Control** — Admin/User/Viewer roles with endpoint protection
- **Enterprise Audit Logging** — 15-field audit records with risk classification, timeline, CSV export
- **Organization Management** — Create orgs, invite members, manage projects

#### Authentication & Security
- **JWT Authentication** — Access + refresh token rotation with JTI blacklisting
- **CSRF Protection** — Paired CSRF tokens for refresh endpoint
- **Per-User Rate Limiting** — Authenticated per-user + anonymous per-IP
- **Account Lockout** — Failed attempt tracking with auto-lockout
- **Password Policy** — Configurable complexity requirements
- **Password Reset** — Token-based reset with email support
- **Security Headers** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options

#### Observability
- **JSON Structured Logging** — Correlation IDs, user context, scan context
- **Prometheus Metrics** — 30+ metrics (HTTP, auth, scanner, AI, system)
- **Kubernetes Health Endpoints** — /ready, /live, /health
- **System Metrics** — CPU, memory, DB latency, Redis status, uptime
- **Optional Sentry** — Error tracking integration via env var

#### Dashboard & Analytics
- **Executive Dashboard** — Risk gauge, severity distribution, scan history
- **Real-Time Charts** — Recharts visualizations (severity donut, scan activity, risk trend, OWASP distribution)
- **Onboarding Flow** — Step-by-step getting started checklist
- **System Health Page** — Real-time infrastructure monitoring (CPU, memory, DB, Redis, AI, workers)

#### Frontend
- **Responsive Design** — Mobile hamburger menu, adaptive layouts
- **Dark/Light Mode** — Full theme system with localStorage persistence
- **Command Palette** — ⌘K fuzzy search across all pages
- **Keyboard Shortcuts** — G+D/N/S/V/C/R/A/H for navigation
- **Error Boundaries** — Page-level error recovery
- **Skeleton Loading** — Loading states for all pages
- **Breadcrumbs** — Auto-generated from URL path

#### DevOps
- **Multi-Stage Docker** — Backend (Python 3.11-slim) + Frontend (Node 20 + nginx 1.25)
- **Docker Compose** — 8 services: Backend, Frontend, Postgres, Redis, Worker, Prometheus, Grafana, Ollama
- **GitHub Actions CI** — 7 jobs: lint, test, coverage, Docker build, Gitleaks, CodeQL, smoke test
- **Dependabot** — Auto-updates for pip, npm, GitHub Actions, Docker
- **Render/Railway** — One-click deployment blueprints
- **Smoke Test Script** — 10-point deployment verification

#### Reporting
- **PDF Reports** — Professional reports with risk gauge, findings, AI analysis
- **JSON Reports** — Machine-readable exports
- **CSV Export** — Audit log and findings export

### 🏗️ Architecture
- **Clean Architecture** — API → Service → Repository → Database
- **Repository Pattern** — Generic CRUD + domain-specific repos (8 repositories)
- **Pydantic v2** — Strict validation with custom validators
- **SQLAlchemy 2.0** — Declarative ORM with Alembic migrations (13 tables)
- **Event-Driven** — WebSocket progress publishing for async scans

### 🧪 Testing
- **150+ Backend Tests** — pytest covering all modules
- **Coverage** — Scanner, auth, audit, cache, repositories, organizations
- **Integration Tests** — Full auth flow, scan flow, API tests

### 📊 Metrics
| Metric | Value |
|--------|-------|
| Backend Files | 81 |
| Frontend Files | 40+ |
| React Components | 24 (15 pages, 10 components) |
| API Endpoints | 30+ |
| Database Tables | 13 |
| Security Rules | 40+ (SAST) |
| OWASP Checks | 10 |
| CVE Database | 70+ |
| Prometheus Metrics | 30+ |
| Backend Tests | 150+ |
| Documentation Pages | 14 (8,300+ lines) |

### 🔒 Security
- JTI-based token blacklisting (Redis + in-memory fallback)
- CSRF protection on state-changing cookie operations
- Per-user rate limiting with authenticated identity
- Structured audit logging with risk classification
- Input validation on all endpoints (Pydantic v2)
- Security headers (CSP, HSTS, X-Frame-Options)
- Non-root Docker containers with tini PID 1
- Secret scanning in CI (Gitleaks)
- CodeQL analysis for JavaScript and Python

### 📦 Dependencies
- **Backend:** FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, ReportLab, prometheus-client
- **Frontend:** React 18, Vite 6, React Router 6, Recharts, Lucide Icons
- **Infrastructure:** PostgreSQL 16, Redis 7, Prometheus, Grafana, Ollama

---

## [Unreleased]

### Planned for v1.1
- CVSS scoring for all findings
- Semantic version comparison for dependencies
- Additional SAST rules
- Interactive risk trend charts
- Scan comparison mode
- SSO integration (SAML/OIDC)

### Planned for v2.0
- Container security scanning
- Infrastructure as Code scanning
- Runtime API monitoring
- Attack graph visualization
- Plugin marketplace
- Multi-region deployment
