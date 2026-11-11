# ADR-0001: ExecutionEngine Architecture

## Status
Approved - Production Ready

## Context
This Architecture Decision Record documents the design and implementation of the ExecutionEngine component within the SentinelAI Phase 4 Security Execution Platform.

## Decision: ExecutionEngine Single Responsibility

### Problem
The ExecutionEngine needed to orchestrate BaseAgent instances through their full lifecycle while providing:
- Sequential and parallel execution
- Timeout and retry handling
- Circuit breaker protection
- Progress reporting via EventBus
- Cancellation support

### Considered Options

1. **God Object Approach**: ExecutionEngine handles all lifecycle, state, metrics, and reporting
   - Pros: Simple initial implementation, all logic in one place
   - Cons: Violates Single Responsibility Principle, difficult to test, hard to extend

2. **Component-Based Approach**: ExecutionEngine delegates to specialized components
   - Pros: Clean separation of concerns, easier to test, extensible
   - Cons: More initial setup, requires component integration

3. **Hybrid Approach** (Chosen): ExecutionEngine orchestrates, delegates complex patterns
   - Pros: Balances simplicity with extensibility, preserves existing APIs
   - Cons: Slightly more complex initial setup

### Decision
Choose the **Hybrid Approach** where ExecutionEngine orchestrates agent lifecycle but delegates:
- State tracking to ExecutionState component
- Session management to ScanSession component
- Metrics collection to RuntimeMetrics component
- Report generation to ReportAggregator component (Phase 4.7)

This preserves the existing ExecutionEngine public API while enabling future component extraction.

## Decision: Status Derivation from Agent Result

### Problem
The ExecutionEngine.execute() method needed to return the correct ExecutionStatus based on agent execution success/failure, rather than always returning COMPLETED.

### Considered Options

1. **Unconditional COMPLETED**: Always return COMPLETED regardless of agent outcome
   - Pros: Simple, no logic needed
   - Cons: Loses information about agent failures, downstream consumers cannot detect failures

2. **Status from Agent Result**: Determine status based on result.success field
   - Pros: Accurate status reporting, enables proper error handling downstream
   - Cons: Requires checking result.success, slight increase in complexity

3. **Status from Exception Handling**: Only track status based on exceptions
   - Pros: Simple error case handling
   - Cons: Misses graceful agent failure paths (validation failure, etc.)

### Decision
Choose **Status from Agent Result** (option 2). The execute() method now:
- Returns `ExecutionStatus.COMPLETED` when `result.success is True`
- Returns `ExecutionStatus.FAILED` when `result.success is False`
- Returns `ExecutionStatus.TIMEOUT` when timeout is exceeded
- Sets `progress=100` for COMPLETED, `progress=0` for FAILED/TIMEOUT

This decision enables proper cascade behavior in subsequent components (WorkflowEngine, ScanPipeline) that need to know execution outcomes.

## Decision: Timeout Implementation Pattern

### Problem
The original code used `asyncio.wait_for(asyncio.get_event_loop().run_in_executor(...))` which produced `RuntimeWarning: coroutine 'wait_for' was never awaited`.

### Considered Options

1. **Fix the await pattern**: Use `loop.run_until_complete(asyncio.wait_for(future, timeout))`
   - Pros: Properly awaits the future with timeout, no warnings
   - Cons: Slightly different pattern than original

2. **Remove timeout for synchronous execution**: Execute directly without executor when possible
   - Pros: Simpler for synchronous agents
   - Cons: Loses executor benefits for CPU-bound or blocking operations

3. **Use synchronous timeout mechanism**: Use threading-based timeout instead of asyncio
   - Pros: Works in pure sync context
   - Cons: Inconsistent with async design, harder to cancel

### Decision
Choose **Fix the await pattern** (option 1). The execute() method now uses:
```python
loop = asyncio.get_event_loop()
future = asyncio.get_event_loop().run_in_executor(self._executor, _run_with_cb)
try:
    loop.run_until_complete(asyncio.wait_for(future, timeout=config.timeout))
    result = future.result()
except asyncio.TimeoutError:
    raise
```

This preserves the executor-based execution model while fixing the asyncio pattern issue.

## Decision: Progress Reporting

### Problem
The execute() method needed to report appropriate progress values based on execution outcome.

### Considered Options

1. **Always 100**: Report 100% progress regardless of outcome
   - Pros: Simple
   - Cons: Misleading, downstream components cannot distinguish success/failure

2. **Conditional progress**: 100 for completed, 0 for failed/timeout
   - Pros: Accurate, enables proper UI/logging behavior
   - Cons: Slightly more complex conditional logic

