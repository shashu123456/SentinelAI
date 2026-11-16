# Changelog

All notable changes to SentinelAI are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- One upload box, three scanners. `POST /api/scans/upload` now takes a `kind`
  (`spec`, `deps` or `code`, default `spec`) and runs the matching engine:
  OpenAPI analysis, dependency scanning, or SAST. All three kinds persist into
  the same `scans` / `findings` tables, each finding tagged with its `source`,
  so the scan detail view and the JSON/PDF reports show which scanner produced
  what (`kind`, `counts_by_source`).
- Uploaded archives are validated before extraction: absolute paths, `..`
  components and symlink entries are rejected, along with archives over 10 000
  entries, over a 100:1 compression ratio, or holding an entry above 2 MB. At
  most 200 files of 2 MB are scanned and the response reports `partial: true`
  when those caps truncate the work.
- Dependency and SAST findings are normalised into the persistence shape
  (`app/services/finding_normalizer.py`): severity is mapped onto the database
  vocabulary, 0-1 confidences become 0-100 integers, missing
  description/impact/remediation are generated, and duplicates collapse by
  (source, package or file, rule, line).
- The web app's New Scan page is the single upload box for all three scanners:
  it detects the scanner from the file name, allows an explicit override, and
  the old `/sast` and `/deps` routes now preselect that kind on the same page.
- Dependency scans now query OSV.dev live (`app/core/dep_scanner/osv_client.py`)
  on top of the curated table. Discovery uses `POST /v1/querybatch` (100 packages
  per request) and full records come from `GET /v1/vulns/{id}` — measured on the
  live API, querybatch answers with ids only, so severity, CVE aliases and fixed
  versions have to be fetched separately. Where OSV publishes no CVSS vector and
  no `database_specific.severity` the finding is reported as `unknown` rather
  than guessed. Results merge instead of replacing: the curated table stays
  authoritative on conflict, a GHSA advisory that aliases a curated CVE counts as
  the same finding, OSV-only packages are added, and an OSV outage falls back to
  curated data with a warning. Responses carry `merge_counts` (`curated_only`,
  `osv_only`, `overlap`, `skipped_queries`) and `osv_warnings`.
- Dependency queries with a version OSV cannot match — Maven property
  placeholders such as `${spring.version}`, npm ranges such as `^4.17.0`,
  wildcards such as `1.x` — are skipped and counted instead of being sent as if
  they were installed versions.

### Fixed

- **Cache isolation for the dashboard and analytics aggregates.** `GET
  /api/scans/dashboard` and `/api/scans/analytics` cached their response under
  the numeric user id alone (`dashboard:{id}`). A numeric id is not a stable
  identity: after a database restore — or any re-seed that reuses ids — the next
  account to hold id 1 was served the previous holder's cached dashboard, scans
  and all. Cache keys now carry the username as well
  (`dashboard:{id}:{username}`), invalidation still deletes by the `dashboard:{id}`
  prefix so a fresh upload is visible on the next read, and
  `backend/tests/test_dashboard_cache.py` pins both properties: an entry left
  under the old id-only key is never served, and two accounts with one upload
  never share a response.

### Removed

- Removed the separate SAST and dependency upload pages (`SASTScan.jsx`,
  `DepScan.jsx`); both routes redirect into the unified upload box with the
  matching kind preselected.

- Removed the unwired `ExecutionRuntime` draft
  (`backend/app/core/execution/execution_runtime.py`): it called three engine
  APIs that no longer exist (`ExecutionEngine(timeout_seconds=)`,
  `execute(workflow, timeout)`, `event_bus.publish(str, dict)`) and had no call
  sites in the application. Its 6 tests were removed with it; the 9 tests in the
  same file that cover live components (`ExecutionState`, `RuntimeMetrics`,
  `RuntimeSnapshot`, `SessionStore`) were kept and moved to
  `backend/app/core/execution/tests/test_execution_state.py`.

## [1.0.0] — 2026-08-27

### Added

