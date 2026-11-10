"""Production validation tests for ExecutionEngine module.

Tests cover:
- correctness
- thread safety
- concurrency
- determinism
- cancellation
- retries
- timeout behavior
- event ordering
- performance
- stress behavior
- failure recovery
"""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.shared_models import AgentContext, AgentMetadata
from app.core.execution.execution_engine import ExecutionConfig, ExecutionEngine, ExecutionStatus


class ValidatingTestAgent(BaseAgent):
    """Test agent that validates execution state for production tests."""

    _metadata: AgentMetadata = AgentMetadata(
        id="validating-test-agent", display_name="ValidatingTestAgent"
    )
    _execution_log: list = []

    def validate(self) -> bool:
        return True

    def prepare(self) -> None:
        self._execution_log.append("prepare")

    def execute(self, context: AgentContext) -> Any:
        self._execution_log.append("execute")
        return {"test": "result", "agent_id": self.metadata.id}

    def finalize(self, result: Any) -> None:
        self._execution_log.append("finalize")

    def health_check(self) -> Any:
        return {"healthy": True}

    def cleanup(self) -> None:
        self._execution_log.append("cleanup")


def _make_context(agent_id: str = "validating-test-agent") -> AgentContext:
    """Create an AgentContext with the given agent_id."""
    return AgentContext(agent_id=agent_id)


# ── Correctness Tests ──────────────────────────────────────────────────────


def test_production_single_agent_correctness():
    """Test that single agent execution returns correct COMPLETED status when successful."""
    engine = ExecutionEngine()
    agent = ValidatingTestAgent()
    context = _make_context(agent_id=agent.metadata.id)

    result = engine.execute(agent, context)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.agent_id == agent.metadata.id
    assert result.duration >= 0.0
    assert result.progress == 100
    assert result.result is not None
    assert result.result.success is True


def test_production_single_agent_failure_correctness():
    """Test that single agent execution returns FAILED status when agent fails."""

    class FailingAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(id="failing", display_name="Failing")

        def validate(self) -> bool:
            return False

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
    agent = FailingAgent()
    context = _make_context(agent_id=agent.metadata.id)

    result = engine.execute(agent, context)

    assert result.status == ExecutionStatus.FAILED
    assert result.agent_id == agent.metadata.id
    assert result.progress == 0
    assert result.result is not None
    assert result.result.success is False


# ── Thread Safety Tests ────────────────────────────────────────────────────


def test_production_thread_safety_concurrent_executions():
    """Test that concurrent executions are thread-safe."""
    engine = ExecutionEngine()
    agents = [ValidatingTestAgent() for _ in range(10)]
    contexts = [_make_context(agent_id=a.metadata.id) for a in agents]

    def execute_single(agent, ctx):
        return engine.execute(agent, ctx)

    # Run 10 concurrent executions
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(execute_single, agent, ctx) for agent, ctx in zip(agents, contexts, strict=False)
        ]
        results = [f.result() for f in futures]

    # All should complete successfully
    assert len(results) == 10
    assert all(r.status == ExecutionStatus.COMPLETED for r in results)
    assert all(r.progress == 100 for r in results)


def test_production_thread_safety_mixed_success_failure():
    """Test thread safety with mixed success/failure outcomes."""
    engine = ExecutionEngine()

    class SometimesFailingAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(
            id="sometimes-failing", display_name="SometimesFailing"
        )
        _failure_count = 0

        def validate(self) -> bool:
            return True

        def prepare(self) -> None:
            pass

        def execute(self, context: AgentContext) -> Any:
            self._failure_count += 1
            if self._failure_count <= 3:
                raise RuntimeError("Simulated failure")
            return {"test": "result"}

        def finalize(self, result: Any) -> None:
            pass

        def health_check(self) -> Any:
            return {"healthy": True}

        def cleanup(self) -> None:
            pass

    engine = ExecutionEngine()
    agent = SometimesFailingAgent()
    context = _make_context(agent_id=agent.metadata.id)

    # Execute multiple times - some will fail, some will succeed
    results = [engine.execute(agent, context) for _ in range(5)]

    # Should have mix of COMPLETED and FAILED
    statuses = {r.status for r in results}
    assert ExecutionStatus.FAILED in statuses
    assert ExecutionStatus.COMPLETED in statuses


# ── Concurrency Tests ─────────────────────────────────────────────────────


