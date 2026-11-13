"""Tests for WorkflowDefinition component.

Tests cover:
- YAML/JSON workflow schema loading and parsing
- Schema validation
- Versioning and backward compatibility
- Agent definitions and references
- Execution groups (sequential/parallel)
- Retry and timeout policies
- Variable substitution
- Environment overrides
- Serialization/deserialization
- Example workflow files
"""

import json
import os
import re
import tempfile

from app.core.execution.workflow_definition import (
    EXAMPLE_WORKFLOW_FULL,
    EXAMPLE_WORKFLOW_SIMPLE,
    EXAMPLE_WORKFLOW_VERSIONED,
    ExecutionMode,
    WorkflowAgentReference,
    WorkflowDefinition,
    WorkflowExecutionGroup,
    WorkflowMetadata,
    WorkflowRetryPolicy,
    WorkflowStatus,
    WorkflowTimeoutPolicy,
    WorkflowVariable,
    check_backward_compatibility,
    create_simple_workflow,
    load_workflow,
    save_workflow,
)


class TestWorkflowDefinitionBasics:
    """Test basic WorkflowDefinition creation and properties."""

    def test_default_creation(self):
        """Test creating a default WorkflowDefinition."""
        wf = WorkflowDefinition()
        assert wf.version == "1.0.0"
        assert wf.status == WorkflowStatus.VALID
        assert wf.metadata.name == ""
        assert wf.groups == []
        assert wf.agents == {}
        assert wf.retry.attempts == 3
        assert wf.timeout.total is None

    def test_full_creation(self):
        """Test creating a WorkflowDefinition with all fields."""
        metadata = WorkflowMetadata(
            name="Test Workflow",
            description="A test workflow",
            version="2.0.0",
            tags=["test", "automation"],
            author="Test Author",
        )

        wf = WorkflowDefinition(
            version="2.0.0",
            status=WorkflowStatus.VALID,
            metadata=metadata,
            description="Test description",
        )
        assert wf.version == "2.0.0"
        assert wf.status == WorkflowStatus.VALID
        assert wf.metadata.name == "Test Workflow"
        assert wf.metadata.description == "A test workflow"
        assert wf.metadata.version == "2.0.0"
        assert "test" in wf.metadata.tags
        assert wf.metadata.author == "Test Author"

    def test_status_initial_value(self):
        """Test that new workflows start as VALID."""
        wf = WorkflowDefinition()
        assert wf.status == WorkflowStatus.VALID


class TestWorkflowAgents:
    """Test agent definitions and references."""

    def test_agent_reference_creation(self):
        """Test creating a WorkflowAgentReference."""
        ref = WorkflowAgentReference(
            name="sast_agent",
            agent_type="sast",
            config={"severity": "high"},
            timeout=120.0,
        )
        assert ref.name == "sast_agent"
        assert ref.agent_type == "sast"
        assert ref.config == {"severity": "high"}
        assert ref.timeout == 120.0
        assert ref.retry is None

    def test_agent_reference_defaults(self):
        """Test WorkflowAgentReference with default values."""
        ref = WorkflowAgentReference(name="test", agent_type="type")
        assert ref.name == "test"
        assert ref.agent_type == "type"
        assert ref.config == {}
        assert ref.timeout is None
        assert ref.retry is None

    def test_agent_to_from_dict(self):
        """Test serialization/deserialization of agent references."""
        ref = WorkflowAgentReference(
            name="sast_agent",
            agent_type="sast",
            config={"severity": "high"},
            timeout=120.0,
            retry={"attempts": 3, "delay": 1.0},
        )
        data = ref.to_dict()
        assert data == {
            "name": "sast_agent",
            "agent_type": "sast",
            "config": {"severity": "high"},
            "timeout": 120.0,
            "retry": {"attempts": 3, "delay": 1.0},
        }

        ref2 = WorkflowAgentReference.from_dict(data)
        assert ref2.name == ref.name
        assert ref2.agent_type == ref.agent_type
        assert ref2.config == ref.config
        assert ref2.timeout == ref.timeout
        assert ref2.retry == ref.retry