#### Core Platform
- API Security Scanner with 21 OWASP API Top 10 checks
- SAST (Static Application Security Testing) engine with 48 security rules
- Dependency vulnerability scanner with CVE database integration
- Risk engine with CVSS v3.1 scoring and severity classification
- WebSocket-based real-time scan progress streaming

#### AI Platform
- AI Security Copilot with 12 specialized capabilities
- Executive report generation with CISO-level summaries
- Risk explanation and threat prediction
- Root cause analysis and remediation generation
- Knowledge graph for vulnerability relationships and attack paths
- Semantic search with TF-IDF similarity matching
- Prompt registry with versioning, validation, and hallucination prevention
- Conversation memory with entity extraction and context windows

#### Enterprise Multi-Tenancy
- Organization management with RBAC (5 roles: owner, admin, security_engineer, developer, viewer)
- Project isolation with per-project scan ownership
- Team management with role-based access control
- User invitations with token-based acceptance
- API key management with scope-based permissions
- Organization analytics and member management

#### SaaS Platform
- Configuration-driven subscription plans (Free, Starter, Professional, Enterprise)
- Subscription lifecycle management (trial, active, canceled, expired)
- Usage tracking with append-only billing records
- Feature flags with 3-tier override system (global → plan → org)
- License management for enterprise and self-hosted deployments
- Customer onboarding wizard with role personalization
- Custom branding with white-label support and domain verification
- Email templates with {{variable}} rendering
- Feedback collection with triage workflow
- Product analytics event tracking

#### Automation
- Scheduled scans with CRON-like recurrence
- Scan templates with compliance framework tagging
- Custom policy engine with rule-based security gates
- Webhook integrations (Slack, Teams, Discord, Email, Custom)
- Export center (CSV, JSON, PDF, SARIF formats)
- Version comparison for scan diff analysis

#### Compliance
- 7 compliance frameworks: OWASP Top 10, OWASP API Security, NIST CSF 2.0, PCI DSS 4.0, ISO 27001:2022, SOC 2 Type II, CWE Top 25
- Automated compliance scoring per framework
- Executive report with KPI dashboard

#### Security
- JWT with refresh token rotation and family tracking
- CSRF double-submit cookie pattern with HMAC
- Rate limiting with progressive lockout
- Account lockout (5 failures → 15-minute lock)
- 13 security headers (CSP, HSTS, COOP, COEP, CORP, Permissions-Policy)
- Input sanitization (XSS, SQLi, path traversal detection)
- SSRF protection with internal IP blocking
- Threat detection engine (suspicious login, IP reputation, brute force)
- Session monitoring with replay detection
- Audit logging (append-only, risk-classified)
- Security events dashboard with real-time alerts

#### SRE & Observability
- Circuit breakers (ollama, database, redis, scanner)
- Retry with exponential backoff and jitter
- Graceful degradation with fallback strategies
- Bulkhead concurrency limits for AI engine, scanner, database
- Distributed tracing with OpenTelemetry-compatible spans
- SLA tracking (availability, latency, error rate, error budget)
- Alert manager with configurable thresholds and auto-resolution
- Uptime monitoring with consecutive failure detection
- Incident tracker with full lifecycle management
- Prometheus metrics (30+ custom metrics)
- Structured JSON logging with correlation IDs
- Health endpoints: /, /api/health, /api/health/detailed, /metrics

#### Plugin System
- Plugin SDK with 6 typed interfaces (Scanner, Report, AI, Notification, Export, Auth)
- Plugin manifest with versioning, permissions, and compatibility ranges
- Plugin registry with install/enable/disable/uninstall lifecycle
- Sandboxed execution with error isolation and health monitoring
- 16 granular permissions with least-privilege access
- Example plugin: Security Headers Scanner

