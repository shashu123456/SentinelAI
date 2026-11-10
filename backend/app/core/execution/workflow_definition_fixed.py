"""WorkflowDefinition — Defines and validates execution workflows.

Responsibilities:
• Define workflow YAML/JSON schema with full type validation
• Support versioned workflow definitions
• Provide agent definitions and references
• Manage dependency declarations between agents
• Define sequential and parallel execution groups
• Support conditional execution branches
• Configure retry and timeout policies
• Handle variable substitution and parameter inheritance
• Support environment overrides
• Enable metadata and tagging
• Enable serialization/deserialization with backward compatibility
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T", bound="WorkflowDefinition")


class WorkflowStatus(str, Enum):
    """Status of a workflow definition."""

    VALID = "valid"
    INVALID = "invalid"
    DEPRECATED = "deprecated"
    LOADED = "loaded"


class ExecutionMode(str, Enum):
    """Execution mode for workflow groups."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"


class ConditionOperator(str, Enum):
    """Condition operators for conditional execution."""

    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"


@dataclass
class WorkflowAgentReference:
    """Reference to an agent within a workflow."""

    name: str
    agent_type: str
    config: dict[str, Any] = field(default_factory=dict)
    timeout: float | None = None
    retry: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "config": self.config,
            "timeout": self.timeout,
            "retry": self.retry,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowAgentReference:
        return cls(
            name=data.get("name", ""),
            agent_type=data.get("agent_type", ""),
            config=data.get("config", {}),
            timeout=data.get("timeout"),
            retry=data.get("retry"),
        )


@dataclass
class WorkflowExecutionGroup:
    """An execution group with mode (sequential/parallel) and conditions."""

    name: str
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    agents: list[WorkflowAgentReference] = field(default_factory=list)
    condition: dict[str, Any] | None = None
    timeout: float | None = None
    retry: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mode": self.mode.value,
            "agents": [a.to_dict() for a in self.agents],
            "condition": self.condition,
            "timeout": self.timeout,
            "retry": self.retry,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowExecutionGroup:
        mode = ExecutionMode(data.get("mode", "sequential"))
        agents_data = data.get("agents", [])
        agents = [WorkflowAgentReference.from_dict(a) for a in agents_data]
        return cls(
            name=data.get("name", ""),
            mode=mode,
            agents=agents,
            condition=data.get("condition"),
            timeout=data.get("timeout"),
            retry=data.get("retry"),
        )


@dataclass
class WorkflowRetryPolicy:
    """Retry policy for workflow execution."""

    attempts: int = 3
    delay: float = 1.0
    backoff: float = 2.0
    exceptions: list[type] = field(default_factory=lambda: [Exception])

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "delay": self.delay,
            "backoff": self.backoff,
            "exceptions": [e.__name__ for e in self.exceptions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowRetryPolicy:
        exceptions = []
        for exc_name in data.get("exceptions", []):
            try:
                exceptions.append(getattr(__builtins__, exc_name))
            except Exception:
                pass
        return cls(
            attempts=data.get("attempts", 3),
            delay=data.get("delay", 1.0),
            backoff=data.get("backoff", 2.0),
            exceptions=exceptions,
        )


@dataclass
class WorkflowTimeoutPolicy:
    """Timeout policy for workflow execution."""

    total: float | None = None
    per_agent: float | None = None
    per_step: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "per_agent": self.per_agent,
            "per_step": self.per_step,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowTimeoutPolicy:
        return cls(
            total=data.get("total"),
            per_agent=data.get("per_agent"),
            per_step=data.get("per_step"),
        )


@dataclass
class WorkflowVariable:
    """A variable for substitution in workflow definitions."""

    name: str
    value: Any
    description: str | None = None
    readonly: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "readonly": self.readonly,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowVariable:
        return cls(
            name=data.get("name", ""),
            value=data.get("value"),
            description=data.get("description"),
            readonly=data.get("readonly", False),
        )


@dataclass
class WorkflowMetadata:
    """Metadata for workflow definitions."""

    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    author: str | None = None
    created: str | None = None
    modified: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "author": self.author,
            "created": self.created,
            "modified": self.modified,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowMetadata:
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            author=data.get("author"),
            created=data.get("created"),
            modified=data.get("modified"),
        )


