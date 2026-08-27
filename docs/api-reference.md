# SentinelAI — API Reference

Base URL: `http://localhost:8000/api`

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

All responses follow the envelope pattern (v1 endpoints):
```json
{ "success": true, "data": {...}, "meta": null }
```

---

## Authentication

### POST /api/auth/register

Register a new user account.

**Request:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecureP@ss1"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    "is_active": true
  }
}
```

**Errors:**
- `400` — Username/email already registered
- `422` — Validation error (weak password, invalid email)

---

### POST /api/auth/login

Authenticate and receive access + refresh tokens.

**Request:**
```json
{
  "username": "john_doe",
  "password": "SecureP@ss1"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": { "id": 1, "username": "john_doe", ... }
}
```

**Set-Cookie:** `sentinelai_refresh=<token>; HttpOnly; Path=/api/auth`

**Errors:**
- `401` — Invalid credentials
- `403` — Account disabled
- `423` — Account locked (too many failed attempts)

---

### POST /api/auth/refresh

Rotate refresh token and get new access token.

**Headers:** `x-csrf-token: <csrf_value>`
**Cookie:** `sentinelai_csrf=<token.signature>`

**Response (200):**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": { ... }
}
```

---

### POST /api/auth/logout

Revoke current tokens. Adds JTI to blacklist.

**Response:** `204 No Content`

---

### POST /api/auth/logout-all

Revoke all refresh tokens for the current user.

**Response:** `204 No Content`

---

### POST /api/auth/forgot-password

Request a password reset token.

**Request:**
```json
{ "email": "john@example.com" }
```

**Response (200):**
```json
{
  "message": "If that email exists, a password reset token has been issued",
  "reset_token": null
}
```

---

### POST /api/auth/reset-password

Reset password using the token from email.

**Request:**
```json
{
  "token": "<reset_token>",
  "new_password": "NewSecureP@ss1"
}
```

**Response (200):**
```json
{ "detail": "Password reset successful" }
```

---

### GET /api/auth/me

Get current user profile.

**Response (200):**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true
}
```

---

## Scanning

### POST /api/scans/upload

Synchronous API security scan.

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | File | Yes | OpenAPI/Swagger spec (.json, .yaml, .yml) |
| api_name | string | No | API name (auto-detected if omitted) |

**Response (200):**
```json
{
  "id": 1,
  "api_name": "Pet Store API",
  "total_endpoints": 15,
  "total_vulnerabilities": 8,
  "risk_score": 72,
  "risk_level": "High",
  "status": "completed",
  "findings": [...],
  "ai_analysis": { ... }
}
```

---

### POST /api/scans/upload/async

Asynchronous scan with WebSocket progress.

**Response (200):**
```json
{ "task_id": "abc-123", "message": "Scan started" }
```

**WebSocket:** `ws://localhost:8000/ws/scan/abc-123`

Progress messages:
```json
{ "task_id": "abc-123", "status": "running", "progress": 35, "message": "[API2] Broken Authentication..." }
{ "task_id": "abc-123", "status": "completed", "progress": 100, "scan_id": 1 }
```

---

### GET /api/scans/

List user's scans (paginated, filtered).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| page | int | Page number (default: 1) |
| page_size | int | Items per page (default: 20, max: 100) |
| status | string | Filter by status (pending/running/completed/failed) |
| risk_level | string | Filter by risk level |
| search | string | Search by API name |
| date_from | datetime | Start date filter |
| date_to | datetime | End date filter |
| sort | string | Sort field (created_at, risk_score, etc.) |

**Response (200):**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

---

### GET /api/scans/dashboard

Dashboard statistics.

**Response (200):**
```json
{
  "total_scans": 42,
  "total_vulnerabilities": 156,
  "average_risk_score": 58.3,
  "recent_scans": [...],
  "severity_distribution": {
    "Critical": 5,
    "High": 23,
    "Medium": 45,
    "Low": 30,
    "Info": 53
  }
}
```

---

### GET /api/scans/analytics

Time-series analytics for charts.

**Response (200):**
```json
{
  "scan_activity": [
    { "date": "2026-08-01", "scans": 3 },
    { "date": "2026-08-02", "scans": 5 }
  ],
  "risk_trend": [
    { "date": "2026-08-01", "score": 72 },
    { "date": "2026-08-02", "score": 45 }
  ],
  "owasp_distribution": [
    { "category": "API2", "count": 8 },
    { "category": "API8", "count": 12 }
  ]
}
```

---

### GET /api/scans/{id}

Get scan detail with findings and AI analysis.

---

### DELETE /api/scans/{id}

Soft-delete a scan.

**Response:** `204 No Content`

---

### GET /api/scans/{id}/report/pdf

Download PDF report.

**Response:** `application/pdf` (binary)

---

### GET /api/scans/{id}/report/json

Download JSON report.

**Response:** `application/json`

---

## Security Intelligence

### POST /api/security/sast/scan

Static analysis of source code.

**Request:** `multipart/form-data`
| Field | Type | Allowed |
|-------|------|---------|
| file | File | .py, .js, .jsx, .ts, .tsx, .java, .zip |

