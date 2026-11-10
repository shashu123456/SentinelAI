from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum

from app.core.agent_framework.shared_models import (
    AgentMetadata,
)


class RegistryScope(Enum):
    """Scope of agent registration."""

    GLOBAL = "global"
    INSTANCE = "instance"
    PLUGIN = "plugin"


@dataclass
class AgentRegistry:
    """Registry managing agent discovery and lookup.

    The registry is the single source of truth for agent discovery.
    It supports:
        - Registering agents by metadata ID
        - Looking up agents by ID
        - Finding agents by capability
        - Listing all registered agents
        - Agent lifecycle management

    Thread-safe for concurrent access.
    """

    _agents: dict[str, BaseAgent] = field(default_factory=dict, repr=False)
    _scope: RegistryScope = field(default=RegistryScope.GLOBAL, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def register(self, agent: BaseAgent, scope: RegistryScope = RegistryScope.GLOBAL) -> None:
        """Register an agent in the registry.

        Args:
            agent: The agent instance to register.
            scope: The registration scope (global, instance, or plugin).

        Raises:
            ValueError: If an agent with the same ID already exists.
        """
        with self._lock:
            agent_id = agent.metadata.id
            if agent_id in self._agents and self._agents[agent_id] is not agent:
                raise ValueError(f"Agent ID already registered: {agent_id}")
            agent._scope = scope
            self._agents[agent_id] = agent

    def unregister(self, agent_id: str) -> BaseAgent | None:
        """Unregister an agent from the registry.

        Args:
            agent_id: The agent's unique ID.

        Returns:
            The unregistered agent instance, or None if not found.
        """
        with self._lock:
            return self._agents.pop(agent_id, None)

    def get(self, agent_id: str) -> BaseAgent | None:
        """Get an agent by its unique ID.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            The agent instance, or None if not found.
        """
        with self._lock:
            return self._agents.get(agent_id)

    def find_by_capability(self, capability_name: str) -> list[BaseAgent]:
        """Find all agents that have a specific capability.

        Args:
            capability_name: The capability name to search for.

        Returns:
            List of agents matching the capability.
        """
        with self._lock:
            matching: list[BaseAgent] = []
            for agent in self._agents.values():
                capabilities = getattr(agent, "capabilities", []) or []
                if capability_name in capabilities:
                    matching.append(agent)
            return matching

    def find_by_file_type(self, file_type: str) -> list[BaseAgent]:
        """Find all agents that support a specific file type.

        Args:
            file_type: The file extension or type (e.g., ".py", ".js").

        Returns:
            List of agents supporting the file type.
        """
        with self._lock:
            matching: list[BaseAgent] = []
            for agent in self._agents.values():
                supported = getattr(agent, "supported_file_types", set()) or set()
                if file_type in supported:
                    matching.append(agent)
            return matching

    def list_all(self) -> list[BaseAgent]:
        """List all registered agents.

        Returns:
            List of all registered agent instances.
        """
        with self._lock:
            return list(self._agents.values())

    def list_metadata(self) -> list[AgentMetadata]:
        """List metadata for all registered agents.

        Returns:
            List of AgentMetadata instances.
        """
        with self._lock:
            return [agent.metadata for agent in self._agents.values()]

    def count(self) -> int:
        """Get the number of registered agents.

        Returns:
            Number of registered agents.
        """
        with self._lock:
            return len(self._agents)

    def contains(self, agent_id: str) -> bool:
        """Check if an agent ID is registered.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            True if the agent is registered, False otherwise.
        """
        with self._lock:
            return agent_id in self._agents

    def get_agents_by_scope(self, scope: RegistryScope) -> list[BaseAgent]:
        """Get all agents registered under a specific scope.

        Args:
            scope: The scope to filter by.

        Returns:
            List of agents with the given scope.
        """
        with self._lock:
            return [
                agent
                for agent in self._agents.values()
                if getattr(agent, "_scope", RegistryScope.GLOBAL) == scope
            ]

    def refresh(self) -> None:
        """Refresh the registry state.

        This can be called by plugins to re-scan for newly available agents.
        """
        with self._lock:
            # Reset internal state; plugins should re-register
            self._agents.clear()


# ------------------------------------------------------------------ #
# Convenience Functions
# ------------------------------------------------------------------ #


_registry_instance: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """Get the global agent registry instance.

    Returns:
        The global AgentRegistry instance.
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentRegistry()
    return _registry_instance


def reset_registry() -> None:
    """Reset the global registry instance.

    Useful for testing.
    """
    global _registry_instance
    _registry_instance = None
