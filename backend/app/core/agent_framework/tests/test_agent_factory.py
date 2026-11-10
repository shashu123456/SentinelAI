"""Unit tests for the AgentFactory class.

Tests cover agent creation, type registration, configuration injection,
and factory integration with the registry.
.. moduleauthor:: SentinelAI Team
.. versionadded:: 2.0.0
"""

from __future__ import annotations

import pytest

from app.core.agent_framework.agent_factory import (
    AgentFactory,
)
from app.core.agent_framework.agent_factory import (
    create_agent as factory_create_agent,
)
from app.core.agent_framework.agent_registry import get_registry
from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.shared_models import (
    AgentMetadata,
)


class TestFactoryInitialization:
    """Test factory initialization."""

    def test_factory_with_registry(self) -> None:
        """Test factory initialized with a custom registry."""
        from app.core.agent_framework.agent_registry import AgentRegistry

        custom_registry = AgentRegistry()
        factory = AgentFactory(registry=custom_registry)
        assert factory._registry is custom_registry

    def test_factory_uses_global_registry(self) -> None:
        """Test factory uses global registry when none provided."""
        factory = AgentFactory()
        assert factory._registry is not None


class TestFactoryAgentCreation:
    """Test agent creation through the factory."""

    def test_create_agent_basic(self) -> None:
        """Test creating a basic agent through the factory."""
        factory = AgentFactory()

        # Register a test agent type first
        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgentClass(BaseAgent):
            def __init__(self, metadata: Any, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)

            def initialize(self) -> None:
                pass

            def validate(self) -> bool:
                return True

            def prepare(self) -> None:
                pass

            def execute(self, context: Any) -> Any:
                from app.core.agent_framework.shared_models import AgentResult

                return AgentResult(agent_id=self.metadata.id, success=True)

            def finalize(self, result: Any) -> None:
                pass

            def health_check(self) -> Any:
                from app.core.agent_framework.shared_models import AgentHealthInfo

                return AgentHealthInfo(healthy=True)

            def cleanup(self) -> None:
                pass

        factory.register_agent_type("test", TestAgentClass)

        agent = factory.create_agent(
            agent_type="test",
            agent_id="factory-001",
            display_name="Factory Test Agent",
            version="2.0.0",
            author="Test Corp",
            description="An agent created via the factory",
            timeout=30,
        )

        assert agent is not None
        assert agent.metadata.id == "factory-001"
        assert agent.metadata.display_name == "Factory Test Agent"
        assert agent.metadata.version == "2.0.0"
        assert agent.metadata.author == "Test Corp"
        assert agent.metadata.description == "An agent created via the factory"
        assert agent.status.value == "pending"
        assert agent.health.value == "unknown"
        assert agent.get_configuration("timeout") == 30

    def test_create_agent_with_configuration(self) -> None:
        """Test creating an agent with configuration parameters."""
        factory = AgentFactory()

        # Register a test agent type first
        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgentClass(BaseAgent):
            def __init__(self, metadata: Any, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)

            def initialize(self) -> None:
                pass

            def validate(self) -> bool:
                return True

            def prepare(self) -> None:
                pass

            def execute(self, context: Any) -> Any:
                from app.core.agent_framework.shared_models import AgentResult

                return AgentResult(agent_id=self.metadata.id, success=True)

            def finalize(self, result: Any) -> None:
                pass

            def health_check(self) -> Any:
                from app.core.agent_framework.shared_models import AgentHealthInfo

                return AgentHealthInfo(healthy=True)

            def cleanup(self) -> None:
                pass

        factory.register_agent_type("test", TestAgentClass)

        agent = factory.create_agent(
            agent_type="test",
            agent_id="config-001",
            display_name="Config Agent",
            learning_rate=0.01,
            max_iterations=100,
            debug_mode=True,
        )

        assert agent.metadata.id == "config-001"
        # Configuration should be accessible as agent attributes
        assert hasattr(agent, "_learning_rate") or hasattr(agent, "learning_rate")


class TestFactoryAgentTypeRegistration:
    """Test agent type registration and lookup."""

    def test_register_agent_type(self) -> None:
        """Test registering an agent type with the factory."""
        factory = AgentFactory()

        class TestAgentClass(BaseAgent):
            def __init__(self, metadata: Any, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)

            def initialize(self) -> None:
                pass

            def validate(self) -> bool:
                return True

            def prepare(self) -> None:
                pass

            def execute(self, context: Any) -> Any:
                from app.core.agent_framework.shared_models import AgentResult

                return AgentResult(agent_id=self.metadata.id, success=True)

            def finalize(self, result: Any) -> None:
                pass

            def health_check(self) -> Any:
                from app.core.agent_framework.shared_models import AgentHealthInfo

                return AgentHealthInfo(healthy=True)

            def cleanup(self) -> None:
                pass

        factory.register_agent_type("my_custom", TestAgentClass)

        agent = factory.create_agent(
            agent_type="my_custom",
            agent_id="registered-001",
            display_name="Registered Agent",
        )

        assert agent.metadata.id == "registered-001"
        assert isinstance(agent, TestAgentClass)

    def test_create_agent_unknown_type_raises(self) -> None:
        """Test that creating an unknown agent type raises ValueError."""
        factory = AgentFactory()

        with pytest.raises(ValueError, match="Unknown agent type"):
            factory.create_agent(
                agent_type="unknown_type",
                agent_id="test",
                display_name="Test",
            )


