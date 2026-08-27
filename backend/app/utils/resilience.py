"""Resilience patterns for SentinelAI.

Provides production-grade resilience patterns:

- Circuit Breaker: Prevents cascading failures by opening the circuit
  when failure rate exceeds threshold.
- Retry with Backoff: Automatic retries with exponential backoff and jitter.
- Graceful Degradation: Fallback strategies when upstream services fail.
- Bulkhead: Isolate failures to prevent resource exhaustion.

Usage::

    from app.utils.resilience import CircuitBreaker, retry_with_backoff, graceful_fallback

    # Circuit breaker around an external service call
    breaker = CircuitBreaker("ollama", failure_threshold=5, recovery_timeout=30)

    @breaker.protect
    def call_ollama(prompt):
        return requests.post(ollama_url, json=prompt, timeout=10)

    # Retry with backoff
    result = await retry_with_backoff(
        lambda: db.query(Scan).first(),
        max_retries=3,
        base_delay=0.5,
    )

    # Graceful fallback
    result = graceful_fallback(
        primary=lambda: call_ai_service(),
        fallback=lambda: get_cached_result(),
        fallback_name="cached_result",
    )
"""

from __future__ import annotations

import asyncio
import functools
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from app.utils.logger import logger


# ═══════════════════════════════════════════════════════════════════════
# Circuit Breaker
# ═══════════════════════════════════════════════════════════════════════


class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    States:
        CLOSED → (failures >= threshold) → OPEN
        OPEN → (timeout expires) → HALF_OPEN
        HALF_OPEN → (success) → CLOSED
        HALF_OPEN → (failure) → OPEN
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    success_threshold: int = 1  # successes needed to close from half-open
    expected_exceptions: tuple = (Exception,)

    # Internal state
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _half_open_successes: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        """Check if we should transition from OPEN to HALF_OPEN."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_successes = 0
                    logger.info(f"Circuit breaker '{self.name}' → HALF_OPEN")
            return self._state

    def _on_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    logger.info(
                        f"Circuit breaker '{self.name}' → CLOSED "
                        f"(recovered after {self._half_open_successes} successes)"
                    )

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' → OPEN "
                    f"(failed during half-open recovery)"
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' → OPEN "
                    f"(failure count {self._failure_count} >= {self.failure_threshold})"
                )

    def protect(self, func: Callable) -> Callable:
        """Decorator to protect a function with the circuit breaker."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry after {self.recovery_timeout}s."
                )
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exceptions:
                self._on_failure()
                raise

        return wrapper

    async def aprotect(self, func: Callable) -> Callable:
        """Decorator to protect an async function with the circuit breaker."""

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry after {self.recovery_timeout}s."
                )
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exceptions:
                self._on_failure()
                raise

        return wrapper

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_successes = 0
            logger.info(f"Circuit breaker '{self.name}' manually reset → CLOSED")

    def get_state(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure": self._last_failure_time,
            "time_since_failure": round(
                time.time() - self._last_failure_time, 1
            )
            if self._last_failure_time
            else None,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is in the OPEN state."""

    pass


# ═══════════════════════════════════════════════════════════════════════
# Retry with Exponential Backoff
# ═══════════════════════════════════════════════════════════════════════


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Callable | None = None,
) -> Any:
    """Execute a function with retry and exponential backoff.

    Args:
        func: The function to execute.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries.
        exponential_base: Base for exponential backoff.
        jitter: Add random jitter to prevent thundering herd.
        retryable_exceptions: Tuple of exceptions that trigger retries.
        on_retry: Callback function(attempt, exception, delay) called on each retry.

    Returns:
        The return value of the function.

    Raises:
        The last exception if all retries fail.
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                break

            delay = min(
                base_delay * (exponential_base**attempt),
                max_delay,
            )
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {type(e).__name__}: {e}"
            )

            if on_retry:
                on_retry(attempt + 1, e, delay)

            time.sleep(delay)

    raise last_exception


async def async_retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
) -> Any:
    """Async version of retry with backoff."""
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                break

            delay = min(
                base_delay * (exponential_base**attempt),
                max_delay,
            )
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                f"Async retry {attempt + 1}/{max_retries} after {delay:.1f}s: {type(e).__name__}"
            )
            await asyncio.sleep(delay)

    raise last_exception


