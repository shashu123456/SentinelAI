# SentinelAI — Project Details (source of truth)

**Owner:** Shashank Gowda N C  
**Role on project:** Backend & Security Developer  
**Last updated:** 2026-11-19

This is the one file to read when you need to know what SentinelAI is, what is live, what to upload, how to run it, and what not to claim.

---

## 1. What SentinelAI is

SentinelAI is a deployed application-security scanning platform. You upload one of three inputs, it runs a deterministic scanner, normalises the findings, scores risk, stores the result, and produces a report.

It is **not** an AI chatbot product and it does **not** run a hosted LLM in the demo. The "Security Copilot" is rule-based and reads your scan data.

### The three scanners

| Scanner | Upload | What it checks | Engine |
|---|---|---|---|
| **API Spec** | OpenAPI/Swagger `.json`, `.yaml`, `.yml` | Endpoints, auth, object-level access, schema/data exposure, injection risks | `backend/app/core/security_engine` |
| **Dependencies** | `requirements.txt`, `package.json`, `pom.xml`, lockfiles, zip | Package/version CVEs using OSV.dev, with curated fallback | `backend/app/core/dep_scanner` |
| **SAST · Source Code** | `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.go`, `.rb`, `.php`, or zip | Source patterns: secrets, injection, insecure crypto, debug exposure | `backend/app/core/sast_engine` |

**Important:** "Source Code" is the input for SAST. It is **not** a fourth engine. The product has exactly three scanners.

The unified upload service is `backend/app/services/unified_scan.py`; its valid kinds are `spec`, `deps`, `code`.

---

## 2. Live links

- **Web app:** https://sentinelai-web.vercel.app
- **API health:** https://sentinelai-api.vercel.app/api/health
- **API version:** https://sentinelai-api.vercel.app/api/v1/version
- **GitHub:** https://github.com/shashu123456/SentinelAI

Use `/api/health`, not `/health` (the root path returns 404 by design).

### Demo

On the landing page or login page, click **Try the live demo**. It signs in as the seeded `demo` user and opens `/reports`.

The demo account has three scans:

| Scan ID | Kind | Name | Findings | Risk |
|---|---|---|---:|---:|
| 4 | spec | Demo Petstore API | 12 | 80 |
| 5 | deps | demo-requirements.txt | 74 | 80 |
| 6 | code | demo-code.zip | 2 | 60 |

You can export each scan as PDF or JSON.

---

## 3. Sample files for all three scanners

Use these from the repo:

| Scanner | Sample file | Notes |
|---|---|---|
| API Spec | `samples/demo-openapi.yaml` | Minimal deliberately weak OpenAPI demo |
| API Spec (larger) | `samples/vulnerable_api.yaml` | More findings for a fuller report |
| Dependencies | `samples/demo-requirements.txt` | Pinned packages with known CVEs |
| Dependencies | `samples/vulnerable-requirements.txt` | Alternate dependency fixture |
| SAST | `samples/demo-code.zip` | Source zip used by the demo |
| SAST (single file) | `samples/vulnerable-app.py` | Python source with insecure patterns |

The seeded demo scans use the demo fixtures above and show **12 / 74 / 2** findings. Your own uploads may differ slightly because rules and OSV data evolve.

### How to run all three

1. Open https://sentinelai-web.vercel.app
2. Click **Try the live demo** (or sign in normally).
3. Go to **New Scan**.
4. Choose **API Spec** → upload `samples/demo-openapi.yaml` → run.
5. Choose **Dependencies** → upload `samples/demo-requirements.txt` → run.
6. Choose **SAST · Source Code** → upload `samples/demo-code.zip` → run.
7. Open **Reports** → open each scan → check findings → export PDF and JSON.

Upload limits: 5 MB request, up to 200 files in a zip, 2 MB per entry. Oversized uploads return 413; unsupported types return 415; unsafe zips return 400.

---

## 4. Why local login says "Failed to fetch"

The frontend reads its API base from `frontend/.env.development.local`, which currently points at:

```text
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

So when you run `npm run dev` locally, the browser calls **your machine**, not Vercel. If the FastAPI backend is not running on port 8000, login fails at the network layer with **"Failed to fetch"**. It is not a wrong password and not a database problem.

### Recommended: use the deployed app

Open https://sentinelai-web.vercel.app and click **Try the live demo**. Nothing to install.

### If you want local development

Terminal 1 — backend:

```powershell
cd C:\Users\kavitha\OneDrive\Desktop\ai-api-security-scanner\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

If the venv path is different, activate the existing backend virtualenv first. Then verify:

```text
http://localhost:8000/api/health
```

Terminal 2 — frontend:

```powershell
cd C:\Users\kavitha\OneDrive\Desktop\ai-api-security-scanner\frontend
npm run dev
```

Open the Vite URL, then click **Try the live demo**.

If you do not want to run the backend, temporarily point `VITE_API_URL` at the deployed API and restart Vite. Do not commit that change; localhost and Vercel CORS are configured differently.

---

## 5. Architecture

