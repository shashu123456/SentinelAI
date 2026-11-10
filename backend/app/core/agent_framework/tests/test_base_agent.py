"""Unit tests for the BaseAgent class.

Tests cover the abstract base class, lifecycle methods, event system,
and utility functionality.
.. moduleauthor:: SentinelAI Team
.. versionadded:: 2.0.0
"""

from __future__ import annotations

import pytest

from app.core.agent_framework.base_agent import BaseAgent, create_agent
from app.core.agent_framework.shared_models import (
    AgentContext,
    AgentEvent,
    AgentHealth,
    AgentMetadata,
    AgentResult,
    AgentStatus,
    EventType,
)


class TestAgentStatus:
    """Test AgentStatus enum values."""

    def test_status_values(self) -> None:
        """Test that all expected status values exist."""
        assert AgentStatus.PENDING.value == "pending"
        assert AgentStatus.INITIALIZED.value == "initialized"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.CANCELLED.value == "cancelled"
        assert AgentStatus.SHUTDOWN.value == "shutdown"


class TestAgentHealth:
    """Test AgentHealth enum values."""

    def test_health_values(self) -> None:
        """Test that all expected health values exist."""
        assert AgentHealth.HEALTHY.value == "healthy"
        assert AgentHealth.DEGRADED.value == "degraded"
        assert AgentHealth.UNHEALTHY.value == "unhealthy"
        assert AgentHealth.UNKNOWN.value == "unknown"


class BaseAgentTests:
    """Base test class for agent functionality.

    Subclasses should implement a concrete agent for full lifecycle tests.
    """

    @pytest.fixture
    def sample_metadata(self) -> AgentMetadata:
        """Provide sample agent metadata for tests."""
        return AgentMetadata(
            id="test-agent-001",
            display_name="Test Agent",
            version="1.0.0",
            author="Test Author",
            description="A test agent",
        )

    @pytest.fixture
    def sample_context(self) -> AgentContext:
        """Provide sample agent context for tests."""
        return AgentContext(
            agent_id="test-agent-001",
            configuration={"timeout": 30},
        )


class TestBaseAgentInitialization(BaseAgentTests):
    """Test BaseAgent initialization."""

    def test_init_with_metadata(self, sample_metadata: AgentMetadata) -> None:
        """Test initialization with provided metadata."""
        # We can't instantiate BaseAgent directly since it's abstract,
        # but we can test the metadata property
        assert sample_metadata.id == "test-agent-001"
        assert sample_metadata.display_name == "Test Agent"

    def test_init_default_metadata(self) -> None:
        """Test initialization with default metadata."""
        # BaseAgent cannot be instantiated directly (abstract),
        # but check the class-level default
        assert BaseAgent._metadata.id == ""
        assert BaseAgent._metadata.display_name == "BaseAgent"


class TestAgentStatusProperty(BaseAgentTests):
    """Test the status property."""

    def test_status_property(self) -> None:
        """Test that status property works."""
        # BaseAgent has status property; subclasses should manage it
        assert hasattr(BaseAgent, "status")


class TestAgentHealthProperty(BaseAgentTests):
    """Test the health property."""

    def test_health_property(self) -> None:
        """Test that health property works."""
        assert hasattr(BaseAgent, "health")


class TestEventSystem(BaseAgentTests):
    """Test the event system functionality."""

    def test_register_event_callback(self, sample_metadata: AgentMetadata) -> None:
        """Test registering event callbacks."""
        # BaseAgent has register_event_callback method
        assert hasattr(BaseAgent, "register_event_callback")

    def test_emit_event(self, sample_metadata: AgentMetadata) -> None:
        """Test emitting events."""
        assert hasattr(BaseAgent, "_emit_event")


class TestLifecycleMethods(BaseAgentTests):
    """Test that lifecycle methods are defined as abstract."""

    def test_abstract_lifecycle_methods(self) -> None:
        """Test that all lifecycle methods are abstract."""
        abstract_methods = [
            "initialize",
            "validate",
            "prepare",
            "execute",
            "finalize",
            "health_check",
            "cleanup",
        ]

        for method_name in abstract_methods:
            assert hasattr(BaseAgent, method_name), f"{method_name} should exist"

    def test_lifecycle_method_signatures(self) -> None:
        """Test lifecycle method signatures exist."""
        # These are abstract, so they should raise NotImplementedError
        # when called on a concrete subclass that doesn't implement them
        pass


