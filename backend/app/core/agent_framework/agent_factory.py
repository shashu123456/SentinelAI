from __future__ import annotations

from typing import Any

from app.core.agent_framework.agent_registry import get_registry
from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.shared_models import (
    AgentMetadata,
)


class AgentFactory:
    """Factory for creating and configuring agent instances.

    The factory handles:
        - Agent type registration and lookup
        - Agent instance creation with metadata
        - Configuration injection
        - Event bus wiring
        - Lifecycle management

    Supports both concrete agent classes and plugin-discovered agents.
    """

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        """Initialize the agent factory.

        Args:
            registry: Optional AgentRegistry instance. If None, uses the global registry.
        """
        self._registry: AgentRegistry = registry if registry is not None else get_registry()
        self._factory_registry: dict[str, type[BaseAgent]] = {}

    def register_agent_type(self, agent_type: str, agent_class: type[BaseAgent]) -> None:
        """Register an agent class for a given type name.

        Args:
            agent_type: The type/name to associate with the class.
            agent_class: The BaseAgent subclass to instantiate.
        """
        self._factory_registry[agent_type] = agent_class

    def create_agent(
        self,
        agent_type: str,
        agent_id: str,
        display_name: str,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
        **configuration: Any,
    ) -> BaseAgent:
        """Create a new agent instance of the given type.

        Args:
            agent_type: The type of agent to create.
            agent_id: Unique identifier for the new agent instance.
            display_name: Human-readable agent name.
            version: Agent version string.
            author: Agent author/organization.
            description: Agent description.
            **configuration: Agent-specific configuration parameters.

        Returns:
            A new BaseAgent instance configured with the given parameters.

        Raises:
            ValueError: If the agent_type is not registered.
        """
        agent_class = self._get_agent_class(agent_type)
        metadata = AgentMetadata(
            id=agent_id,
            display_name=display_name,
            version=version,
            author=author,
            description=description,
        )

        agent: BaseAgent = agent_class(
            metadata=metadata,
            **configuration,
        )

        # Register with the registry
        self._registry.register(agent, scope=AgentFactory._determine_scope(agent))

        return agent

    def create_from_metadata(
        self,
        metadata: AgentMetadata,
        agent_class: type[BaseAgent],
        **configuration: Any,
    ) -> BaseAgent:
        """Create an agent from existing metadata and a specific class.

        Args:
            metadata: The AgentMetadata for the agent.
            agent_class: The BaseAgent subclass to instantiate.
            **configuration: Additional configuration parameters.

        Returns:
            A new BaseAgent instance.
        """
        agent: BaseAgent = agent_class(
            metadata=metadata,
            **configuration,
        )
        self._registry.register(agent, scope=AgentFactory._determine_scope(agent))
        return agent

    def _get_agent_class(self, agent_type: str) -> type[BaseAgent]:
        """Get the agent class for the given type.

        Args:
            agent_type: The type name to look up.

        Returns:
            The BaseAgent subclass.

        Raises:
            ValueError: If the agent_type is not registered.
        """
        agent_class = self._factory_registry.get(agent_type)
        if agent_class is None:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return agent_class

    @staticmethod
    def _determine_scope(agent: BaseAgent) -> str:
        """Determine the registry scope for an agent.

        Args:
            agent: The agent instance.

        Returns:
            The RegistryScope value as string.
        """
        # Default to global; subclasses can override
        return "global"


# ------------------------------------------------------------------ #
# Convenience Functions
# ------------------------------------------------------------------ #


def create_agent(
    factory: AgentFactory,
    agent_type: str,
    agent_id: str,
    display_name: str,
    version: str = "1.0.0",
    author: str = "",
    description: str = "",
    **configuration: Any,
) -> BaseAgent:
    """Convenience function to create an agent using a factory.

    Args:
        factory: The AgentFactory instance.
        agent_type: The type of agent to create.
        agent_id: Unique identifier for the new agent instance.
        display_name: Human-readable agent name.
        version: Agent version string.
        author: Agent author/organization.
        description: Agent description.
        **configuration: Agent-specific configuration parameters.

    Returns:
        A new BaseAgent instance.
    """
    return factory.create_agent(
        agent_type=agent_type,
        agent_id=agent_id,
        display_name=display_name,
        version=version,
        author=author,
        description=description,
        **configuration,
    )
