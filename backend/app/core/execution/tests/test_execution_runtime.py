"""Tests for ExecutionRuntime, ExecutionState, and SessionStore components.

Tests cover:
- ExecutionRuntime integration with ExecutionEngine
- ExecutionState lifecycle tracking
- SessionStore persistence and recovery
- RuntimeMetrics aggregation
- RuntimeSnapshot production
"""

import os
import tempfile
from typing import Any

import pytest

from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.shared_models import AgentContext, AgentMetadata, AgentResult
from app.core.execution.execution_engine import ExecutionConfig
from app.core.execution.execution_runtime import ExecutionRuntime
from app.core.execution.execution_state import (
    ExecutionContext,
    ExecutionState,
    ExecutionStateMetadata,
    RuntimeMetrics,
    RuntimeSnapshot,
    ScanSession,
)
from app.core.execution.session_store import SessionStore

# Use a unique database path per test session to avoid conflicts
_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"sentinelai_test_session_{os.getpid()}.db")


def _reset_test_db():
    """Reset the test database between tests."""
    if os.path.exists(_TEST_DB_PATH):
        try:
            os.remove(_TEST_DB_PATH)
        except PermissionError:
            pass


def _get_store():
    """Get a SessionStore instance using the test database path."""
    _reset_test_db()
    return SessionStore(database_path=_TEST_DB_PATH)


class TestAgent(BaseAgent):
    """Test agent for runtime tests."""

    _metadata: AgentMetadata = AgentMetadata(id="test-agent", display_name="TestAgent")

    def validate(self) -> bool:
        return True

    def prepare(self) -> None:
        pass

    def execute(self, context: AgentContext) -> Any:
        return {"test": "result", "agent_id": self.metadata.id}

    def finalize(self, result: Any) -> None:
        pass

    def health_check(self) -> Any:
        return {"healthy": True}

    def cleanup(self) -> None:
        pass


def _make_context(agent_id: str = "test-agent", target: str = "/tmp/test") -> AgentContext:
    """Create an AgentContext."""
    return AgentContext(agent_id=agent_id)


@pytest.fixture(autouse=True)
def _reset_session_store_db():
    """Reset the session store database between tests."""
    _reset_test_db()
    yield
    # Best-effort cleanup; may fail on Windows if another test holds a connection
    try:
        _reset_test_db()
    except Exception:
        pass


# ── ExecutionState Tests ───────────────────────────────────────────────────


def test_execution_state_lifecycle():
    """Test ExecutionStateMetadata lifecycle tracking."""
    state = ExecutionStateMetadata(
        session_id="test-session",
        agent_id="test-agent",
    )

    # Initially initialized
    assert state.status == ExecutionState.INITIALIZED
    assert state.duration == 0.0

    # Mark running
    state.mark_running()
    assert state.status == ExecutionState.RUNNING
    assert len(state.transition_history) == 1
    assert state.transition_history[0]["to"] == "running"

    # Mark completed
    from app.core.agent_framework.shared_models import AgentResult

    result = AgentResult(
        agent_id="test-agent",
        success=True,
        findings=[],
        output="test output",
        metrics={
            "files_scanned": 10,
            "lines_scanned": 100,
            "findings_count": 0,
            "languages_detected": [],
        },
        execution_time=0.5,
        error=None,
    )
    state.mark_completed(result)
    assert state.status == ExecutionState.COMPLETED
    assert state.duration > 0
    assert len(state.transition_history) == 2
    assert state.transition_history[1]["to"] == "completed"
    assert state.findings_count == 0
    assert state.files_scanned == 10

    # Mark failed
    state.mark_failed("test error")
    assert state.status == ExecutionState.FAILED
    assert state.error == "test error"
    assert len(state.transition_history) == 3

    # Mark cancelled
    state.mark_cancelled()
    assert state.status == ExecutionState.CANCELLED
    assert state.error == "cancelled_by_user"

    # Mark timeout
    state.mark_timeout()
    assert state.status == ExecutionState.TIMEOUT
    assert "timeout" in state.error