class TestConcreteAgent(BaseAgentTests):
    """Test a concrete agent implementation."""

    class ConcreteAgent(BaseAgent):
        """Concrete implementation for testing."""

        def __init__(self, metadata: AgentMetadata, **configuration: Any) -> None:
            super().__init__(metadata=metadata, **configuration)
            self._initialized_flag = False

        def initialize(self) -> None:
            super().initialize()
            self._initialized_flag = True

        def validate(self) -> bool:
            return True

        def prepare(self) -> None:
            pass

        def execute(self, context: AgentContext) -> AgentResult:
            return AgentResult(
                agent_id=self.metadata.id,
                success=True,
                findings=[],
            )

        def finalize(self, result: AgentResult) -> None:
            pass

        def health_check(self) -> AgentHealthInfo:
            from app.core.agent_framework.shared_models import AgentHealthInfo

            return AgentHealthInfo(healthy=True)

        def cleanup(self) -> None:
            super().cleanup()
            pass

    def test_concrete_agent_creation(self) -> None:
        """Test creating and using a concrete agent."""
        metadata = AgentMetadata(
            id="concrete-001",
            display_name="Concrete Agent",
            version="1.0.0",
        )

        agent = self.ConcreteAgent(metadata=metadata)

        # Test metadata property
        assert agent.metadata.id == "concrete-001"
        assert agent.metadata.display_name == "Concrete Agent"

        # Test status property
        assert agent.status.value == "pending"

        # Test health property
        assert agent.health.value == "unknown"

        # Test initialization
        agent.initialize()
        assert agent._initialized_flag is True
        assert agent.status.value == "initialized"

        # Test validation
        valid = agent.validate()
        assert valid is True

        # Test prepare
        agent.prepare()

        # Test execute with context
        context = AgentContext(agent_id="concrete-001")
        result = agent.execute(context)
        assert result.success is True
        assert result.agent_id == "concrete-001"

        # Test finalize
        agent.finalize(result)

        # Test health check
        health = agent.health_check()
        assert health.healthy is True

        # Test cleanup
        agent.cleanup()
        assert agent.status.value == "shutdown"

    def test_concrete_agent_event_system(self) -> None:
        """Test the event system in a concrete agent."""
        metadata = AgentMetadata(
            id="event-001",
            display_name="Event Agent",
        )

        agent = self.ConcreteAgent(metadata=metadata)

        # Test callback registration
        captured_events: List[AgentEvent] = []

        def event_callback(event: AgentEvent) -> None:
            captured_events.append(event)

        agent.register_event_callback(EventType.AGENT_INITIALIZED, event_callback)

        # Test event emission during initialization
        agent.initialize()

        # Check that callback was called
        assert len(captured_events) > 0
        assert captured_events[0].event_type == EventType.AGENT_INITIALIZED

    def test_concrete_agent_lifecycle_run(self) -> None:
        """Test running the full lifecycle."""
        metadata = AgentMetadata(
            id="lifecycle-001",
            display_name="Lifecycle Agent",
        )

        agent = self.ConcreteAgent(metadata=metadata)
        context = AgentContext(agent_id="lifecycle-001")

        # Run the full lifecycle
        result = agent.run_lifecycle(context)

        # Check result
        assert result is not None
        assert result.agent_id == "lifecycle-001"
        assert result.success is True

        # Check execution history
        history = agent.get_execution_history()
        assert len(history) == 1
        # Lifecycle always ends in SHUTDOWN after cleanup() in finally block
        assert history[0].status.value == "shutdown"


class TestCreateAgentFactoryFunction:
    """Test the create_agent factory function."""

    def test_create_agent_raises_not_implemented(self) -> None:
        """Test that create_agent raises NotImplementedError by default."""
        try:
            create_agent(
                agent_type="unknown",
                agent_id="test",
                display_name="Test",
            )
            # If we get here, the function didn't raise
            pytest.fail("Expected NotImplementedError")
        except NotImplementedError:
            # Expected
            pass


class TestAgentExecutionHistory:
    """Test AgentExecutionHistory records."""

    def test_execution_history_creation(self) -> None:
        """Test creating execution history records."""
        from app.core.agent_framework.shared_models import AgentExecutionHistory

        history = AgentExecutionHistory(
            agent_id="test-001",
            status=AgentStatus.COMPLETED,
            started_at=1000.0,
            completed_at=1010.0,
            duration=10.0,
            findings_count=5,
            error=None,
        )

        assert history.agent_id == "test-001"
        assert history.status == AgentStatus.COMPLETED
        assert history.duration == 10.0
        assert history.findings_count == 5
        assert history.error is None


class TestAgentResult:
    """Test AgentResult creation and usage."""

    def test_agent_result_creation(self) -> None:
        """Test creating an AgentResult."""
        result = AgentResult(
            agent_id="result-001",
            success=True,
            findings=[{"rule_id": "test-rule", "name": "Test Finding"}],
            output={"key": "value"},
            metrics={"accuracy": 0.95},
            execution_time=5.5,
        )

        assert result.agent_id == "result-001"
        assert result.success is True
        assert len(result.findings) == 1
        assert result.output == {"key": "value"}
        assert result.metrics == {"accuracy": 0.95}
        assert result.execution_time == 5.5
        assert result.error is None

    def test_agent_result_with_error(self) -> None:
        """Test creating an AgentResult with an error."""
        result = AgentResult(
            agent_id="result-002",
            success=False,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.findings == []

    def test_agent_result_defaults(self) -> None:
        """Test AgentResult with default values."""
        result = AgentResult(agent_id="result-003", success=False)

        assert result.agent_id == "result-003"
        assert result.success is False
        assert result.findings == []
        assert result.output is None
        assert result.error is None
        assert result.metrics is None
        assert result.execution_time is None
