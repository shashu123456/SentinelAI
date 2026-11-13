from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.shared_models import (
    AgentContext,
    AgentResult,
    EventType,
)


class LifecycleState(Enum):
    """Possible states of the agent lifecycle."""

    PENDING = "pending"
    INITIALIZED = "initialized"
    VALIDATING = "validating"
    PREPARING = "preparing"
    EXECUTING = "executing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SHUTDOWN = "shutdown"


@dataclass
class LifecycleTransition:
    """Records a lifecycle state transition."""

    from_state: LifecycleState
    to_state: LifecycleState
    timestamp: float = field(default_factory=time.time)
    reason: str | None = None
    executed_by: str | None = None


@dataclass
class LifecycleMetrics:
    """Metrics collected during the agent lifecycle."""

    total_initialization_time: float = 0.0
    total_validation_time: float = 0.0
    total_preparation_time: float = 0.0
    total_execution_time: float = 0.0
    total_finalization_time: float = 0.0
    total_health_check_time: float = 0.0
    transition_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    cancellation_count: int = 0


class AgentLifecycleManager:
    """Manages the lifecycle state machine for an agent.

    The lifecycle manager tracks state transitions, timing, and events
    for an agent's lifecycle. It can be used independently or as part
    of a BaseAgent subclass.

    Lifecycle order:
        PENDING -> INITIALIZED -> VALIDATING -> PREPARING -> EXECUTING ->
        FINALIZING -> COMPLETED/SHUTDOWN
        |                    |
        +--> FAILED/CANCELLED+

    Attributes:
        agent: The associated agent instance.
        state: Current lifecycle state.
        start_time: When the lifecycle started.
        transitions: List of state transition records.
        metrics: Collected lifecycle metrics.
    """

    def __init__(self, agent: BaseAgent) -> None:
        """Initialize the lifecycle manager.

        Args:
            agent: The agent instance to manage lifecycle for.
        """
        self.agent: BaseAgent = agent
        self._state: LifecycleState = LifecycleState.PENDING
        self._start_time: float | None = None
        self._transitions: list[LifecycleTransition] = []
        self._metrics: LifecycleMetrics = LifecycleMetrics()
        self._event_callbacks: dict[EventType, list[Any]] = {}

        # Register default event callbacks
        self.register_event_callback(EventType.AGENT_HEALTH_CHANGED, self._on_health_changed)

    @property
    def state(self) -> LifecycleState:
        """Get the current lifecycle state."""
        return self._state

    @state.setter
    def state(self, new_state: LifecycleState) -> None:
        """Set the lifecycle state and emit transition event.

        Args:
            new_state: The new lifecycle state.
        """
        previous = self._state
        if previous == new_state:
            return

        transition = LifecycleTransition(
            from_state=previous,
            to_state=new_state,
            timestamp=time.time(),
            executed_by=self.agent.metadata.id if self.agent else None,
        )
        self._transitions.append(transition)
        self._metrics.transition_count += 1
        self._state = new_state

        # Emit transition event
        self._emit_event(
            EventType.AGENT_HEALTH_CHANGED,
            payload={
                "state": new_state.value,
                "previous_state": previous.value,
                "agent_id": self.agent.metadata.id if self.agent else None,
            },
        )

    def start(self) -> None:
        """Start the lifecycle timer."""
        self._start_time = time.time()

    def stop(self) -> float:
        """Stop the lifecycle timer and return elapsed time.

        Returns:
            Elapsed time in seconds.
        """
        if self._start_time is not None:
            elapsed = time.time() - self._start_time
            self._start_time = None
            return elapsed
        return 0.0

    # ------------------------------------------------------------------ #
    # Lifecycle Phase Methods
    # ------------------------------------------------------------------ #

    def transition_to_initialized(self) -> None:
        """Transition to the INITIALIZED state."""
        self.state = LifecycleState.INITIALIZED

    def transition_to_validating(self) -> None:
        """Transition to the VALIDATING state."""
        self.state = LifecycleState.VALIDATING

    def transition_to_preparing(self) -> None:
        """Transition to the PREPARING state."""
        self.state = LifecycleState.PREPARING

    def transition_to_executing(self) -> None:
        """Transition to the EXECUTING state."""
        self.state = LifecycleState.EXECUTING

    def transition_to_finalizing(self) -> None:
        """Transition to the FINALIZING state."""
        self.state = LifecycleState.FINALIZING

    def transition_to_completed(self) -> None:
        """Transition to the COMPLETED state."""
        self.state = LifecycleState.COMPLETED
        self._metrics.success_count += 1

    def transition_to_failed(self, reason: str = "") -> None:
        """Transition to the FAILED state.

        Args:
            reason: Optional reason for the failure.
        """
        self.state = LifecycleState.FAILED
        self._metrics.failure_count += 1
        # Emit failure event
        self._emit_event(
            EventType.AGENT_FAILED,
            payload={"agent_id": self.agent.metadata.id, "reason": reason},
        )

    def transition_to_cancelled(self) -> None:
        """Transition to the CANCELLED state."""
        self.state = LifecycleState.CANCELLED
        self._metrics.cancellation_count += 1
        # Emit cancellation event
        self._emit_event(
            EventType.AGENT_CANCELLED,
            payload={"agent_id": self.agent.metadata.id},
        )

    def transition_to_shutdown(self) -> None:
        """Transition to the SHUTDOWN state."""
        self.state = LifecycleState.SHUTDOWN

    # ------------------------------------------------------------------ #
    # Timing and Metrics
    # ------------------------------------------------------------------ #

    def record_initialization_time(self, duration: float) -> None:
        """Record the initialization duration.

        Args:
            duration: Time in seconds.
        """
        self._metrics.total_initialization_time += duration

    def record_validation_time(self, duration: float) -> None:
        """Record the validation duration.

        Args:
            duration: Time in seconds.
        """
        self._metrics.total_validation_time += duration

    def record_preparation_time(self, duration: float) -> None:
        """Record the preparation duration.

        Args:
            duration: Time in seconds.
        """
        self._metrics.total_preparation_time += duration

    def record_execution_time(self, duration: float) -> None:
        """Record the execution duration.

        Args:
            duration: Time in seconds.
        """
        self._metrics.total_execution_time += duration

    def record_finalization_time(self, duration: float) -> None:
        """Record the finalization duration.

        Args:
            duration: Time in seconds.
        """
        self._metrics.total_finalization_time += duration

    def record_health_check_time(self, duration: float) -> None:
        """Record the health check duration.

        Args:
            duration: Time in seconds.
        """
        self._metrics.total_health_check_time += duration

    def get_metrics(self) -> LifecycleMetrics:
        """Get the collected lifecycle metrics.

        Returns:
            LifecycleMetrics instance with accumulated data.
        """
        return self._metrics

    # ------------------------------------------------------------------ #
    # Event System
    # ------------------------------------------------------------------ #

    def register_event_callback(self, event_type: EventType, callback: Any) -> None:
        """Register a callback for a specific event type.

        Args:
            event_type: The event type to callback.
            callback: The callable to invoke when the event is emitted.
        """
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)

    def _emit_event(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit an event to registered callbacks.

        Args:
            event_type: The event type.
            payload: Additional event data.
        """
        event = type(
            "AgentEvent",
            (),
            {
                "event_type": event_type,
                "agent_id": self.agent.metadata.id if self.agent else None,
                "payload": payload,
                "timestamp": time.time(),
            },
        )()
        for callback in self._event_callbacks.get(event_type, []):
            # Swallow callback errors to avoid breaking the lifecycle
            with contextlib.suppress(Exception):
                callback(event)

    def get_transition_history(self) -> list[LifecycleTransition]:
        """Get the lifecycle transition history.

        Returns:
            List of LifecycleTransition records.
        """
        return self._transitions.copy()


# ------------------------------------------------------------------ #
# Convenience Functions
# ------------------------------------------------------------------ #


def run_agent_lifecycle(
    agent: BaseAgent,
    context: AgentContext,
) -> AgentResult:
    """Run the full agent lifecycle using the lifecycle manager.

    This is a convenience function that creates a lifecycle manager
    and executes the agent lifecycle through it.

    Args:
        agent: The BaseAgent instance.
        context: The AgentContext for execution.

    Returns:
        The AgentResult from execution.
    """

    lifecycle = AgentLifecycleManager(agent)
    lifecycle.start()

    try:
        # Initialize
        lifecycle.transition_to_initialized()
        agent.initialize()

        # Validate
        lifecycle.transition_to_validating()
        if not agent.validate():
            lifecycle.transition_to_failed("Validation failed")
            return AgentResult(
                agent_id=agent.metadata.id,
                success=False,
                error="Agent validation failed",
            )

        # Prepare
        lifecycle.transition_to_preparing()
        agent.prepare()

        # Execute
        lifecycle.transition_to_executing()
        result = agent.execute(context)

        # Finalize
        lifecycle.transition_to_finalizing()
        agent.finalize(result)

        lifecycle.transition_to_completed()

        return result

    except KeyboardInterrupt:
        lifecycle.transition_to_cancelled()
        return AgentResult(
            agent_id=agent.metadata.id,
            success=False,
            error="Execution cancelled by user",
        )

    except Exception as exc:
        lifecycle.transition_to_failed(str(exc))
        return AgentResult(
            agent_id=agent.metadata.id,
            success=False,
            error=str(exc),
        )

    finally:
        lifecycle.transition_to_shutdown()
        agent.cleanup()