@dataclass
class WorkflowDefinition:
    """Main workflow definition class.

    Holds a complete workflow specification with all configuration,
    agents, execution groups, policies, and metadata.
    """

    version: str = "1.0.0"
    status: WorkflowStatus = WorkflowStatus.VALID
    metadata: WorkflowMetadata = field(default_factory=WorkflowMetadata)
    agents: dict[str, WorkflowAgentReference] = field(default_factory=dict)
    groups: list[WorkflowExecutionGroup] = field(default_factory=list)
    retry: WorkflowRetryPolicy = field(default_factory=WorkflowRetryPolicy)
    timeout: WorkflowTimeoutPolicy = field(default_factory=WorkflowTimeoutPolicy)
    variables: dict[str, WorkflowVariable] = field(default_factory=dict)
    env_overrides: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    # Schema version for backward compatibility
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert workflow definition to dictionary."""
        return {
            "version": self.version,
            "status": self.status.value,
            "metadata": self.metadata.to_dict(),
            "agents": {name: ref.to_dict() for name, ref in self.agents.items()},
            "groups": [group.to_dict() for group in self.groups],
            "retry": self.retry.to_dict(),
            "timeout": self.timeout.to_dict(),
            "variables": {name: var.to_dict() for name, var in self.variables.items()},
            "env_overrides": self.env_overrides,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowDefinition:
        """Create workflow definition from dictionary."""
        definition = cls(
            version=data.get("version", "1.0.0"),
            status=WorkflowStatus(data.get("status", "valid")),
            metadata=WorkflowMetadata.from_dict(data.get("metadata", {})),
            description=data.get("description", ""),
        )

        # Load agents
        for name, agent_data in data.get("agents", {}).items():
            definition.agents[name] = WorkflowAgentReference.from_dict(agent_data)

        # Load execution groups
        for group_data in data.get("groups", []):
            definition.groups.append(WorkflowExecutionGroup.from_dict(group_data))

        # Load policies
        definition.retry = WorkflowRetryPolicy.from_dict(data.get("retry", {}))
        definition.timeout = WorkflowTimeoutPolicy.from_dict(data.get("timeout", {}))

        # Load variables
        for name, var_data in data.get("variables", {}).items():
            definition.variables[name] = WorkflowVariable.from_dict(var_data)

        # Load environment overrides
        definition.env_overrides = data.get("env_overrides", {})

        return definition

    def validate(self) -> bool:
        """Validate the workflow definition.

        Returns True if valid, False otherwise.
        """
        errors = []

        # Validate version
        try:
            if self.version:
                version_parts = self.version.split(".")
                if len(version_parts) < 1:
                    errors.append("Version must have at least one component")
        except (ValueError, AttributeError) as e:
            errors.append(f"Invalid version format: {e}")

        # Validate metadata
        if not self.metadata.name:
            errors.append("Workflow metadata name is required")

        # Validate groups exist
        if not self.groups:
            errors.append("At least one execution group is required")
        else:
            for i, group in enumerate(self.groups):
                if not group.agents:
                    errors.append(f"Group '{group.name}' must have at least one agent")

                if group.mode not in ExecutionMode:
                    errors.append(f"Group '{group.name}' has invalid mode: {group.mode}")

                if group.condition:
                    if not isinstance(group.condition, dict):
                        errors.append(f"Group '{group.name}' condition must be a dictionary")

            if not any(g.agents for g in self.groups):
                errors.append("At least one group must have agents defined")

        # Validate retry policy
        if self.retry.attempts < 1:
            errors.append("Retry attempts must be at least 1")

        # Validate timeout policy
        if self.timeout.total and self.timeout.total < 0:
            errors.append("Total timeout must be non-negative")

        # Validate agents have names and types
        for name, agent in self.agents.items():
            if not agent.name:
                errors.append(f"Agent '{name}' must have a name")
            if not agent.agent_type:
                errors.append(f"Agent '{name}' must have an agent_type")

        if errors:
            self.status = WorkflowStatus.INVALID
            return False

        self.status = WorkflowStatus.VALID
        return True

    def get_executable_agents(self) -> list[WorkflowAgentReference]:
        """Get all agents that can be executed (from all groups)."""
        agents = []
        for group in self.groups:
            agents.extend(group.agents)
        return agents

    def get_agent(self, name: str) -> WorkflowAgentReference | None:
        """Get a specific agent by name."""
        if name in self.agents:
            return self.agents[name]

        for group in self.groups:
            for agent in group.agents:
                if agent.name == name:
                    return agent

        return None

    def get_groups_for_agent(self, agent_name: str) -> list[WorkflowExecutionGroup]:
        """Get all groups that contain a specific agent."""
        groups = []
        for group in self.groups:
            if any(a.name == agent_name for a in group.agents):
                groups.append(group)
        return groups


class WorkflowSchema(Enum):
    """Supported workflow schema versions."""

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


def detect_schema_version(data: dict[str, Any]) -> str:
    """Detect the schema version from workflow data."""
    version = data.get("version", "1.0")
    if isinstance(version, str):
        match = re.match(r"^(\d+)", version)
        if match:
            return match.group(1)
    return "1"


def load_workflow(filepath: str | Path) -> WorkflowDefinition:
    """Load a workflow definition from a file (YAML or JSON).

    Args:
        filepath: Path to the workflow file

    Returns:
        WorkflowDefinition instance

    Raises:
        ValueError: If the file format is unsupported or validation fails
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Workflow file not found: {filepath}")

    suffix = filepath.suffix.lower()

    if suffix in (".yaml", ".yml"):
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        try:
            data = json.loads(content)  # Try JSON first
        except json.JSONDecodeError:
            data = _parse_simple_yaml(content)
            suffix = ".yaml"  # Mark as YAML for save
    elif suffix == ".json":
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        try:
            data = json.loads(content)
            suffix = ".json"
        except json.JSONDecodeError:
            data = _parse_simple_yaml(content)
            suffix = ".yaml"

    schema_version = detect_schema_version(data)
    definition = WorkflowDefinition.from_dict(data)
    definition.schema_version = schema_version

    if not definition.validate():
        raise ValueError(f"Workflow validation failed for {filepath}")

    return definition