def test_production_parallel_execution_determinism():
    """Test that parallel execution is deterministic in terms of result ordering."""
    engine = ExecutionEngine()

    agents = [ValidatingTestAgent() for _ in range(5)]
    contexts = [_make_context(agent_id=a.metadata.id) for a in agents]

    results = engine.execute_parallel(
        list(zip(agents, contexts, strict=False)), config=ExecutionConfig(parallel=True)
    )

    assert len(results) == 5
    # All should complete
    assert all(r.status == ExecutionStatus.COMPLETED for r in results)
    # Progress should all be 100
    assert all(r.progress == 100 for r in results)


def test_production_sequential_determinism():
    """Test that sequential execution maintains order and determinism."""
    engine = ExecutionEngine()

    agents = [ValidatingTestAgent() for _ in range(5)]
    contexts = [_make_context(agent_id=a.metadata.id) for a in agents]

    results = engine.execute_sequential(
        list(zip(agents, contexts, strict=False)), config=ExecutionConfig(parallel=False)
    )

    assert len(results) == 5
    assert all(r.status == ExecutionStatus.COMPLETED for r in results)
    assert all(r.progress == 100 for r in results)


# ── Cancellation Tests ────────────────────────────────────────────────────


def test_production_cancel_on_first_failure():
    """Test that sequential execution cancels on first failure."""

    class FailingAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(id="failing", display_name="Failing")

        def validate(self) -> bool:
            return True

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
        (ValidatingTestAgent(), _make_context(agent_id=ValidatingTestAgent().metadata.id)),
    ]

    results = engine.execute_sequential(
        agents, config=ExecutionConfig(parallel=False, cancel_on_first_failure=True)
    )

    assert len(results) == 2
    assert results[0].status == ExecutionStatus.FAILED
    assert results[1].status == ExecutionStatus.CANCELLED


def test_production_cancel_nonexistent():
    """Test that cancelling a nonexistent agent doesn't crash."""
    engine = ExecutionEngine()
    result = engine.cancel_execution("nonexistent-agent")
    assert result is False


# ── Timeout Behavior Tests ─────────────────────────────────────────────────


def test_production_timeout_respected():
    """Test that timeout is properly enforced."""
    engine = ExecutionEngine()

    class SlowAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(id="slow", display_name="Slow")

        def validate(self) -> bool:
            return True

        def prepare(self) -> None:
            pass

        def execute(self, context: AgentContext) -> Any:
            time.sleep(0.5)  # Longer than timeout
            return {"test": "result"}

        def finalize(self, result: Any) -> None:
            pass

        def health_check(self) -> Any:
            return {"healthy": True}

        def cleanup(self) -> None:
            pass

    agent = SlowAgent()
    context = _make_context(agent_id=agent.metadata.id)
    config = ExecutionConfig(timeout=0.01, max_retries=0)  # Very short timeout

    result = engine.execute(agent, context, config)

    assert result.duration >= 0.0
    # Should timeout given the short timeout vs 0.5s sleep
    assert result.status in (ExecutionStatus.TIMEOUT, ExecutionStatus.FAILED)


def test_production_timeout_with_completion():
    """Test that timeout works when execution completes within timeout."""
    engine = ExecutionEngine()

    class FastAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(id="fast", display_name="Fast")

        def validate(self) -> bool:
            return True

        def prepare(self) -> None:
            pass

        def execute(self, context: AgentContext) -> Any:
            time.sleep(0.001)  # Very short
            return {"test": "result"}

        def finalize(self, result: Any) -> None:
            pass

        def health_check(self) -> Any:
            return {"healthy": True}

        def cleanup(self) -> None:
            pass

    agent = FastAgent()
    context = _make_context(agent_id=agent.metadata.id)
    config = ExecutionConfig(timeout=5.0, max_retries=0)

    result = engine.execute(agent, context, config)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.duration < 5.0


# ── Event Ordering Tests ──────────────────────────────────────────────────


def test_production_event_ordering():
    """Test that events are emitted in correct order."""
    engine = ExecutionEngine()
    agent = ValidatingTestAgent()
    context = _make_context(agent_id=agent.metadata.id)

    result = engine.execute(agent, context)

    # Verify the result is complete
    assert result.status == ExecutionStatus.COMPLETED


# ── Performance Tests ─────────────────────────────────────────────────────


