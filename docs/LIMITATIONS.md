# Limitations

SentinelAI is a static-analysis scanner with three deterministic engines. This file
states plainly what it does **not** do so the Coverage page and the README never
over-claim.

## Not a pentest tool

- **No exploitation.** It does not send exploit payloads, prove auth bypass, or
  demonstrate impact against a running system.
- **No fuzzing.** Inputs are not mutated and replayed against a target.
- **No automatic fixing.** A finding includes a fix *instruction*; the tool never
  edits or patches your code.

## Three input kinds only

| Kind | Accepted | Engine |
|---|---|---|
| `spec` | OpenAPI/Swagger `.json`, `.yaml`, `.yml` | `security_engine` + `risk_engine` |
| `deps` | `requirements.txt`, `package.json`, `pom.xml`, lockfiles | `dep_scanner` + OSV.dev |
| `code` | single source file or small `.zip` | `sast_engine` |

- **No full-repository scanning.** Archive scans are capped at 200 source files /
  2 MB; beyond that the scan returns `partial: true` with scanned/skipped counts.
- **No live-URL scanning.** The tool reads an uploaded file; it never sends traffic
  to a host you name.

## Dependency data

- Source: live **OSV.dev** (`api.osv.dev`) merged with a small curated fallback
  table. If OSV is unreachable the curated table is used and a warning is recorded;
  the scan does not fail.
- **Staleness:** results are cached in memory for up to 1 hour, so a brand-new
  advisory can lag by up to an hour.
- Supported ecosystems: PyPI, npm, Maven. Manifests for other ecosystems are skipped
  with a recorded reason.

## Serverless ceiling

- The API runs on Vercel with a ~10 s function budget. Scans are work-capped so a
  large input returns **200 with `partial: true`** rather than a 504. A partial
  report lists how many files were scanned and skipped.

## SAST is pattern-based

- The source scanner matches known-dangerous patterns (command injection, SQL
  injection, XSS, hardcoded secrets, weak crypto, unsafe deserialization, path
  traversal, SSRF). It does **not** perform full data-flow or taint analysis.
- **False positives and false negatives are expected.** Treat a finding as a lead to
  verify, not a verdict.

## AgentGuard (prompt-injection probe) — not enabled

- This build does **not** ship the AgentGuard prompt-injection probe. It is listed
  as "Not enabled" on the Coverage page and is not reachable from the app.

## Trust and data

- Uploaded files are deleted immediately after the scan; stored specs are purged
  after 24 hours (lazily, on read).
- Only outbound call: `api.osv.dev`. No LLM call is made by the product.
- Scanning requires accepting the authorized-use terms: only scan material you own
  or have written permission to test.
