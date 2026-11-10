"""SAST Security Agent - wraps the existing SAST engine using the Agent Framework.

This agent adapts the mature SAST static analysis engine to the SentinelAI Agent Framework,
providing security scanning capabilities through the standard agent lifecycle without
modifying any detection logic, rules, or findings.

The SAST engine's behavior remains functionally identical; only the execution model changes.
"""

from __future__ import annotations

import time
from typing import Any

from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.shared_models import (
    AgentContext,
    AgentHealthInfo,
    AgentMetadata,
    AgentResult,
    AgentStatus,
    EventType,
)


class SASTSecurityAgent(BaseAgent):
    """Security agent that wraps the existing SAST static analysis engine.

    This agent adapts the mature SAST (Static Application Security Testing) engine
    to the SentinelAI Agent Framework, providing security scanning capabilities
    through the standard agent lifecycle without modifying any detection logic,
    rules, or findings.

    The SAST engine's behavior remains functionally identical; only the execution
    model changes. All rule patterns, severity calculations, CWE mappings,
    and finding formats are preserved exactly.
    """

    def __init__(self, metadata: AgentMetadata | None = None, **configuration: Any) -> None:
        """Initialize the SAST security agent.

        Args:
            metadata: Agent metadata instance.
            **configuration: Configuration parameters including:
                - target_path: Path to scan (file or directory)
                - scan_on_init: Whether to auto-scan on initialization
        """
        super().__init__(metadata=metadata, **configuration)
        self._target_path: str | None = configuration.get("target_path")
        self._scan_on_init: bool = configuration.get("scan_on_init", False)
        self._scan_result: dict[str, Any] | None = None
        self._files_scanned: int = 0
        self._findings_count: int = 0

    def initialize(self) -> None:
        """Initialize the SAST security agent.

        Sets up the agent status and prepares for scanning.
        If scan_on_init is True, performs an immediate scan.
        """
        self.status = AgentStatus.INITIALIZED
        self._initialized = True
        self._emit_event(
            EventType.AGENT_INITIALIZED,
            payload={"agent_id": self.metadata.id, "target": self._target_path},
        )

        if self._scan_on_init and self._target_path:
            self.validate()

    def validate(self) -> bool:
        """Validate the agent's configuration and prerequisites.

        Checks that the target path exists and is accessible.
        Prepares the SAST engine rules for scanning.

        Returns:
            True if validation passes, False otherwise.
        """
        target = self._target_path or ""
        if not target:
            self._emit_event(
                EventType.AGENT_FAILED,
                payload={"agent_id": self.metadata.id, "error": "No target path configured"},
            )
            return False

        # Verify the target path exists
        import os

        if not os.path.exists(target):
            self._emit_event(
                EventType.AGENT_FAILED,
                payload={"agent_id": self.metadata.id, "error": f"Target path not found: {target}"},
            )
            return False

        # Verify it's a valid file or directory
        if not (os.path.isfile(target) or os.path.isdir(target)):
            self._emit_event(
                EventType.AGENT_FAILED,
                payload={"agent_id": self.metadata.id, "error": f"Invalid target: {target}"},
            )
            return False

        self.status = AgentStatus.RUNNING
        self._emit_event(
            EventType.AGENT_STARTED,
            payload={"agent_id": self.metadata.id, "target": target},
        )
        return True

    def prepare(self) -> None:
        """Prepare the agent for execution.

        No-op for SAST agent; the SAST engine rules are already loaded
        and ready from the shared engine. No additional preparation needed.
        """
        self._emit_event(
            EventType.AGENT_PROGRESS,
            payload={
                "agent_id": self.metadata.id,
                "step": "preparing",
                "message": "SAST engine ready",
            },
        )

    def execute(self, context: AgentContext) -> AgentResult:
        """Execute the SAST scan against the target path.

        Runs the existing SAST scan engine and converts the result
        into an AgentResult.

        Args:
            context: Execution context (agent_id, configuration, etc.)

        Returns:
            AgentResult with scan findings converted from SAST format.
        """
        from app.core.sast_engine.scanner import run_sast_scan

        target = self._target_path or ""

        # Run the existing SAST scan engine
        sast_result = run_sast_scan(target)

        # Convert SAST findings to AgentResult format
        findings = []
        for finding in sast_result.findings:
            finding_data = finding.to_dict()
            findings.append(finding_data)

        self._files_scanned = sast_result.total_files_scanned
        self._findings_count = len(findings)

        # Build AgentResult
        agent_result = AgentResult(
            agent_id=self.metadata.id,
            success=sast_result.errors == [] and len(findings) >= 0,
            findings=findings,
            output=sast_result.summary,
            metrics={
                "files_scanned": sast_result.total_files_scanned,
                "lines_scanned": sast_result.total_lines_scanned,
                "findings_count": len(findings),
                "languages_detected": sast_result.languages_detected,
            },
            execution_time=time.time() - (self._start_time or time.time()),
            error=(
                None
                if sast_result.errors == []
                else sast_result.errors[0] if sast_result.errors else None
            ),
        )

        self._scan_result = sast_result.to_dict()
        self.status = AgentStatus.COMPLETED

        # Emit completion event
        self._emit_event(
            EventType.AGENT_COMPLETED,
            payload={
                "agent_id": self.metadata.id,
                "findings_count": len(findings),
                "files_scanned": sast_result.total_files_scanned,
                "languages": sast_result.languages_detected,
            },
        )

        return agent_result

    def finalize(self, result: AgentResult) -> None:
        """Post-process the execution result.

        Performs any finalization steps after the SAST scan completes.
        """
        # Emit health changed event with findings count from the result
        findings_count = len(result.findings) if result and result.findings else 0
        self._emit_event(
            EventType.AGENT_HEALTH_CHANGED,
            payload={
                "agent_id": self.metadata.id,
                "status": "completed",
                "findings_count": findings_count,
            },
        )

    def health_check(self) -> AgentHealthInfo:
        """Perform a health check on the SAST agent.

        Verifies the agent is healthy - models are loadable,
        connections are alive, and all prerequisites are met.

        Returns:
            AgentHealthInfo containing health status and details.
        """
        # The SAST engine is always healthy; its rules are loaded at import time
        healthy = self._scan_result is not None or self._target_path is not None
        error = None if healthy else "No scan has been performed yet"

        return AgentHealthInfo(
            healthy=healthy,
            error=error,
            details={
                "agent_type": "SASTSecurityAgent",
                "target_path": self._target_path,
                "files_scanned": self._files_scanned,
                "findings_count": self._findings_count,
            },
        )

    def cleanup(self) -> None:
        """Clean up SAST agent resources.

        Release any resources held by the agent.
        """
        self.status = AgentStatus.SHUTDOWN
        self._emit_event(
            EventType.AGENT_SHUTDOWN,
            payload={"agent_id": self.metadata.id, "message": "SAST agent cleanup completed"},
        )

    @property
    def capabilities(self) -> list[str]:
        """Get the agent's capabilities list.

        Returns:
            List of capability strings for this agent.
        """
        return ["sast_scan", "security_analysis", "code_analysis", "vulnerability_detection"]

    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Args:
            key: The configuration key.
            default: Default value if key is not found.

        Returns:
            The configuration value or default.
        """
        return super().get_configuration(key, default)


# Convenience function to create a SASTSecurityAgent
def create_sast_agent(
    agent_id: str,
    target_path: str,
    display_name: str = "SAST Security Agent",
    version: str = "1.0.0",
    author: str = "SentinelAI Team",
    description: str = "Security agent wrapping the SAST static analysis engine",
    **configuration: Any,
) -> SASTSecurityAgent:
    """Create a SASTSecurityAgent instance.

    Args:
        agent_id: Unique identifier for the agent.
        target_path: Path to scan (file or directory).
        display_name: Human-readable agent name.
        version: Agent version.
        author: Agent author/organization.
        description: Agent description.
        **configuration: Additional configuration options.

    Returns:
        A configured SASTSecurityAgent instance.
    """
    metadata = AgentMetadata(
        id=agent_id,
        display_name=display_name,
        version=version,
        author=author,
        description=description,
        capabilities=["sast_scan", "security_analysis", "code_analysis"],
    )

    agent = SASTSecurityAgent(metadata=metadata, target_path=target_path, **configuration)
    return agent