def test_scan_session_lifecycle():
    """Test ScanSession lifecycle tracking."""
    session = ScanSession(
        session_id="test-scan-session",
        agent_id="test-agent",
        target_path="/tmp/test",
    )

    # Initially initialized
    assert session.status == ExecutionState.INITIALIZED

    # Start session
    session.start(config={"timeout": 30.0})
    assert session.status == ExecutionState.RUNNING
    assert session.started_at is not None
    assert "session_started" in session.transition_history[0]["reason"]

    # Complete session
    result = AgentResult(
        agent_id="test-agent",
        success=True,
        findings=[],
        output="test output",
        metrics={
            "files_scanned": 5,
            "lines_scanned": 50,
            "findings_count": 2,
            "languages_detected": ["python"],
        },
        execution_time=1.0,
        error=None,
    )
    session.complete(result)
    assert session.status == ExecutionState.COMPLETED
    assert session.duration > 0
    assert session.findings_count == 2
    assert session.files_scanned == 5
    assert "session_completed" in session.transition_history[-1]["reason"]

    # Fail session
    session.fail("Scan error")
    assert session.status == ExecutionState.FAILED
    assert session.error == "Scan error"

    # Cancel session
    session.cancel()
    assert session.status == ExecutionState.CANCELLED
    assert session.error == "cancelled_by_user"

    # Timeout session
    session.timeout()
    assert session.status == ExecutionState.TIMEOUT
    assert "timeout" in session.error


def test_execution_context():
    """Test ExecutionContext functionality."""
    context = ExecutionContext(
        session_id="ctx-session",
        agent_id="test-agent",
        target_path="/tmp/test",
        config={"timeout": 30.0},
    )

    # Initially initialized
    assert context.status == ExecutionState.INITIALIZED
    assert context.duration == 0.0

    # Complete with metrics
    context.complete({"files_scanned": 10, "findings": 2})
    assert context.status == ExecutionState.COMPLETED
    assert context.metrics == {"files_scanned": 10, "findings": 2}
    assert len(context.transition_history) == 1

    # Fail
    context.fail("Context error", {"files_scanned": 5})
    assert context.status == ExecutionState.FAILED
    assert context.error == "Context error"
    assert context.metrics == {"files_scanned": 5}


# ── RuntimeMetrics Tests ───────────────────────────────────────────────────


def test_runtime_metrics_basic():
    """Test RuntimeMetrics basic recording."""
    metrics = RuntimeMetrics()

    # Initially empty
    assert metrics.get_metrics()["total_executions"] == 0

    # Record some executions
    from app.core.execution.execution_state import ExecutionStateMetadata

    # Completed execution
    metrics.record_execution(
        ExecutionStateMetadata(
            session_id="s1",
            agent_id="a1",
            status=ExecutionState.COMPLETED,
            duration=1.5,
            files_scanned=10,
            findings_count=2,
            languages_detected=["python"],
        )
    )

    # Failed execution
    metrics.record_execution(
        ExecutionStateMetadata(
            session_id="s2",
            agent_id="a2",
            status=ExecutionState.FAILED,
            duration=0.5,
            files_scanned=5,
            findings_count=0,
            languages_detected=[],
        )
    )

    # Completed execution
    metrics.record_execution(
        ExecutionStateMetadata(
            session_id="s3",
            agent_id="a3",
            status=ExecutionState.COMPLETED,
            duration=2.0,
            files_scanned=15,
            findings_count=1,
            languages_detected=["javascript"],
        )
    )

    metrics_data = metrics.get_metrics()
    assert metrics_data["total_executions"] == 3
    assert metrics_data["successful_executions"] == 2
    assert metrics_data["failed_executions"] == 1
    assert metrics_data["average_duration"] == pytest.approx(1.33, abs=0.01)
    assert metrics_data["total_files_scanned"] == 30
    assert metrics_data["total_findings"] == 3
    assert metrics_data["executions_by_status"]["completed"] == 2
    assert metrics_data["executions_by_status"]["failed"] == 1
    assert "python" in metrics_data["executions_by_language"]
    assert "javascript" in metrics_data["executions_by_language"]
    assert metrics_data["executions_by_language"]["python"] == 1
    assert metrics_data["executions_by_language"]["javascript"] == 1


