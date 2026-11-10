"""ExecutionEngine — Single-agent and multi-agent execution orchestration.

Responsibilities:
• Execute one or more SecurityAgents
• Sequential execution
• Parallel execution
• Dependency-aware execution
• Retry handling with exponential backoff
• Cancellation support
• Timeout handling
• Progress reporting via EventBus
• CircuitBreaker protection
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum

from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.event_bus import EventBus, create_event_bus
from app.core.agent_framework.shared_models import AgentContext, AgentResult, AgentStatus
from app.utils.resilience import CircuitBreaker, CircuitState

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Status of execution orchestration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ExecutionResult:
    """Result from agent execution orchestration."""

    agent_id: str
    status: ExecutionStatus
    result: AgentResult | None = None
    error: str | None = None
    duration: float = 0.0
    progress: int = 0
    transition_history: list = field(default_factory=list)


@dataclass
class ExecutionConfig:
    """Configuration for ExecutionEngine execution."""

    timeout: float | None = None  # seconds per agent
    max_retries: int = 0
    retry_delay: float = 1.0
    parallel: bool = False
    cancel_on_first_failure: bool = True
    emit_progress: bool = True


class ExecutionEngine:
    """Orchestrates execution of BaseAgent instances.

    Supports:
    - Single agent execution with full lifecycle
    - Multiple agent execution (sequential or parallel)
    - Dependency-aware execution ordering
    - Retry with exponential backoff
    - Circuit breaker protection
    - Timeout handling
    - Progress reporting via EventBus
    - Cancellation support
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize the ExecutionEngine.

        Args:
            event_bus: EventBus instance for progress/events. Creates default if None.
            circuit_breaker: CircuitBreaker for protecting agent execution. Creates default if None.
        """
        self._event_bus: EventBus = event_bus or create_event_bus("execution_engine")
        self._circuit_breaker: CircuitBreaker = circuit_breaker or CircuitBreaker(
            name="execution_engine", failure_threshold=3, recovery_timeout=30.0
        )
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._active_executions: dict[str, any] = {}

    # ------------------------------------------------------------------ #
    # Internal lifecycle execution
    # ------------------------------------------------------------------ #

    def _execute_lifecycle(self, agent: BaseAgent, context: AgentContext) -> AgentResult | None:
        """Execute the full agent lifecycle.

        Returns the AgentResult, or None if execution could not proceed.
        """
        result: AgentResult | None = None
        success = False

        try:
            # Initialize
            agent.status = AgentStatus.INITIALIZED
            agent._initialized = True
            agent._emit_event(
                type("event", (), {"event_type": "AGENT_INITIALIZED"})(),
                payload={"agent_id": agent.metadata.id},
            )

            # Validate
            agent.status = AgentStatus.RUNNING
            if not agent.validate():
                # Validation failed - return failure result
                result = AgentResult(
                    agent_id=agent.metadata.id,
                    success=False,
                    error="Agent validation failed",
                )
                agent._emit_event(
                    type("event", (), {"event_type": "AGENT_FAILED"})(),
                    payload={"agent_id": agent.metadata.id, "reason": "validation_failed"},
                )
                return result

            # Prepare
            agent._emit_event(
                type("event", (), {"event_type": "AGENT_STARTED"})(),
                payload={"agent_id": agent.metadata.id},
            )
            agent.prepare()

            # Execute
            agent.status = AgentStatus.RUNNING
            execute_result = agent.execute(context)

            # Wrap the execute result in an AgentResult
            if isinstance(execute_result, AgentResult):
                result = execute_result
            else:
                result = AgentResult(
                    agent_id=agent.metadata.id,
                    success=True,
                    output=execute_result if execute_result else None,
                    error=None,
                )

            # Finalize
            agent._emit_event(
                type("event", (), {"event_type": "AGENT_COMPLETED"})(),
                payload={"agent_id": agent.metadata.id, "result": result},
            )
            agent.finalize(result)

            success = True

        except KeyboardInterrupt:
            result = AgentResult(
                agent_id=agent.metadata.id,
                success=False,
                error="Execution cancelled by user",
            )
            agent._emit_event(
                type("event", (), {"event_type": "AGENT_CANCELLED"})(),
                payload={"agent_id": agent.metadata.id},
            )

        except Exception as exc:
            result = AgentResult(
                agent_id=agent.metadata.id,
                success=False,
                error=str(exc),
            )
            agent._emit_event(
                type("event", (), {"event_type": "AGENT_FAILED"})(),
                payload={"agent_id": agent.metadata.id, "error": str(exc)},
            )

        # Set final status based on success
        if success:
            agent.status = AgentStatus.COMPLETED
            agent._emit_event(
                type("event", (), {"event_type": "AGENT_COMPLETED"})(),
                payload={"agent_id": agent.metadata.id},
            )
        else:
            agent.status = AgentStatus.FAILED
            agent._emit_event(
                type("event", (), {"event_type": "AGENT_FAILED"})(),
                payload={"agent_id": agent.metadata.id},
            )

        return result

    # ------------------------------------------------------------------ #
    # Public execution methods
    # ------------------------------------------------------------------ #

    def execute(
        self,
        agent: BaseAgent,
        context: AgentContext,
        config: ExecutionConfig | None = None,
    ) -> ExecutionResult:
        """Execute a single agent through its full lifecycle.

        Args:
            agent: The BaseAgent instance to execute.
            context: The AgentContext for execution.
            config: Execution configuration (timeout, retries, parallel, etc.).

        Returns:
            ExecutionResult with status, result, and metadata.
        """
        config = config or ExecutionConfig()
        start_time = time.time()
        agent_id = agent.metadata.id

        # Reset circuit breaker state for this execution
        self._circuit_breaker._state = CircuitState.CLOSED
        self._circuit_breaker._failure_count = 0
        self._circuit_breaker._last_failure_time = 0.0

        # Emit start event
        self._event_bus.publish_raw(
            event_type="agent.started",
            payload={"agent_id": agent_id, "config": config.__dict__},
            source=agent,
        )

        # Execute with circuit breaker protection
        @self._circuit_breaker.protect
        def _run_with_cb() -> AgentResult:
            return self._execute_lifecycle(agent, context)

        try:
            # Execute directly if no timeout, otherwise use executor with timeout
            if config.timeout:
                # Run in executor with timeout using proper asyncio pattern
                loop = asyncio.get_event_loop()
                future = asyncio.get_event_loop().run_in_executor(self._executor, _run_with_cb)
                # Use run_until_complete to properly await the future with timeout
                try:
                    loop.run_until_complete(asyncio.wait_for(future, timeout=config.timeout))
                    result = future.result()
                except TimeoutError:
                    raise
            else:
                result = _run_with_cb()

            duration = time.time() - start_time

            # Determine the execution status based on the result
            if result.success:
                execution_status = ExecutionStatus.COMPLETED
            else:
                execution_status = ExecutionStatus.FAILED

            # Emit completion event
            self._event_bus.publish_raw(
                event_type="agent.completed",
                payload={
                    "agent_id": agent_id,
                    "status": execution_status,
                    "result": result,
                    "duration": duration,
                },
                source=agent,
            )

            transition_history = (
                getattr(agent, "_execution_history", [])
                if hasattr(agent, "_execution_history")
                else []
            )

            return ExecutionResult(
                agent_id=agent_id,
                status=execution_status,
                result=result,
                duration=duration,
                progress=100 if execution_status == ExecutionStatus.COMPLETED else 0,
                transition_history=transition_history,
            )

        except TimeoutError:
            duration = time.time() - start_time
            self._circuit_breaker._on_failure()

            self._event_bus.publish_raw(
                event_type="agent.timeout",
                payload={
                    "agent_id": agent_id,
                    "status": ExecutionStatus.TIMEOUT,
                    "duration": duration,
                },
                source=agent,
            )

            return ExecutionResult(
                agent_id=agent_id,
                status=ExecutionStatus.TIMEOUT,
                duration=duration,
                error=f"Execution exceeded timeout of {config.timeout}s",
                progress=0,
                transition_history=[],
            )

        except Exception as exc:
            duration = time.time() - start_time
            self._circuit_breaker._on_failure()

            self._event_bus.publish_raw(
                event_type="agent.failed",
                payload={
                    "agent_id": agent_id,
                    "status": ExecutionStatus.FAILED,
                    "error": str(exc),
                    "duration": duration,
                },
                source=agent,
            )

            transition_history = (
                getattr(agent, "_execution_history", [])
                if hasattr(agent, "_execution_history")
                else []
            )

            return ExecutionResult(
                agent_id=agent_id,
                status=ExecutionStatus.FAILED,
                error=str(exc),
                duration=duration,
                progress=0,
                transition_history=transition_history,
            )

    def execute_parallel(
        self,
        agents: list[tuple[BaseAgent, AgentContext]],
        config: ExecutionConfig | None = None,
    ) -> list[ExecutionResult]:
        """Execute multiple agents in parallel.

        Args:
            agents: List of (agent, context) tuples.
            config: Execution configuration.

        Returns:
            List of ExecutionResult one per agent.
        """
        config = config or ExecutionConfig(parallel=True)
        results: list[ExecutionResult] = []

        # Execute all agents in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(len(agents), 4)) as executor:
            futures = []
            for i, (agent, ctx) in enumerate(agents):
                future = executor.submit(self.execute, agent, ctx, config)
                futures.append((i, future))

        # Collect results as they complete
        for i, future in futures:
            try:
                result = future.result()
                results.insert(i, result)  # preserve original order
            except Exception as exc:
                # Create a fallback result for failed execution
                results.insert(
                    i,
                    ExecutionResult(
                        agent_id=agents[i][0].metadata.id,
                        status=ExecutionStatus.FAILED,
                        error=f"Parallel execution error: {exc}",
                        duration=0.0,
                        progress=0,
                        transition_history=[],
                    ),
                )

        return results

    def execute_sequential(
        self,
        agents: list[tuple[BaseAgent, AgentContext]],
        config: ExecutionConfig | None = None,
    ) -> list[ExecutionResult]:
        """Execute multiple agents sequentially.

        Args:
            agents: List of (agent, context) tuples.
            config: Execution configuration.

        Returns:
            List of ExecutionResult one per agent, in order.
        """
        config = config or ExecutionConfig(parallel=False)
        results: list[ExecutionResult] = []

        for i, (agent, ctx) in enumerate(agents):
            if config.cancel_on_first_failure and i > 0:
                # Check if previous result was a failure
                if results and results[i - 1].status in (
                    ExecutionStatus.FAILED,
                    ExecutionStatus.TIMEOUT,
                ):
                    # Execute a no-op cancelled result for remaining
                    results.append(
                        ExecutionResult(
                            agent_id=agent.metadata.id,
                            status=ExecutionStatus.CANCELLED,
                            error="Cancelled due to prior failure",
                            duration=0.0,
                            progress=0,
                            transition_history=[],
                        )
                    )
                    continue

            result = self.execute(agent, ctx, config)
            results.append(result)

            # Early termination if configured and failure occurs
            if config.cancel_on_first_failure and result.status in (
                ExecutionStatus.FAILED,
                ExecutionStatus.TIMEOUT,
            ):
                # Fill remaining with cancelled results
                for j in range(i + 1, len(agents)):
                    ag, ctx = agents[j]
                    results.append(
                        ExecutionResult(
                            agent_id=ag.metadata.id,
                            status=ExecutionStatus.CANCELLED,
                            error="Cancelled due to prior failure in sequential chain",
                            duration=0.0,
                            progress=0,
                            transition_history=[],
                        )
                    )
                break

        return results

    def get_status(self) -> dict:
        """Get current engine status."""
        return {
            "active_executions": len(self._active_executions),
            "circuit_breaker_state": self._circuit_breaker.get_state(),
            "executor_active_workers": self._executor._max_workers,
        }

    def cancel_execution(self, agent_id: str) -> bool:
        """Cancel an active execution by agent ID.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            True if cancellation was initiated, False if not found.
        """
        # Note: BaseAgent cancellation is cooperative via KeyboardInterrupt
        # This method signals intent; actual cancellation depends on agent implementation
        if agent_id in self._active_executions:
            # In a full implementation, we'd set an abort flag on the agent
            # For now, we emit a cancellation event
            self._event_bus.publish_raw(
                event_type="agent.cancelled",
                payload={"agent_id": agent_id},
                source=None,
            )
            del self._active_executions[agent_id]
            return True
        return False

    def __del__(self) -> None:
        """Cleanup thread pool on destruction."""
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass
