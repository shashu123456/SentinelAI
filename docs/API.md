# SentinelAI — API Documentation

> Complete REST API reference for all 93 endpoints.

---

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL & Versioning](#base-url--versioning)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Endpoint Reference](#endpoint-reference)
  - [Authentication](#auth-endpoints)
  - [Scans](#scan-endpoints)
  - [Organizations](#organization-endpoints)
  - [Teams](#team-endpoints)
  - [Invitations](#invitation-endpoints)
  - [API Keys](#api-key-endpoints)
  - [AI Copilot](#copilot-endpoints)
  - [SAST Scanner](#sast-endpoints)
  - [Dependency Scanner](#dependency-endpoints)
  - [Security Engine](#security-engine-endpoints)
  - [Audit](#audit-endpoints)
  - [Security Events](#security-events-endpoints)
  - [WebSocket](#websocket-endpoints)
  - [System](#system-endpoints)
- [OpenAPI Specification](#openapi-specification)

---

## Overview

SentinelAI provides a RESTful API with JSON request/response bodies. The API is versioned (`/api/v1/`) and uses JWT Bearer tokens for authentication.

### API Statistics

| Metric | Value |
|--------|-------|
| Total Endpoints | 93 |
| Versioned Endpoints | 65+ |
| Legacy Endpoints | 28 |
| Auth Required | 89 |
| Rate Limited | 12 |
| WebSocket Endpoints | 1 |

---

## Authentication

### JWT Bearer Token

```bash
# Login to get tokens
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'

# Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 1, "username": "admin", "role": "admin" }
}

# Use token in subsequent requests
curl http://localhost:8000/api/scans \
  -H "Authorization: Bearer eyJ..."
```

### Refresh Token Flow

```bash
# Refresh automatically when access token expires (401)
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -b "refresh_token=<token>"

# New access token returned, old refresh token rotated
```

### CSRF Protection

```bash
# GET requests set a CSRF cookie automatically
curl -c cookies.txt http://localhost:8000/api/auth/me

# POST requests must include the CSRF token in header
curl -X POST http://localhost:8000/api/scans \
  -H "X-CSRF-Token: <csrf_token>" \
  -b cookies.txt \
  -d '{...}'
```

---

## Base URL & Versioning

| Environment | Base URL |
|-------------|----------|
| Development | `http://localhost:8000` |
| Production | `https://api.sentinelai.com` |

### API Versions

| Version | Path | Status |
|---------|------|--------|
| v0 (Legacy) | `/api/*` | Deprecated — maintained for backward compatibility |
| v1 | `/api/v1/*` | **Current — recommended** |

All v1 endpoints return responses wrapped in a standard envelope:

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed",
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

---

## Response Format

### Success (200)

```json
{
  "success": true,
  "data": {
    "id": 1,
    "api_name": "My API",
    "status": "completed",
    "total_vulnerabilities": 12,
    "risk_score": 72
  },
  "message": "Scan completed successfully"
}
```

### Created (201)

```json
{
  "success": true,
  "data": { "id": 1, "name": "Engineering Team" },
  "message": "Team created"
}
```

### Paginated (200)

```json
{
  "success": true,
  "data": [...],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 156,
    "pages": 8
  }
}
```

### Error (4xx/5xx)

```json
{
  "success": false,
  "error": "Insufficient permissions",
  "detail": "Requires admin role or higher"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input / validation error |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Valid token but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource (e.g., username taken) |
| 413 | Payload Too Large | File exceeds 10MB limit |
| 422 | Unprocessable Entity | Schema validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side failure |

### Validation Error Detail

```json
{
  "success": false,
  "error": "Validation failed",
  "detail": "username: field required; email: invalid email format"
}
```

---

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /api/auth/login` | 10 | 15 minutes |
| `POST /api/auth/register` | 5 | 1 hour |
| `POST /api/auth/password-reset` | 3 | 1 hour |
| All other endpoints | 100 | 1 minute |

### Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067200
Retry-After: 30
```

---

## Endpoint Reference

### Auth Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | No | Create new user account |
| POST | `/api/auth/login` | No | Authenticate and get tokens |
| POST | `/api/auth/logout` | Yes | Logout and revoke tokens |
| POST | `/api/auth/logout-all` | Yes | Logout from all devices |
| POST | `/api/auth/refresh` | Yes (cookie) | Refresh access token |
| GET | `/api/auth/me` | Yes | Get current user profile |
| POST | `/api/auth/password-reset-request` | No | Request password reset email |
| POST | `/api/auth/password-reset` | No | Reset password with token |

#### POST /api/auth/register

```json
// Request
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecureP@ss123"
}

// Response (201)
{
  "success": true,
  "data": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  "message": "Registration successful"
}
```

#### POST /api/auth/login

```json
// Request
{
  "username": "johndoe",
  "password": "SecureP@ss123"
}

// Response (200)
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "role": "user"
    }
  },
  "message": "Login successful"
}

// Set-Cookie headers:
// refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/api/auth
// csrf_token=<token>; Secure; SameSite=Strict; Path=/
```

---

### Scan Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/scans/upload` | Yes | Upload OpenAPI spec and scan |
| GET | `/api/scans` | Yes | List all scans |
| GET | `/api/scans/{id}` | Yes | Get scan details |
| GET | `/api/scans/{id}/findings` | Yes | Get scan findings |
| POST | `/api/scans/{id}/report` | Yes | Generate PDF report |
| GET | `/api/scans/{id}/report` | Yes | Download report |
| GET | `/api/scans/{id}/ai-analysis` | Yes | Get AI analysis |
| POST | `/api/scans/{id}/ai-analyze` | Yes | Run AI analysis |
| DELETE | `/api/scans/{id}` | Yes | Delete scan |
| GET | `/api/scans/analytics/severity` | Yes | Severity distribution |
| GET | `/api/scans/analytics/owasp` | Yes | OWASP category distribution |
| GET | `/api/scans/analytics/timeline` | Yes | Scan timeline |
| GET | `/api/scans/dashboard/stats` | Yes | Dashboard statistics |
| GET | `/api/scans/dashboard/recent` | Yes | Recent scans |
| GET | `/api/scans/dashboard/top-vulns` | Yes | Top vulnerabilities |
| GET | `/api/scans/dashboard/risk-trend` | Yes | Risk trend data |
| GET | `/api/scans/org/{org_id}` | Yes | Scans by organization |
| GET | `/api/scans/project/{project_id}` | Yes | Scans by project |
| POST | `/api/scans/org/{org_id}/upload` | Yes | Upload scan to org |

#### POST /api/scans/upload

```bash
# Upload OpenAPI spec (YAML or JSON)
curl -X POST http://localhost:8000/api/scans/upload \
  -H "Authorization: Bearer eyJ..." \
  -H "X-CSRF-Token: <token>" \
  -F "file=@openapi.yaml" \
  -F "api_name=My API"
```

```json
// Response (201)
{
  "success": true,
  "data": {
    "id": 1,
    "api_name": "My API",
    "api_title": "My API",
    "total_endpoints": 42,
    "total_vulnerabilities": 8,
    "risk_score": 45,
    "risk_level": "medium",
    "status": "completed",
    "created_at": "2024-01-01T00:00:00Z",
    "completed_at": "2024-01-01T00:00:15Z"
  },
  "message": "Scan completed: 42 endpoints, 8 vulnerabilities found"
}
```

#### GET /api/scans (Paginated)

```bash
curl "http://localhost:8000/api/scans?page=1&per_page=10&status=completed" \
  -H "Authorization: Bearer eyJ..."
```

---

### Organization Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/api/v1/orgs` | Yes | Any | Create organization |
| GET | `/api/v1/orgs` | Yes | Any | List my organizations |
| GET | `/api/v1/orgs/{id}` | Yes | viewer | Get organization details |
| PUT | `/api/v1/orgs/{id}` | Yes | owner | Update organization settings |
| GET | `/api/v1/orgs/{id}/dashboard` | Yes | viewer | Org dashboard stats |
| GET | `/api/v1/orgs/{id}/analytics` | Yes | viewer | Org analytics |
| POST | `/api/v1/orgs/{id}/members` | Yes | admin | Invite member |
| DELETE | `/api/v1/orgs/{id}/members/{uid}` | Yes | admin | Remove member |
| PUT | `/api/v1/orgs/{id}/members/{uid}/role` | Yes | owner | Change member role |
| GET | `/api/v1/orgs/{id}/projects` | Yes | viewer | List org projects |
| POST | `/api/v1/orgs/{id}/projects` | Yes | developer | Create project |

#### POST /api/v1/orgs

```json
// Request
{
  "name": "Acme Security Team",
  "description": "Enterprise security platform"
}

// Response (201)
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Acme Security Team",
    "slug": "acme-security-team",
    "subscription_tier": "free",
    "max_members": 5,
    "max_projects": 3,
    "owner_id": 1,
    "role": "owner"
  },
  "message": "Organization created"
}
```

---

### Team Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/orgs/{id}/teams` | Yes | viewer | List teams |
| POST | `/api/v1/orgs/{id}/teams` | Yes | admin | Create team |
| GET | `/api/v1/orgs/{id}/teams/{tid}` | Yes | viewer | Get team details |
| PUT | `/api/v1/orgs/{id}/teams/{tid}` | Yes | admin | Update team |
| DELETE | `/api/v1/orgs/{id}/teams/{tid}` | Yes | admin | Delete team |
| GET | `/api/v1/orgs/{id}/teams/{tid}/members` | Yes | viewer | List team members |
| POST | `/api/v1/orgs/{id}/teams/{tid}/members` | Yes | admin | Add member |
| DELETE | `/api/v1/orgs/{id}/teams/{tid}/members/{uid}` | Yes | admin | Remove member |
| PUT | `/api/v1/orgs/{id}/teams/{tid}/members/{uid}/role` | Yes | admin | Change member role |
| GET | `/api/v1/orgs/{id}/teams/{tid}/stats` | Yes | viewer | Team stats |

---

### Invitation Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/api/v1/orgs/{id}/invitations` | Yes | admin | Send invitation |
| GET | `/api/v1/orgs/{id}/invitations` | Yes | admin | List invitations |
| DELETE | `/api/v1/orgs/{id}/invitations/{iid}` | Yes | admin | Revoke invitation |
| POST | `/api/v1/invitations/accept` | Yes | Any | Accept invitation |
| GET | `/api/v1/invitations/{token}` | No | Any | Verify invitation token |

#### POST /api/v1/orgs/{id}/invitations

```json
// Request
{
  "email": "newuser@company.com",
  "role": "developer",
  "project_ids": [1, 2]
}

// Response (201)
{
  "success": true,
  "data": {
    "id": 1,
    "email": "newuser@company.com",
    "role": "developer",
    "status": "pending",
    "expires_at": "2024-02-01T00:00:00Z"
  },
  "message": "Invitation sent to newuser@company.com"
}
```

---

### API Key Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/orgs/{id}/api-keys` | Yes | admin | List API keys |
| POST | `/api/v1/orgs/{id}/api-keys` | Yes | admin | Create API key |
| DELETE | `/api/v1/orgs/{id}/api-keys/{kid}` | Yes | admin | Revoke API key |

#### POST /api/v1/orgs/{id}/api-keys

```json
// Request
{
  "name": "CI/CD Pipeline",
  "scopes": ["scans:read", "scans:write"]
}

// Response (201) — Key shown ONCE
{
  "success": true,
  "data": {
    "id": 1,
    "name": "CI/CD Pipeline",
    "key_prefix": "snt_",
    "key": "snt_a1b2c3d4e5f6...",  // FULL KEY — shown once only!
    "scopes": ["scans:read", "scans:write"],
    "is_active": true
  },
  "message": "API key created. Store it securely — it won't be shown again."
}
```

---

### Copilot Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/copilot/chat` | Yes | Chat with AI security copilot |
| GET | `/api/copilot/history` | Yes | Get conversation history |
| GET | `/api/copilot/intents` | Yes | List available intents |
| GET | `/api/copilot/health` | Yes | AI engine health check |

#### POST /api/copilot/chat

```json
// Request
{
  "message": "Explain the BOLA vulnerability found in my scan",
  "scan_id": 1,
  "context": {}
}

// Response (200)
{
  "success": true,
  "data": {
    "response": "BOLA (Broken Object Level Authorization)...",
    "intent": "explain_vulnerability",
    "confidence": 0.92,
    "sources": ["OWASP API1", "CWE-639"],
    "suggestions": [
      "How do I fix BOLA?",
      "Show me secure examples",
      "Map this to PCI DSS"
    ]
  }
}
```

---

### SAST Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/sast/scan` | Yes | Run SAST scan |
| GET | `/api/sast/rules` | Yes | List all SAST rules |
| GET | `/api/sast/stats` | Yes | SAST statistics |

---

### Dependency Scanner Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/deps/scan` | Yes | Scan dependencies |
| POST | `/api/deps/upload` | Yes | Upload manifest file |
| GET | `/api/deps/stats` | Yes | Dependency statistics |

---

### Security Engine Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/security/analyze` | Yes | Analyze API spec |
| GET | `/api/security/rules` | Yes | List security rules |

---

### Audit Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/audit` | Yes | viewer | List audit logs |
| GET | `/api/audit/{id}` | Yes | viewer | Get audit entry |
| GET | `/api/audit/stats` | Yes | viewer | Audit statistics |
| GET | `/api/audit/user/{uid}` | Yes | admin | User audit history |

---

### Security Events Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/security/events` | Yes | List security events |
| GET | `/api/v1/security/events/{id}` | Yes | Get event details |
| GET | `/api/v1/security/stats` | Yes | Security statistics |
| GET | `/api/v1/security/threats` | Yes | Active threats |
| GET | `/api/v1/security/dashboard` | Yes | Security dashboard |

---

### WebSocket Endpoints

| Protocol | Path | Auth | Description |
|----------|------|------|-------------|
| WS | `/ws/scan/{scan_id}` | Yes (JWT) | Real-time scan progress |

#### WebSocket Connection

```javascript
// Connect with JWT token
const ws = new WebSocket(
  `ws://localhost:8000/ws/scan/1?token=${accessToken}`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data = { type: "progress|finding|completed|error", ... }
};

ws.onerror = (error) => {
  // Handle: { detail: "Authentication required" }
};
```

#### Message Types

```json
// Scan progress
{ "type": "progress", "phase": "parsing", "progress": 30, "message": "Parsing OpenAPI spec..." }

// New finding
{ "type": "finding", "finding": { "name": "BOLA", "severity": "high" } }

// Scan complete
{ "type": "completed", "summary": { "endpoints": 42, "vulnerabilities": 8 } }

// Error
{ "type": "error", "message": "Invalid spec format" }
```

---

### System Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | No | Health check |
| GET | `/api/ready` | No | Readiness probe |
| GET | `/api/metrics` | No | Prometheus metrics |
| GET | `/api/v1/health` | No | Health check (v1) |
| GET | `/api/v1/ready` | No | Readiness probe |
| GET | `/api/v1/metrics` | No | Prometheus metrics |

#### GET /api/health

```json
{
  "status": "healthy",
  "version": "1.1.0",
  "uptime": 3600,
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "ai_engine": "available"
  }
}
```

---

## OpenAPI Specification

### Interactive Documentation

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/openapi.json` | OpenAPI 3.0 Spec |

### Downloading the Spec

```bash
curl http://localhost:8000/openapi.json > sentinelai-openapi.json
```

### Client Generation

```bash
# Generate TypeScript client
npx @openapitools/openapi-generator-cli generate \
  -i sentinelai-openapi.json \
  -g typescript-fetch \
  -o frontend/src/generated/api

# Generate Python client
openapi-generator generate \
  -i sentinelai-openapi.json \
  -g python \
  -o sdk/python
```

---

## SDK Examples

### Python

```python
import requests

BASE = "http://localhost:8000"
session = requests.Session()

# Login
resp = session.post(f"{BASE}/api/auth/login", json={
    "username": "admin",
    "password": "secret"
})
token = resp.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Upload and scan
with open("openapi.yaml", "rb") as f:
    resp = session.post(
        f"{BASE}/api/scans/upload",
        headers=headers,
        files={"file": f},
        data={"api_name": "My API"}
    )
scan = resp.json()["data"]
print(f"Found {scan['total_vulnerabilities']} vulnerabilities")

# Chat with AI copilot
resp = session.post(
    f"{BASE}/api/copilot/chat",
    headers=headers,
    json={"message": "Explain the top vulnerability", "scan_id": scan["id"]}
)
print(resp.json()["data"]["response"])
```

### JavaScript

```javascript
const API = "http://localhost:8000";

// Login
const loginRes = await fetch(`${API}/api/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username: "admin", password: "secret" }),
});
const { data: { access_token } } = await loginRes.json();

// Fetch scans
const scansRes = await fetch(`${API}/api/scans?page=1&per_page=10`, {
  headers: { Authorization: `Bearer ${access_token}` },
});
const { data: scans, meta } = await scansRes.json();
console.log(`Showing ${scans.length} of ${meta.total} scans`);
```