class TestFactoryCreateFromMetadata:
    """Test creating agents from metadata."""

    def test_create_from_metadata(self) -> None:
        """Test creating an agent from metadata and a specific class."""
        factory = AgentFactory()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgentClass(BaseAgent):
            def __init__(self, metadata: Any, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)

            def initialize(self) -> None:
                pass

            def validate(self) -> bool:
                return True

            def prepare(self) -> None:
                pass

            def execute(self, context: Any) -> Any:
                from app.core.agent_framework.shared_models import AgentResult

                return AgentResult(agent_id=self.metadata.id, success=True)

            def finalize(self, result: Any) -> None:
                pass

            def health_check(self) -> Any:
                from app.core.agent_framework.shared_models import AgentHealthInfo

                return AgentHealthInfo(healthy=True)

            def cleanup(self) -> None:
                pass

        metadata = AgentMetadata(
            id="from-meta-001",
            display_name="From Meta Agent",
        )

        agent = factory.create_from_metadata(
            metadata=metadata,
            agent_class=TestAgentClass,
        )

        assert agent.metadata.id == "from-meta-001"
        assert isinstance(agent, TestAgentClass)


class TestFactoryConvenienceFunction:
    """Test the convenience factory function."""

    def test_factory_convenience_function(self) -> None:
        """Test the create_agent convenience function."""
        factory = AgentFactory()

        # Register a test agent type first
        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgentClass(BaseAgent):
            def __init__(self, metadata: Any, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)

            def initialize(self) -> None:
                pass

            def validate(self) -> bool:
                return True

            def prepare(self) -> None:
                pass

            def execute(self, context: Any) -> Any:
                from app.core.agent_framework.shared_models import AgentResult

                return AgentResult(agent_id=self.metadata.id, success=True)

            def finalize(self, result: Any) -> None:
                pass

            def health_check(self) -> Any:
                from app.core.agent_framework.shared_models import AgentHealthInfo

                return AgentHealthInfo(healthy=True)

            def cleanup(self) -> None:
                pass

        factory.register_agent_type("test", TestAgentClass)

        agent = factory_create_agent(
            factory=factory,
            agent_type="test",
            agent_id="conv-001",
            display_name="Convenience Agent",
            description="Test via convenience function",
        )

        assert agent is not None
        assert agent.metadata.id == "conv-001"
        assert agent.metadata.display_name == "Convenience Agent"


class TestFactoryAgentLifecycleIntegration:
    """Test factory integration with agent lifecycle."""

    def test_factory_registers_with_registry(self) -> None:
        """Test that factory-created agents are registered with the registry."""
        factory = AgentFactory()

        # Register a test agent type first
        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgentClass(BaseAgent):
            def __init__(self, metadata: Any, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)

            def initialize(self) -> None:
                pass

            def validate(self) -> bool:
                return True

            def prepare(self) -> None:
                pass

            def execute(self, context: Any) -> Any:
                from app.core.agent_framework.shared_models import AgentResult

                return AgentResult(agent_id=self.metadata.id, success=True)

            def finalize(self, result: Any) -> None:
                pass

            def health_check(self) -> Any:
                from app.core.agent_framework.shared_models import AgentHealthInfo

                return AgentHealthInfo(healthy=True)

            def cleanup(self) -> None:
                pass

        factory.register_agent_type("test", TestAgentClass)

        agent = factory.create_agent(
            agent_type="test",
            agent_id="lifecycle-001",
            display_name="Lifecycle Test",
        )

        # Agent should be registered with the registry

        registry = get_registry()
        assert registry.contains("lifecycle-001")


class TestFactoryEdgeCases:
    """Test edge cases for the factory."""

    def test_create_agent_empty_configuration(self) -> None:
        """Test creating an agent with no configuration."""
        factory = AgentFactory()

        # Register a test agent type first
        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgentClass(BaseAgent):
            def __init__(self, metadata: Any, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)

            def initialize(self) -> None:
                pass

            def validate(self) -> bool:
                return True

            def prepare(self) -> None:
                pass

            def execute(self, context: Any) -> Any:
                from app.core.agent_framework.shared_models import AgentResult

                return AgentResult(agent_id=self.metadata.id, success=True)

            def finalize(self, result: Any) -> None:
                pass

            def health_check(self) -> Any:
                from app.core.agent_framework.shared_models import AgentHealthInfo

                return AgentHealthInfo(healthy=True)

            def cleanup(self) -> None:
                pass

        factory.register_agent_type("test", TestAgentClass)

        agent = factory.create_agent(
            agent_type="test",
            agent_id="no-config-001",
            display_name="No Config Agent",
        )

        assert agent is not None
        assert agent.metadata.id == "no-config-001"

    def test_create_agent_with_all_parameters(self) -> None:
        """Test creating an agent with all optional parameters."""
        factory = AgentFactory()

        # Register a test agent type first
        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgentClass(BaseAgent):
            def __init__(self, metadata: Any, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)

            def initialize(self) -> None:
                pass

            def validate(self) -> bool:
                return True

            def prepare(self) -> None:
                pass

            def execute(self, context: Any) -> Any:
                from app.core.agent_framework.shared_models import AgentResult

                return AgentResult(agent_id=self.metadata.id, success=True)

            def finalize(self, result: Any) -> None:
                pass

            def health_check(self) -> Any:
                from app.core.agent_framework.shared_models import AgentHealthInfo

                return AgentHealthInfo(healthy=True)

            def cleanup(self) -> None:
                pass

        factory.register_agent_type("test", TestAgentClass)

        agent = factory.create_agent(
            agent_type="test",
            agent_id="all-params-001",
            display_name="All Params Agent",
            version="3.5.0",
            author="Acme Inc.",
            description="An agent with all parameters set",
            timeout=60,
            verbose=True,
            retry_count=3,
        )

        assert agent.metadata.version == "3.5.0"
        assert agent.metadata.author == "Acme Inc."
        assert agent.metadata.description == "An agent with all parameters set"
