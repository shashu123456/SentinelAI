# mypy remediation ledger

Target: `python -m mypy app` clean in CI. Status below reflects the run on
`main` after this pass.

## Environment

| Item | Value |
| --- | --- |
| Local interpreter | Python 3.11.9 (Windows) |
| Local mypy | 2.3.0 (compiled) |
| CI interpreter | Python 3.11 (ubuntu-latest) |
| CI mypy | from `backend/requirements.txt` (`mypy>=1.14.0,<3.0.0`) |
| Config | `backend/pyproject.toml` `[tool.mypy]` — unchanged |
| CI command | `python -m mypy app` (`.github/workflows/ci.yml`, `backend-lint`) |

`ignore_missing_imports = true` and `check_untyped_defs = false` are the repo's
existing settings and were **not** relaxed.

## Baseline

`python -m mypy app --no-error-summary` before any change:

```
Found 129 errors in 30 files (checked 168 source files)
```

Local 129 vs CI 126 is a stub-version delta (platform-specific modules such as
`resource`/`os.getloadavg` exist locally only on POSIX CI). Every error CI
reports is in the local list.

Baseline by code:

| Code | Count |
| --- | --- |
| arg-type | 45 |
| attr-defined | 34 |
| annotation-unchecked (notes) | 33 |
| var-annotated | 25 |
| assignment | 11 |
| union-attr | 5 |
| misc | 3 |
| return-value | 2 |
| operator | 2 |
| valid-type | 1 |
| index | 1 |

## Waves

Each wave was verified with `mypy`, `ruff`, `black` and targeted tests, and
committed separately.

| Wave | Area | Errors |
| --- | --- | --- |
| 1 | `ai_platform/engine.py`, `services/enterprise_service.py` | 129 → 100 |
| 2 | test fixtures, performance counters, knowledge graph, workflow result | 100 → 73 |
| 3 | event bus payload contract, `ScanTask.transition_history`, copilot ordering, POSIX-only metrics | 73 → 53 |
| 4 | execution-state contracts (`ExecutionStateLike`, `ExecutionStateRecord`, `from_dict`) | 53 → 43 |
| 5 | route guards, SQLAlchemy truthiness, quota typing, path selection typing | 43 → 34 |
| 6 | model/typing imports, SARIF typing, defaultdict keys, `getloadavg`, session params | 34 → 17 |
| 7 | remaining None guards, `capabilities` setter, registry return types | 17 → 0 |

Final:

```
Success: no issues found in 168 source files
```

## `# type: ignore` ledger

**Zero.** No `# type: ignore` was added in this pass, and no file-wide ignore
exists in `app/`.

## Real root causes found (not silenced)

* `ExecutionStateMetadata.from_dict` returned the `ExecutionState` **enum**
  and assigned `transition_history` onto it, while its annotation promised
  metadata. It now builds and returns the metadata object.
* `RuntimeMetrics.record_state` and `ExecutionStateRegistry` were annotated
  with the status enum but read `status`/`duration`/`is_running`/`is_terminal`/
  `execution_id`. Their real contract is expressed with narrow `Protocol`s.
* `EventBus.publish_raw` was typed `event_type: EventType, source: str | None`
  while callers pass raw strings and agent objects, and the body already does
  `getattr(source, "id", str(source))`. The signature and `AgentEvent` now say
  so.
* `ScanTask` had `transition_history` assigned by the worker but never declared.
* `ExecutionStateRegistry._store` was typed with the enum, not the records it
  stores.
* `enterprise_service._matches_conditions` did `getattr(finding, field)` with a
  possibly-`None` field name and compared against an arbitrary JSON `value`;
  the field is guarded and the value cast (the operator branch decides its
  shape).
* `system_metrics` assigned `None` to the `resource` module and called
  `os.getloadavg()` unguarded, which is POSIX-only.

## Latent-bug findings (typing fixed, semantics deliberately unchanged)

These are error paths that previously raised `AttributeError`/`TypeError`. They
are guarded so mypy can prove the path, and the guard's semantics were left as
close to the old failure as possible. They are recorded here rather than
silently changing an API.

* `app/api/routes/organizations.py` — `can_add_member`/`can_create_project`
  failure paths dereference `org_repo.get(...)`; if the organization row is
  missing the message now renders `?` instead of crashing.
* `app/services/invitation_service.py`, `app/utils/rbac.py` — the same missing
  organization is asserted, because reaching that branch means the repository
  already returned contradictory data.
* `app/api/routes/ai_platform.py` — `scan_id` is asserted non-null before AI
  analysis; the request schema requires it.
* `app/core/agent_framework/agent_lifecycle.py` — `_on_health_changed` is
  referenced at construction but defined nowhere in the class; it is annotated
  as an optional attribute so runtime behaviour is untouched. Wiring a real
  handler is still open design work.