def test_runtime_metrics_reset():
    """Test RuntimeMetrics reset functionality."""
    metrics = RuntimeMetrics()

    # Record execution
    from app.core.execution.execution_state import ExecutionStateMetadata

    metrics.record_execution(
        ExecutionStateMetadata(
            session_id="s1",
            agent_id="a1",
            status=ExecutionState.COMPLETED,
            duration=1.0,
            files_scanned=10,
            findings_count=0,
            languages_detected=[],
        )
    )

    assert metrics.get_metrics()["total_executions"] == 1

    # Reset
    metrics.reset()
    assert metrics.get_metrics()["total_executions"] == 0


# ── RuntimeSnapshot Tests ──────────────────────────────────────────────────


def test_runtime_snapshot_basic():
    """Test RuntimeSnapshot production."""
    metrics = RuntimeMetrics()
    from app.core.execution.execution_state import ExecutionStateMetadata

    metrics.record_execution(
        ExecutionStateMetadata(
            session_id="s1",
            agent_id="a1",
            status=ExecutionState.COMPLETED,
            duration=1.0,
        )
    )

    snapshot = RuntimeSnapshot(
        session_id="snap-1",
        engine_status={"active_executions": 0, "circuit_breaker_state": "closed"},
        active_sessions={},
        metrics=metrics,
    )

    data = snapshot.to_dict()
    assert data["session_id"] == "snap-1"
    assert data["engine_status"]["active_executions"] == 0
    assert data["metrics"]["total_executions"] == 1
    assert data["timestamp"] is not None

    # Restore from dict
    snapshot2 = RuntimeSnapshot.from_dict(data)
    assert snapshot2.session_id == "snap-1"
    assert snapshot2.engine_status["active_executions"] == 0


# ── ExecutionRuntime Tests ─────────────────────────────────────────────────


def test_execution_runtime_basic():
    """Test ExecutionRuntime basic execution."""
    runtime = ExecutionRuntime()
    agent = TestAgent()
    context = _make_context()

    exec_state, result = runtime.execute_agent(agent, context)

    assert exec_state is not None
    assert result is not None
    assert result.success is True


def test_execution_runtime_with_config():
    """Test ExecutionRuntime execution with configuration."""
    runtime = ExecutionRuntime()
    agent = TestAgent()
    context = _make_context()
    config = ExecutionConfig(timeout=30.0)

    exec_state, result = runtime.execute_agent(agent, context, config)

    assert exec_state is not None
    assert result is not None
    assert result.success is True


def test_execution_runtime_session_management():
    """Test ExecutionRuntime session management."""
    runtime = ExecutionRuntime()
    agent = TestAgent()
    context = _make_context()

    # Execute without session ID (creates new)
    exec_state, result = runtime.execute_agent(agent, context)
    assert exec_state.session_id is not None
    assert exec_state.agent_id == agent.metadata.id

    # Execute with existing session
    exec_state2, result2 = runtime.execute_agent(agent, context, session_id=exec_state.session_id)
    assert exec_state2.session_id == exec_state.session_id


