"""Distributed tracing for SentinelAI.

Provides OpenTelemetry-compatible tracing with:

- Correlation ID propagation across services
- Span creation and context propagation
- Trace and span ID extraction from headers
- Integration with structured logging
- Performance timing for spans
- Custom attribute support

If OpenTelemetry is installed, traces are exported to the configured
backend (Jaeger, Zipkin, OTLP). Otherwise, falls back to local
correlation-ID-only tracing.

Usage::

    from app.utils.tracing import traced, get_trace_context, correlation_id

    @traced("scan.execute")
    def execute_scan(scan_id):
        with create_span("parse_spec") as span:
            span.set_attribute("scan.id", scan_id)
            return parse_openapi_spec(scan_id)
"""

from __future__ import annotations

import contextvars
import functools
import time
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from typing import Any

from app.utils.logger import logger

# ── Correlation context ──────────────────────────────────────────────

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")
_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_span_id: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")
_trace_sampled: contextvars.ContextVar[bool] = contextvars.ContextVar("trace_sampled", default=True)


def correlation_id() -> str:
    """Get the current correlation ID."""
    cid = _correlation_id.get()
    if not cid:
        cid = str(uuid.uuid4())
        _correlation_id.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for this context."""
    _correlation_id.set(cid)


def trace_id() -> str:
    """Get the current trace ID."""
    return _trace_id.get()


def span_id() -> str:
    """Get the current span ID."""
    return _span_id.get()


# ── Trace Context for HTTP propagation ───────────────────────────────


def get_trace_context() -> dict[str, str]:
    """Get trace context headers for outbound HTTP requests.

    Returns a dict suitable for passing as headers:
        {
            "X-Request-ID": "...",
            "X-Trace-ID": "...",
            "X-Correlation-ID": "...",
        }
    """
    return {
        "X-Request-ID": correlation_id(),
        "X-Trace-ID": trace_id() or correlation_id(),
        "X-Correlation-ID": correlation_id(),
    }


def extract_trace_context(headers: dict[str, str]) -> dict[str, str]:
    """Extract trace context from incoming request headers.

    Returns a dict with correlation_id, trace_id, span_id.
    """
    cid = headers.get("X-Correlation-ID") or headers.get("X-Request-ID", "")
    tid = headers.get("X-Trace-ID", "")
    sid = headers.get("X-Span-ID", "")

    if cid:
        set_correlation_id(cid)
    if tid:
        _trace_id.set(tid)

    return {
        "correlation_id": cid,
        "trace_id": tid,
        "span_id": sid,
    }


# ── Span tracking ────────────────────────────────────────────────────


@dataclass
class Span:
    """A trace span representing a unit of work."""

    name: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "OK"
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status_message: str = ""

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add a timed event to the span."""
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def set_status(self, status: str, message: str = "") -> None:
        """Set span status (OK, ERROR, UNSET)."""
        self.status = status
        self.status_message = message

    def finish(self) -> None:
        """End the span."""
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        """Span duration in milliseconds."""
        end = self.end_time or time.time()
        return round((end - self.start_time) * 1000, 2)

    def to_dict(self) -> dict:
        """Serialize span to dict."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": self.events,
        }


# ── Span storage ─────────────────────────────────────────────────────

_current_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "current_span", default=None
)
_completed_spans: list[dict[str, Any]] = []
_max_completed_spans = 1000


@contextmanager
def create_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[Span, None, None]:
    """Create a child span within the current context.

    Usage::

        with create_span("parse_spec", {"scan.id": 42}) as span:
            result = parse_spec()
            span.set_attribute("spec.version", "3.0")
    """
    tid = trace_id() or correlation_id()
    parent = _current_span.get()
    parent_sid = parent.span_id if parent else None

    span = Span(
        name=name,
        trace_id=tid,
        span_id=str(uuid.uuid4())[:16],
        parent_span_id=parent_sid,
        attributes=attributes or {},
    )

    token = _current_span.set(span)
    try:
        yield span
        span.set_status("OK")
    except Exception as e:
        span.set_status("ERROR", str(e))
        span.add_event(
            "exception",
            {
                "type": type(e).__name__,
                "message": str(e),
            },
        )
        raise
    finally:
        span.finish()
        _current_span.reset(token)

        # Store completed span
        with _span_lock:
            _completed_spans.append(span.to_dict())
            if len(_completed_spans) > _max_completed_spans:
                _completed_spans.pop(0)

        # Log span completion
        logger.info(
            f"Span completed: {span.name}",
            extra={
                "span_name": span.name,
                "duration_ms": span.duration_ms,
                "status": span.status,
                "trace_id": span.trace_id,
                "span_id": span.span_id,
            },
        )


_span_lock = __import__("threading").Lock()


def traced(
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Callable:
    """Decorator to trace a function as a span.

    Usage::

        @traced("scan.execute")
        def execute_scan(scan_id):
            ...
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with create_span(span_name, attributes) as span:
                # Add function arguments as attributes
                import inspect

                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                for key, value in bound.arguments.items():
                    if key != "self" and not key.startswith("_"):
                        with suppress(Exception):
                            span.set_attribute(f"arg.{key}", str(value)[:200])

                result = func(*args, **kwargs)
                span.set_attribute("return_type", type(result).__name__)
                return result

        return wrapper

    return decorator


@contextmanager
def trace_from_headers(headers: dict[str, str]) -> Generator[None, None, None]:
    """Start a trace from incoming HTTP request headers.

    Usage::

        with trace_from_headers(request.headers):
            response = handle_request()
    """
    ctx = extract_trace_context(headers)
    cid = ctx.get("correlation_id") or str(uuid.uuid4())
    set_correlation_id(cid)

    token = _trace_id.set(ctx.get("trace_id", cid))
    try:
        yield
    finally:
        _trace_id.reset(token)


# ── Completed spans access ───────────────────────────────────────────


def get_recent_spans(limit: int = 50) -> list[dict]:
    """Get recent completed spans."""
    with _span_lock:
        return list(_completed_spans[-limit:])


def get_trace_spans(trace_id: str) -> list[dict]:
    """Get all spans for a specific trace ID."""
    with _span_lock:
        return [s for s in _completed_spans if s.get("trace_id") == trace_id]


def clear_spans() -> None:
    """Clear completed span storage."""
    with _span_lock:
        _completed_spans.clear()


# ── OpenTelemetry Integration (optional) ─────────────────────────────

_otel_initialized = False


def init_opentelemetry(
    service_name: str = "sentinelai",
    endpoint: str | None = None,
) -> None:
    """Initialize OpenTelemetry if available.

    Falls back gracefully if opentelemetry packages are not installed.
    """
    global _otel_initialized
    if _otel_initialized:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()
        trace.set_tracer_provider(provider)

        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info(f"OpenTelemetry exporter configured: {endpoint}")
            except ImportError:
                logger.warning("OTLP exporter not available; using console exporter")
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter

                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        _otel_initialized = True
        logger.info("OpenTelemetry tracing initialized")

    except ImportError:
        logger.info("OpenTelemetry not installed; using correlation-ID-only tracing")
    except Exception as e:
        logger.warning(f"OpenTelemetry init failed: {e}")