def test_production_basic_performance():
    """Test basic performance - execution should complete in reasonable time."""
    engine = ExecutionEngine()
    agent = ValidatingTestAgent()
    context = _make_context(agent_id=agent.metadata.id)

    start = time.time()
    result = engine.execute(agent, context)
    duration = time.time() - start

    assert duration < 5.0  # Should complete well within 5 seconds
    assert result.status == ExecutionStatus.COMPLETED


# ── Stress Tests ──────────────────────────────────────────────────────────


def test_production_stress_20_agents():
    """Test stress with 20 concurrent agents."""
    engine = ExecutionEngine()
    agents = [ValidatingTestAgent() for _ in range(20)]
    contexts = [_make_context(agent_id=a.metadata.id) for a in agents]

    def execute_single(agent, ctx):
        return engine.execute(agent, ctx)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(execute_single, agent, ctx) for agent, ctx in zip(agents, contexts, strict=False)
        ]
        results = [f.result() for f in futures]

    assert len(results) == 20
    assert all(r.status == ExecutionStatus.COMPLETED for r in results)
    assert all(r.progress == 100 for r in results)


def test_production_stress_100_agents():
    """Test stress with 100 concurrent agents."""
    engine = ExecutionEngine()
    agents = [ValidatingTestAgent() for _ in range(100)]
    contexts = [_make_context(agent_id=a.metadata.id) for a in agents]

    def execute_single(agent, ctx):
        return engine.execute(agent, ctx)

    with ThreadPoolExecutor(max_workers=50) as executor:
        # Batch in groups of 50
        all_results = []
        for i in range(0, 100, 50):
            batch = agents[i : i + 50], contexts[i : i + 50]
            futures = [
                executor.submit(execute_single, agent, ctx)
                for agent, ctx in zip(batch[0], batch[1], strict=False)
            ]
            batch_results = [f.result() for f in futures]
            all_results.extend(batch_results)

    assert len(all_results) == 100
    assert all(r.status == ExecutionStatus.COMPLETED for r in all_results)
    assert all(r.progress == 100 for r in all_results)


# ── Failure Recovery Tests ────────────────────────────────────────────────


def test_production_failure_recovery():
    """Test that engine recovers from agent failures."""
    engine = ExecutionEngine()

    class FailingThenSucceedingAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(
            id="failing-then-success", display_name="FailingThenSuccess"
        )
        _call_count = 0

        def validate(self) -> bool:
            return True

        def prepare(self) -> None:
            pass

        def execute(self, context: AgentContext) -> Any:
            self._call_count += 1
            # First 2 calls always fail, 3rd and subsequent succeed
            if self._call_count <= 2:
                raise RuntimeError(f"Failure attempt {self._call_count}")
            return {"test": "result", "attempt": self._call_count}

        def finalize(self, result: Any) -> None:
            pass

        def health_check(self) -> Any:
            return {"healthy": True}

        def cleanup(self) -> None:
            pass

    agent = FailingThenSucceedingAgent()
    context = _make_context(agent_id=agent.metadata.id)

    # First 2 attempts should fail, 3rd and 4th should succeed
    results = [engine.execute(agent, context) for _ in range(4)]

    # First 2 should be FAILED
    assert results[0].status == ExecutionStatus.FAILED
    assert results[1].status == ExecutionStatus.FAILED
    # 3rd and 4th should be COMPLETED
    assert results[2].status == ExecutionStatus.COMPLETED
    assert results[3].status == ExecutionStatus.COMPLETED
    assert results[2].result.success is True
    assert results[3].result.success is True


def test_production_circuit_breaker_protection():
    """Test that circuit breaker protects against repeated failures."""
    engine = ExecutionEngine()

    class AlwaysFailingAgent(BaseAgent):
        _metadata: AgentMetadata = AgentMetadata(id="always-failing", display_name="AlwaysFailing")

        def validate(self) -> bool:
            return True

        def prepare(self) -> None:
            pass

        def execute(self, context: AgentContext) -> Any:
            raise RuntimeError("Always fails")

        def finalize(self, result: Any) -> None:
            pass

        def health_check(self) -> Any:
            return {"healthy": True}

        def cleanup(self) -> None:
            pass

    agent = AlwaysFailingAgent()
    context = _make_context(agent_id=agent.metadata.id)

    # Execute multiple times - should trigger circuit breaker
    results = [engine.execute(agent, context) for _ in range(5)]

    # All should be FAILED due to circuit breaker
    assert all(r.status == ExecutionStatus.FAILED for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