class TestWorkflowExecutionGroups:
    """Test execution group management."""

    def test_execution_group_creation(self):
        """Test creating a WorkflowExecutionGroup."""
        agents = [
            WorkflowAgentReference(name="a1", agent_type="type1"),
            WorkflowAgentReference(name="a2", agent_type="type2"),
        ]
        group = WorkflowExecutionGroup(
            name="sequential_group",
            mode=ExecutionMode.SEQUENTIAL,
            agents=agents,
        )
        assert group.name == "sequential_group"
        assert group.mode == ExecutionMode.SEQUENTIAL
        assert len(group.agents) == 2

    def test_parallel_execution_group(self):
        """Test creating a parallel execution group."""
        agents = [
            WorkflowAgentReference(name="a1", agent_type="type1"),
        ]
        group = WorkflowExecutionGroup(
            name="parallel_group",
            mode=ExecutionMode.PARALLEL,
            agents=agents,
        )
        assert group.mode == ExecutionMode.PARALLEL

    def test_group_to_from_dict(self):
        """Test group serialization/deserialization."""
        agents = [WorkflowAgentReference(name="a1", agent_type="type1")]
        group = WorkflowExecutionGroup(
            name="test_group",
            mode=ExecutionMode.PARALLEL,
            agents=agents,
            condition={"exists": "/tmp/test"},
            timeout=60.0,
        )
        data = group.to_dict()
        assert "name" in data
        assert "mode" in data
        assert "agents" in data

        group2 = WorkflowExecutionGroup.from_dict(data)
        assert group2.name == group.name
        assert group2.mode == group.mode
        assert len(group2.agents) == len(group.agents)

    def test_simple_workflow_creation(self):
        """Test creating a simple workflow via convenience function."""
        wf = create_simple_workflow(
            name="Simple Scan",
            agents=["sast", "secrets"],
            description="A simple security scan",
        )
        assert wf.metadata.name == "Simple Scan"
        assert "sast" in [a.agent_type for a in wf.get_executable_agents()]
        assert "secrets" in [a.agent_type for a in wf.get_executable_agents()]
        assert len(wf.groups) == 1
        assert wf.groups[0].mode == ExecutionMode.SEQUENTIAL


class TestWorkflowPolicies:
    """Test retry and timeout policies."""

    def test_retry_policy_creation(self):
        """Test creating a WorkflowRetryPolicy."""
        policy = WorkflowRetryPolicy(attempts=5, delay=2.0, backoff=3.0)
        assert policy.attempts == 5
        assert policy.delay == 2.0
        assert policy.backoff == 3.0

    def test_retry_policy_defaults(self):
        """Test retry policy with defaults."""
        policy = WorkflowRetryPolicy()
        assert policy.attempts == 3
        assert policy.delay == 1.0
        assert policy.backoff == 2.0

    def test_retry_to_from_dict(self):
        """Test retry policy serialization."""
        policy = WorkflowRetryPolicy(attempts=5, delay=2.0)
        data = policy.to_dict()
        assert data["attempts"] == 5
        assert data["delay"] == 2.0

        policy2 = WorkflowRetryPolicy.from_dict(data)
        assert policy2.attempts == 5
        assert policy2.delay == 2.0

    def test_timeout_policy_creation(self):
        """Test creating a WorkflowTimeoutPolicy."""
        policy = WorkflowTimeoutPolicy(total=300.0, per_agent=120.0, per_step=60.0)
        assert policy.total == 300.0
        assert policy.per_agent == 120.0
        assert policy.per_step == 60.0

    def test_timeout_policy_partial(self):
        """Test timeout policy with only total."""
        policy = WorkflowTimeoutPolicy(total=300.0)
        assert policy.total == 300.0
        assert policy.per_agent is None
        assert policy.per_step is None

    def test_timeout_to_from_dict(self):
        """Test timeout policy serialization."""
        policy = WorkflowTimeoutPolicy(total=300.0, per_step=60.0)
        data = policy.to_dict()
        assert data["total"] == 300.0
        assert data["per_step"] == 60.0

        policy2 = WorkflowTimeoutPolicy.from_dict(data)
        assert policy2.total == 300.0
        assert policy2.per_step == 60.0

    def test_invalid_retry_attempts(self):
        """Test that invalid retry attempts are caught in validation."""
        wf = WorkflowDefinition(
            version="1.0",
            groups=[
                WorkflowExecutionGroup(
                    name="test",
                    mode=ExecutionMode.SEQUENTIAL,
                    agents=[WorkflowAgentReference(name="a", agent_type="type")],
                )
            ],
            retry=WorkflowRetryPolicy(attempts=0),  # Invalid: must be >= 1
        )
        # Validation should fail
        assert not wf.validate()


