# AgentGuard — status

**Status: NOT ENABLED in this build.**

AgentGuard was planned as an optional prompt-injection probe for agent endpoints
(not one of the three scanners). The source modules for it were never committed to
`main`; only partial CLI/router wiring exists in a local git stash. Because the
engine, corpus and adapter are not present on disk, AgentGuard is **not** wired into
the API, has no routes, and is shown as **"Not enabled"** on the Coverage page.

## What it would have been

- 40 deterministic cases across 6 injection classes, each with a unique canary.
- Deterministic verdicts (canary leaked → fail; refusal → pass; otherwise
  indeterminate), with indeterminate cases excluded from the score.
- Score `100 * passed / (passed + failed)` with letter grades, and a reproducible
  evidence hash.

## Why it is cut

Shipping a half-restored probe would mean either a broken route or a score with no
corpus behind it. Both are worse than an honest "not enabled". The runbook
explicitly marks Phase 7 as cuttable.

## What this means for claims

Do **not** claim AgentGuard is available, tested, or deployed. The product's promise
is three scanners and one upload box; AgentGuard is not part of it in this build.