def _parse_simple_yaml(content: str) -> dict[str, Any]:
    """Parse simple YAML structures without full YAML dependency.

    Supports basic key-value pairs, lists, and nested dictionaries.
    Uses a state machine to handle indentation-based nesting.
    """
    lines = content.split("\n")
    result: dict[str, Any] = {}

    # State machine for YAML parsing
    # States: ROOT, UNDER_METADATA, UNDER_GROUPS, UNDER_GROUP, UNDER_AGENTS
    state = "ROOT"
    current_group: int | None = None
    current_agent: int | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Calculate indentation level (2 spaces per level)
        indent = len(line) - len(line.lstrip())
        level = indent // 2  # Each indent level is 2 spaces

        # Reset state to ROOT when we see a line at indent 0
        # This allows root-level keys to be re-processed after nested sections
        if indent == 0:
            state = "ROOT"

        # Handle list items (starting with "- ")
        if stripped.startswith("- "):
            value = stripped[2:].strip()

            if state == "UNDER_GROUPS" and level == 1:
                # List item under groups: - name: group1
                if ":" in value:
                    gkey, _, gvalue = value.partition(":")
                    gkey = gkey.strip()
                    gvalue = gvalue.strip()

                    if "groups" not in result:
                        result["groups"] = []

                    group_dict = {gkey: gvalue}
                    result["groups"].append(group_dict)
                    current_group = len(result["groups"]) - 1
                    current_agent = None

            continue

        # Handle key: value at level 2 under UNDER_GROUPS state (group properties like mode: sequential)
        if state == "UNDER_GROUPS" and level == 2 and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            # Type coercion
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            elif val.isdigit():
                val = int(val)
            else:
                try:
                    val = float(val)
                except ValueError:
                    pass

            if current_group is not None:
                result["groups"][current_group][key] = val

            # Handle agent items at level 2 under agents key: - name: agent1
            if current_group is not None and key == "agents":
                if stripped.startswith("- "):
                    agent_value = stripped[2:].strip()
                    if ":" in agent_value:
                        akey, _, aval = agent_value.partition(":")
                        akey = akey.strip()
                        aval = aval.strip()

                        if "agents" not in result["groups"][current_group]:
                            result["groups"][current_group]["agents"] = []

                        agent_dict = {akey: aval}
                        result["groups"][current_group]["agents"].append(agent_dict)

        # Handle key: value
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            # Remove quotes from value
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
                value = value[1:-1]

            # Determine value type
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string

            if state == "ROOT":
                # Root-level key-value
                # If this key will have nested content, initialize accordingly
                if key == "metadata" and value == "":
                    result[key] = {}
                elif key == "groups" and value == "":
                    result[key] = []
                else:
                    result[key] = value

                # Check if this key triggers a state change
                if key == "metadata":
                    state = "UNDER_METADATA"
                elif key == "groups":
                    state = "UNDER_GROUPS"

            elif state == "UNDER_METADATA":
                # Nested under metadata
                if level == 1:
                    if "metadata" not in result:
                        result["metadata"] = {}
                    result["metadata"][key] = value

                    # Check if we should go back to ROOT
                    # (This will be detected on next line with indent 0)

            elif state == "UNDER_GROUPS":
                if level == 1 and stripped.startswith("- "):
                    # New group item: - name: group1
                    if ":" in value:
                        gkey, _, gvalue = value.partition(":")
                        gkey = gkey.strip()
                        gvalue = gvalue.strip()

                    if "groups" not in result:
                        result["groups"] = []

                    group_dict = {gkey: gvalue}
                    result["groups"].append(group_dict)
                    current_group = len(result["groups"]) - 1
                    current_agent = None

                elif level == 2 and current_group is not None:
                    # Group properties: mode: sequential, agents: ...
                    if ":" in value:
                        pkey, _, pval = value.partition(":")
                        pkey = pkey.strip()
                        pval = pval.strip()

                        # Type coercion
                        if pval.lower() == "true":
                            pval = True
                        elif pval.lower() == "false":
                            pval = False
                        elif pval.isdigit():
                            pval = int(pval)
                        else:
                            try:
                                pval = float(pval)
                            except ValueError:
                                pass

                        if pkey == "mode":
                            result["groups"][current_group]["mode"] = ExecutionMode(pval)
                        elif pkey == "agents":
                            # Agents list will be populated by subsequent '- ' items
                            result["groups"][current_group]["agents"] = []
                        else:
                            result["groups"][current_group][pkey] = pval

                elif level == 3 and current_group is not None:
                    # Agent items: - name: agent1
                    if ":" in value:
                        akey, _, aval = value.partition(":")
                        akey = akey.strip()
                        aval = aval.strip()

                    if "agents" not in result["groups"][current_group]:
                        result["groups"][current_group]["agents"] = []

                    agent_dict = {akey: aval}
                    result["groups"][current_group]["agents"].append(agent_dict)
                    current_agent = len(result["groups"][current_group]["agents"]) - 1

    return result


