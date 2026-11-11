# `sentinel` CLI

The developer CLI runs scans **locally** (no server, database, or network) and
drives a **running API** for uploads, reports, and inspection.

```bash
make cli ARGS="scan samples/vulnerable_api.yaml"
scripts/sentinel scan samples/vulnerable_api.yaml      # launcher, no venv activation
backend/venv/Scripts/python -m tools.sentinel_cli ...  # explicit interpreter
```

> Optional: `alias sentinel="$PWD/scripts/sentinel"` for a global command.

---

## Commands at a glance

| Command | Needs API? | Purpose |
|---------|-----------|---------|
| `scan` | no | scan local OpenAPI specs |
| `demo` | no | seed demo user, org, project, scans |
| `doctor` | no | environment diagnostics |
| `login` / `logout` / `whoami` | yes | manage the stored session |
| `health` | yes | dependency health report |
| `upload` | yes | upload a spec and scan server-side |
| `scans` | yes | list scans |
| `show` | yes | one scan with findings |
| `report` | yes | download JSON/PDF report |
| `open-playground` | no | print the playground URL |

Every command supports `--help`.

---

## Local scanning

```bash
sentinel scan samples/vulnerable_api.yaml
sentinel scan samples/*.yaml --all
sentinel scan spec.json --format json -o findings.json
sentinel scan spec.yaml --format markdown -o report.md
sentinel scan spec.yaml --format sarif -o results.sarif
sentinel scan spec.yaml --fail-on high        # CI gate, exit 1 on High+
```

```
ShopEasy E-Commerce API
  source   samples/vulnerable_api.yaml
  version  2.1.0
  routes   19
  findings 63

  ████████████████████████░░░░░░ 80/100  Critical

  Critical 12  High     25  Medium   26

#    SEVERITY  FINDING                             ENDPOINT                      CVSS
---  --------  ----------------------------------  ----------------------------  -----
1    Critical  Broken Authentication - Unprotect...  POST /api/v1/orders           8.8
```

| Flag | Values | Notes |
|------|--------|-------|
| `--format` | `table` (default), `json`, `markdown`, `sarif` | SARIF 2.1.0 for GitHub code scanning |
| `-o, --output` | file path | writes the chosen format to disk |
| `--all` | flag | show every finding, not the top 10 |
| `--fail-on` | `none` (default), `low`…`critical` | non-zero exit for CI |
| `-v, --verbose` | flag | full detail (description, evidence, remediation) |

`scan` uses the same engines as the API, so a local result matches a server
scan of the same spec. It costs ~300ms and needs no Ollama.

### JSON shape

```json
{
  "api_title": "ShopEasy E-Commerce API",
  "api_version": "2.1.0",
  "total_endpoints": 19,
  "findings": [{ "vulnerability_name": "…", "severity": "Critical", "cvss_score": 8.8 }],
  "risk": { "score": 80, "level": "Critical", "critical_count": 12 },
  "source": "samples/vulnerable_api.yaml",
  "elapsed_ms": 280.4
}
```

---

## Demo data

```bash
sentinel demo
```

Creates (idempotently) `demo / demo1234`, organization *Demo Security*, project
*Core Payments API*, and one scan per `samples/*.yaml`. The AI step is pointed
at a closed port so seeding never waits on Ollama.

Re-running only adds scans that do not exist yet.

---

## Environment diagnostics

```bash
sentinel doctor
sentinel doctor --stats     # repository size / file counts
```

Exit code `1` when something must be fixed (`0` with warnings only).

---

## Talking to a running API

```bash
# 1. Log in (stored in ~/.sentinelai/config.json, mode 0600)
sentinel login --url http://localhost:8000
#   Username: demo
#   Password: demo1234

sentinel whoami
sentinel health
sentinel health --json

# 2. Run a server-side scan
sentinel upload samples/vulnerable_api.yaml --name "ShopEasy v2"
sentinel upload spec.yaml --org 1

# 3. Inspect results
sentinel scans --limit 10
sentinel show 3 --all
sentinel report 3 --format pdf -o report.pdf
sentinel report 3 --format json -o report.json

# 4. Forget the session
sentinel logout
```

### Credentials and configuration

| Source | Variable | Notes |
|--------|----------|-------|
| env | `SENTINEL_API_URL` | overrides the stored base URL |
| env | `SENTINEL_TOKEN` | overrides the stored token (CI-friendly) |
| env | `SENTINEL_CONFIG` | alternate config file path |
| file | `~/.sentinelai/config.json` | written by `login`, `0600` |

Environment variables win, so CI never needs credentials on disk:

```bash
SENTINEL_API_URL=https://sentinel.example.com SENTINEL_TOKEN=$TOKEN \
  sentinel scans --json
```

---

## CI example

```yaml
- name: Scan the API spec
  run: |
    python -m tools.sentinel_cli scan openapi.yaml \
      --format sarif -o results.sarif --fail-on high

- name: Upload SARIF
  if: always()
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

---

## Design notes

- **Two modes, one binary.** Local mode imports the backend engines lazily; the
  remote mode uses only the standard library, so it also works from a machine
  that never ran `make setup`.
- **No silent successes.** Every failure prints the server's own message and
  exits non-zero. Network errors name the URL and the fix.
- **ASCII fallback.** Consoles that cannot encode box-drawing characters get a
  plain-text report instead of a `UnicodeEncodeError`.
- **Secrets stay out of git.** Tokens live outside the repository, are never
  printed, and are revoked with `logout`.
