# Final evidence

All figures below were produced by the commands shown. Where a command has not
been run yet, the item is marked **PENDING** — nothing here is asserted without
output.

---

## 0. Truth audit (this session)

A previous session reported Phases 5–12 complete and deployed. That report was
**false**. Verified at session start:

| Claim from prior summary | Reality (verified) |
|---|---|
| HEAD after all phases | HEAD was `92a05d3` (OSV only); no later commit existed |
| Coverage / BetaBanner / `/beta` routes | absent; `App.jsx` had 33 top-level routes |
| Design system done | only an untracked `tokens.css` + 2 CSS colour swaps |
| AgentGuard 40 cases | `agent_guard/` held only `.pyc`; source was not on disk |
| Demo / trust / honesty | no seed script, no demo-login, no LIMITATIONS/EVIDENCE docs |
| Deployed SHA matches HEAD | live `/api/v1/version` was `cce6a8e`; HEAD `92a05d3` |
| CI green | latest runs failing |

This file is the corrected record.

---

## 1. Baseline test run (before this session's changes)

Command:
```
cd backend
python -m pytest -q --durations=20
```
Result:
```
1083 passed, 2 skipped, 17 deselected, 773 warnings in 1635.12s (0:27:15)
```

---

## 2. Backend changes this session, with targeted tests

Command:
```
cd backend
python -m pytest tests/test_osv_client.py -q --durations=0
```
Result: `39 passed, 1 skipped in 2.82s`

Command:
```
python -m pytest tests/test_redaction.py tests/test_trust_gate.py -q
```
Result: `7 passed` (redaction masking + authorized-use gate + delete-data)

Command:
```
python -m ruff check app/api/routes/account.py app/utils/redaction.py \
  app/api/routes/auth.py app/services/scan_service.py app/api/routes/scans.py \
  app/models/models.py app/config.py scripts/seed_demo.py \
  tests/test_redaction.py tests/test_trust_gate.py \
  alembic/versions/j8k9l0m1n2o3_add_authorized_use_acceptances.py
```
Result: `All checks passed!`

---

## 3. Frontend build

Command:
```
cd frontend
npm run build
```
Result (final build):
```
✓ built in 35.31s
```

Stray-hex check on the golden-path scope (NewScan, ReportCenter, Coverage, Navbar):
```
pages/NewScan.css: 0
pages/ReportCenter.css: 0
pages/Coverage.css: 0
components/Navbar.css: 0
components/Navbar.jsx: 0
pages/Coverage.jsx: 0
```

---

## 4. Full suite after all changes

Command:
```
cd backend
python -m pytest -q --durations=20
```
Result:
```
1090 passed, 2 skipped, 17 deselected, 785 warnings in 1580.05s (0:26:20)
```

Baseline before this session was 1083 passed; the +7 are the new redaction and
trust-gate tests. Zero failures, zero errors.

---

## 5. Deployment

Live targets: API `https://sentinelai-api.vercel.app`, web
`https://sentinelai-web.vercel.app`. Vercel project ids: `sentinelai-api`
(`prj_tW6GRKaF7Yue2DAhm4QpsEKyXuOc`), `sentinelai-web`, both under scope
`shashu1`.

### 5.1 Production schema repair (additive only)

The production database was recorded at an older Alembic revision
(`h6i7j8k9l0m1`) and was missing `scans.kind`, `findings.source`, and the
`authorized_use_acceptances` table. Repair applied out of band, then again on
every startup by `ensure_runtime_schema()`
(`backend/app/database/database.py`). Only `CREATE TABLE IF NOT EXISTS`,
`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS` are used; nothing is
dropped or rewritten.

```
scans.kind now: True
findings.source now: True
authorized_use_acceptances now: True
```

While seeding, Alembic also advanced the recorded revision normally:

```
INFO  [alembic.runtime.migration] Running upgrade h6i7j8k9l0m1 -> i7j8k9l0m1n2, add scan.kind and finding.source
```

### 5.2 Deployed commit

```
$ curl -s https://sentinelai-api.vercel.app/api/v1/version
{"success":true,"data":{"commit":"769d7e2aab7ba7bfddf159999f7b5a4eb809d064","env":"production","build":"769d7e2"},"meta":null}
```

The `commit` field equals `git rev-parse HEAD` for the pushed revision at the
time of this run.

### 5.3 Health endpoints

```
/api/health        {"status":"healthy"} HTTP 200
/api/v1/health     {"success":true,"data":{"status":"healthy","version":"1.0.0",...}} HTTP 200
/api/v1/live       {"success":true,"data":{"status":"alive","uptime_seconds":186.0,...}} HTTP 200
/api/v1/ready      {"success":true,"data":{"status":"ready",...}} HTTP 200
```

### 5.4 Routes published in the live OpenAPI document

Selected paths returned by `GET /openapi.json` (full document lists 170):

```
/api/account/authorized-use
/api/account/delete-data
/api/auth/demo-login
/api/auth/register
/api/auth/login
/api/scans/upload
/api/scans/upload/async
/api/v1/dashboard/overview
/api/v1/version
```

### 5.5 Trust gate, end to end on production

A throwaway account was registered against production; output trimmed to the
relevant lines.

```
=== register ===
{"access_token":"<redacted-jwt>","token_type":"bearer","user":{"id":6,"username":"evid1794830408",...}}
HTTP 201
=== account/authorized-use GET (before accepting) ===
{"accepted":false,"accepted_at":null,"version":"1","text":"Only scan material you own or have written permission to test."}
HTTP 200
=== upload BEFORE acceptance ===
{"detail":"authorization_required"}
HTTP 403
=== POST acceptance ===
{"accepted":true,"accepted_at":"2026-11-16T12:00:12.511925","version":"1",...}
HTTP 200
```