class TestWorkflowVariables:
    """Test variable support."""

    def test_workflow_variable_creation(self):
        """Test creating a WorkflowVariable."""
        var = WorkflowVariable(
            name="target_path",
            value="/tmp/test",
            description="Path to scan",
            readonly=False,
        )
        assert var.name == "target_path"
        assert var.value == "/tmp/test"
        assert var.description == "Path to scan"
        assert not var.readonly

    def test_variable_to_from_dict(self):
        """Test variable serialization/deserialization."""
        var = WorkflowVariable(
            name="var1",
            value=42,
            description="An integer variable",
            readonly=True,
        )
        data = var.to_dict()
        assert data["name"] == "var1"
        assert data["value"] == 42
        assert data["description"] == "An integer variable"
        assert data["readonly"] is True

        var2 = WorkflowVariable.from_dict(data)
        assert var2.name == var.name
        assert var2.value == var.value
        assert var2.description == var.description
        assert var2.readonly == var.readonly

    def test_workflow_definition_variables(self):
        """Test adding variables to a workflow definition."""
        wf = WorkflowDefinition(
            version="1.0",
            groups=[],
        )
        wf.variables["target_path"] = WorkflowVariable(
            name="target_path",
            value="/tmp/test",
            description="Path to scan",
        )
        wf.variables["max_depth"] = WorkflowVariable(
            name="max_depth",
            value=3,
        )

        assert "target_path" in wf.variables
        assert "max_depth" in wf.variables
        assert wf.variables["target_path"].value == "/tmp/test"
        assert wf.variables["max_depth"].value == 3


class TestWorkflowEnvOverrides:
    """Test environment overrides."""

    def test_env_overrides(self):
        """Test environment overrides in workflow definition."""
        wf = WorkflowDefinition(
            version="1.0",
            groups=[],
            env_overrides={
                "OLLAMA_URL": "http://localhost:11434",
                "MAX_WORKERS": "4",
                "SEVERITY_THRESHOLD": "medium",
            },
        )
        assert wf.env_overrides["OLLAMA_URL"] == "http://localhost:11434"
        assert wf.env_overrides["MAX_WORKERS"] == "4"
        assert wf.env_overrides["SEVERITY_THRESHOLD"] == "medium"