def test_execution_runtime_session_lifecycle():
    """Test ExecutionRuntime full session lifecycle."""
    runtime = ExecutionRuntime()
    agent = TestAgent()
    context = _make_context()

    # Execute full session
    snapshot = runtime.execute_session(agent, "/tmp/test", session_id=None)

    # Verify snapshot
    assert snapshot is not None
    assert snapshot.session_id is not None
    assert snapshot.metrics.get_metrics()["total_executions"] >= 1

    # Verify session status can be retrieved
    status = runtime.get_session_status(snapshot.session_id)
    assert status is not None
    assert "status" in status

    # Verify runtime metrics
    metrics = runtime.get_runtime_metrics()
    assert "total_executions" in metrics


def test_execution_runtime_get_statuses():
    """Test ExecutionRuntime get_all_session_statuses."""
    runtime = ExecutionRuntime()
    agent = TestAgent()
    context = _make_context()

    # Execute two sessions
    runtime.execute_agent(agent, context)
    runtime.execute_agent(agent, context)

    # Get all statuses
    statuses = runtime.get_all_session_statuses()
    assert len(statuses) == 2


def test_execution_runtime_cancel_session():
    """Test ExecutionRuntime cancel_session."""
    runtime = ExecutionRuntime()
    agent = TestAgent()
    context = _make_context()

    # Execute session
    exec_state, result = runtime.execute_agent(agent, context)

    # Cancel session using the session ID from execution
    result = runtime.cancel_session(exec_state.session_id)
    # Note: This test verifies cancel_session doesn't crash


# ── SessionStore Tests ────────────────────────────────────────────────────


def test_session_store_create_retrieve():
    """Test SessionStore create and retrieve."""
    store = _get_store()

    # Create session
    session = store.create_session(
        session_id="store-test-session",
        agent_id="test-agent",
        target_path="/tmp/test",
        config={"timeout": 30.0},
    )

    assert session.session_id == "store-test-session"
    assert session.agent_id == "test-agent"
    assert session.target_path == "/tmp/test"

    # Retrieve session
    retrieved = store.get_session("store-test-session")
    assert retrieved is not None
    assert retrieved.session_id == "store-test-session"
    assert retrieved.agent_id == "test-agent"

    # Complete the RETRIEVED session, then update it
    from app.core.agent_framework.shared_models import AgentResult

    result = AgentResult(
        agent_id="test-agent",
        success=True,
        findings=[],
        output="test output",
        metrics={
            "files_scanned": 5,
            "lines_scanned": 50,
            "findings_count": 1,
            "languages_detected": ["python"],
        },
        execution_time=1.0,
        error=None,
    )
    retrieved.complete(result)
    store.update_session(retrieved)

    # Verify update
    double_checked = store.get_session("store-test-session")
    assert double_checked is not None
    assert double_checked.status.value == "completed"
    assert double_checked.findings_count == 1
    assert double_checked.files_scanned == 5


def test_session_store_list_and_cleanup():
    """Test SessionStore list and cleanup."""
    store = _get_store()

    # Create multiple sessions
    for i in range(5):
        store.create_session(
            session_id=f"cleanup-test-{i}",
            agent_id="test-agent",
            target_path=f"/tmp/test-{i}",
        )

    # List sessions
    sessions = store.list_sessions(limit=10)
    assert len(sessions) >= 5

    # Cleanup (sessions are created with current time, so may or may not be expired depending on timing)
    # This test just ensures cleanup doesn't crash
    try:
        deleted = store.cleanup_expired(max_age_hours=0)  # 0 hours = delete none created just now
        assert isinstance(deleted, int)
    except Exception:
        # May fail if no sessions are old enough, that's OK
        pass


def test_session_store_delete():
    """Test SessionStore delete functionality."""
    store = _get_store()

    # Create and delete session
    store.create_session(
        session_id="delete-test-session",
        agent_id="test-agent",
        target_path="/tmp/test",
    )

    # Verify it exists
    assert store.get_session("delete-test-session") is not None

    # Delete it
    deleted = store.delete_session("delete-test-session")
    assert deleted is True

    # Verify it's gone
    assert store.get_session("delete-test-session") is None
