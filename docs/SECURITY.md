# SentinelAI — Security Documentation

> Threat model, security architecture, hardening guide, and OWASP compliance.

---

## Table of Contents

- [Security Overview](#security-overview)
- [Threat Model](#threat-model)
- [Security Architecture](#security-architecture)
- [Authentication](#authentication)
- [Authorization (RBAC)](#authorization-rbac)
- [Input Validation](#input-validation)
- [Output Encoding](#output-encoding)
- [OWASP Compliance](#owasp-compliance)
- [Security Headers](#security-headers)
- [Rate Limiting](#rate-limiting)
- [Audit Logging](#audit-logging)
- [Threat Detection](#threat-detection)
- [Known Issues](#known-issues)
- [Security Testing](#security-testing)
- [Reporting Vulnerabilities](#reporting-vulnerabilities)

---

## Security Overview

SentinelAI implements defense-in-depth security across 6 layers:

1. **Network** — TLS, rate limiting, DDoS protection
2. **Application** — CSP, CORS, security headers
3. **Authentication** — JWT + refresh rotation, bcrypt, account lockout
4. **Authorization** — 6-tier RBAC, org/project scoping
5. **Input** — XSS, SQLi, SSRF, file upload validation
6. **Threat** — IP reputation, brute force detection, session monitoring

### Security Scorecard

| Area | Score | Notes |
|------|-------|-------|
| Authentication | 8/10 | JWT rotation, CSRF, lockout |
| Authorization | 7/10 | 6-tier RBAC, org scoping |
| Input Validation | 7/10 | XSS, SQLi, path traversal detection |
| OWASP Coverage | 8/10 | 21 OWASP API Top 10 checks |
| Security Headers | 9/10 | 13 headers including COOP/COEP |
| Audit Logging | 8/10 | Append-only, risk-classified |
| Threat Detection | 7/10 | IP reputation, brute force, geo anomaly |
| Secrets Management | 6/10 | Env-based, vault recommended for prod |
| **Overall** | **7.5/10** | Strong for portfolio, prod hardening recommended |

---

## Threat Model

### Assets

| Asset | Sensitivity | Protection |
|-------|-------------|------------|
| User credentials | Critical | bcrypt, JTI blacklist |
| JWT tokens | High | Short-lived (15min), refresh rotation |
| API keys | High | SHA-256 hashed, prefix-only storage |
| Scan data | Medium | Org-scoped isolation |
| Audit logs | High | Append-only, no delete API |
| AI conversations | Medium | Per-user isolation |
| Organization data | Critical | Multi-tenant isolation |

### Threat Actors

| Actor | Motivation | Primary Attack Vectors |
|-------|------------|----------------------|
| External attacker | Data theft, disruption | Auth bypass, injection, SSRF |
| Malicious insider | Privilege escalation | RBAC bypass, org hopping |
| Compromised account | Lateral movement | Token theft, session hijack |
| AI attacker | Prompt injection | Copilot manipulation |

### Attack Surface

```
┌─────────────────────────────────────────────────────┐
│                    ATTACK SURFACE                     │
├─────────────────────────────────────────────────────┤
│                                                       │
│  HTTP API ←── JWT Auth ←── User Input                │
│      │                                                │
│      ├── File Upload (OpenAPI specs)                  │
│      ├── WebSocket (scan streaming)                   │
│      ├── AI Copilot (prompt injection)                │
│      └── Organization APIs (multi-tenant)             │
│                                                       │
│  Internal                                             │
│      ├── Database (SQL injection)                     │
│      ├── Redis (cache poisoning)                      │
│      └── File System (path traversal)                 │
│                                                       │
└─────────────────────────────────────────────────────┘
```

---

## Security Architecture

### Defense-in-Depth Diagram

```
Layer 1: Network
  └── TLS Termination (Nginx)
  └── Rate Limiting (Slowapi + Nginx)
  └── IP Blocking (SSRF protection)

Layer 2: Application
  └── Security Headers (13 headers)
  └── CORS Policy (configurable origins)
  └── Content Security Policy (strict)
  └── CSRF Protection (double-submit cookie)

Layer 3: Authentication
  └── bcrypt Password Hashing
  └── JWT Access Tokens (15min)
  └── Refresh Token Rotation
  └── Account Lockout (5 failures → 30min)
  └── Token Blacklist (Redis + memory fallback)

Layer 4: Authorization
  └── 6-Tier RBAC (owner > admin > security_eng > developer > viewer)
  └── Organization Scoping
  └── Project Scoping
  └── Team Permissions

Layer 5: Input Validation
  └── XSS Detection & Sanitization
  └── SQL Injection Pattern Detection
  └── Path Traversal Blocking
  └── SSRF Protection (internal IP blocking)
  └── File Upload Validation (magic bytes, size, encoding)
  └── Pydantic Schema Validation

Layer 6: Monitoring
  └── Threat Detection (IP reputation, brute force)
  └── Session Monitoring (replay detection)
  └── Security Events Dashboard
  └── Audit Logging (append-only)
```

---

## Authentication

### JWT Token Structure

```json
{
  "sub": "1",
  "username": "admin",
  "role": "admin",
  "org_id": 1,
  "jti": "unique-token-id",
  "iat": 1704067200,
  "exp": 1704068100,
  "token_type": "access"
}
```

### Token Lifecycle

```
Login
  ├── Verify password (bcrypt, timing-safe)
  ├── Check account lockout
  ├── Assess threat level (IP, device, location)
  ├── Generate refresh token (60 days)
  ├── Generate access token (15 minutes)
  ├── Set HTTP-only cookies
  ├── Set CSRF cookie
  └── Audit log

Refresh
  ├── Validate CSRF header
  ├── Extract refresh token from HTTP-only cookie
  ├── Check token reuse (family revocation if stolen)
  ├── Revoke old refresh token
  ├── Create new refresh token (same family)
  ├── Generate new access token
  └── Audit log

Logout
  ├── Add JTI to blacklist (Redis)
  ├── Revoke refresh token
  └── Audit log
```

### Refresh Token Rotation

SentinelAI implements **one-time-use refresh tokens with family tracking**:

1. Each refresh token belongs to a **family** (one per login session)
2. When refreshed, the old token is revoked and a new one created in the same family
3. If a revoked token is reused (token theft detected), **the entire family is revoked**
4. This forces all sessions from the stolen token to re-authenticate

```
Login → Token_A (family=f1)
Refresh → Token_A revoked, Token_B (family=f1)
Refresh → Token_B revoked, Token_C (family=f1)

If Token_A is used after revocation:
  → Family f1 revoked
  → Token_C also revoked
  → User must re-login
```

### Password Policy

| Rule | Requirement |
|------|-------------|
| Minimum length | 8 characters |
| Complexity | Mixed case + numbers |
| Hashing | bcrypt with 12 rounds |
| Comparison | Timing-safe (DUMMY_HASH equalization) |
| Reset | Token-based, 1 hour expiry |

### Account Lockout

| Threshold | Duration | Reset |
|-----------|----------|-------|
| 5 failed attempts | 30 minutes | Successful login or manual admin reset |

---

## Authorization (RBAC)

### Role Hierarchy

```
super_admin (level 100)
    └── Full system access (platform admin)

owner (level 40)
    └── Full org access: settings, members, roles, billing

admin (level 30)
    └── Manage: members, teams, API keys, projects

security_engineer (level 20)
    └── Run: scans, find/manage vulnerabilities, reports

developer (level 10)
    └── Create: projects, upload specs, view findings

viewer (level 5)
    └── Read-only: dashboards, scan results, reports
```

### Permission Matrix

| Action | Viewer | Developer | Security Eng | Admin | Owner |
|--------|--------|-----------|-------------|-------|-------|
| View dashboards | ✅ | ✅ | ✅ | ✅ | ✅ |
| View scans | ✅ | ✅ | ✅ | ✅ | ✅ |
| Run scans | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create projects | ❌ | ✅ | ✅ | ✅ | ✅ |
| View audit logs | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invite members | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage teams | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create API keys | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage members | ❌ | ❌ | ❌ | ✅ | ✅ |
| Update org settings | ❌ | ❌ | ❌ | ❌ | ✅ |
| Change roles | ❌ | ❌ | ❌ | ❌ | ✅ |
| Delete org | ❌ | ❌ | ❌ | ❌ | ✅ |

### Data Isolation

```
Organization A
├── Scans A (only visible to Org A members)
├── Projects A
├── Members A
└── Audit Logs A

Organization B
├── Scans B (only visible to Org B members)
├── Projects B
├── Members B
└── Audit Logs B

// Cross-organization data leakage: PREVENTED
// Each query is scoped to the user's organization
```

---

## Input Validation

### XSS Protection

```python
from app.utils.sanitization import sanitize_for_display, contains_xss

# Detect XSS in input
if contains_xss(user_input):
    raise HTTPException(400, "Invalid input detected")

# Sanitize output
safe_output = sanitize_for_display(user_input)
```

**Blocked patterns:**
- `<script>` tags and variations
- `javascript:` protocol
- `on*` event handlers
- `data:` URI scheme
- HTML entity encoding attacks

### SQL Injection Protection

```python
from app.utils.sanitization import contains_sql_injection

# Detect SQLi patterns
if contains_sql_injection(user_input):
    raise HTTPException(400, "Invalid input detected")
```

**Blocked patterns:**
- `UNION SELECT`, `INSERT`, `DELETE`, `DROP`
- `1=1`, `OR 1`, `AND 1`
- Comment sequences (`--`, `/*`)
- Hex-encoded strings
- Time-based blind injection (`WAITFOR`, `BENCHMARK`)

### Path Traversal Protection

```python
from app.utils.sanitization import contains_path_traversal

if contains_path_traversal(user_input):
    raise HTTPException(400, "Invalid path detected")
```

### SSRF Protection

```python
from app.utils.ssrf_protection import is_url_safe

# Blocks internal/private IPs
if not is_url_safe(url):
    raise HTTPException(400, "URL points to restricted resource")
```

**Blocked targets:**
- Private IP ranges (10.x, 172.16-31.x, 192.168.x)
- Loopback (127.x, ::1, localhost)
- Cloud metadata (169.254.169.254)
- Link-local addresses
- IPv6 private ranges

### File Upload Security

```python
from app.utils.ssrf_protection import validate_file_upload

valid, reason = validate_file_upload(filename, content)
if not valid:
    raise HTTPException(413, reason)
```

**Validation checks:**
- File size limit (10MB)
- Magic byte validation (YAML/JSON signatures)
- UTF-8 encoding check
- Null byte detection
- Extension vs content mismatch detection

---

## OWASP Compliance

### OWASP API Security Top 10 Coverage

| # | Category | Check ID | Status |
|---|----------|----------|--------|
| API1 | Broken Object Level Authorization | SA-01 | ✅ Detected |
| API2 | Broken Authentication | SA-02, SA-03, SA-21 | ✅ Detected |
| API3 | Broken Object Property Level Authorization | SA-04, SA-05, SA-06 | ✅ Detected |
| API4 | Unrestricted Resource Consumption | SA-07, SA-08, SA-09 | ✅ Detected |
| API5 | Broken Function Level Authorization | SA-10, SA-11 | ✅ Detected |
| API6 | Unrestricted Access to Sensitive Business Flows | SA-12 | ✅ Detected |
| API7 | Server Side Request Forgery | SA-13, SA-14 | ✅ Detected |
| API8 | Security Misconfiguration | SA-15, SA-16, SA-17 | ✅ Detected |
| API9 | Improper Inventory Management | SA-18, SA-19 | ✅ Detected |
| API10 | Unsafe Consumption of APIs | SA-20 | ✅ Detected |

### OWASP ASVS Reference

| ASVS Section | SentinelAI Coverage |
|--------------|-------------------|
| V1 Architecture | ✅ Documented |
| V2 Authentication | ✅ JWT, refresh rotation, lockout |
| V3 Session Management | ✅ Token blacklist, expiry |
| V4 Access Control | ✅ RBAC, org scoping |
| V5 Validation | ✅ Input sanitization, Pydantic |
| V6 Cryptography | ✅ bcrypt, SHA-256 |
| V7 Error Handling | ✅ Envelope responses |
| V8 Data Protection | ✅ Org isolation |
| V9 Communications | ✅ TLS, CORS, CSP |
| V10 Malicious Code | ✅ XSS, SQLi detection |
| V11 Business Logic | ⚠️ Partial (scanner rules) |
| V12 Files | ✅ Upload validation |
| V13 API | ✅ OpenAPI, rate limiting |
| V14 Config | ✅ Env-based settings |

---

## Security Headers

### Implemented Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `0` | Disable legacy XSS filter (CSP replaces) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer info |
| `Permissions-Policy` | `30+ features disabled` | Disable browser features |
| `Content-Security-Policy` | `self-only` | Prevent XSS, data injection |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | Force HTTPS |
| `Cross-Origin-Opener-Policy` | `same-origin` | Prevent cross-origin attacks |
| `Cross-Origin-Embedder-Policy` | `require-corp` | Prevent embedding |
| `Cross-Origin-Resource-Policy` | `same-origin` | Prevent resource theft |
| `Server` | *removed* | Hide server information |

### Content Security Policy

```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self';
connect-src 'self' ws://localhost:8000 wss://api.sentinelai.com;
frame-ancestors 'none';
object-src 'none';
base-uri 'self';
form-action 'self';
```

---

## Rate Limiting

### Endpoint Limits

| Endpoint | Limit | Window | Lockout |
|----------|-------|--------|---------|
| `POST /api/auth/login` | 10 | 15 min | Progressive |
| `POST /api/auth/register` | 5 | 1 hour | Account |
| `POST /api/auth/password-reset` | 3 | 1 hour | Email |
| `POST /api/copilot/chat` | 30 | 1 minute | User |
| `POST /api/scans/upload` | 10 | 5 minutes | User |
| All other endpoints | 100 | 1 minute | IP |

### Progressive Lockout

```
Failed Attempt 1-4: Normal processing
Failed Attempt 5: Account locked for 30 minutes
Failed Attempt 6-10: IP flagged, 1 hour cooldown
Failed Attempt 10+: Temporary IP ban, alert generated
```

---

## Audit Logging

### Logged Events

| Category | Events |
|----------|--------|
| Authentication | login, logout, logout_all, failed_login, account_lock, password_reset, password_change |
| User Management | user_create, user_delete, role_change, permission_change, account_activate, account_deactivate |
| Organization | org_create, org_update, org_delete, member_invite, member_remove |
| Security | scan_start, scan_complete, scan_cancel, report_export, settings_change |
| API | api_key_create, api_key_delete, api_key_rotate |

### Audit Record Format

```json
{
  "id": 1234,
  "timestamp": "2024-01-01T00:00:00Z",
  "user_id": 1,
  "username": "admin",
  "organization_id": 1,
  "action": "login",
  "module": "auth",
  "entity_type": "user",
  "entity_id": 1,
  "old_value": null,
  "new_value": null,
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "request_id": "req_abc123",
  "status": "success",
  "risk_level": "low",
  "metadata": "{\"method\": \"password\"}"
}
```

### Risk Classification

| Risk Level | Trigger |
|------------|---------|
| **Critical** | Multiple failed logins, org deletion, role escalation |
| **High** | Account lockout, password change, API key creation |
| **Medium** | Login, logout, scan completion |
| **Low** | Dashboard views, read operations |

---

## Threat Detection

### Suspicious Login Assessment

```python
from app.utils.threat_detection import assess_login_threat

assessment = assess_login_threat(
    user_id=1,
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    login_successful=True
)

# Returns:
# - threat_level: "low" | "medium" | "high" | "critical"
# - is_suspicious: bool
# - reasons: list[str]
# - recommended_action: str
```

### Detection Signals

| Signal | Weight | Source |
|--------|--------|--------|
| Failed login threshold | High | Failed attempts tracking |
| Known malicious IP | High | Internal reputation list |
| Login from new IP | Medium | IP history |
| Multiple rapid attempts | High | Time-based analysis |
| Unusual time of day | Low | Hour-of-day analysis |
| Impossible travel | High | Geo-location change speed |

### IP Reputation Categories

| Category | Action |
|----------|--------|
| `clean` | Allow, no restrictions |
| `suspicious` | Allow with enhanced logging |
| `malicious` | Block with alert |
| `internal` | Allow (SSRF protection bypass for health checks) |

---

## Known Issues

### Tracked Security Issues

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| SEC-001 | Medium | WebSocket broadcasts to all connected clients (no per-user isolation) | Known limitation |
| SEC-002 | Medium | File upload scanning doesn't validate file content deeply | Known limitation |
| SEC-003 | Low | Token blacklist has in-memory fallback (lost on restart without Redis) | Config-dependent |
| SEC-004 | Low | No automated secrets rotation | Future improvement |
| SEC-005 | Low | No MFA/TOTP support | Planned v1.5 |

### Mitigations Applied

| Risk | Mitigation |
|------|-----------|
| JWT theft | Refresh token rotation with family tracking |
| Brute force | Account lockout + progressive delays |
| XSS | Input sanitization + output encoding + CSP |
| SQL injection | ORM (SQLAlchemy) + pattern detection |
| SSRF | Internal IP blocking + cloud metadata blocking |
| Prompt injection | Input validation + intent classification |

---

## Security Testing

### Test Coverage

| Test Category | Tests | Status |
|--------------|-------|--------|
| XSS Protection | 17 | ✅ All pass |
| SQL Injection | 8 | ✅ All pass |
| Path Traversal | 5 | ✅ All pass |
| Filename Sanitization | 5 | ✅ All pass |
| URL Validation | 7 | ✅ All pass |
| SSRF Protection | 7 | ✅ All pass |
| File Upload Security | 6 | ✅ All pass |
| Email & Input | 9 | ✅ All pass |
| Threat Detection | 13 | ✅ Logic verified |
| WebSocket Auth | 3 | ✅ All pass |
| Security Headers | 3 | ✅ All pass |
| Password Reset | 3 | ✅ All pass |
| **Total** | **86** | **✅ All pass** |

### Running Security Tests

```bash
cd backend

# All security tests
python -m pytest tests/test_security_hardening.py -v

# Specific category
python -m pytest tests/test_security_hardening.py -k "test_xss" -v

# Enterprise RBAC tests
python -m pytest tests/test_enterprise_multitenancy.py -v
```

---

## Reporting Vulnerabilities

If you discover a security vulnerability in SentinelAI:

1. **Do NOT** open a public GitHub issue
2. Email security reports to: `security@sentinelai.example.com`
3. Include: description, steps to reproduce, impact assessment
4. Allow 90 days for remediation before public disclosure

### Responsible Disclosure Policy

- We will acknowledge receipt within 48 hours
- We will provide a timeline for fix within 7 days
- We will credit reporters in release notes (unless anonymity preferred)
- We will not pursue legal action against good-faith security researchers