**Response (200):**
```json
{
  "target_path": "app.py",
  "summary": {
    "total_findings": 12,
    "severity_counts": { "High": 3, "Medium": 5, "Low": 4 },
    "files_scanned": 1,
    "lines_scanned": 250,
    "languages_detected": ["python"]
  },
  "findings": [
    {
      "rule_id": "PY-SQL-INJECT",
      "rule_name": "SQL Injection",
      "severity": "High",
      "cwe_id": "CWE-89",
      "language": "python",
      "file_path": "app.py",
      "line_number": 42,
      "line_content": "cursor.execute(f\"SELECT * FROM users WHERE id={user_id}\")",
      "description": "User input directly interpolated into SQL query",
      "remediation": "Use parameterized queries instead of string formatting",
      "confidence": 0.92
    }
  ]
}
```

---

### POST /api/security/deps/scan

Dependency vulnerability scan.

**Request:** `multipart/form-data`
| Field | Type | Allowed |
|-------|------|---------|
| file | File | requirements.txt, package.json, pom.xml |

**Response (200):**
```json
{
  "summary": {
    "total_dependencies": 45,
    "total_vulnerabilities": 8,
    "severity_counts": { "Critical": 2, "High": 3, "Medium": 3 }
  },
  "findings": [
    {
      "package": "django",
      "installed_version": "3.2.0",
      "severity": "Critical",
      "cvss_score": 9.8,
      "cve_id": "CVE-2021-44420",
      "fixed_in": "3.2.11"
    }
  ]
}
```

---

### POST /api/security/copilot/chat

Chat with the AI Security Copilot.

**Request:**
```json
{
  "message": "What is my highest risk issue?",
  "scan_id": 1
}
```

**Response (200):**
```json
{
  "response": "**Highest Risk Findings**\n\n### 1. Broken Object Level Authorization (High)...",
  "intent": "highest_risk",
  "tool_used": "get_critical_findings",
  "has_context": true
}
```

---

## Audit Center

### GET /api/audit/logs

Paginated, filtered audit log list.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| page | int | Page number |
| page_size | int | Items per page (max: 200) |
| module | string | Filter by module (authentication, scanning, etc.) |
| risk_level | string | Filter by risk (high, medium, info) |
| action | string | Exact action match |
| action_prefix | string | Action prefix match |
| search | string | Full-text search |
| date_from | datetime | Start date |
| date_to | datetime | End date |

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "username": "admin",
      "action": "auth.login",
      "module": "authentication",
      "entity_type": "user",
      "entity_id": 1,
      "risk_level": "medium",
      "status": "success",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "request_id": "abc-123",
      "created_at": "2026-08-20T10:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

---

### GET /api/audit/stats

Aggregate audit statistics (admin only).

**Response (200):**
```json
{
  "total_events": 1500,
  "by_module": { "authentication": 800, "scanning": 400, "organization": 300 },
  "by_risk_level": { "high": 50, "medium": 200, "info": 1250 },
  "top_actions": [
    { "action": "auth.login", "count": 500 },
    { "action": "scan.completed", "count": 200 }
  ]
}
```

---

### GET /api/audit/export

CSV export of filtered audit logs (admin only).

**Response:** `text/csv` (attachment)

---

## Organizations

### POST /api/organizations

Create an organization.

**Request:**
```json
{
  "name": "Acme Security Team",
  "slug": "acme-security",
  "description": "Internal security team"
}
```

---

### GET /api/organizations

List user's organizations.

---

### POST /api/organizations/{id}/members

Add member to organization (admin only).

**Request:**
```json
{ "user_id": 2, "role": "member" }
```

---

### POST /api/organizations/{id}/projects

Create a project within an organization.

---

## Health & Observability

### GET /api/v1/health

Full health check with all component details.

**Response (200/207/503):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "uptime_human": "1h 0m",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "ai_engine": "unavailable",
    "workers": "healthy"
  },
  "details": {
    "database": { "status": "healthy", "latency_ms": 2.1 },
    "cpu": { "usage_percent": 15.3, "cores": 4 },
    "memory": { "process_rss_mb": 128.5 },
    "environment": { "python_version": "3.11.9", "platform": "Linux" }
  }
}
```

---

### GET /api/v1/ready

Kubernetes readiness probe. Returns 503 if database is down.

---

### GET /api/v1/live

Kubernetes liveness probe. Always returns 200.

---

### GET /metrics

Prometheus metrics in text format.

---

## WebSocket

### ws://localhost:8000/ws/scan/{task_id}

Real-time scan progress updates.

**Messages received:**
```json
{
  "task_id": "abc-123",
  "status": "running",
  "progress": 45,
  "message": "[API5] Broken Function Level Authorization...",
  "scan_id": 1
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 422 | Validation error (Pydantic) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/auth/register` | 30 | per minute |
| `/api/auth/login` | 30 | per minute |
| `/api/auth/refresh` | 60 | per minute |
| `/api/security/copilot/chat` | 20 | per minute |
| All other endpoints | 30 | per minute |

Rate limits are per-user when authenticated, per-IP when anonymous.
