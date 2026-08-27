"""SRE and Observability tests.

Tests cover:
- Circuit breaker states and transitions
- Retry with exponential backoff
- Graceful degradation and fallback
- Bulkhead concurrency limits
- SLA tracking and error budget
- Alert thresholds and management
- Uptime monitoring
- Incident tracking
- Distributed tracing and correlation
- Performance metrics
"""

import pytest
import time
import threading
from unittest.mock import MagicMock

from app.utils.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    Bulkhead,
    BulkheadRejectionError,
    retry_with_backoff,
    graceful_fallback,
)
from app.utils.sla import (
    SLATracker,
    SLADefinition,
    AlertManager,
    AlertSeverity,
    AlertStatus,
    UptimeMonitor,
    IncidentTracker,
)
from app.utils.tracing import (
    create_span,
    traced,
    correlation_id,
    set_correlation_id,
    get_trace_context,
    extract_trace_context,
    get_recent_spans,
    clear_spans,
)


# ═══════════════════════════════════════════════════════════════════════
# Circuit Breaker Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCircuitBreaker:
    """Test circuit breaker state machine."""

    def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            try:
                cb._on_failure()
            except Exception:
                pass
        assert cb.state == CircuitState.OPEN

    def test_protect_raises_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb._on_failure()  # Opens the circuit

        @cb.protect
        def do_something():
            return "ok"

        with pytest.raises(CircuitBreakerOpenError):
            do_something()

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        cb._on_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_after_success_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1, success_threshold=1)
        cb._on_failure()
        time.sleep(0.15)
        _ = cb.state  # Triggers transition to HALF_OPEN
        cb._on_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        cb._on_failure()
        time.sleep(0.15)
        _ = cb.state  # HALF_OPEN
        cb._on_failure()
        assert cb.state == CircuitState.OPEN

    def test_protect_decorator_success(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        @cb.protect
        def succeed():
            return 42

        assert succeed() == 42
        assert cb.state == CircuitState.CLOSED

    def test_protect_decorator_failure(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        @cb.protect
        def fail():
            raise ValueError("boom")

        for _ in range(3):
            with pytest.raises(ValueError):
                fail()
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb._on_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_get_state(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        state = cb.get_state()
        assert state["name"] == "test"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0


# ═══════════════════════════════════════════════════════════════════════
# Retry Tests
# ═══════════════════════════════════════════════════════════════════════


class TestRetryWithBackoff:
    """Test retry with exponential backoff."""

    def test_succeeds_on_first_try(self):
        result = retry_with_backoff(lambda: "ok", max_retries=3, base_delay=0.01)
        assert result == "ok"

    def test_succeeds_after_retries(self):
        counter = {"attempts": 0}

        def flaky():
            counter["attempts"] += 1
            if counter["attempts"] < 3:
                raise ValueError("not yet")
            return "done"

        result = retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        assert result == "done"
        assert counter["attempts"] == 3

    def test_fails_after_max_retries(self):
        def always_fail():
            raise ValueError("always")

        with pytest.raises(ValueError, match="always"):
            retry_with_backoff(always_fail, max_retries=2, base_delay=0.01)

    def test_retry_callback(self):
        callback_calls = []

        def on_retry(attempt, exc, delay):
            callback_calls.append(attempt)

        counter = {"n": 0}

        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise ValueError("nope")
            return "ok"

        retry_with_backoff(
            flaky, max_retries=3, base_delay=0.01, on_retry=on_retry
        )
        assert len(callback_calls) == 2  # 2 retries before success


# ═══════════════════════════════════════════════════════════════════════
# Graceful Degradation Tests
# ═══════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    """Test graceful fallback patterns."""

    def test_primary_succeeds(self):
        result = graceful_fallback(
            primary=lambda: "primary",
            fallback=lambda: "fallback",
        )
        assert result == "primary"

    def test_primary_fails_fallback_succeeds(self):
        def fail():
            raise ValueError("broken")

        result = graceful_fallback(
            primary=fail,
            fallback=lambda: "fallback_result",
        )
        assert result == "fallback_result"

    def test_both_fail_returns_none(self):
        def fail():
            raise ValueError("broken")

        result = graceful_fallback(
            primary=fail,
            fallback=fail,
        )
        assert result is None

    def test_no_fallback_returns_none(self):
        def fail():
            raise ValueError("broken")

        result = graceful_fallback(primary=fail)
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# Bulkhead Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBulkhead:
    """Test bulkhead concurrency limits."""

    def test_allows_within_limit(self):
        bh = Bulkhead("test", max_concurrent=3)
        result = bh.execute(lambda: "ok")
        assert result == "ok"

    def test_rejects_when_full(self):
        bh = Bulkhead("test", max_concurrent=1)
        lock = threading.Event()
        released = threading.Event()

        def hold():
            lock.wait()
            return "done"

        # Hold the bulkhead
        def run_hold():
            try:
                bh.execute(hold)
            finally:
                released.set()

        t = threading.Thread(target=run_hold)
        t.start()
        time.sleep(0.05)

        with pytest.raises(BulkheadRejectionError):
            bh.execute(lambda: "should fail")

        lock.set()
        t.join()

    def test_get_state(self):
        bh = Bulkhead("test", max_concurrent=5)
        state = bh.get_state()
        assert state["name"] == "test"
        assert state["max_concurrent"] == 5
        assert state["active"] == 0


# ═══════════════════════════════════════════════════════════════════════
# SLA Tracker Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSLATracker:
    """Test SLA tracking and error budget."""

    def test_availability_with_no_data(self):
        tracker = SLATracker()
        avail = tracker.get_availability()
        assert avail["availability_percent"] == 100.0

    def test_availability_calculation(self):
        tracker = SLATracker()
        for _ in range(90):
            tracker.record_request(success=True, latency_ms=10)
        for _ in range(10):
            tracker.record_request(success=False, latency_ms=100)

        avail = tracker.get_availability()
        assert avail["availability_percent"] == 90.0
        assert avail["met"] is False

    def test_latency_percentiles(self):
        tracker = SLATracker()
        for i in range(100):
            tracker.record_request(success=True, latency_ms=float(i))

        latency = tracker.get_latency()
        assert latency["p50_ms"] > 0
        assert latency["p95_ms"] > 0
        assert latency["p99_ms"] > 0

    def test_error_rate(self):
        tracker = SLATracker()
        for _ in range(98):
            tracker.record_request(success=True, latency_ms=10)
        for _ in range(2):
            tracker.record_request(success=False, latency_ms=100)

        error_rate = tracker.get_error_rate()
        assert error_rate["error_rate_percent"] == 2.0

    def test_error_budget(self):
        tracker = SLATracker()
        for _ in range(99900):
            tracker.record_request(success=True, latency_ms=10)
        for _ in range(10):
            tracker.record_request(success=False, latency_ms=100)

        budget = tracker.get_error_budget()
        assert budget["budget_percent"] == 0.1
        assert budget["allowed_failures"] > 0
        assert budget["status"] in ("healthy", "warning", "critical")

    def test_sla_summary(self):
        tracker = SLATracker()
        for _ in range(50):
            tracker.record_request(success=True, latency_ms=10)

        summary = tracker.get_sla_summary()
        assert "overall_status" in summary
        assert "availability" in summary
        assert "latency" in summary
        assert "error_rate" in summary
        assert "error_budget" in summary


# ═══════════════════════════════════════════════════════════════════════
# Alert Manager Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAlertManager:
    """Test alert threshold detection and management."""

    def test_no_alerts_when_healthy(self):
        tracker = SLATracker()
        for _ in range(100):
            tracker.record_request(success=True, latency_ms=10)

        manager = AlertManager()
        fired = manager.check_thresholds(tracker)
        assert len(fired) == 0

    def test_alert_fires_on_low_availability(self):
        tracker = SLATracker()
        for _ in range(10):
            tracker.record_request(success=False, latency_ms=100)

        manager = AlertManager()
        fired = manager.check_thresholds(tracker)
        # Should fire availability alerts
        assert len(fired) > 0

    def test_acknowledge_alert(self):
        manager = AlertManager()
        from app.utils.sla import Alert

        # Manually add an active alert
        alert = Alert(
            id="test-1",
            name="test_alert",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            message="test",
            source="test",
            created_at=time.time(),
        )
        manager._active_alerts["test_alert"] = alert

        result = manager.acknowledge_alert("test_alert")
        assert result is True

    def test_get_active_alerts(self):
        manager = AlertManager()
        alerts = manager.get_active_alerts()
        assert isinstance(alerts, list)


# ═══════════════════════════════════════════════════════════════════════
# Uptime Monitor Tests
# ═══════════════════════════════════════════════════════════════════════


class TestUptimeMonitor:
    """Test uptime monitoring."""

    def test_record_success(self):
        monitor = UptimeMonitor()
        monitor.record_check("api", success=True, latency_ms=5.0)
        summary = monitor.get_uptime_summary()
        assert summary["api"]["status"] == "healthy"

    def test_record_failure(self):
        monitor = UptimeMonitor()
        monitor.record_check("api", success=False)
        summary = monitor.get_uptime_summary()
        assert summary["api"]["consecutive_failures"] == 1

    def test_uptime_calculation(self):
        monitor = UptimeMonitor()
        for _ in range(9):
            monitor.record_check("api", success=True)
        monitor.record_check("api", success=False)

        summary = monitor.get_uptime_summary()
        assert summary["api"]["uptime_percent"] == 90.0


# ═══════════════════════════════════════════════════════════════════════
# Incident Tracker Tests
# ═══════════════════════════════════════════════════════════════════════


class TestIncidentTracker:
    """Test incident lifecycle management."""

    def test_create_incident(self):
        tracker = IncidentTracker()
        incident = tracker.create_incident("Test outage", AlertSeverity.CRITICAL)
        assert incident.id.startswith("INC-")
        assert incident.status == "investigating"

    def test_update_incident(self):
        tracker = IncidentTracker()
        incident = tracker.create_incident("Test incident")
        updated = tracker.update_incident(
            incident.id, status="identified", message="Root cause found"
        )
        assert updated.status == "identified"
        assert updated.identified_at is not None

    def test_resolve_incident(self):
        tracker = IncidentTracker()
        incident = tracker.create_incident("Test incident")
        tracker.update_incident(incident.id, status="resolved", message="Fixed")
        active = tracker.get_active_incidents()
        assert len(active) == 0

    def test_incident_history(self):
        tracker = IncidentTracker()
        for i in range(5):
            tracker.create_incident(f"Incident {i}")
        history = tracker.get_incident_history()
        assert len(history) == 5


# ═══════════════════════════════════════════════════════════════════════
# Tracing Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDistributedTracing:
    """Test correlation IDs and span tracking."""

    def test_correlation_id_generation(self):
        cid = correlation_id()
        assert len(cid) > 0

    def test_set_correlation_id(self):
        set_correlation_id("test-123")
        assert correlation_id() == "test-123"

    def test_trace_context_headers(self):
        set_correlation_id("ctx-456")
        headers = get_trace_context()
        assert headers["X-Correlation-ID"] == "ctx-456"
        assert "X-Request-ID" in headers

    def test_extract_trace_context(self):
        headers = {
            "X-Correlation-ID": "extracted-789",
            "X-Trace-ID": "trace-abc",
        }
        ctx = extract_trace_context(headers)
        assert ctx["correlation_id"] == "extracted-789"

    def test_create_span(self):
        clear_spans()
        with create_span("test_span", {"key": "value"}) as span:
            span.set_attribute("extra", "data")
            time.sleep(0.01)
        assert span.duration_ms > 0
        assert span.status == "OK"

    def test_span_on_exception(self):
        clear_spans()
        with pytest.raises(ValueError):
            with create_span("failing_span") as span:
                raise ValueError("test error")
        assert span.status == "ERROR"

    def test_traced_decorator(self):
        clear_spans()

        @traced("my_function")
        def my_function(x):
            return x * 2

        result = my_function(21)
        assert result == 42

    def test_get_recent_spans(self):
        clear_spans()
        with create_span("span_1"):
            pass
        with create_span("span_2"):
            pass
        spans = get_recent_spans()
        assert len(spans) >= 2

    def test_trace_from_headers(self):
        clear_spans()
        headers = {"X-Correlation-ID": "from-headers-123"}
        from app.utils.tracing import trace_from_headers

        with trace_from_headers(headers):
            assert correlation_id() == "from-headers-123"