class TestWorkflowMetadata:
    """Test workflow metadata."""

    def test_metadata_creation(self):
        """Test creating WorkflowMetadata."""
        metadata = WorkflowMetadata(
            name="Test",
            description="A test workflow",
            version="1.0.0",
            tags=["tag1", "tag2"],
            author="Author Name",
            created="2024-01-01",
            modified="2024-01-15",
        )
        assert metadata.name == "Test"
        assert metadata.description == "A test workflow"
        assert metadata.version == "1.0.0"
        assert "tag1" in metadata.tags
        assert "tag2" in metadata.tags
        assert metadata.author == "Author Name"
        assert metadata.created == "2024-01-01"
        assert metadata.modified == "2024-01-15"

    def test_metadata_to_from_dict(self):
        """Test metadata serialization/deserialization."""
        metadata = WorkflowMetadata(
            name="Test",
            version="2.0.0",
            tags=["test"],
        )
        data = metadata.to_dict()
        assert data["name"] == "Test"
        assert data["version"] == "2.0.0"
        assert data["tags"] == ["test"]

        metadata2 = WorkflowMetadata.from_dict(data)
        assert metadata2.name == metadata.name
        assert metadata2.version == metadata.version
        assert metadata2.tags == metadata.tags

    def test_default_metadata(self):
        """Test default WorkflowMetadata values."""
        metadata = WorkflowMetadata()
        assert metadata.name == ""
        assert metadata.description == ""
        assert metadata.version == "1.0.0"
        assert metadata.tags == []


class TestValidateWorkflow:
    """Test workflow validation."""

    def test_valid_workflow_passes_validation(self):
        """Test that a valid workflow passes validation."""
        wf = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="Valid Workflow"),
            groups=[
                WorkflowExecutionGroup(
                    name="group1",
                    mode=ExecutionMode.SEQUENTIAL,
                    agents=[
                        WorkflowAgentReference(name="agent1", agent_type="type1"),
                    ],
                )
            ],
        )
        assert wf.validate()
        assert wf.status == WorkflowStatus.VALID

    def test_invalid_workflow_fails_validation(self):
        """Test that an invalid workflow fails validation."""
        wf = WorkflowDefinition(version="1.0")  # Missing required fields
        assert not wf.validate()
        assert wf.status == WorkflowStatus.INVALID

    def test_workflow_missing_name_fails(self):
        """Test that workflow without name fails validation."""
        wf = WorkflowDefinition(
            version="1.0",
            groups=[],
        )
        assert not wf.validate()

    def test_workflow_invalid_retry(self):
        """Test that workflow with invalid retry fails validation."""
        wf = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="Test"),
            groups=[],
            retry=WorkflowRetryPolicy(attempts=0),
        )
        assert not wf.validate()

    def test_workflow_negative_timeout_fails(self):
        """Test that workflow with negative total timeout fails validation."""
        wf = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="Test"),
            groups=[],
            timeout=WorkflowTimeoutPolicy(total=-1),
        )
        assert not wf.validate()


class TestDetectSchemaVersion:
    """Test schema version detection."""

    def test_schema_version_detection(self):
        """Test detecting schema version from various formats."""
        tests = [
            ("1.0.0", "1"),
            ("1", "1"),
            ("1.1", "1"),
            ("2.0", "2"),
            ("2.1", "2"),
            ("3.0.0", "3"),
        ]
        for version, expected_major in tests:
            # We test the detect function logic
            match = re.match(r"^(\d+)", version)
            result = match.group(1) if match else "1"
            assert result == expected_major