So the upload gate is enforced on the deployed service, not only in tests.

### 5.6 Real scans of the bundled samples, on production

```
=== kind=deps (samples/vulnerable-requirements.txt) ===
{"id":2,"api_name":"vulnerable-requirements.txt","total_vulnerabilities":67,"risk_score":80,"risk_level":"Critical","status":"completed","kind":"deps","counts_by_source":{"deps":67}}
HTTP 200
=== kind=code (samples/vulnerable-app.py) ===
{"id":3,"api_name":"vulnerable-app.py","total_vulnerabilities":3,"risk_score":86,"risk_level":"Critical","status":"completed","kind":"code","counts_by_source":{"code":3}}
HTTP 200
```

`kind` and `counts_by_source` in these responses prove the repaired
`scans.kind` and `findings.source` columns are in use at runtime.

### 5.7 Oversize upload

```
=== 5MB body ===
HTTP/1.1 413 Request Entity Too Large
Content-Type: text/plain; charset=utf-8
X-Vercel-Error: FUNCTION_PAYLOAD_TOO_LARGE
Request Entity Too Large
```

Recorded honestly: on Vercel the platform request-body ceiling rejects the
upload before the application's own 5 MB check runs, so the 413 comes from
Vercel rather than from `MAX_UPLOAD_SIZE_MB`. The application-level check is
covered by the test suite.

### 5.8 Demo account

Seeded with `scripts/seed_demo.py` (refuses to run without
`SENTINEL_DEMO_PASSWORD`):

```
Created demo user demo <demo@sentinelai.dev>
Seeded spec scan #4 (12 findings)
Seeded deps scan #5 (74 findings, partial=False)
Seeded code scan #6 (2 findings, partial=False)
Demo account ready: 3 completed scan(s).
```

Live demo path:

```
=== POST /api/auth/demo-login ===
{"access_token":"<redacted-jwt>","token_type":"bearer","user":{"id":7,...}}
=== GET /api/scans/ (demo) ===
count: 3
  6 code demo-code.zip 2 None
  5 deps demo-requirements.txt 74 None
  4 spec Demo Petstore API 12 None
=== GET /api/scans/4/report/json ===
json HTTP 200 bytes=18876
{"api_name": "Demo Petstore API", "kind": "spec", "counts_by_source": {"spec": 12}, ...}
=== GET /api/scans/4/report/pdf ===
pdf HTTP 200 bytes=27892 ctype=application/pdf
%PDF-
=== GET /api/v1/dashboard/overview ===
{"success":true,"data":{"total_scans":3,"completed_scans":3,"total_vulnerabilities":88,"average_risk_score":73.3,...}}
HTTP 200
```

CORS for the deployed web origin, which the demo button relies on:

```
OPTIONS /api/auth/demo-login  Origin: https://sentinelai-web.vercel.app
HTTP/1.1 200 OK
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: https://sentinelai-web.vercel.app

POST /api/auth/demo-login  Origin: https://sentinelai-web.vercel.app
HTTP 200
Access-Control-Allow-Origin: https://sentinelai-web.vercel.app
```

### 5.9 Deployed frontend

Every golden-path route returns the SPA shell (HTTP 200, one `#root` node):

```
/                      HTTP 200 root=1
/scans/new             HTTP 200 root=1
/reports               HTTP 200 root=1
/coverage              HTTP 200 root=1
/privacy               HTTP 200 root=1
/beta/authorized-use   HTTP 200 root=1
/beta/coverage         HTTP 200 root=1
/terms                 HTTP 200 root=1
```

The served bundle contains the new pages and calls the live API:

```
asset: /assets/index-EXyO2R6v.js
contains: "Authorized use"
contains: "Coverage"
contains: "sentinelai-api.vercel.app"
contains: "demo-login"
```

Vercel `vercel ls sentinelai-web` shows the newest production deployment
`● Ready` with a 26–27 s build.

### 5.10 Commit deployed after the demo-credential fixes

```
fix(config): trim whitespace from demo credential env values   -> 769d7e2
fix(db): idempotent additive schema repair for deployment drift -> ed87343
```

The whitespace trim was required because secrets added through the CLI carried
a trailing newline; the demo email lookup then missed and the endpoint reported
`Demo account is unavailable` instead of the configuration problem.

---

## 6. CI status

`gh run list` today (most recent first):

```
2026-11-16T12:20  failure  769d7e2  fix(config): trim whitespace from demo credential env values
2026-11-16T11:55  failure  ed87343  fix(db): idempotent additive schema repair for deployment drift
2026-11-16T11:28  failure  e2a8590  docs: record baseline, targeted tests, and full-suite evidence
2026-11-13T21:18  failure  cce6a8e  fix(ruff): clear remaining F841/F841 warnings in b
2026-11-13T20:51  failure  7611578  docs(ratchet): add MYPY_BASELINE and mypy gate; ci
... (every run back to 2026-11-12 is also `failure`)
```

The workflow is red on every recorded commit, including commits from before this
session, so CI was already failing when this work started.

What this session changed about the failure:

* `python -m black --check app tests` failed on 14 files; formatted all of them.
  It now reports `219 files would be left unchanged.` and `black_exit=0`.
* The remaining failures are pre-existing and outside this session's change:
  `python -m ruff check app tests` still reports unused imports in
  `app/core/execution/tests/`, and `python -m mypy app` reports
  `Found 129 errors in 30 files`. Both are staged remediation, not something to
  fix by loosening the gate.

Verified locally after formatting:

```
python -m ruff check <files touched this session>   -> All checks passed!
python -c "import app.main"                          -> import app.main OK
python -m pytest -q tests/test_trust_gate.py tests/test_redaction.py
                                                    -> 7 passed
```
