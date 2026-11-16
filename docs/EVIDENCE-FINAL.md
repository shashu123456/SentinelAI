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

**PENDING** — see final report.
