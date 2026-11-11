"""Shared data models for the SentinelAI Agent Framework.

These models are the foundation for every current and future security capability.
.. moduleauthor:: SentinelAI Team
.. versionadded:: 2.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Status of an agent during its lifecycle."""

    PENDING = "pending"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SHUTDOWN = "shutdown"


class AgentHealth(str, Enum):
    """Health state of an agent."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class AgentMetadata:
    """Metadata describing an agent."""

    id: str
    display_name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    supported_file_types: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)


@dataclass
class AgentContext:
    """Context passed to an agent during its lifecycle."""

    agent_id: str
    request_id: str | None = None
    configuration: dict[str, Any] = field(default_factory=dict)
    working_directory: str | None = None
    timeout: float | None = None
    stop_event: Any | None = None


@dataclass
class AgentResult:
    """Result returned by an agent after execution."""

    agent_id: str
    success: bool
    findings: list[dict[str, Any]] = field(default_factory=list)
    output: dict[str, Any] | None = None
    error: str | None = None
    metrics: dict[str, Any] | None = None
    execution_time: float | None = None


@dataclass
class AgentCapability:
    """Capability description for an agent."""

    name: str
    description: str = ""
    version: str = "1.0.0"
    confidence: float = 1.0
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentHealthInfo:
    """Health information for an agent."""

    healthy: bool = True
    last_check: float | None = None
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecutionHistory:
    """Execution history record for an agent."""

    agent_id: str
    request_id: str | None = None
    status: AgentStatus = AgentStatus.PENDING
    started_at: float | None = None
    completed_at: float | None = None
    duration: float | None = None
    findings_count: int = 0
    error: str | None = None


class EventType(str, Enum):
    """Typed event types for the agent event bus."""

    AGENT_INITIALIZED = "agent.initialized"
    AGENT_STARTED = "agent.started"
    AGENT_PROGRESS = "agent.progress"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_CANCELLED = "agent.cancelled"
    AGENT_HEALTH_CHANGED = "agent.health_changed"
    AGENT_SHUTDOWN = "agent.shutdown"


@dataclass
class AgentEvent:
    """Typed event published through the event bus."""

    event_type: EventType
    agent_id: str
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    source: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


def create_agent_metadata(
    agent_id: str,
    display_name: str,
    version: str = "1.0.0",
    author: str = "",
    description: str = "",
    capabilities: list[str] | None = None,
    supported_file_types: set[str] | None = None,
) -> AgentMetadata:
    """Factory function to create agent metadata."""
    return AgentMetadata(
        id=agent_id,
        display_name=display_name,
        version=version,
        author=author,
        description=description,
        capabilities=capabilities or [],
        supported_file_types=supported_file_types or set(),
    )


def create_agent_context(
    agent_id: str,
    configuration: dict[str, Any] | None = None,
    working_directory: str | None = None,
    timeout: float | None = None,
) -> AgentContext:
    """Factory function to create agent context."""
    return AgentContext(
        agent_id=agent_id,
        configuration=configuration or {},
        working_directory=working_directory,
        timeout=timeout,
    )


def create_agent_result(
    agent_id: str,
    success: bool,
    findings: list[dict[str, Any]] | None = None,
    error: str | None = None,
    metrics: dict[str, Any] | None = None,
    execution_time: float | None = None,
) -> AgentResult:
    """Factory function to create agent result."""
    return AgentResult(
        agent_id=agent_id,
        success=success,
        findings=findings or [],
        error=error,
        metrics=metrics or {},
        execution_time=execution_time,
    )
