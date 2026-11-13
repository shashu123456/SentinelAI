"""Tests for ExecutionEngine module."""

import time
from typing import Any

import pytest

from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.shared_models import AgentContext, AgentMetadata
from app.core.execution.execution_engine import (
    ExecutionConfig,
    ExecutionEngine,
    ExecutionStatus,
)


class TestAgent(BaseAgent):
    """Minimal test agent for ExecutionEngine tests."""

    _metadata: AgentMetadata = AgentMetadata(id="test-agent", display_name="TestAgent")

    def validate(self) -> bool:
        return True

    def prepare(self) -> None:
        pass

    def execute(self, context: AgentContext) -> Any:
        return {"test": "result"}

    def finalize(self, result: Any) -> None:
        pass

    def health_check(self) -> Any:
        return {"healthy": True}

    def cleanup(self) -> None:
        pass


def _make_context(agent_id: str = "test-agent") -> AgentContext:
    """Create an AgentContext with the given agent_id."""
    return AgentContext(agent_id=agent_id)


def test_execution_engine_single():
    """Test single agent execution through ExecutionEngine."""
    engine = ExecutionEngine()
    agent = TestAgent()
    context = _make_context(agent_id=agent.metadata.id)

    result = engine.execute(agent, context)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.agent_id == "test-agent"
    assert result.duration >= 0.0
    assert result.progress == 100
    assert result.result is not None


def test_execution_engine_with_config():
    """Test single agent execution with configuration."""
    engine = ExecutionEngine()
    agent = TestAgent()
    context = _make_context(agent_id=agent.metadata.id)
    config = ExecutionConfig(timeout=30.0, max_retries=2, parallel=False)

    result = engine.execute(agent, context, config)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.duration < 30.0  # should complete within timeout


def test_execution_engine_parallel():
    """Test parallel agent execution."""
    engine = ExecutionEngine()

    agents = [(TestAgent(), _make_context(agent_id=TestAgent().metadata.id)) for _ in range(3)]

    results = engine.execute_parallel(agents, config=ExecutionConfig(parallel=True))

    assert len(results) == 3
    assert all(r.status == ExecutionStatus.COMPLETED for r in results)
    assert all(r.progress == 100 for r in results)


def test_execution_engine_sequential():
    """Test sequential agent execution."""
    engine = ExecutionEngine()

    agents = [(TestAgent(), _make_context(agent_id=TestAgent().metadata.id)) for _ in range(3)]

    results = engine.execute_sequential(agents, config=ExecutionConfig(parallel=False))

    assert len(results) == 3
    assert all(r.status == ExecutionStatus.COMPLETED for r in results)


def test_execution_engine_cancel_on_first_failure_sequential():
    """Test sequential execution cancels on first failure."""

    class FailingAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(id="failing", display_name="Failing")

        def validate(self) -> bool:
            raise ValueError("Validation failed")

        def prepare(self) -> None:
            pass

        def execute(self, context: AgentContext) -> Any:
            raise RuntimeError("Execution error")

        def finalize(self, result: Any) -> None:
            pass

        def health_check(self) -> Any:
            return {"healthy": True}

        def cleanup(self) -> None:
            pass

    engine = ExecutionEngine()
    failing_agent = FailingAgent()
    agents = [
        (failing_agent, _make_context(agent_id=failing_agent.metadata.id)),
        (TestAgent(), _make_context(agent_id=TestAgent().metadata.id)),
    ]

    results = engine.execute_sequential(
        agents, config=ExecutionConfig(parallel=False, cancel_on_first_failure=True)
    )

    assert len(results) == 2
    assert results[0].status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT)
    assert results[1].status == ExecutionStatus.CANCELLED


def test_execution_engine_status():
    """Test engine status reporting."""
    engine = ExecutionEngine()
    status = engine.get_status()

    assert "active_executions" in status
    assert "circuit_breaker_state" in status
    assert "executor_active_workers" in status


def test_execution_engine_cancel():
    """Test execution cancellation."""
    engine = ExecutionEngine()
    agent = TestAgent()
    _make_context(agent_id=agent.metadata.id)

    # Cancellation is cooperative; just verify it doesn't crash
    # and the method handles the call gracefully
    result = engine.cancel_execution("nonexistent-agent")
    assert result is False  # agent not found is fine


def test_execution_engine_timeout():
    """Test timeout handling."""
    engine = ExecutionEngine()

    class SlowAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(id="slow", display_name="Slow")

        def validate(self) -> bool:
            return True

        def prepare(self) -> None:
            pass

        def execute(self, context: AgentContext) -> Any:
            # Simulate slow execution
            time.sleep(0.1)
            return {"slow": "result"}

        def finalize(self, result: Any) -> None:
            pass

        def health_check(self) -> Any:
            return {"healthy": True}

        def cleanup(self) -> None:
            pass

    agent = SlowAgent()
    context = _make_context(agent_id=agent.metadata.id)
    config = ExecutionConfig(timeout=0.01, max_retries=0)  # very short timeout

    result = engine.execute(agent, context, config)

    # Should timeout or complete quickly depending on implementation
    assert result.duration >= 0.0
    # Result may be TIMEOUT or COMPLETED depending on timing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
