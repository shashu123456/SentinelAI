"""Unit tests for the AgentRegistry class.

Tests cover agent registration, lookup, capability searching,
and scope management.
.. moduleauthor:: SentinelAI Team
.. versionadded:: 2.0.0
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.agent_framework.agent_registry import (
    AgentRegistry,
    RegistryScope,
    get_registry,
    reset_registry,
)
from app.core.agent_framework.shared_models import (
    AgentMetadata,
)


class TestRegistryInitialization:
    """Test registry initialization and singleton behavior."""

    def test_default_registry_creation(self) -> None:
        """Test that a default registry can be created."""
        registry = AgentRegistry()
        assert registry is not None
        assert registry.count() == 0

    def test_global_registry_singleton(self) -> None:
        """Test that get_registry returns the same instance."""
        reset_registry()
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    def test_reset_registry(self) -> None:
        """Test that reset_registry clears the singleton."""
        reset_registry()
        registry = get_registry()
        assert registry.count() == 0


class TestRegistryRegistration:
    """Test agent registration functionality."""

    def test_register_agent(self) -> None:
        """Test registering an agent."""
        registry = AgentRegistry()
        metadata = AgentMetadata(
            id="test-agent-001",
            display_name="Test Agent",
        )

        # Create a concrete agent for testing
        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        agent = TestAgent(metadata=metadata)
        registry.register(agent, scope=RegistryScope.GLOBAL)
        assert registry.contains("test-agent-001")
        assert registry.count() == 1

    def test_register_duplicate_agent_raises(self) -> None:
        """Test that registering a duplicate agent raises ValueError."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        metadata1 = AgentMetadata(id="dup-agent", display_name="First")
        metadata2 = AgentMetadata(id="dup-agent", display_name="Second")  # Same ID

        agent1 = TestAgent(metadata=metadata1)
        agent2 = TestAgent(metadata=metadata2)

        registry.register(agent1)
        with pytest.raises(ValueError, match="Agent ID already registered"):
            registry.register(agent2)

    def test_unregister_agent(self) -> None:
        """Test unregistering an agent."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        metadata = AgentMetadata(id="unreg-agent", display_name="Unregister Me")
        agent = TestAgent(metadata=metadata)
        registry.register(agent)

        unregistered = registry.unregister("unreg-agent")
        assert unregistered is not None
        assert registry.count() == 0

    def test_unregister_nonexistent_agent(self) -> None:
        """Test unregistering an agent that doesn't exist."""
        registry = AgentRegistry()
        result = registry.unregister("nonexistent")
        assert result is None


