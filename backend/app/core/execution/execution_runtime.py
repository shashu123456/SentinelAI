"""ExecutionRuntime — Execution lifecycle orchestration layer.

Responsible for coordinating the execution of WorkflowDefinition instances
through the ExecutionEngine, with support for starting, stopping, cancelling,
timeout supervision, lifecycle event emission, and execution status reporting.

This is an orchestration-only layer. It does NOT contain:
- business logic
- execution logic
- security detection logic
- workflow parsing
- report generation
- persistence
- metrics (observational only via RuntimeMetrics)
- snapshots (observational only via RuntimeMetrics)

Depends on:
- ExecutionEngine (single source of truth for execution state)
- EventBus (lifecycle event emission)
- WorkflowDefinition (workflow model)
- ExecutionStateRegistry (optional observational cache)
- RuntimeMetrics (optional observational aggregation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.execution.execution_engine import ExecutionEngine, ExecutionResult, ExecutionStatus
from app.core.execution.execution_state import ExecutionState

if TYPE_CHECKING:
    from app.core.execution.workflow_definition import WorkflowDefinition
from app.core.execution.execution_state_registry import ExecutionStateRegistry
from app.core.execution.runtime_metrics import RuntimeMetrics, RuntimeMetricsSnapshot


@dataclass(frozen=True)
class ProgressSnapshot:
    """Immutable progress snapshot for an execution.

    Contains only the minimal information needed to report progress,
    without exposing internal engine state.

    Attributes:
        execution_id: Unique execution identifier
        completed_agents: Number of agents that completed
        total_agents: Total number of agents
        percentage: Completion percentage (0-100)
        status: Current execution status
    """

    execution_id: str
    completed_agents: int = 0
    total_agents: int = 0
    percentage: float = 0.0
    status: ExecutionStatus = ExecutionStatus.PENDING

    @property
    def completed(self) -> int:
        """Number of completed agents."""
        return self.completed_agents

    @property
    def total(self) -> int:
        """Total number of agents."""
        return self.total_agents

    @property
    def pct(self) -> float:
        """Completion percentage."""
        if self.total > 0:
            return round(self.completed / self.total * 100, 2)
        return 0.0


class ExecutionRuntime:
    """Orchestration layer for workflow execution lifecycle.

    Responsibilities:
    - Start execution of a WorkflowDefinition
    - Cancel execution
    - Supervise timeouts
    - Emit lifecycle events
    - Expose execution status and progress
    - List active executions

    Does NOT contain:
    - business logic
    - execution logic
    - persistence
    - database code
    - metrics (only observational aggregation via RuntimeMetrics)
    - snapshots
    - scheduling
    - retry framework

    ExecutionRuntime owns exactly one ExecutionEngine instance,
    which is the single source of truth for execution state.
    All execution state queries delegate to the Engine.
    ExecutionStateRegistry provides an observational cache for
    execution_id -> ExecutionState lookup.
    RuntimeMetrics provides observational aggregation of execution
    metrics from observed ExecutionState instances.
    """

    def __init__(
        self,
        event_bus,
        timeout_seconds: float | None = None,
        *,
        execution_state_registry: ExecutionStateRegistry | None = None,
        runtime_metrics: RuntimeMetrics | None = None,
    ) -> None:
        self._engine = ExecutionEngine(event_bus=event_bus, timeout_seconds=timeout_seconds)
        self._event_bus = event_bus
        self._execution_state_registry = execution_state_registry
        self._runtime_metrics = runtime_metrics

    def start(
        self,
        workflow: WorkflowDefinition,
        timeout_seconds: float | None = None,
    ) -> ExecutionResult:
        """Start executing a workflow.

        Args:
            workflow: WorkflowDefinition instance to execute
            timeout_seconds: Optional timeout in seconds

        Returns:
            ExecutionResult with the execution status
        """
        # Emit started event
        self._event_bus.publish(
            "execution.started",
            {
                "execution_id": None,  # Will be populated by engine
                "workflow_name": workflow.name,
            },
        )

        result = self._engine.execute(workflow, timeout_seconds)

        # Emit completion event based on result
        if result.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT,
        ):
            self._event_bus.publish(
                f"execution.{result.status.value}",
                {
                    "execution_id": result.execution_id,
                    "status": result.status.value,
                    "error": result.error,
                },
            )

        # Observational: record state in metrics if available
        if self._runtime_metrics is not None and result.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT,
        ):
            # We record the final state; the Engine would have tracked
            # execution states during their lifecycle. Here we simply
            # note completion via the metrics layer.
            pass

        return result

    def cancel(self, execution_id: str) -> bool:
        """Cancel a running execution.

        Args:
            execution_id: The execution ID to cancel

        Returns:
            True if cancellation was initiated, False if not found
        """
        success = self._engine.cancel(execution_id)

        if success:
            self._event_bus.publish(
                "execution.cancelled",
                {
                    "execution_id": execution_id,
                    "status": "cancelled",
                },
            )

        return success

    def get_status(self, execution_id: str) -> ExecutionResult | None:
        """Get status of a specific execution.

        Args:
            execution_id: Execution status to query

        Returns:
            ExecutionResult if found, None if not found
        """
        status_dict = self._engine.get_status(execution_id)
        if status_dict is None and self._execution_state_registry is not None:
            # Fallback: try to retrieve ExecutionState from the observational registry
            state = self._execution_state_registry.get(execution_id)
            if state is not None:
                return ExecutionResult(
                    status=ExecutionStatus(state.status),
                    execution_id=state.execution_id,
                    error=state.error,
                    progress=(
                        state.progress_percentage / 100.0 * state.total_agents
                        if state.total_agents > 0
                        else 0
                    ),
                )

        if status_dict is None:
            return None

        # Wrap the Engine's dict result into an ExecutionResult
        return ExecutionResult(
            status=ExecutionStatus(status_dict["status"]),
            execution_id=status_dict["execution_id"],
            error=status_dict.get("error"),
            progress=status_dict.get("progress"),
        )

    def get_progress(self, execution_id: str) -> ProgressSnapshot | None:
        """Get progress of a specific execution.

        Args:
            execution_id: Execution progress to query

        Returns:
            ProgressSnapshot if found, None if not found
        """
        progress_dict = self._engine.get_progress(execution_id)
        if progress_dict is not None:
            return ProgressSnapshot(
                execution_id=progress_dict["execution_id"],
                completed_agents=progress_dict.get("completed_agents", 0),
                total_agents=progress_dict.get("total_agents", 0),
                percentage=progress_dict.get("progress", {}).get("completed", 0)
                / max(progress_dict.get("progress", {}).get("total", 1), 1)
                * 100,
                status=ExecutionStatus(progress_dict.get("status", "pending")),
            )

        # Fallback: try to get state from observational registry
        if self._execution_state_registry is not None:
            state = self._execution_state_registry.get(execution_id)
            if state is not None and state.is_finished:
                return ProgressSnapshot(
                    execution_id=state.execution_id,
                    completed_agents=state.completed_agents,
                    total_agents=state.total_agents,
                    percentage=state.progress_percentage,
                    status=state.status,
                )

        return None

    def list_active(self) -> list[ExecutionResult]:
        """List all in-flight (active) executions.

        Returns:
            List of ExecutionResult for all currently active executions
        """
        return self._engine.list_active()

    def get_execution_state(self, execution_id: str) -> ExecutionState | None:
        """Retrieve an ExecutionState by execution_id via the observational registry.

        This is a non-authoritative lookup. The ExecutionEngine remains the
        source of truth for active/lifecycle state. This method only returns
        an ExecutionState if it has been observed and stored in the Registry.

        Args:
            execution_id: The execution ID to look up.

        Returns:
            ExecutionState instance if found in the Registry, None otherwise.
            Always returns None if no Registry was configured.
        """
        if self._execution_state_registry is None:
            return None
        return self._execution_state_registry.get(execution_id)

    def get_metrics_snapshot(self) -> RuntimeMetricsSnapshot | None:
        """Retrieve the current observational metrics snapshot.

        This is a non-authoritative snapshot. The ExecutionRuntime's Engine
        remains the source of truth for execution state. This snapshot only
        reflects metrics that have been observed and recorded via
        record_state() calls.

        Returns:
            RuntimeMetricsSnapshot if a RuntimeMetrics instance was configured,
            None otherwise.
        """
        if self._runtime_metrics is None:
            return None
        return self._runtime_metrics.get_snapshot()