def _serialize_to_yaml(data: dict[str, Any], indent: int = 0) -> str:
    """Serialize a dictionary to simple YAML format.

    Supports basic structures - full YAML features would require pyyaml.
    Properly handles nested dicts, lists, booleans, and numbers without unnecessary quotes.
    """
    spaces = "  " * indent
    lines: list[str] = []

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{spaces}{key}:")
            lines.append(_serialize_to_yaml(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{spaces}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(_serialize_to_yaml(item, indent + 2))
                elif isinstance(item, bool):
                    lines.append(f'{spaces}  - {"true" if item else "false"}')
                elif isinstance(item, (int, float)):
                    lines.append(f"{spaces}  - {item}")
                elif isinstance(item, str):
                    # Only quote strings that need it (contain special chars)
                    if any(
                        c in item
                        for c in [
                            ":",
                            "#",
                            "\n",
                            "\t",
                            '"',
                            "{",
                            "}",
                            "[",
                            "]",
                            "@",
                            "!",
                            "|",
                            "&",
                            "(",
                            ")",
                            "=",
                            "+",
                            "<",
                            ">",
                            "'",
                            "`",
                            " ",
                        ]
                    ):
                        escaped = item.replace('"', '\\"')
                        lines.append(f'{spaces}  - "{escaped}"')
                    else:
                        lines.append(f"{spaces}  - {item}")
                else:
                    lines.append(f"{spaces}  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{spaces}{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            # Don't quote numbers
            if isinstance(value, float) and value == int(value) and abs(value) < 1e15:
                lines.append(f"{spaces}{key}: {int(value)}")
            else:
                lines.append(f"{spaces}{key}: {value}")
        elif isinstance(value, str):
            # Only quote strings that need it
            if any(
                c in value
                for c in [
                    ":",
                    "#",
                    "\n",
                    "\t",
                    '"',
                    "{",
                    "}",
                    "[",
                    "]",
                    "@",
                    "!",
                    "|",
                    "&",
                    "(",
                    ")",
                    "=",
                    "+",
                    "<",
                    ">",
                    "'",
                    "`",
                    " ",
                ]
            ):
                escaped = value.replace('"', '\\"')
                lines.append(f'{spaces}{key}: "{escaped}"')
            else:
                lines.append(f"{spaces}{key}: {value}")
        else:
            lines.append(f"{spaces}{key}: {value}")

    return "\n".join(lines)


def save_workflow(definition: WorkflowDefinition, filepath: str | Path) -> None:
    """Save a workflow definition to a file.

    Args:
        definition: WorkflowDefinition instance to save
        filepath: Path to write the workflow file
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    data = definition.to_dict()

    # Determine output format based on extension
    suffix = filepath.suffix.lower()

    if suffix in (".yaml", ".yml"):
        content = _serialize_to_yaml(data)
    else:
        content = json.dumps(data, indent=2)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


# Convenience functions


def create_simple_workflow(
    name: str,
    agents: list[str],
    description: str = "",
    version: str = "1.0.0",
) -> WorkflowDefinition:
    """Create a simple workflow definition with minimal configuration.

    Args:
        name: Workflow name
        agents: List of agent type names
        description: Workflow description
        version: Workflow version

    Returns:
        WorkflowDefinition instance
    """
    definition = WorkflowDefinition(
        version=version,
        metadata=WorkflowMetadata(name=name, description=description),
        description=description,
    )

    # Add agents as references
    for i, agent_type in enumerate(agents):
        agent_ref = WorkflowAgentReference(
            name=f"agent_{i}",
            agent_type=agent_type,
        )
        definition.agents[f"agent_{i}"] = agent_ref

    # Create a default sequential group
    group = WorkflowExecutionGroup(
        name="default",
        mode=ExecutionMode.SEQUENTIAL,
        agents=[
            WorkflowAgentReference(
                name=f"agent_{i}",
                agent_type=agent_type,
            )
            for i, agent_type in enumerate(agents)
        ],
    )
    definition.groups.append(group)

    return definition


# Example workflow definitions for documentation

EXAMPLE_WORKFLOW_FULL = """version: 1.0.0
name: Full Repository Security Scan
description: Comprehensive security scan including SAST, secrets, and SBOM
status: valid
schema_version: 1.0

metadata:
  name: Full Repository Security Scan
  description: Comprehensive security scan including SAST, secrets, and SBOM
  version: 1.0.0
  tags: [security, scanning, full]
  author: SentinelAI
  created: 2024-01-01
  modified: 2024-01-15

agents:
  sast:
    name: sast_agent
    agent_type: sast
    config:
      severity_threshold: medium
      timeout: 120
  secrets:
    name: secrets_agent
    agent_type: secrets
    config:
      entropy_threshold: 4
      directory: /
  sbom:
    name: sbom_agent
    agent_type: sbom
    config:
      format: spdx
      output: detailed

env_overrides:
  OLLAMA_URL: http://localhost:11434

retry:
  attempts: 3
  delay: 1.0
  backoff: 2.0

timeout:
  total: 300
  per_agent: 120

variables:
  target_path:
    value: /tmp/test_repo
    description: Path to scan
    readonly: false

groups:
  - name: sast_group
    mode: sequential
    agents:
      - name: sast_agent
        agent_type: sast
        config:
          severity_threshold: medium
    timeout: 120

  - name: secrets_group
    mode: parallel
    agents:
      - name: secrets_agent
        agent_type: secrets
        config:
          entropy_threshold: 4
      - name: sbom_agent
        agent_type: sbom
        config:
          format: spdx
    timeout: 180

  - name: finalize_group
    mode: sequential
    agents:
      - name: report_agent
        agent_type: report"""

EXAMPLE_WORKFLOW_SIMPLE = """version: 1.0
name: Basic Directory Scan
description: Simple scan of a directory for security issues
status: valid

metadata:
  name: Basic Directory Scan
  version: 1.0
  tags: [security, scan]

agents:
  scan:
    name: scan_agent
    agent_type: sast
    config:
      severity_threshold: high

groups:
  - name: scan_group
    mode: sequential
    agents:
      - name: scan_agent
        agent_type: sast
        config:
          severity_threshold: high"""

EXAMPLE_WORKFLOW_VERSIONED = """version: 2.0
name: Version 2 Workflow
description: Workflow with version 2 features
status: valid

metadata:
  name: Version 2 Workflow
  version: 2.0
  tags: [v2, new]

agents:
  new_agent:
    name: new_agent_ref
    agent_type: new_agent_type
    config:
      new_feature: true

groups:
  - name: main_group
    mode: mixed
    agents:
      - name: new_agent_ref
        agent_type: new_agent_type"""

# Backward compatibility mapping
SCHEMA_VERSION_MAP = {
    "1": "1.0",
    "1.0": "1.0",
    "1.1": "1.1",
    "2.0": "2.0",
}


def _get_agent_names_from_definition(wf: WorkflowDefinition) -> set:
    """Get all agent names from a workflow definition (from agents dict and groups)."""
    names = set()
    names.update(wf.agents.keys())
    for group in wf.groups:
        for agent in group.agents:
            names.add(agent.name)
    return names


def check_backward_compatibility(
    old_definition: WorkflowDefinition,
    new_definition: WorkflowDefinition,
) -> dict[str, Any]:
    """Check backward compatibility between two workflow definitions.

    Args:
        old_definition: The older workflow definition
        new_definition: The newer workflow definition

    Returns:
        Dictionary with compatibility assessment
    """
    result = {
        "compatible": True,
        "breaking_changes": [],
        "new_features": [],
        "migration_notes": [],
    }

    old_version = old_definition.version
    new_version = new_definition.version

    if old_version != new_version:
        result["new_features"].append(
            f"Workflow version updated from {old_version} to {new_version}"
        )

    old_agent_names = _get_agent_names_from_definition(old_definition)
    new_agent_names = _get_agent_names_from_definition(new_definition)
    removed_agents = old_agent_names - new_agent_names

    if removed_agents:
        result["breaking_changes"].append(f"Removed agents: {', '.join(sorted(removed_agents))}")
        result["compatible"] = False
        result["migration_notes"].append(
            f"Agents {', '.join(sorted(removed_agents))} must be redefined or referenced differently"
        )

    added_agents = new_agent_names - old_agent_names
    if added_agents:
        result["new_features"].append(f"Added agents: {', '.join(sorted(added_agents))}")

    old_group_names = set(g.name for g in old_definition.groups)
    new_group_names = set(g.name for g in new_definition.groups)
    removed_groups = old_group_names - new_group_names
    added_groups = new_group_names - old_group_names

    if removed_groups:
        result["breaking_changes"].append(f"Removed groups: {', '.join(removed_groups)}")
        result["compatible"] = False

    if added_groups:
        result["new_features"].append(f"Added groups: {', '.join(added_groups)}")

    return result


# Export main classes and functions
__all__ = [
    "WorkflowDefinition",
    "WorkflowStatus",
    "ExecutionMode",
    "ConditionOperator",
    "WorkflowAgentReference",
    "WorkflowExecutionGroup",
    "WorkflowRetryPolicy",
    "WorkflowTimeoutPolicy",
    "WorkflowVariable",
    "WorkflowMetadata",
    "WorkflowSchema",
    "detect_schema_version",
    "load_workflow",
    "save_workflow",
    "create_simple_workflow",
    "check_backward_compatibility",
    "EXAMPLE_WORKFLOW_FULL",
    "EXAMPLE_WORKFLOW_SIMPLE",
    "EXAMPLE_WORKFLOW_VERSIONED",
]