```text
React + Vite (Vercel)
        |
        |  HTTPS, JWT
        v
FastAPI (Vercel serverless)
        |
        +-- unified_scan.py  -> spec | deps | code
        +-- security_engine  -> OpenAPI/API checks
        +-- dep_scanner      -> OSV.dev + fallback
        +-- sast_engine      -> source rules
        +-- risk engine      -> normalised score
        +-- report service   -> PDF / JSON
        |
        v
Neon Postgres
  users, scans, findings, ai_analysis,
  transition_history, authorized_use_acceptances
```

Key facts:

- Auth uses JWT; the frontend stores `sentinelai_token` and `sentinelai_user`.
- All API JSON responses are enveloped as `{success, data, meta}`. The frontend unwraps this centrally in `frontend/src/services/api.js` (`unwrapEnvelope`). This was the root cause of the earlier broken demo/report screens.
- Production database is Neon Postgres; the backend reads `DATABASE_URL`.
- Vercel deployment retention is separate from Neon. Deleting an old Vercel deployment does not delete Neon rows, GitHub code, or the live site.
- Reports are available at `/api/scans/{id}/report/pdf` and `/api/scans/{id}/report/json`. The `/api/v1/scans/.../report/*` path returns 404.

---

## 6. Verification and evidence

- Code fix commit: `342b29b` — unwrap response envelope; repair demo, reports, scan detail.
- Visual pass commit: `bc798cf` — display type system and hierarchy.
- Docs sync commit: `ed3fb4f` — preview and evidence aligned.
- CI run `44546076930` on `ed3fb4f`: **8/8 success** (Secret scanning, Frontend test & build, Backend tests, CodeQL js, Backend lint & type check, CodeQL py, Docker build, Deployment smoke).
- Tests: **1,090 backend passed / 2 skipped / 17 deselected**; **35 frontend passed**.
- Live API version returned `ed3fb4f` at the last check; the shipped frontend bundle is `index-XGuVbAcl.js` from the `342b29b` code build.
- Screenshots: `docs/screenshots/` includes landing, mobile landing, reports, reports mobile, scan detail, scan detail mobile, scans-new, coverage, login-demo, beta dashboard, copilot, badge crops, and historical before/after captures.

Detailed evidence: `docs/EVIDENCE-FINAL.md`.  
Recruiter preview: `docs/PROJECT-PREVIEW.md`.

---

## 7. What not to claim

Do not say any of these about SentinelAI:

- "four engines" or "four security engines"
- "enterprise multi-tenancy"
- "6-tier RBAC"
- "Ollama-backed copilot" (the demo copilot is rule-based; `/ai/*` exists but the UI does not call it)
- "90+ API endpoints" as a shipped product feature
- "scheduled scans / templates / policies / webhooks / compliance center" as shipped demo features
- "live URL scanning"
- "autofix" or "exploitation"

Safe claims:

> Deployed application-security scanning platform with three scanners — OpenAPI/Swagger analysis, OSV-backed dependency CVE scanning, and rule-based SAST for source code. Normalised findings, CVSS-style risk scoring, rule-based Security Copilot, PDF/JSON reports, JWT auth, Postgres, Docker, GitHub Actions, CodeQL and Gitleaks.

---

## 8. CV and supporting files

Corrected CV sources:

- `C:\Users\kavitha\OneDrive\Desktop\my-resume\TARGET_CV.md`
- `C:\Users\kavitha\OneDrive\Desktop\my-resume\SHASHANK_GOWDA_NC_combined-resume.md`
- Other target variants and notes in the same folder were propagated to the same three-scanner truth.

Exported PDFs (if present):

- `C:\Users\kavitha\OneDrive\Desktop\Shashank-resumes\`

The CV must not repeat the claims in section 7. If a claim cannot be demonstrated live, remove it or label it as planned.

---

## 9. Other projects on the CV

These are listed on the CV and are **not** part of this repository. Verify their repos before making detailed claims.

| Project | CV description | Status |
|---|---|---|
| **Fluxora** | Electron local-first AI desktop app, 304 tests, Windows installer | CV project |
| **EcoMind AI** | Ten-stage energy intelligence platform | CV project |
| **TrustGuard** | Zero Trust IoT monitoring; 3rd Prize, VIVEKA-26 hackathon | CV project |
| **SentinelCore** | Planned capstone | Planned — do not present as shipped |

---

## 10. Quick answers

**What is this project?** A deployed scanner for API specs, dependencies, and source code.

**How many scanners?** Three: spec, deps, SAST.

**Is "Source Code" a fourth scanner?** No. It is the SAST input.

**Does it use an LLM?** Not in the demo. The Copilot is rule-based. An optional self-hosted Ollama path exists in the backend but the UI does not call it.

**Where is the database?** Neon Postgres in production.

**Why did login fail locally?** The local frontend points at `http://localhost:8000`; the backend was not running, so the browser reported "Failed to fetch".

**What should I show a recruiter?** Live landing → Try demo → Reports → three scans → open a scan → export PDF. Then the CI/evidence page.
