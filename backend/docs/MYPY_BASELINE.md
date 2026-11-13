# Mypy baseline

baseline: 140
measured: 2026-11-14 6870f56

Top files:
  app/services/enterprise_service.py: 17
  app/core/execution/execution_runtime.py: 17
  app/core/agent_framework/tests/test_event_bus.py: 16
  app/core/ai_platform/engine.py: 14
  app/core/execution/execution_engine.py: 11
  app/core/execution/workflow_definition.py: 6
  app/core/execution/tasks.py: 6
  app/utils/system_metrics.py: 4
  app/core/execution/workflow_definition.py: 4
  app/core/execution/execution_state.py: 4

Rationale: 140 of these are pre-existing typing debt in the execution engine and service layer,
inherited before CI reached the mypy step (black aborted the job for months). We are fixing them
incrementally; new code must not add errors.
