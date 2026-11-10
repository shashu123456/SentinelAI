# Release evidence — SentinelAI v1.1.0

Everything below was produced by a command in this repository on the branch
`release/sentinelai-v1.1`. Items that could not be run are listed under
[Not verified](#not-verified) instead of being asserted.

- Date: 2026-11-10
- Branch: `release/sentinelai-v1.1`
- Tip commits checked: `3d1ef53` (code) and `61058b7` (this document). Documentation-only
  commits reproduce the same job conclusions listed below.
- Pull request: [#1](https://github.com/shashu123456/SentinelAI/pull/1) (draft, not merged)

## CI — run 42873263175

Workflow `.github/workflows/ci.yml`, triggered by the pull request. Conclusions
are the ones reported by the Actions API:

- code tip `3d1ef530` → run [42873263175](https://github.com/shashu123456/SentinelAI/actions/runs/42873263175)
- documentation tip `61058b78` → run [42877206618](https://github.com/shashu123456/SentinelAI/actions/runs/42877206618) (identical conclusions)

Table below is run 42873263175.

| Job | Conclusion | Detail |
|---|---|---|
| Backend lint & type check | failure | `black --check app tests` passed, `ruff check app tests` passed, `mypy app` failed with `Found 77 errors in 20 files (checked 140 source files)` |
| Backend tests | success | `779 passed, 2 skipped` in 156.62 s, total coverage 72% |
| Frontend test & build | success | Vitest suite + `npm run build` |
| Secret scanning | success | gitleaks, no findings |
| CodeQL analysis (python) | success | — |
| CodeQL analysis (javascript) | success | — |
| Docker build | skipped | `needs: [backend-lint, backend-tests, frontend-build]`; skipped because the lint job failed |
| Deployment smoke test | skipped | `needs: [docker-build]`; skipped because the Docker job was skipped |

Of the eight jobs in the workflow, five are green, two were skipped and one is
red. The Docker build and the compose smoke test never ran, so container startup
is **not** verified by CI. The single red job is the `mypy` step; `ruff` and
`black` pass on the same tree.

## Local checks

Backend (`cd backend`):

| Check | Result |
|---|---|
| `python -m ruff check app tests` (tracked tree, 176 files) | `All checks passed!` |
| `python -m black --check app tests` (tracked tree, 176 files) | `176 files would be left unchanged` |
| `python -m mypy app` | 77 errors in 20 files — pre-existing, see below |
| `python -m pytest tests/ -q --tb=short --durations=20` | `2 failed, 793 passed, 1 skipped` in 945.64 s — see [Full backend suite](#full-backend-suite) |

Frontend (`cd frontend`):

| Check | Result |
|---|---|
| `npm ci` | 293 packages installed; 13 advisories reported (2 critical) by the registry |
| `npm test` | 25 tests passed in 5 files |
| `npm run build` | built successfully in 25.03 s |

### Full backend suite

The same command CI runs, executed on the development machine:

```
python -m pytest tests/ -q --tb=short --durations=20
```

Result on this development machine: `2 failed, 793 passed, 1 skipped` in
945.64 s.

Both failures are wall-clock assertions in `tests/test_performance_benchmarks.py`:

| Test | Threshold | Measured here |
|---|---|---|
| `TestAPIResponseTimes::test_login_response_time` | login `p95 < 500 ms` | `p95 = 836.2 ms` |
| `TestDatabasePerformance::test_single_record_lookup` | single lookup `p95 < 50 ms` | `p95 = 154.2 ms` |

Both thresholds are met on the CI runner with the same commit (`Backend tests`
job green in runs 42872050648 and 42873263175), so the gap is machine speed
rather than behaviour: a bcrypt-12 password verification alone costs roughly
470–490 ms on this workstation, and the SQLite timing budget is under load from
the rest of the suite. The thresholds were left as they are — no assertion was
relaxed — and the discrepancy is recorded here instead.

The local run also collects more tests than CI because two test modules
(`tests/test_helpers.py`, `tests/test_sast_agent_integration.py`) are present in
the working tree but not tracked in git, so CI never sees them.

## Test-integrity notes

These decisions changed test or application code and are recorded so they can be
reviewed on their own merit.

- **Login rate limit in `conftest.py`.** The suite pins
  `LOGIN_RATE_LIMIT_PER_MINUTE=10`. Removing the pin makes
  `tests/test_auth_hardening.py` fail (`1 failed, 795 deselected`): the test hits
  the limiter instead of the account-lockout path it is about. With the pin the
  429 body is slowapi's `Rate limit exceeded: 10 per 1 minute`, and the test now
  asserts that exact text so the pin cannot silently mask a different rejection.
- **Password-reset token pinning.** `tests/test_auth_hardening.py` pins the
  reset token with `monkeypatch` so the test can assert that the API never echoes
  the token back; the token value itself is not part of the contract.
- **`test_backend_audit.py` environment independence.** The module builds its
  settings with `Settings(_env_file=None, SECRET_KEY="…")` instead of reading the
  developer's `.env`. No assertion was removed or relaxed.
- **Health endpoint.** `/api/v1/health` was slow (~2.1 s, cold) because it
  recomputed system metrics per request. It now serves a cached snapshot
  refreshed off-request and warmed during application startup; measured through a
  real uvicorn server it answers in ~21 ms (p50 17 ms) instead of raising the
  100 ms threshold the test asserts.

## Defects fixed during this release

Each of these was found by running the suite, the linters or CI, and is fixed in
the application code rather than in the checks:

1. `requirements.txt` pinned `packaging<3.0.0`, which made `pip install` fail and
   blocked every backend CI job at install time.
2. `Repository.paginate()` issued `LIMIT/OFFSET` without an `ORDER BY`, so pages
   could repeat or skip rows; it failed as an intermittent audit-log pagination
   failure on CI. It now defaults to descending primary key when the caller
   supplies no order.
3. The response-envelope middleware rewrote `Content-Length` for streamed bodies,
   producing framing errors; entity headers are now skipped.
4. `app/tasks.py` used `time` without importing it; `tracing.py` missed a
   `Callable` import; `app/core/…/workflow_definition.py` had two syntax errors.
5. `backend/pyproject.toml` still listed `plugins = ["sqlalchemy.ext.mypy.plugin"]`
   after SQLAlchemy 2.1 removed that plugin, so `mypy` aborted before checking a
   single file and the lint job failed for the wrong reason.
6. `frontend/src/pages/Dashboard.jsx` had unbalanced JSX, and
   `frontend/src/components/Timeline.jsx` mixed TypeScript syntax into a `.jsx`
   file plus 200 lines of inline CSS (moved to `Timeline.css`).
7. Ten route handlers re-raised `HTTPException` without `from e` (B904), nested
   conditions that could be a single condition (SIM102/SIM103) and ambiguous
   loop variables (E741) — all now clean, with no behaviour change.
8. gitleaks reported four findings that are documentation examples and test
   fixtures (a truncated JWT and API key in `docs/API.md`, the fake
   `sk_live_abcdef1234567890` key that `tests/test_sast.py` asserts the SAST
   scanner detects, and a feature-flag name in `tests/test_saas_platform.py`).
   `.gitleaks.toml` allowlists exactly those paths and values.

## Not verified

- **Type-check gate.** `mypy app` reports 77 pre-existing errors in 20 files
  (35 `arg-type`, 18 `attr-defined`, 8 `var-annotated`, 6 `assignment`,
  5 `union-attr`, 2 `operator`, 2 `misc`, 1 `index`). The release instruction was
  to report the count and stop rather than refactor the codebase, so this is
  reported and not fixed, and the CI lint job stays red as a result.
- **Production deployment.** No deployment to Render (or any other host) was
  performed: no credentials or account access were available in this
  environment. The "Deploy to Render" path in `docs/DEPLOYMENT-GUIDE.md` is
  therefore unexercised for v1.1.0.
- **Benchmarks against Juice Shop / crAPI.** Neither containerized target was
  run, so no scan-timing or detection-rate numbers exist for this release.
- **Docker image build and compose stack.** CI skips both jobs (see the table
  above) and `docker compose up` was not run locally, so the containers are not
  verified to build or start from this commit.
- **Frontend dependency advisories.** `npm ci` reports 13 advisories (2
  critical). No audit fix was applied, since it would change the lockfile and the
  dependency surface beyond this release's scope.
- **`frontend/src/main.jsx` hook usage.** Hooks are invoked at module scope after
  `ReactDOM.render`; the frontend builds and its tests pass, but this is a latent
  runtime problem and is not fixed here.

## Reproduction

```bash
git checkout release/sentinelai-v1.1 && git pull
cd backend
pip install -r requirements.txt
python -m ruff check app tests
python -m black --check app tests
python -m mypy app            # 77 pre-existing errors
python -m pytest tests/ -q --tb=short

cd ../frontend
npm ci && npm test && npm run build
```

CI: `gh api repos/shashu123456/SentinelAI/actions/runs/42877206618/jobs` (tip) or
`gh api repos/shashu123456/SentinelAI/actions/runs/42873263175/jobs` (code tip).