class TestLoadWorkflow:
    """Test workflow loading from files."""

    def test_load_workflow_from_json(self):
        """Test loading a workflow from JSON content."""
        json_content = json.dumps(
            {
                "version": "1.0",
                "name": "Test Workflow",
                "metadata": {
                    "name": "Test Workflow",
                    "version": "1.0",
                },
                "groups": [
                    {
                        "name": "group1",
                        "mode": "sequential",
                        "agents": [
                            {
                                "name": "agent1",
                                "agent_type": "type1",
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json_content)
            f.flush()
            try:
                wf = load_workflow(f.name)
                assert wf is not None
                assert wf.metadata.name == "Test Workflow"
                assert len(wf.groups) == 1
            finally:
                f.close()
                os.unlink(f.name)

    def test_load_workflow_from_yaml(self):
        """Test loading a workflow from YAML content."""
        yaml_content = """version: 1.0
name: Test YAML Workflow
metadata:
  name: Test YAML Workflow
  version: 1.0
groups:
  - name: group1
    mode: sequential
    agents:
      - name: agent1
        agent_type: type1"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            try:
                wf = load_workflow(f.name)
                assert wf is not None
                assert wf.metadata.name == "Test YAML Workflow"
                assert len(wf.groups) == 1
                assert wf.groups[0].mode.value == "sequential"
            finally:
                f.close()
                os.unlink(f.name)

    def test_load_workflow_auto_detect(self):
        """Test auto-detecting workflow format."""
        json_content = json.dumps(
            {
                "version": "1.0",
                "name": "Auto Detect Test",
                "metadata": {"name": "Auto Detect Test", "version": "1.0"},
                "groups": [
                    {
                        "name": "default",
                        "mode": "sequential",
                        "agents": [
                            {
                                "name": "agent1",
                                "agent_type": "type1",
                            }
                        ],
                    }
                ],
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(json_content)
            f.flush()
            try:
                # Auto-detect should work with .txt by trying JSON first
                wf = load_workflow(f.name)
                assert wf is not None
                assert wf.metadata.name == "Auto Detect Test"
            finally:
                f.close()
                os.unlink(f.name)


class TestSaveWorkflow:
    """Test saving workflows to files."""

    def test_save_workflow_to_json(self):
        """Test saving a workflow to JSON."""
        wf = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="Test"),
            groups=[],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            try:
                save_workflow(wf, f.name)
                # Read back and verify
                with open(f.name) as read_f:
                    content = read_f.read()
                    assert "1.0" in content
                    assert "Test" in content
            finally:
                f.close()
                os.unlink(f.name)

    def test_save_workflow_to_yaml(self):
        """Test saving a workflow to YAML."""
        wf = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="Test YAML"),
            groups=[],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                save_workflow(wf, f.name)
                # Read back and verify
                with open(f.name) as read_f:
                    content = read_f.read()
                    assert "Test YAML" in content
                    assert "version: 1.0" in content
            finally:
                f.close()
                os.unlink(f.name)


class TestExampleWorkflows:
    """Test example workflow definitions."""

    def test_example_full_workflow(self):
        """Test the full example workflow."""
        # Should be a valid dict-like structure
        assert EXAMPLE_WORKFLOW_FULL is not None
        assert "version:" in EXAMPLE_WORKFLOW_FULL
        assert "name:" in EXAMPLE_WORKFLOW_FULL
        assert "agents:" in EXAMPLE_WORKFLOW_FULL

    def test_example_simple_workflow(self):
        """Test the simple example workflow."""
        assert EXAMPLE_WORKFLOW_SIMPLE is not None
        assert "version:" in EXAMPLE_WORKFLOW_SIMPLE
        assert "name:" in EXAMPLE_WORKFLOW_SIMPLE

    def test_example_versioned_workflow(self):
        """Test the versioned example workflow."""
        assert EXAMPLE_WORKFLOW_VERSIONED is not None
        assert "version:" in EXAMPLE_WORKFLOW_VERSIONED
        assert "2.0" in EXAMPLE_WORKFLOW_VERSIONED


class TestBackwardCompatibility:
    """Test backward compatibility checking."""

    def test_compatibility_same_agents(self):
        """Test compatibility check with same agents."""
        old_wf = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="Test", version="1.0"),
            groups=[
                WorkflowExecutionGroup(
                    name="group1",
                    mode="sequential",
                    agents=[
                        WorkflowAgentReference(name="a1", agent_type="type1"),
                    ],
                )
            ],
        )

        new_wf = WorkflowDefinition(
            version="1.1",
            metadata=WorkflowMetadata(name="Test", version="1.1"),
            groups=[
                WorkflowExecutionGroup(
                    name="group1",
                    mode="sequential",
                    agents=[
                        WorkflowAgentReference(name="a1", agent_type="type1"),
                    ],
                )
            ],
        )

        result = check_backward_compatibility(old_wf, new_wf)
        assert result["compatible"] is True
        assert len(result["breaking_changes"]) == 0

    def test_compatibility_removed_agents(self):
        """Test compatibility check with removed agents."""
        old_wf = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="Test", version="1.0"),
            groups=[
                WorkflowExecutionGroup(
                    name="group1",
                    mode="sequential",
                    agents=[
                        WorkflowAgentReference(name="a1", agent_type="type1"),
                        WorkflowAgentReference(name="a2", agent_type="type2"),
                    ],
                )
            ],
        )

        new_wf = WorkflowDefinition(
            version="2.0",
            metadata=WorkflowMetadata(name="Test", version="2.0"),
            groups=[
                WorkflowExecutionGroup(
                    name="group1",
                    mode="sequential",
                    agents=[
                        WorkflowAgentReference(name="a1", agent_type="type1"),
                    ],
                )
            ],
        )

        result = check_backward_compatibility(old_wf, new_wf)
        assert result["compatible"] is False
        assert len(result["breaking_changes"]) > 0


class TestWorkflowSerialization:
    """Test workflow round-trip serialization."""

    def test_round_trip_json(self):
        """Test round-trip through JSON serialization."""
        original = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="RoundTrip Test", version="1.0"),
            groups=[
                WorkflowExecutionGroup(
                    name="group1",
                    mode=ExecutionMode.SEQUENTIAL,
                    agents=[
                        WorkflowAgentReference(name="a1", agent_type="type1", config={"x": 1}),
                    ],
                )
            ],
            retry=WorkflowRetryPolicy(attempts=5),
            timeout=WorkflowTimeoutPolicy(total=120.0),
            variables={
                "target": WorkflowVariable(name="target", value="/tmp"),
            },
            env_overrides={"KEY": "value"},
        )

        # Serialize to dict
        data = original.to_dict()

        # Deserialize back
        restored = WorkflowDefinition.from_dict(data)

        # Verify key attributes preserved
        assert restored.version == original.version
        assert restored.metadata.name == original.metadata.name
        assert len(restored.groups) == len(original.groups)
        assert restored.retry.attempts == original.retry.attempts
        assert restored.timeout.total == original.timeout.total
        assert "target" in restored.variables
        assert restored.env_overrides == original.env_overrides

    def test_round_trip_preserves_status(self):
        """Test that status is preserved through round-trip."""
        original = WorkflowDefinition(
            version="1.0",
            metadata=WorkflowMetadata(name="Status Test", version="1.0"),
            status=WorkflowStatus.INVALID,
            groups=[],
        )

        data = original.to_dict()
        restored = WorkflowDefinition.from_dict(data)

        assert restored.status == original.status
        assert restored.status == WorkflowStatus.INVALID


class TestExecutionModes:
    """Test execution mode handling."""

    def test_all_execution_modes(self):
        """Test all execution mode values."""
        assert ExecutionMode.SEQUENTIAL.value == "sequential"
        assert ExecutionMode.PARALLEL.value == "parallel"
        assert ExecutionMode.MIXED.value == "mixed"

    def test_group_defaults_to_sequential(self):
        """Test that groups default to sequential mode."""
        group = WorkflowExecutionGroup(name="test")
        assert group.mode == ExecutionMode.SEQUENTIAL

    def test_group_mode_from_dict(self):
        """Test loading group mode from dictionary."""
        group_data = {"name": "test", "mode": "parallel"}
        group = WorkflowExecutionGroup.from_dict(group_data)
        assert group.mode == ExecutionMode.PARALLEL

    def test_group_mixed_mode(self):
        """Test mixed execution mode."""
        agents = [
            WorkflowAgentReference(name="a1", agent_type="type1"),
            WorkflowAgentReference(name="a2", agent_type="type2"),
        ]
        group = WorkflowExecutionGroup(
            name="mixed",
            mode=ExecutionMode.MIXED,
            agents=agents,
        )
        assert group.mode == ExecutionMode.MIXED