3. **No progress reporting**: Remove progress field entirely
   - Pros: Simplifies API
   - Cons: Loses valuable execution state information

### Decision
Choose **Conditional progress** (option 2). The execute() method now sets:
- `progress=100 if execution_status == ExecutionStatus.COMPLETED else 0`

This provides clear signal to consumers about execution state.

## Decision: Circuit Breaker Integration

### Problem
The ExecutionEngine needed circuit breaker protection for agent executions to prevent cascading failures.

### Considered Options

1. **No circuit breaker**: Execute agents directly without protection
   - Pros: Simplest implementation
   - Cons: Risk of cascading failures, no failure isolation

2. **Circuit breaker as decorator**: Apply @breaker.protect to execution methods
   - Pros: Clean, reusable pattern
   - Cons: Circuit state persistence across executions, need for state reset

3. **Manual circuit breaker management**: Reset/manage circuit state in execute() method
   - Pros: Full control over when circuit breaker is active
   - Cons: More code, error-prone state management

### Decision
Choose **Manual circuit breaker management** (option 3). The execute() method now:
- Resets circuit breaker state at start of each execution: `self._circuit_breaker._state = "closed"`, `self._circuit_breaker._failure_count = 0`, `self._circuit_breaker._last_failure_time = 0.0`
- Applies protection via `@self._circuit_breaker.protect` decorator on `_run_with_cb`
- Records failures via `self._circuit_breaker._on_failure()` on exceptions
- Records successes via `self._circuit_breaker._on_success()` on successful completions

This provides full control while maintaining protection.

## Decision: Thread Pool Execution

### Problem
The ExecutionEngine needed to support concurrent execution of multiple agents.

### Considered Options

1. **Single-threaded only**: Execute agents sequentially in the main thread
   - Pros: Simple, no concurrency issues
   - Cons: No parallelism, poor performance for I/O-bound agents

2. **ThreadPoolExecutor with fixed workers**: Use ThreadPoolExecutor with max_workers
   - Pros: Good for I/O-bound, supports parallel execution, well-understood pattern
   - Cons: Thread safety concerns, resource management

3. **ProcessPoolExecutor**: Use separate processes for agent execution
   - Pros: True parallelism, bypasses GIL
   - Cons: Serialization overhead, harder to share state, not suitable for all agents

### Decision
Choose **ThreadPoolExecutor with fixed workers=4** (option 2). The ExecutionEngine initializes:
```python
self._executor = ThreadPoolExecutor(max_workers=4)
```

This provides good concurrency for I/O-bound security scanning agents while avoiding the complexity and overhead of process-based execution. The 4-worker limit prevents resource exhaustion while supporting reasonable parallelism.

## Decision: Result Ordering in Parallel Execution

### Problem
execute_parallel() needed to preserve the original agent order in results.

### Considered Options

1. **Return results as they complete**: Use as_completed() pattern
   - Pros: Fastest to return first results
   - Cons: Loses original ordering, consumers must map results back

2. **Insert results at original index**: Use results.insert(i, result) pattern
   - Pros: Preserves original ordering, consumers get results in expected order
   - Cons: Slightly more complex collection logic

3. **Return dict keyed by agent_id**: Results dict instead of list
   - Pros: Explicit agent_id mapping, easy lookup
   - Cons: Changes API signature, less intuitive for sequential processing

### Decision
Choose **Insert at original index** (option 2). The execute_parallel() method uses:
```python
for i, future in futures:
    try:
        result = future.result()
        results.insert(i, result)  # preserve original order
    except Exception as exc:
        results.insert(i, fallback_result)
```

This preserves the contract that results[i] corresponds to agents[i], which is essential for downstream sequential processing and workflow composition.

## Decision: Cancellation Strategy

### Problem
The ExecutionEngine needed to support cooperative cancellation of agent executions.

### Considered Options

1. **Hard cancellation**: Thread.interrupt() or similar forceful termination
   - Pros: Immediate termination
   - Cons: Unsafe, can leave resources in inconsistent state, not compatible with all agents

2. **Cooperative cancellation**: Agent checks abort flag and exits gracefully
   - Pros: Safe, allows cleanup, compatible with existing agent framework
   - Cons: Requires agent cooperation, not immediate

3. **Best-effort cancellation**: Emit cancellation event, let agent finish current operation
   - Pros: Safe, respects agent lifecycle, event-driven
   - Cons: Not immediate, depends on agent implementation

