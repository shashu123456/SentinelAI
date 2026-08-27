# SentinelAI — Database Architecture

> Complete database reference: schemas, relationships, indexes, and migration guide.

---

## Table of Contents

- [Overview](#overview)
- [Technology](#technology)
- [Schema Reference](#schema-reference)
- [Entity Relationships](#entity-relationships)
- [Indexes](#indexes)
- [Constraints](#constraints)
- [Migrations](#migrations)
- [Performance](#performance)
- [Backup & Recovery](#backup--recovery)
- [Scaling Strategy](#scaling-strategy)

---

## Overview

SentinelAI uses **PostgreSQL 16** in production and **SQLite** for development and testing. The database stores all platform data across 17 tables with 121+ columns and 26+ indexes.

### Statistics

| Metric | Value |
|--------|-------|
| Tables | 17 |
| Columns | 121+ |
| Indexes | 26+ |
| Foreign Keys | 20+ |
| Unique Constraints | 8+ |
| ORM | SQLAlchemy 2.0 (async-ready) |
| Migrations | Alembic |

---

## Technology

### Production (PostgreSQL 16)

```python
# Connection configuration
DATABASE_URL = "postgresql://user:password@localhost:5432/sentinelai"

# Connection pooling (production)
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Persistent connections
    max_overflow=10,       # Burst connections
    pool_timeout=30,       # Connection wait timeout
    pool_recycle=1800,     # Recycle after 30 minutes
    pool_pre_ping=True,    # Validate connections
)
```

### Development/Testing (SQLite)

```python
DATABASE_URL = "sqlite:///sentinelai.db"  # Dev
DATABASE_URL = "sqlite://"                # In-memory for tests
```

### Connection Pooling

| Parameter | Production | Development | Testing |
|-----------|-----------|-------------|---------|
| pool_size | 20 | 5 | 5 |
| max_overflow | 10 | 5 | 5 |
| pool_timeout | 30s | 30s | 10s |
| pool_recycle | 1800s | 3600s | 600s |
| pool_pre_ping | True | True | False |

---

## Schema Reference

### users

Core authentication and identity table.

```sql
CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    username        VARCHAR(80)  NOT NULL UNIQUE,
    email           VARCHAR(120) NOT NULL UNIQUE,
    hashed_password VARCHAR(256) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'user',
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Security fields
    failed_login_attempts  INTEGER  NOT NULL DEFAULT 0,
    locked_until           DATETIME NULL,
    last_login_at          DATETIME NULL,
    last_login_ip          VARCHAR(45) NULL,

    -- Multi-tenancy
    current_organization_id INTEGER NULL,

    -- Password reset
    password_reset_token_hash VARCHAR(256) NULL,
    password_reset_expires    DATETIME NULL
);
```

**Indexes:** `ix_users_id`, `ix_users_username`, `ix_users_email`

---

### organizations

Enterprise organization container.

```sql
CREATE TABLE organizations (
    id                      INTEGER PRIMARY KEY,
    name                    VARCHAR(200) NOT NULL,
    slug                    VARCHAR(200) NOT NULL UNIQUE,
    description             TEXT,
    owner_id                INTEGER NOT NULL REFERENCES users(id),
    default_project_visibility VARCHAR(20) NOT NULL DEFAULT 'private',
    is_active               BOOLEAN NOT NULL DEFAULT 1,
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Enterprise settings
    enforce_sso             BOOLEAN NOT NULL DEFAULT 0,
    allowed_email_domains   TEXT,

    -- Billing
    subscription_tier       VARCHAR(20) NOT NULL DEFAULT 'free',
    max_members             INTEGER NOT NULL DEFAULT 5,
    max_projects            INTEGER NOT NULL DEFAULT 3,
    max_scans_per_month     INTEGER NOT NULL DEFAULT 50,
    max_api_keys            INTEGER NOT NULL DEFAULT 5,

    -- Security
    require_mfa             BOOLEAN NOT NULL DEFAULT 0,
    ip_whitelist            TEXT,
    session_timeout_minutes INTEGER NOT NULL DEFAULT 480,
    scan_isolation_enabled  BOOLEAN NOT NULL DEFAULT 1
);
```

**Indexes:** `ix_organizations_id`, `ix_organizations_slug`

---

### organization_members

Many-to-many: users ↔ organizations with role.

```sql
CREATE TABLE organization_members (
    id              INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    role            VARCHAR(30) NOT NULL DEFAULT 'developer',
    joined_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    invited_by      INTEGER REFERENCES users(id),

    UNIQUE(organization_id, user_id)
);
```

**Role hierarchy:**
1. `owner` (level 40) — Full control
2. `admin` (level 30) — Manage members, teams, settings
3. `security_engineer` (level 20) — Run scans, manage findings
4. `developer` (level 10) — Create projects, run scans
5. `viewer` (level 5) — Read-only access

---

### projects

Scoped within organizations.

```sql
CREATE TABLE projects (
    id              INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(200) NOT NULL,
    description     TEXT,
    owner_id        INTEGER NOT NULL REFERENCES users(id),
    is_active       BOOLEAN NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(organization_id, slug)
);
```

---

### project_members

Many-to-many: users ↔ projects with role.

```sql
CREATE TABLE project_members (
    id         INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    user_id    INTEGER NOT NULL REFERENCES users(id),
    role       VARCHAR(20) NOT NULL DEFAULT 'developer',
    added_by   INTEGER REFERENCES users(id),
    added_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(project_id, user_id)
);
```

---

### teams

Grouping mechanism within organizations.

```sql
CREATE TABLE teams (
    id              INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(200) NOT NULL,
    description     TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(organization_id, slug)
);
```

---

### team_members

Many-to-many: users ↔ teams.

```sql
CREATE TABLE team_members (
    id         INTEGER PRIMARY KEY,
    team_id    INTEGER NOT NULL REFERENCES teams(id),
    user_id    INTEGER NOT NULL REFERENCES users(id),
    role       VARCHAR(20) NOT NULL DEFAULT 'member',
    added_by   INTEGER REFERENCES users(id),
    added_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(team_id, user_id)
);
```

**Team member roles:** `admin` (level 10), `member` (level 5)

---

### scans

Central scanning data, scoped to organization and project.

```sql
CREATE TABLE scans (
    id                   INTEGER PRIMARY KEY,
    user_id              INTEGER NOT NULL REFERENCES users(id),
    organization_id      INTEGER REFERENCES organizations(id),
    project_id           INTEGER REFERENCES projects(id),
    api_name             VARCHAR(200),
    api_title            VARCHAR(500),
    api_description      TEXT,
    api_version          VARCHAR(50),
    total_endpoints      INTEGER DEFAULT 0,
    total_vulnerabilities INTEGER DEFAULT 0,
    risk_score           INTEGER DEFAULT 0,
    risk_level           VARCHAR(20) DEFAULT 'low',
    status               VARCHAR(20) NOT NULL DEFAULT 'processing',
    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at         DATETIME,
    source_spec          TEXT,
    deleted_at           DATETIME
);
```

**Status values:** `processing`, `completed`, `failed`, `cancelled`

**Risk levels:** `critical`, `high`, `medium`, `low`, `info`

**Indexes:** `ix_scans_id`, `ix_scans_organization_id`, `ix_scans_project_id`

---

### findings

Individual security findings within scans.

```sql
CREATE TABLE findings (
    id                   INTEGER PRIMARY KEY,
    scan_id              INTEGER NOT NULL REFERENCES scans(id),
    vulnerability_name   VARCHAR(200) NOT NULL,
    owasp_category       VARCHAR(100),
    cwe_id               VARCHAR(20),
    severity             VARCHAR(20) NOT NULL,
    confidence           INTEGER DEFAULT 80,
    description          TEXT,
    affected_endpoint    VARCHAR(500),
    affected_method      VARCHAR(10),
    affected_parameters  TEXT,
    remediation          TEXT,
    evidence             TEXT,
    cvss_score           FLOAT DEFAULT 0.0,
    cvss_vector          VARCHAR(200),
    is_false_positive    BOOLEAN DEFAULT 0,
    is_resolved          BOOLEAN DEFAULT 0,
    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Additional fields
    reference_url        TEXT,
    compliance_mapping   TEXT,
    risk_level           VARCHAR(20),
    function_name        VARCHAR(200),
    file_path            VARCHAR(500),
    line_number          INTEGER,
    code_snippet         TEXT,
    secure_example       TEXT,
    ai_explanation       TEXT,
    tags                 TEXT
);
```

**Indexes:** `ix_findings_id`, `ix_findings_scan_id`

---

### ai_analysis

AI-generated analysis for scans.

```sql
CREATE TABLE ai_analysis (
    id                     INTEGER PRIMARY KEY,
    scan_id                INTEGER NOT NULL REFERENCES scans(id),
    executive_summary      TEXT,
    technical_explanation   TEXT,
    business_impact        TEXT,
    recommendations        TEXT,
    compliance_notes       TEXT,
    confidence_score       FLOAT DEFAULT 0.8,
    model_used             VARCHAR(100),
    created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(scan_id)
);
```

---

### refresh_tokens

HTTP-only cookie refresh tokens with rotation tracking.

```sql
CREATE TABLE refresh_tokens (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    token_hash      VARCHAR(256) NOT NULL UNIQUE,
    family_id       VARCHAR(100) NOT NULL,
    expires_at      DATETIME NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    revoked_at      DATETIME
);
```

---

### invitations

Email-based organization invitations.

```sql
CREATE TABLE invitations (
    id              INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    email           VARCHAR(120) NOT NULL,
    role            VARCHAR(30) NOT NULL DEFAULT 'developer',
    token           VARCHAR(256) NOT NULL UNIQUE,
    invited_by      INTEGER NOT NULL REFERENCES users(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME NOT NULL,
    accepted_at     DATETIME
);
```

---

### api_keys

Organization-scoped API keys with scoped access.

```sql
CREATE TABLE api_keys (
    id              INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    name            VARCHAR(200) NOT NULL,
    key_prefix      VARCHAR(10) NOT NULL,
    key_hash        VARCHAR(256) NOT NULL UNIQUE,
    scopes          TEXT,  -- JSON array
    is_active       BOOLEAN NOT NULL DEFAULT 1,
    last_used_at    DATETIME,
    last_used_ip    VARCHAR(45),
    expires_at      DATETIME,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at      DATETIME
);
```

---

### audit_logs

Append-only audit trail for all security-sensitive actions.

```sql
CREATE TABLE audit_logs (
    id              INTEGER PRIMARY KEY,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id         INTEGER REFERENCES users(id),
    username        VARCHAR(80),
    organization_id INTEGER REFERENCES organizations(id),
    action          VARCHAR(100) NOT NULL,
    module          VARCHAR(50),
    entity_type     VARCHAR(50),
    entity_id       INTEGER,
    old_value       TEXT,
    new_value       TEXT,
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    request_id      VARCHAR(100),
    status          VARCHAR(20) NOT NULL DEFAULT 'success',
    risk_level      VARCHAR(10) NOT NULL DEFAULT 'low',
    metadata        TEXT  -- JSON
);
```

**Indexes:** `ix_audit_logs_id`, `ix_audit_logs_user_id`

**Risk levels:** `low`, `medium`, `high`, `critical`

---

### reports

Generated security reports (PDF, JSON, CSV, HTML).

```sql
CREATE TABLE reports (
    id         INTEGER PRIMARY KEY,
    scan_id    INTEGER NOT NULL REFERENCES scans(id),
    format     VARCHAR(20) NOT NULL,
    content    BLOB,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

### testimonials

Public testimonials for the landing page.

```sql
CREATE TABLE testimonials (
    id            INTEGER PRIMARY KEY,
    quote         TEXT NOT NULL,
    author_name   VARCHAR(100) NOT NULL,
    author_role   VARCHAR(100),
    is_active     BOOLEAN NOT NULL DEFAULT 1,
    display_order INTEGER DEFAULT 0,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## Indexes

### Performance Indexes

```sql
-- Primary key indexes (automatic)
-- Unique constraint indexes (automatic)
-- Additional performance indexes:

CREATE INDEX ix_scans_organization_id ON scans(organization_id);
CREATE INDEX ix_scans_project_id ON scans(project_id);
CREATE INDEX ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX ix_findings_scan_id ON findings(scan_id);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX ix_invitations_organization_id ON invitations(organization_id);
CREATE INDEX ix_api_keys_organization_id ON api_keys(organization_id);
```

### Composite Index Recommendations

For production at scale, consider:

```sql
-- Scan listing by org + status (most common query)
CREATE INDEX idx_scans_org_status ON scans(organization_id, status);

-- Findings by scan + severity (dashboard query)
CREATE INDEX idx_findings_scan_severity ON findings(scan_id, severity);

-- Audit logs by timestamp + org (audit center)
CREATE INDEX idx_audit_org_time ON audit_logs(organization_id, timestamp);

-- API keys by prefix + active (authentication)
CREATE INDEX idx_apikeys_prefix_active ON api_keys(key_prefix, is_active);
```

---

## Constraints

### Unique Constraints

| Table | Columns | Constraint |
|-------|---------|------------|
| users | username | UNIQUE |
| users | email | UNIQUE |
| organizations | slug | UNIQUE |
| organization_members | (organization_id, user_id) | UNIQUE |
| projects | (organization_id, slug) | UNIQUE |
| project_members | (project_id, user_id) | UNIQUE |
| teams | (organization_id, slug) | UNIQUE |
| team_members | (team_id, user_id) | UNIQUE |
| refresh_tokens | token_hash | UNIQUE |
| invitations | token | UNIQUE |
| api_keys | key_hash | UNIQUE |

### Foreign Key Relationships

All foreign keys use `ON DELETE CASCADE` or `ON DELETE SET NULL` as appropriate:

- **Cascade:** Findings → Scans, Audit Logs → Users
- **Set NULL:** Scans → Organizations, Projects (allows orphaned data retention)

---

## Migrations

### Alembic Setup

```bash
# Initialize Alembic (already configured)
cd backend
alembic init alembic

# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current

# Show migration history
alembic history
```

### Migration Files

| Version | Description | Tables Affected |
|---------|-------------|-----------------|
| Initial | Base schema | users, organizations, scans, findings, ai_analysis |
| Enterprise | Multi-tenancy | teams, team_members, invitations, api_keys |
| Enhanced | Org/project | Enhanced organizations, projects, project_members |

### Creating Migrations

```bash
# 1. Modify models in backend/app/models/models.py
# 2. Generate migration
cd backend
alembic revision --autogenerate -m "add new feature"
# 3. Review the generated file
# 4. Apply
alembic upgrade head
# 5. Run tests
pytest
```

### Migration Best Practices

1. **Never modify applied migrations** — create new ones instead
2. **Always test rollback** before merging
3. **Separate data migrations** from schema migrations
4. **Use batch operations** for large tables
5. **Add indexes in background** for production (PostgreSQL `CREATE INDEX CONCURRENTLY`)

---

## Performance

### Query Optimization

| Pattern | Anti-Pattern | Recommended |
|---------|-------------|-------------|
| N+1 queries | Lazy loading relationships | Eager loading with `joinedload()` |
| Full table scan | `SELECT *` without filter | Indexed queries with `LIMIT` |
| Unbounded results | No pagination | Cursor or offset pagination |
| Lock contention | `SELECT FOR UPDATE` everywhere | Optimistic locking with version |

### Connection Pool Tuning

```python
# Production configuration
DATABASE_CONFIG = {
    "pool_size": 20,          # 20 persistent connections
    "max_overflow": 10,       # Up to 30 total connections
    "pool_timeout": 30,       # Wait up to 30s for connection
    "pool_recycle": 1800,     # Recycle connections after 30min
    "pool_pre_ping": True,    # Validate before use
}
```

### Monitoring Queries

```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Check index usage
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Table bloat analysis
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

## Backup & Recovery

### Automated Backups

```bash
# Full backup
pg_dump -h localhost -U sentinelai sentinelai > backup_$(date +%Y%m%d).sql

# Restore
psql -h localhost -U sentinelai sentinelai < backup_20240101.sql
```

### Docker Compose Backup Service

```yaml
# Included in docker-compose.yml
backup:
  build: ./backend
  command: python -c "import time; while True: time.sleep(3600)"
  volumes:
    - backup-data:/backups
  environment:
    - BACKUP_INTERVAL=3600
    - BACKUP_RETENTION_DAYS=30
```

### Recovery Time Objectives

| Metric | Target |
|--------|--------|
| RTO (Recovery Time Objective) | 15 minutes |
| RPO (Recovery Point Objective) | 1 hour |
| Backup Retention | 30 days |
| Backup Verification | Weekly |

---

## Scaling Strategy

### Vertical Scaling (First 1K users)

- Increase PostgreSQL resources (CPU, RAM, IOPS)
- Tune connection pool and shared_buffers
- Add read replicas for analytics queries

### Horizontal Scaling (1K-100K users)

- **Read Replicas:** Separate read-heavy queries (dashboards, analytics)
- **Connection Pooler:** PgBouncer for connection multiplexing
- **Partitioning:** Partition `audit_logs` and `findings` by date
- **Archival:** Move old scans to cold storage

### Partition Strategy

```sql
-- Partition audit_logs by month
CREATE TABLE audit_logs (
    -- ... columns
) PARTITION BY RANGE (timestamp);

CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE audit_logs_2024_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

### Data Lifecycle

| Table | Hot Data | Warm Data | Cold Archive |
|-------|----------|-----------|--------------|
| scans | 90 days | 1 year | 5 years |
| findings | 90 days | 1 year | 5 years |
| audit_logs | 30 days | 1 year | 7 years |
| refresh_tokens | Active only | — | — |
| invitations | 7 days | — | — |
