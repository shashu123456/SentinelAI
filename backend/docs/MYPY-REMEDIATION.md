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

## Wave 8 — the CI-only error (`_scope`)

The local run above was green, but CI run `43920459529` on `4329147` still
failed `backend-lint` with exactly one error:

```
app/core/agent_framework/agent_registry.py:57: error: "BaseAgent" has no attribute "_scope"  [attr-defined]
Found 1 error in 1 file (checked 168 source files)
```

Why CI saw it and the local run did not: the earlier local pass reused mypy's
incremental cache, so the already-cached modules were not re-checked. A fresh
checkout has no cache. **`--no-incremental` is therefore the proof command**, and
no local "clean" result counts without it.

The error was real, not a version mismatch: `AgentRegistry.register` assigns the
registry scope onto the agent (`agent._scope = scope`), but `BaseAgent` never
declared the attribute, so mypy treated `agent._scope` as an undeclared member of
the base class rather than a typed one.

Fix (`app/core/agent_framework/base_agent.py`): declare the member **annotation
only**, with the `RegistryScope` import guarded so no runtime import cycle is
created.

```python
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.agent_framework.agent_registry import RegistryScope


class BaseAgent(abc.ABC):
    """...unchanged class docstring..."""

    # Registry scope, assigned by AgentRegistry.register(). Annotation only: an
    # agent that was never registered has no _scope attribute, and the registry
    # reads it with getattr(agent, "_scope", RegistryScope.GLOBAL).
    _scope: RegistryScope | str
```

There is deliberately **no `= None` default**. `AgentRegistry.get_agents_by_scope`
reads the scope with `getattr(agent, "_scope", RegistryScope.GLOBAL)`, so an
unregistered agent is treated as GLOBAL. A `None` default would give the attribute
a value before registration and silently drop that agent out of GLOBAL scope
queries — a typing change that alters runtime behaviour. An annotation-only
declaration adds no attribute, so `hasattr(BaseAgent, "_scope")` stays `False` and
the fallback still returns `RegistryScope.GLOBAL`.

The annotation needs no quotes because the module already uses
`from __future__ import annotations`; the `if TYPE_CHECKING` guard keeps
`agent_registry` out of the runtime import graph. No `setattr`, no `cast`, no
`# type: ignore`, and no relaxation of `pyproject.toml`.

Proof on the committed file (`base_agent.py` at the fix commit):

```
$ python -c "hasattr/getattr check"
has _scope attr: False
getattr fallback: RegistryScope.GLOBAL

$ python -m mypy app --no-incremental
Success: no issues found in 168 source files
MYPY_EXIT=0

$ python -m ruff check app tests
All checks passed!
RUFF_EXIT=0

$ python -m black --check app tests
219 files would be left unchanged.
BLACK_EXIT=0

$ python -m pytest -q app/core/agent_framework/tests
86 passed in 0.69s

$ python -m pytest -q app/core/agent_framework/tests/test_agent_registry.py \
    app/core/agent_framework/tests/test_agent_factory.py \
    app/core/agent_framework/tests/test_plugin_loader.py
50 passed in 0.29s
```

The change is annotation-only, so the full-suite proof in `docs/EVIDENCE-FINAL.md`
(`1090 passed, 2 skipped, 17 deselected`) still describes this code.

## Ignore ledger (final)

Zero `# type: ignore` comments added across all eight waves. The 13 that already
exist are unchanged and confined to three files (`api/errors.py` ×5,
`core/execution/execution_state.py` ×4, `core/execution/workflow_definition.py` ×4);
`git log -S"type: ignore" cb36ce7..HEAD -- backend/app` returns no commit that
changes that count. `pyproject.toml` `[tool.mypy]` is unchanged from baseline
(`ignore_missing_imports = true`, `check_untyped_defs = false`).