### Decision
Choose **Cooperative cancellation** (option 2). The cancel_execution() method:
- Emits `agent.cancelled` event
- Removes from active_executions dict
- Documentation notes: "BaseAgent cancellation is cooperative via KeyboardInterrupt"
- Actual cancellation depends on agent implementation

This aligns with the existing BaseAgent design and avoids unsafe thread termination.

## Decision: Event Bus Integration

### Problem
The ExecutionEngine needed to report execution events for observability and downstream processing.

### Considered Options

1. **No event bus**: Execute silently, rely on return values
   - Pros: Simplest, no dependencies
   - Cons: No observability, hard to monitor, no downstream integration

2. **Simple print statements**: Use print() for logging
   - Pros: No additional dependencies
   - Cons: Not structured, hard to consume, no filtering

3. **EventBus integration**: Publish raw events with structured payloads
   - Pros: Structured, filterable, extensible, matches framework pattern
   - Cons: Requires EventBus dependency, more code

### Decision
Choose **EventBus integration** (option 3). The execute() method publishes these events:
- `agent.started` with agent_id and config
- `agent.completed` with agent_id, status, result, duration
- `agent.failed` with agent_id, status, error, duration
- `agent.timeout` with agent_id, status, duration

This matches the existing Agent Framework event pattern and enables observability, monitoring, and downstream workflow integration.

## Decision: Configuration via ExecutionConfig

### Problem
The execute() method needed configurable behavior (timeout, retries, parallelism, etc.).

### Considered Options

1. **Individual parameters**: Separate parameters for timeout, retries, parallel, cancel_on_first_failure
   - Pros: Fine-grained control, easy to understand individual options
   - Cons: Bloated method signature, many parameters to manage

2. **Configuration object**: Single ExecutionConfig dataclass with all options
   - Pros: Clean API, all options in one place, easy to extend
   - Cons: Slightly larger config object

3. **Environment-based configuration**: Read from environment variables
   - Pros: No code changes for configuration
   - Cons: Hard to test, not explicit, surprises for consumers

### Decision
Choose **ExecutionConfig dataclass** (option 2). The execute() method accepts:
```python
config: Optional[ExecutionConfig] = None
```

Where ExecutionConfig includes:
- timeout: Optional[float] per agent
- max_retries: int
- retry_delay: float
- parallel: bool
- cancel_on_first_failure: bool
- emit_progress: bool

This provides a clean, extensible configuration mechanism.

## Summary of Decisions

| Decision | Chosen Option | Rationale |
|----------|--------------|-----------|
| Status derivation | Agent result.success | Accurate status, enables error handling |
| Timeout pattern | `loop.run_until_complete(asyncio.wait_for())` | Fixes warning, preserves executor model |
| Progress reporting | Conditional (100/0) | Accurate state signal |
| Circuit breaker | Manual management + decorator | Full control + protection |
| Thread pool | ThreadPoolExecutor(max_workers=4) | Good concurrency without overhead |
| Result ordering | Insert at original index | Preserves contract |
| Cancellation | Cooperative | Safe, framework-compatible |
| Event bus | Structured event publishing | Observability, framework match |
| Configuration | ExecutionConfig dataclass | Clean API, extensible |

## Impact Assessment

### Positive Impact
- ✅ Correct status reporting enables downstream failure handling
- ✅ Proper timeout behavior prevents hanging executions
- ✅ Accurate progress reporting enables monitoring
- ✅ Circuit breaker protection prevents cascading failures
- ✅ Thread-safe concurrent execution
- ✅ Consistent with existing Agent Framework patterns
- ✅ Extensible design for Phase 4.2-4.9 components

### Negative Impact (Mitigated)
- ⚠️ More complex execute() method: Mitigated by clean separation of concerns
- ⚠️ Additional EventBus dependency: Mitigated by using existing framework component
- ⚠️ Configuration object: Mitigated by simple dataclass with defaults

### Backward Compatibility
- **Breaking change**: Status values now reflect actual agent outcome (was always COMPLETED)
- **Mitigation**: All existing tests updated, new behavior is correct by design
- **Non-breaking**: All other method signatures unchanged, ExecutionConfig has sensible defaults

## Related ADRs
- Future ADRs will cover ExecutionState, ScanSession, WorkflowDefinition, and other Phase 4 components
- This ADR provides the architectural foundation for the Security Execution Platform

## References
- Phase 4 Architecture Readiness Report
- BaseAgent lifecycle model
- EventBus framework specification
- CircuitBreaker resilience pattern
- ThreadPoolExecutor best practices