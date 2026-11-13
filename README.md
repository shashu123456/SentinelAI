# SentinelAI

A production-ready AI-powered API security scanner that detects OWASP API vulnerabilities, runs static application security testing, and performs dependency checks.

[![CI](https://github.com/shashu123456/SentinelAI/actions/workflows/ci.yml/badge.svg)](https://github.com/shashu123456/SentinelAI/actions/workflows/ci.yml)
[![CodeQL](https://img.shields.io/badge/codeql-analysis-enabled-blue.svg)](https://github.com/shashu123456/SentinelAI/tree/main/docs)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/download/releases/3.11/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Try it

1. **Register** — open the app and create an account
2. **New scan** — provide an OpenAPI spec URL or upload a spec file
3. **Report** — view detected findings with severity, CWEs, and remediation hints

Live API: https://sentinelai-api.vercel.app  
Live Web: https://sentinelai-web.vercel.app

---

## Capabilities

| Check Type | Rules / Checks | Description |
|------------|---------------|-------------|
| **OWASP API Security** | 10 checks | API1–API10: injection, authentication, authorization, rate limiting, data validation, etc. |
| **SAST Rules** | 48 rules | Python source-level security checks for hardcoded secrets, injection flaws, unsafe deserialization |
| **Dependency Scanner** | Verified | Cross-references installed packages against known CVE databases |
| **Passive URL checks** | Ongoing | Emitted per-scan for discovered endpoints |

---

## Architecture

```mermaid
graph TD
  subgraph "Frontend (Vite + React)"
    UI -->|OpenAPI spec| API
  end
  subgraph "Backend (FastAPI)"
    API -->|Scan orchestration| Engine
    Engine -->|SAST| Python parser
    Engine -->|OpenAPI analysis| Spec analyzer
    Engine -->|Dep scan| Package index
    Engine -->|Report generation| Markdown/HTML
  end
  subgraph "Data (local SQLite)"
    Engine -->|Results| DB
  end
```

---

## Limitations

- **No live exploitation** — all checks are static/spec-based; nothing is sent to target endpoints
- **Static spec analysis only** — async endpoints, websockets, and runtime behaviour are not analysed
- **Async scans hidden** — background scan status is not persisted across restarts (ephemeral container storage)
- **Vercel function timeout** — 12-second limit may truncate large spec analyses; results may be partial

Deploy: see [docs/DEPLOY.md](docs/DEPLOY.md)

---

## Badges

- CI: [![CI](https://github.com/shashu123456/SentinelAI/actions/workflows/ci.yml/badge.svg)](https://github.com/shashu123456/SentinelAI/actions/workflows/ci.yml)
- CodeQL: [![CodeQL](https://img.shields.io/badge/codeql-analysis-enabled-blue.svg)](https://github.com/shashu123456/SentinelAI/tree/main/docs)
- Python: [![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/download/releases/3.11/)
- License: [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