class TestRegistryLookup:
    """Test agent lookup functionality."""

    def test_get_agent(self) -> None:
        """Test getting an agent by ID."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        metadata = AgentMetadata(id="lookup-agent", display_name="Lookup Me")
        agent = TestAgent(metadata=metadata)
        registry.register(agent)

        retrieved = registry.get("lookup-agent")
        assert retrieved is agent

    def test_get_nonexistent_agent(self) -> None:
        """Test getting an agent that doesn't exist."""
        registry = AgentRegistry()
        result = registry.get("nonexistent")
        assert result is None

    def test_contains_agent(self) -> None:
        """Test contains check."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        metadata = AgentMetadata(id="contains-agent", display_name="Contains Me")
        agent = TestAgent(metadata=metadata)
        registry.register(agent)

        assert registry.contains("contains-agent")
        assert not registry.contains("other-agent")


class TestRegistryCapabilitySearch:
    """Test capability-based agent searching."""

    def test_find_by_capability(self) -> None:
        """Test finding agents by capability."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent1(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)
                self.capabilities = ["sql-injection", "xss"]

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

        class TestAgent2(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)
                self.capabilities = ["ssrf", "cors"]

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

        # Register agents with different capabilities
        metadata1 = AgentMetadata(id="agent-1", display_name="Agent 1")
        agent1 = TestAgent1(metadata=metadata1)
        registry.register(agent1, scope=RegistryScope.GLOBAL)

        metadata2 = AgentMetadata(id="agent-2", display_name="Agent 2")
        agent2 = TestAgent2(metadata=metadata2)
        registry.register(agent2, scope=RegistryScope.GLOBAL)

        # Find agents with "sql-injection" capability
        found = registry.find_by_capability("sql-injection")
        assert len(found) == 1
        assert found[0].metadata.id == "agent-1"

        # Find agents with "ssrf" capability
        found = registry.find_by_capability("ssrf")
        assert len(found) == 1
        assert found[0].metadata.id == "agent-2"

        # Find agents with non-existent capability
        found = registry.find_by_capability("nonexistent")
        assert len(found) == 0

    def test_find_by_file_type(self) -> None:
        """Test finding agents by supported file type."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class PythonAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)
                self.supported_file_types = {".py", ".pyw"}

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

        class JavaAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
                super().__init__(metadata=metadata, **kwargs)
                self.supported_file_types = {".java"}

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

        # Register agents with different file type support
        metadata1 = AgentMetadata(id="py-agent", display_name="Python Agent")
        py_agent = PythonAgent(metadata=metadata1)
        registry.register(py_agent, scope=RegistryScope.GLOBAL)

        metadata2 = AgentMetadata(id="java-agent", display_name="Java Agent")
        java_agent = JavaAgent(metadata=metadata2)
        registry.register(java_agent, scope=RegistryScope.GLOBAL)

        # Find agents supporting .py
        found = registry.find_by_file_type(".py")
        assert len(found) == 1
        assert found[0].metadata.id == "py-agent"

        # Find agents supporting .java
        found = registry.find_by_file_type(".java")
        assert len(found) == 1
        assert found[0].metadata.id == "java-agent"

        # Find agents supporting .js (none)
        found = registry.find_by_file_type(".js")
        assert len(found) == 0


class TestRegistryListing:
    """Test agent listing functionality."""

    def test_list_all_agents(self) -> None:
        """Test listing all registered agents."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        # Register multiple agents
        for i in range(3):
            metadata = AgentMetadata(id=f"list-agent-{i}", display_name=f"List Agent {i}")
            agent = TestAgent(metadata=metadata)
            registry.register(agent)

        agents = registry.list_all()
        assert len(agents) == 3

    def test_list_metadata(self) -> None:
        """Test listing agent metadata."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        # Register agents with different metadata
        for i, desc in enumerate(["first", "second", "third"]):
            metadata = AgentMetadata(
                id=f"meta-agent-{i}",
                display_name=f"Metadata Agent {desc}",
                version="1.0.0",
                author="Test Author",
                description=f"Description for agent {desc}",
            )
            agent = TestAgent(metadata=metadata)
            registry.register(agent)

        metadata_list = registry.list_metadata()
        assert len(metadata_list) == 3
        assert metadata_list[0].display_name == "Metadata Agent first"


class TestRegistryScope:
    """Test registry scope functionality."""

    def test_scope_assignment(self) -> None:
        """Test that agents are assigned a scope."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        metadata = AgentMetadata(id="scope-agent", display_name="Scope Agent")
        agent = TestAgent(metadata=metadata)

        # Register with global scope
        registry.register(agent, scope=RegistryScope.GLOBAL)
        global_agents = registry.get_agents_by_scope(RegistryScope.GLOBAL)
        assert len(global_agents) == 1

    def test_plugin_scope(self) -> None:
        """Test plugin scope registration."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        metadata = AgentMetadata(id="plugin-agent", display_name="Plugin Agent")
        agent = TestAgent(metadata=metadata)

        # Register with plugin scope
        registry.register(agent, scope=RegistryScope.PLUGIN)
        plugin_agents = registry.get_agents_by_scope(RegistryScope.PLUGIN)
        assert len(plugin_agents) == 1


class TestRegistryRefresh:
    """Test registry refresh functionality."""

    def test_refresh_clears_agents(self) -> None:
        """Test that refresh clears all agents."""
        registry = AgentRegistry()

        from app.core.agent_framework.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def __init__(self, metadata: AgentMetadata, **kwargs: Any) -> None:
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

        metadata = AgentMetadata(id="refresh-agent", display_name="Refresh Agent")
        agent = TestAgent(metadata=metadata)
        registry.register(agent)

        assert registry.count() == 1

        registry.refresh()
        assert registry.count() == 0