#### Frontend
- React 18 with lazy loading and code splitting
- Dark/Light theme with CSS variables and localStorage persistence
- Command Palette (Linear-style ⌘K) with grouped results
- Keyboard shortcuts with global navigation
- Mobile bottom navigation with touch-friendly targets (48px)
- Executive Mobile Dashboard with swipeable KPI cards
- Offline indicator with reconnection animation
- PWA support: manifest.json, service worker, push notifications
- Responsive design (380px, 768px, 1024px breakpoints)
- Skeleton loading states with shimmer animation
- Error boundaries (app-level and page-level)
- Toast system with stacking, progress bars, and actions

#### DevOps
- Docker Compose with 10 services (backend, frontend, Postgres, Redis, Prometheus, Grafana, Loki, Alertmanager, Ollama, Worker)
- Multi-stage Docker builds (builder + production)
- Nginx with TLS termination and rate limiting
- Terraform AWS module (VPC, RDS, ElastiCache, ECS, S3, ALB)
- GitHub Actions CI/CD pipeline
- Backup and rollback scripts
- One-click deployment script

#### Documentation
- README.md with architecture diagram and capability matrix
- ARCHITECTURE.md with 6 Mermaid diagrams
- DATABASE.md with ER diagrams and schema reference
- API.md with full 183-endpoint reference
- DEVELOPER-GUIDE.md with setup and coding standards
- SECURITY.md with threat model and OWASP ASVS compliance
- CONTRIBUTING.md with PR process and code review
- DEPLOYMENT-GUIDE.md with multi-platform deployment
- OPS-HANDBOOK.md with 8 runbooks and scaling guide
- PLUGIN-ARCHITECTURE.md with SDK documentation
- SAAS-ARCHITECTURE.md with billing and subscription design
- RELEASE-NOTES-v1.0.md with complete release notes

#### Testing
- 183+ backend tests across 33 test files
- Frontend tests with Vitest
- Security hardening test suite (86 tests)
- Enterprise multi-tenancy test suite
- SaaS platform test suite (67 tests)
- SRE resilience test suite (47 tests)
- Plugin system test suite (31 tests)

### Security
- JWT token rotation prevents token theft via family tracking
- CSRF protection prevents cross-site request forgery
- SSRF protection blocks internal IP access
- XSS protection with HTML/JS/attribute escaping
- SQL injection detection in user inputs
- Rate limiting prevents brute-force attacks
- Account lockout after failed attempts
- Audit logging for all security-sensitive actions
- SECRET_KEY validation warns on default key usage

### Fixed
- WebSocket authentication vulnerability (JWT required)
- Password reset token leak (token never returned in API response)
- Unused imports cleanup (19 imports removed)
- Hardcoded SECRET_KEY detection at startup

---

## [0.9.0] — 2026-08-25

### Added
- Initial enterprise features
- Scheduled scans and scan templates
- Compliance center with 7 frameworks
- Webhook integrations
- Policy engine
- Export center (CSV, JSON, PDF, SARIF)

## [0.8.0] — 2026-08-24

### Added
- Premium UI/UX overhaul
- Command palette
- Keyboard shortcuts
- Skeleton loading states
- Toast system with actions

## [0.7.0] — 2026-08-23

### Added
- World-class documentation suite
- Architecture diagrams with Mermaid
- Full API reference
- Developer guide

## [0.6.0] — 2026-08-22

### Added
- Production deployment infrastructure
- Docker Compose with observability stack
- Terraform AWS module
- CI/CD pipeline

## [0.5.0] — 2026-08-21

### Added
- Dashboard and analytics
- Report generation (PDF, HTML)
- Executive reports
- Vulnerability explorer

## [0.4.0] — 2026-08-20

### Added
- Scanner engine with OWASP API Top 10
- SAST engine with 48 rules
- Dependency scanner
- Risk engine with CVSS scoring

## [0.3.0] — 2026-08-19

### Added
- Database layer with SQLAlchemy 2.0
- Repository pattern
- Alembic migrations
- Connection pooling

## [0.2.0] — 2026-08-18

### Added
- JWT authentication
- Refresh token rotation
- RBAC authorization
- Rate limiting

## [0.1.0] — 2026-08-17

### Added
- Initial project setup
- FastAPI backend
- React frontend
- Basic health check