# ═══════════════════════════════════════════════════════════════════════
# Graceful Degradation
# ═══════════════════════════════════════════════════════════════════════


def graceful_fallback(
    primary: Callable,
    fallback: Callable | None = None,
    fallback_name: str = "fallback",
    log_degradation: bool = True,
) -> Any:
    """Execute primary function with optional fallback on failure.

    If the primary function raises an exception, execute the fallback.
    If no fallback is provided, return None.
    """
    try:
        return primary()
    except Exception as e:
        if log_degradation:
            logger.warning(
                f"Graceful degradation: primary failed ({type(e).__name__}: {e}), "
                f"using {fallback_name}"
            )
        if fallback:
            try:
                return fallback()
            except Exception as fb_error:
                logger.error(
                    f"Fallback '{fallback_name}' also failed: "
                    f"{type(fb_error).__name__}: {fb_error}"
                )
                return None
        return None


async def async_graceful_fallback(
    primary: Callable,
    fallback: Callable | None = None,
    fallback_name: str = "fallback",
) -> Any:
    """Async version of graceful fallback."""
    try:
        return await primary()
    except Exception as e:
        logger.warning(
            f"Graceful degradation: primary failed ({type(e).__name__}), "
            f"using {fallback_name}"
        )
        if fallback:
            try:
                return await fallback()
            except Exception:
                return None
        return None


# ═══════════════════════════════════════════════════════════════════════
# Bulkhead (Isolation)
# ═══════════════════════════════════════════════════════════════════════


class Bulkhead:
    """Limit concurrent executions to prevent resource exhaustion.

    Similar to a thread pool limiter but works with both sync and async.
    """

    def __init__(self, name: str, max_concurrent: int = 10):
        self.name = name
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active = 0
        self._total_executions = 0
        self._rejected = 0
        self._lock = threading.Lock()

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function within the bulkhead."""
        if not self._semaphore.acquire(blocking=False):
            with self._lock:
                self._rejected += 1
            raise BulkheadRejectionError(
                f"Bulkhead '{self.name}' full "
                f"({self.max_concurrent} concurrent limit)"
            )
        try:
            with self._lock:
                self._active += 1
                self._total_executions += 1
            return func(*args, **kwargs)
        finally:
            with self._lock:
                self._active -= 1
            self._semaphore.release()

    def get_state(self) -> dict:
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active": self._active,
            "available": self.max_concurrent - self._active,
            "total_executions": self._total_executions,
            "rejected": self._rejected,
        }


class BulkheadRejectionError(Exception):
    """Raised when the bulkhead rejects a request due to capacity."""

    pass


# ═══════════════════════════════════════════════════════════════════════
# Pre-built Circuit Breakers
# ═══════════════════════════════════════════════════════════════════════

# Ollama / AI engine circuit breaker
ollama_breaker = CircuitBreaker(
    name="ollama",
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exceptions=(Exception,),
)

# Database circuit breaker
database_breaker = CircuitBreaker(
    name="database",
    failure_threshold=5,
    recovery_timeout=15.0,
    expected_exceptions=(Exception,),
)

# Redis circuit breaker
redis_breaker = CircuitBreaker(
    name="redis",
    failure_threshold=3,
    recovery_timeout=20.0,
    expected_exceptions=(Exception,),
)

# External API circuit breakers
scanner_breaker = CircuitBreaker(
    name="scanner",
    failure_threshold=5,
    recovery_timeout=10.0,
    expected_exceptions=(Exception,),
)

# Bulkheads
ai_bulkhead = Bulkhead(name="ai_engine", max_concurrent=5)
scan_bulkhead = Bulkhead(name="scanner", max_concurrent=3)
db_bulkhead = Bulkhead(name="database", max_concurrent=20)


# ═══════════════════════════════════════════════════════════════════════
# Resilience Dashboard
# ═══════════════════════════════════════════════════════════════════════


def get_resilience_status() -> dict:
    """Get the current status of all resilience components."""
    return {
        "circuit_breakers": [
            ollama_breaker.get_state(),
            database_breaker.get_state(),
            redis_breaker.get_state(),
            scanner_breaker.get_state(),
        ],
        "bulkheads": [
            ai_bulkhead.get_state(),
            scan_bulkhead.get_state(),
            db_bulkhead.get_state(),
        ],
    }
