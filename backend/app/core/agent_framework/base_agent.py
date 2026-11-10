from __future__ import annotations

import abc
import time
from typing import Any

from app.core.agent_framework.shared_models import (
    AgentContext,
    AgentEvent,
    AgentExecutionHistory,
    AgentHealth,
    AgentHealthInfo,
    AgentMetadata,
    AgentResult,
    AgentStatus,
    EventType,
)


class BaseAgent(abc.ABC):
    """Abstract base class for all SentinelAI agents.

    Every security capability must inherit from BaseAgent and implement
    the lifecycle methods: initialize, validate, prepare, execute, finalize,
    health_check, and shutdown.

    The lifecycle order is:
        1. initialize() - Set up resources, connections, configuration
        2. validate() - Validate configuration and prerequisites
        3. prepare() - Prepare for execution (load models, compile patterns)
        4. execute() - Run the actual analysis/security check
        5. finalize() - Post-processing, result aggregation
        6. health_check() - Verify agent is still healthy
        7. cleanup() - Release resources, close connections

    Agents must implement:
        - AgentMetadata (via class property or method)
        - The full lifecycle methods
        - Event publishing through the event bus

    Agents may optionally override:
        - Custom initialization logic
        - Custom event handling
        - Additional analysis methods
    """

    # Class-level default metadata
    _metadata: AgentMetadata = AgentMetadata(id="", display_name="BaseAgent")
    _capabilities: list[str] = []  # Default empty capabilities

    def __init__(self, metadata: AgentMetadata | None = None, **configuration: Any) -> None:
        """Initialize the base agent.

        Args:
            metadata: Agent metadata instance. If None, uses class-level metadata.
            **configuration: Agent-specific configuration parameters.
        """
        # Set default metadata from class-level or provided metadata
        if metadata is not None:
            self._metadata = metadata
        else:
            self._metadata = self.__class__._metadata

        # Apply configuration from constructor
        for key, value in configuration.items():
            setattr(self, f"_{key}", value)

        # Initialize agent state
        self._status: AgentStatus = AgentStatus.PENDING
        self._health: AgentHealth = AgentHealth.UNKNOWN
        self._initialized: bool = False
        self._start_time: float | None = None
        self._execution_count: int = 0

        self._execution_history: list[AgentExecutionHistory] = []
        self._event_callbacks: dict[EventType, list[Any]] = {}

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    @property
    def metadata(self) -> AgentMetadata:
        """Get the agent's metadata."""
        return self._metadata

    @metadata.setter
    def metadata(self, value: AgentMetadata) -> None:
        """Set the agent's metadata."""
        self._metadata = value

    @property
    def capabilities(self) -> list[str]:
        """Get the agent's capabilities list.

        Returns the agent's configured capabilities. Subclasses can override
        this property or set ``self._capabilities`` in their ``__init__``.
        """
        return self._capabilities or []

    @capabilities.setter
    def capabilities(self, value: list[str]) -> None:
        """Set the agent's capabilities."""
        self._capabilities = value or []

    @property
    def status(self) -> AgentStatus:
        """Get the current agent status."""
        return self._status

    @status.setter
    def status(self, value: AgentStatus) -> None:
        """Set the agent status and emit event."""
        self._status = value
        self._emit_event(EventType.AGENT_HEALTH_CHANGED, payload={"status": value})

    @property
    def health(self) -> AgentHealth:
        """Get the agent's health state."""
        return self._health

    @health.setter
    def health(self, value: AgentHealth) -> None:
        """Set the agent health and emit event."""
        self._health = value
        self._emit_event(EventType.AGENT_HEALTH_CHANGED, payload={"health": value})

    # ------------------------------------------------------------------ #
    # Lifecycle Methods
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        """Initialize the agent.

        Set up resources, connections, configuration, and load any
        required models or patterns. This is called once during agent
        creation, before any scanning begins.

        The default implementation sets the status to INITIALIZED,
        marks the agent as initialized, and emits the AGENT_INITIALIZED
        event. Subclasses should override this method to provide custom
        initialization logic.

        Raises:
            AgentInitializationError: If initialization fails.
        """
        self.status = AgentStatus.INITIALIZED
        self._initialized = True
        self._emit_event(EventType.AGENT_INITIALIZED, payload={"agent_id": self.metadata.id})

    @abc.abstractmethod
    def validate(self) -> bool:
        """Validate the agent's configuration and prerequisites.

        Check that all required configuration is present, models are
        loadable, and the agent can function properly.

        Returns:
            True if validation passes, False otherwise.

        Raises:
            AgentValidationError: If validation fails.
        """
        raise NotImplementedError("Subclasses must implement validate()")

    @abc.abstractmethod
    def prepare(self) -> None:
        """Prepare the agent for execution.

        Load models, compile patterns, set up internal state. This is
        called before each execution cycle.

        Raises:
            AgentPreparationError: If preparation fails.
        """
        raise NotImplementedError("Subclasses must implement prepare()")

    @abc.abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's analysis.

        Run the actual security analysis against the target.

        Args:
            context: The execution context containing configuration and
                working environment details.

        Returns:
            An AgentResult containing findings, metrics, and status.

        Raises:
            AgentExecutionError: If execution fails.
        """
        raise NotImplementedError("Subclasses must implement execute()")

    @abc.abstractmethod
    def finalize(self, result: AgentResult) -> None:
        """Post-process the execution result.

        Perform any finalization steps after execution, such as result
        aggregation, formatting, or cleanup.

        Args:
            result: The AgentResult from the execute() call.

        Raises:
            AgentFinalizationError: If finalization fails.
        """
        raise NotImplementedError("Subclasses must implement finalize()")

    @abc.abstractmethod
    def health_check(self) -> AgentHealthInfo:
        """Perform a health check on the agent.

        Verify that the agent is still healthy — models are loadable,
        connections are alive, and all prerequisites are met.

        Returns:
            AgentHealthInfo containing health status and details.

        Raises:
            AgentHealthCheckError: If the health check fails.
        """
        raise NotImplementedError("Subclasses must implement health_check()")

    @abc.abstractmethod
    def cleanup(self) -> None:
        """Clean up agent resources.

        Release resources, close connections, and perform any necessary
        cleanup. This is called when the agent is being shut down.

        Raises:
            AgentCleanupError: If cleanup fails.
        """
        raise NotImplementedError("Subclasses must implement cleanup()")

    # ------------------------------------------------------------------ #
    # Lifecycle Orchestrator
    # ------------------------------------------------------------------ #

    def run_lifecycle(self, context: AgentContext) -> AgentResult:
        """Run the full agent lifecycle.

        Executes the lifecycle in order: initialize -> validate -> prepare ->
        execute -> finalize -> cleanup.

        Args:
            context: The execution context.

        Returns:
            The AgentResult from execution.

        Raises:
            Exception: Any exception raised during the lifecycle.
        """
        result: AgentResult | None = None

        try:
            # Initialize
            self.status = AgentStatus.INITIALIZED
            self._start_time = time.time()
            self._emit_event(EventType.AGENT_INITIALIZED, payload={"agent_id": self.metadata.id})
            self.initialize()

            # Validate
            self.status = AgentStatus.RUNNING
            if not self.validate():
                raise RuntimeError("Agent validation failed")

            # Prepare
            self._emit_event(EventType.AGENT_STARTED, payload={"agent_id": self.metadata.id})
            self.prepare()

            # Execute
            self._status = AgentStatus.RUNNING
            result = self.execute(context)

            # Finalize
            self._emit_event(
                EventType.AGENT_COMPLETED, payload={"agent_id": self.metadata.id, "result": result}
            )
            self.finalize(result)

            self.status = AgentStatus.COMPLETED
            self._execution_count += 1

        except KeyboardInterrupt:
            self.status = AgentStatus.CANCELLED
            self._emit_event(EventType.AGENT_CANCELLED, payload={"agent_id": self.metadata.id})
            result = AgentResult(
                agent_id=self.metadata.id,
                success=False,
                error="Execution cancelled by user",
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._emit_event(
                EventType.AGENT_FAILED, payload={"agent_id": self.metadata.id, "error": str(exc)}
            )
            result = AgentResult(
                agent_id=self.metadata.id,
                success=False,
                error=str(exc),
            )

        finally:
            # Always run cleanup
            self._start_time = time.time()
            self.cleanup()
            self.status = AgentStatus.SHUTDOWN
            self._emit_event(EventType.AGENT_SHUTDOWN, payload={"agent_id": self.metadata.id})

        # Record execution history
        duration = time.time() - self._start_time if self._start_time else None
        history = AgentExecutionHistory(
            agent_id=self.metadata.id,
            status=self.status,
            started_at=result._start_time if result and hasattr(result, "_start_time") else None,
            completed_at=time.time(),
            duration=duration,
            findings_count=len(result.findings) if result and result.findings else 0,
            error=result.error if result else None,
        )
        self._execution_history.append(history)

        return result

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
        event = AgentEvent(event_type=event_type, agent_id=self.metadata.id, payload=payload)
        for callback in self._event_callbacks.get(event_type, []):
            try:
                callback(event)
            except Exception:
                # Swallow callback errors to avoid breaking the agent
                pass

    # ------------------------------------------------------------------ #
    # Utility Methods
    # ------------------------------------------------------------------ #

    def get_execution_history(self) -> list[AgentExecutionHistory]:
        """Get the agent's execution history."""
        return self._execution_history

    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Args:
            key: The configuration key.
            default: Default value if key is not found.

        Returns:
            The configuration value or default.
        """
        return getattr(self, f"_{key}", default)

    def get_duration(self) -> float | None:
        """Get the total execution duration across all runs."""
        durations = [h.duration for h in self._execution_history if h.duration is not None]
        return sum(durations) / len(durations) if durations else None

    def cleanup(self) -> None:
        """Clean up agent resources.

        Release resources, close connections, and perform any necessary
        cleanup. This is called when the agent is being shut down.

        The default implementation sets the status to SHUTDOWN.
        Subclasses can override this to provide custom cleanup logic.
        """
        self.status = AgentStatus.SHUTDOWN
        self._emit_event(EventType.AGENT_SHUTDOWN, payload={"agent_id": self.metadata.id})

    def reset(self) -> None:
        """Reset the agent state for a new execution cycle."""
        self._initialized = False
        self._start_time = None
        self._execution_history = []
        self._event_callbacks = {}


# ------------------------------------------------------------------ #
# Convenience Factory Function
# ------------------------------------------------------------------ #


def create_agent(
    agent_type: str,
    agent_id: str,
    display_name: str,
    version: str = "1.0.0",
    author: str = "",
    description: str = "",
    **configuration: Any,
) -> BaseAgent:
    """Factory function to create a specific agent type.

    Args:
        agent_type: The type/name of agent to create.
        agent_id: Unique identifier for the agent instance.
        display_name: Human-readable agent name.
        version: Agent version.
        author: Agent author/organization.
        description: Agent description.
        **configuration: Agent-specific configuration.

    Returns:
        A configured BaseAgent subclass instance.

    Raises:
        ValueError: If the agent_type is not recognized.
    """
    raise NotImplementedError(f"Unknown agent type: {agent_type}")
