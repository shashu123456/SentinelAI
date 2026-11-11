"""RuntimeMetrics — Aggregates runtime execution metrics from ExecutionState observations.

Responsibilities:
• Maintain counters for execution lifecycle
• Maintain timing aggregates (durations, averages)
• Compute metric snapshots from observed ExecutionState instances
• Provide immutable snapshot output via frozen dataclass

Never contains:
• Execution logic
• Workflow parsing
• Lifecycle orchestration
• Persistence
• Reporting
• Business logic
• Event emission

Dependencies: ONLY ExecutionState, ExecutionStateRegistry, Python standard library.
No circular imports. No frozen component modifications.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from app.core.execution.execution_state import ExecutionState


@dataclass(frozen=True)
class RuntimeMetricsSnapshot:
    """Immutable snapshot of aggregated runtime metrics.

    This dataclass is frozen (immutable) so callers cannot mutate the
    internal metric state. All fields represent counts or averages derived
    from observed ExecutionState instances.

    Fields:
        total_executions: Total number of executions observed.
        running: Number of executions currently in RUNNING state.
        completed: Number of executions that completed successfully.
        failed: Number of executions that ended in FAILED state.
        cancelled: Number of executions that were CANCELLED.
        timeout: Number of executions that timed out.
        average_duration_seconds: Mean duration across all observed executions.
    """

    total_executions: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    timeout: int = 0
    average_duration_seconds: float = 0.0


class RuntimeMetrics:
    """Aggregates runtime execution metrics from ExecutionState observations.

    This is a pure observation layer. It never mutates ExecutionState,
    never executes workflows, never participates in lifecycle orchestration.
    It only aggregates counters and timing data from ExecutionState
    instances passed to it, and exposes immutable snapshots.

    Thread safety: All methods are safe for concurrent access using
    threading.RLock. Reads (get_snapshot) can proceed concurrently;
    writes (record_state, record_duration, reset) require exclusive access.

    Dependencies: ONLY ExecutionState and ExecutionStateRegistry
    (for potential future integration). No Engine, no Runtime, no
    WorkflowDefinition, no EventBus, no database, no networking.
    """

    def __init__(self) -> None:
        """Initialize an empty RuntimeMetrics with zero counters."""
        self._lock = threading.RLock()
        self._total_executions: int = 0
        self._running: int = 0
        self._completed: int = 0
        self._failed: int = 0
        self._cancelled: int = 0
        self._timeout: int = 0
        self._duration_total: float = 0.0
        self._duration_count: int = 0

    def record_state(self, state: ExecutionState) -> None:
        """Record a completed ExecutionState instance for metrics aggregation.

        Updates all relevant counters based on the state's status and
        accumulates duration timing information.

        Args:
            state: ExecutionState instance to aggregate metrics from.
        """
        with self._lock:
            self._total_executions += 1

            # Count by status
            if state.is_running:
                self._running += 1
            elif state.is_terminal:
                if state.status.value == "completed":
                    self._completed += 1
                elif state.status.value == "failed":
                    self._failed += 1
                elif state.status.value == "cancelled":
                    self._cancelled += 1
                elif state.status.value == "timeout":
                    self._timeout += 1

            # Accumulate duration timing
            duration = state.duration
            if duration > 0:
                self._duration_total += duration
                self._duration_count += 1

    def record_duration(self, execution_id: str, duration_seconds: float) -> None:
        """Record a duration for a given execution ID.

        This method allows recording duration for executions even if
        the full ExecutionState was not passed to record_state(). The
        execution_id is stored for potential future reference, but the
        primary metrics tracking comes from record_state().

        Args:
            execution_id: The execution ID being timed.
            duration_seconds: Duration in seconds (non-negative).
        """
        with self._lock:
            if duration_seconds >= 0:
                self._duration_total += duration_seconds
                self._duration_count += 1

    def get_snapshot(self) -> RuntimeMetricsSnapshot:
        """Return an immutable snapshot of current aggregated metrics.

        Concurrent calls to get_snapshot() can proceed simultaneously
        without blocking each other (RLock read mode).

        Returns:
            RuntimeMetricsSnapshot — frozen dataclass with current
            aggregated metrics. Snapshot reflects state at time of call;
            caller cannot mutate the returned object.
        """
        with self._lock:
            # Compute average duration safely
            if self._duration_count > 0:
                avg_duration = round(self._duration_total / self._duration_count, 2)
            else:
                avg_duration = 0.0

            return RuntimeMetricsSnapshot(
                total_executions=self._total_executions,
                running=self._running,
                completed=self._completed,
                failed=self._failed,
                cancelled=self._cancelled,
                timeout=self._timeout,
                average_duration_seconds=avg_duration,
            )

    def reset(self) -> None:
        """Reset all counters to zero.

        Bulk reset for testing or restart. Concurrent reads will
        complete before the store is cleared.
        """
        with self._lock:
            self._total_executions = 0
            self._running = 0
            self._completed = 0
            self._failed = 0
            self._cancelled = 0
            self._timeout = 0
            self._duration_total = 0.0
            self._duration_count = 0
