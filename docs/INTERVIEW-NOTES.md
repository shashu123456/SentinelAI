# Interview notes

Five talking points that map a real decision to a real commit in this repo.

## 1. Three scanners, four doors

The product is deliberately scoped to three input kinds — an API spec, a dependency
manifest, and a source file — behind **one** upload box. A fourth door (live-URL
scanning) and a whole second product (the AgentGuard probe) were cut on purpose:
each adds a page and a claim without adding a reason to use the tool. The Coverage
page states the cut lines in plain language.

## 2. Deterministic rules, not an LLM judge

Scoring comes from fixed rules in `security_engine`, `dep_scanner` and `sast_engine`.
The only place a model is involved is the optional summary, and it is trimmed and
best-effort. Determinism is what makes a score reproducible and an evidence hash
meaningful; an LLM-as-judge would make both flaky.

## 3. Designing around a 10-second serverless ceiling

The API runs on Vercel Hobby (~10 s function limit). Instead of letting a big upload
time out with a 504, code scans are work-capped (200 files / 2 MB) and return
**200 with `partial: true`** plus scanned/skipped counts. The UI shows a partial
banner rather than an error.

## 4. An evidence hash you can re-derive

Every report carries a hash over the scan inputs and findings, shown in monospace
with a copy button. Two runs over the same input produce the same hash — that is the
difference between "trust me" and "verify it".

## 5. The regression I caught in my own performance commit

A perf change started feeding a *trimmed* findings payload into the persistence
layer, which requires `description`/`impact`/`remediation`. Every scan began
returning HTTP 500 "Scan execution failed" and 20 tests failed. The fix pins the
invariant: storage and risk scoring get complete findings; only the AI prompt
payload is trimmed. There is a regression test on the boundary. Catching and
naming your own regression is worth more than shipping a feature.
