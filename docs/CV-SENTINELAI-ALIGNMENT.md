# CV ↔ SentinelAI alignment

This sheet maps typical CV wording about SentinelAI onto what the deployed project
actually demonstrates. It is documentation only — no CV file in this repository is
edited.

Product truth: three scanners (OpenAPI spec, dependency manifest, SAST/source code),
deterministic rules, rule-based Copilot, no hosted LLM, no live-URL scanning, no
autofix, AgentGuard not enabled.

| CV claim | What the live product actually shows | Action |
|---|---|---|
| "Four engines" / "four scanners" | Three scanners: `spec`, `deps`, `code`. "Source Code" is the SAST input, not a fourth engine. `docs/LIMITATIONS.md` states the three kinds and their engines. | **Replace** with "three deterministic scanners". |
| "AI-powered platform" / "Ollama-backed Copilot" | The Copilot is rule-based: `app/core/copilot/` has no HTTP client. Optional Ollama support exists only on the `/ai/*` platform endpoints, which the UI never calls. | **Remove** the AI/Ollama claim. Say "rule-based Security Copilot". |
| "Enterprise multi-tenancy" | `Organization`, `Project`, and `OrganizationMember` models plus org/project routes exist in `backend/app/models/models.py` and `backend/app/api/routes/`. The demo is a single read-only user session; nothing in the live demo exercises tenant isolation. | **Qualify**: "organisation/project data model with role-scoped routes" — do not claim live multi-tenant isolation. |
| "6-tier RBAC" | `ORG_ROLES` has 5 roles (`owner`, `admin`, `security_engineer`, `developer`, `viewer`); `PROJECT_ROLES` has 4; `SUBSCRIPTION_TIERS` has 4 (`free`, `starter`, `professional`, `enterprise`). There is no 6-tier role ladder. | **Correct** to "5 organisation roles and 4 project roles". |
| "90+ endpoints" | 182 route decorators (`@router.get|post|put|patch|delete`) across the routers in `backend/app/api`. | **Keep, or strengthen**: "180+ HTTP route handlers". |
| "Scheduled scans, scan templates, webhooks, compliance centre" | Routes exist in the app under `/beta` (`scheduled-scans`, `templates`, `webhooks`, `compliance`, `policies`). They are outside the golden path, are not part of the demo, and are not covered by the product pages used in evidence. | **Don't list as shipped features.** At most: "Beta-area scaffolding for scheduled scans and webhooks". |
| "1090 tests" | Backend suite: 1,090 passed / 2 skipped in the last full local run (`docs/EVIDENCE-FINAL.md` §7); the CI `Backend tests` job is green. Frontend: 35/35. | **Keep**, scope it: "1,090 backend tests; 35 frontend tests". |
| "CI/CD pipeline" | GitHub Actions run 44347054492 on `6faabf3`: backend tests, backend lint & type check (mypy, ruff, black), frontend test & build, CodeQL python, CodeQL javascript, secret scanning (Gitleaks), Docker build, deployment smoke — 8/8. | **Keep** — this is well evidenced. |
| "OSV.dev integration" | The dependency scanner calls `api.osv.dev` for PyPI, npm and Maven advisories, with a curated fallback when OSV is unreachable. | **Keep**, note the fallback. |
| "PDF/JSON reporting" | Every scan card offers PDF and JSON export; the scan detail page has the same two actions. | **Keep**. |
| "Trust / authorization gate" | `/authorized-use` page plus an "I am authorized to scan this material" checkbox before a scan can start. | **Keep**. |
| "CVSS scoring" | Findings carry a CVSS-style numeric score and severity; the risk engine produces a 0–100 risk score and level. It is not a certified CVSS calculator. | **Keep** as "CVSS-style score". |

## Ready-to-paste bullets

Each bullet below is true for the deployed project at `a38693e` / `6faabf3`.

- Built and deployed **SentinelAI**, a full-stack application-security scanner
  (React 18 + Vite, FastAPI, SQLAlchemy, PostgreSQL) that analyzes OpenAPI specs,
  dependency manifests and source code with three deterministic scanners.
- Implemented 10 OWASP API Top 10 checks (API1–API10), 48 SAST pattern rules across
  Python/JavaScript/Java, and dependency scanning against live OSV.dev advisories,
  normalizing every result into severity, CWE and a CVSS-style score.
- Designed the reporting pipeline that turns raw findings into a prioritized,
  filterable report with a remediation instruction per finding and PDF/JSON export.
- Shipped a rule-based Security Copilot and an authorization/trust gate, and kept the
  product honest about its limits (no live-URL scanning, no autofix, no hosted LLM).
- Built CI/CD on GitHub Actions — 1,090 backend tests, 35 frontend tests,
  mypy/ruff/black, CodeQL (Python + JavaScript), Gitleaks, Docker build and a
  post-deploy smoke test — currently 8/8 green.
- Deployed the frontend and API separately on Vercel against a Neon PostgreSQL
  database, with environment-scoped configuration and documented limitations.

## Claims to avoid until they are demonstrated

- "Enterprise multi-tenant SaaS" — the data model exists, the demo does not prove it.
- "6-tier RBAC" — the role constants are 5 + 4, not 6.
- "AI/LLM-powered analysis" — the shipped Copilot is rule-based.
- "Real-time or scheduled scanning" — the demo runs an on-demand file scan only.
- "Compliance certification" — the Compliance page is Beta scaffolding, not an audited
  control set.
