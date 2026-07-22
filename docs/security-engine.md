# Security Engine

## Overview

The security engine analyzes OpenAPI specifications against the OWASP API Security Top 10. It consists of three components: the Parser, the Scanner, and the Risk Engine.

## Parser

Extracts structured data from OpenAPI 3.x and Swagger 2.0 specifications:

- **Endpoints**: Path, HTTP method, operation ID, tags, summary
- **Parameters**: Name, location (path/query/header), schema, required flag
- **Request Bodies**: Content type, schema properties
- **Security Schemes**: Authentication mechanisms from components.securitySchemes
- **Global Security**: Top-level security requirements
- **Per-endpoint Security**: Operation-level security overrides

The parser resolves `$ref` JSON pointers to support schema reuse and modular specifications.

## Scanner

10 independent check functions, one per OWASP API Security Top 10 category:

### API1 - Broken Object Level Authorization (CWE-639)
- **Pattern**: Paths with `{id}` parameters without user-scoping
- **Confidence**: 75%
- **Logic**: Finds all path parameters matching `/{*id*}` and checks if any parameter name contains "user" or "tenant"

### API2 - Broken Authentication (CWE-287)
- **Pattern**: State-changing methods (POST/PUT/DELETE/PATCH) without auth
- **Confidence**: 80-90%
- **Logic**: Checks endpoint auth_required flag, identifies sensitive paths (login, admin, password)

### API3 - Broken Object Property Level Authorization (CWE-200)
- **Pattern**: Sensitive field names in request body schemas
- **Confidence**: 70%
- **Logic**: Scans properties for keywords: password, secret, admin, role, salary, ssn, etc.

### API4 - Unrestricted Resource Consumption (CWE-770)
- **Pattern**: GET endpoints without pagination parameters
- **Confidence**: 65%
- **Logic**: Checks for limit/page/offset/size/per_page parameters

### API5 - Broken Function Level Authorization (CWE-862)
- **Pattern**: Admin/internal/debug paths
- **Confidence**: 70-80%
- **Logic**: Regex matching against /admin, /internal, /debug, /console patterns

### API6 - Sensitive Business Flow Abuse (CWE-284)
- **Pattern**: Payment/order/signup endpoints without auth
- **Confidence**: 72%
- **Logic**: Regex matching against purchase, checkout, payment, transfer patterns

### API7 - Server-Side Request Forgery (CWE-918)
- **Pattern**: URL-type parameters in requests
- **Confidence**: 78%
- **Logic**: Checks parameter names and request body properties for url/webhook/callback/redirect

### API8 - Security Misconfiguration (CWE-16)
- **Pattern**: Missing security schemes, no global security, deprecated endpoints
- **Confidence**: 40-85%
- **Logic**: Multiple sub-checks for different misconfiguration types

### API9 - Improper Inventory Management (CWE-200)
- **Pattern**: Multiple API versions, deprecated endpoints
- **Confidence**: 65-75%
- **Logic**: Regex matching for version prefixes (/v1, /v2), deprecated flag counting

### API10 - Unsafe Consumption of APIs (CWE-918)
- **Pattern**: External URL properties in request bodies
- **Confidence**: 68%
- **Logic**: Checks property names for url/endpoint/webhook keywords

## Risk Engine

### Scoring Algorithm
```
raw_score = sum(count[severity] * weight[severity])
max_possible = total_findings * weight["Critical"]
normalized = min((raw_score / max_possible) * 100, 100)
```

### Severity Weights
| Severity | Weight |
|----------|--------|
| Critical | 25 |
| High | 15 |
| Medium | 8 |
| Low | 3 |
| Info | 1 |

### Floor Rules
- 1+ Critical finding: score >= 80
- 1+ High finding: score >= 60
- 1+ Medium finding (and score < 30): score = 30

### Risk Levels
| Range | Level |
|-------|-------|
| 80-100 | Critical |
| 60-79 | High |
| 30-59 | Medium |
| 10-29 | Low |
| 0-9 | Low Risk |
