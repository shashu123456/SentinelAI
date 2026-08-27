"""Structured JSON logger for SentinelAI.

Features:
- JSON-formatted output for log aggregation (ELK, Datadog, etc.)
- Correlation ID propagation via contextvars
- User ID and scan ID context binding
- Request path and method in every log entry
- Performance slow-log threshold
- Optional Sentry integration
- File + stdout dual output

Usage::

    from app.utils.logger import logger, bind_request_context, clear_request_context

    # In middleware:
    bind_request_context(request_id="abc", user_id=123, path="/api/scans")
    logger.info("Scan started", extra={"scan_id": 42})
    clear_request_context()
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# ── Context variables for correlation ────────────────────────────────
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
_user_id_ctx: ContextVar[int | None] = ContextVar("user_id", default=None)
_username_ctx: ContextVar[str | None] = ContextVar("username", default=None)
_scan_id_ctx: ContextVar[int | None] = ContextVar("scan_id", default=None)
_path_ctx: ContextVar[str] = ContextVar("path", default="")
_method_ctx: ContextVar[str] = ContextVar("method", default="")


def bind_request_context(
    request_id: str = "-",
    user_id: int | None = None,
    username: str | None = None,
    path: str = "",
    method: str = "",
) -> None:
    """Bind request context for all log entries within this coroutine."""
    _request_id_ctx.set(request_id)
    _user_id_ctx.set(user_id)
    _username_ctx.set(username)
    _path_ctx.set(path)
    _method_ctx.set(method)


def bind_scan_context(scan_id: int | None) -> None:
    """Bind a scan ID for correlating logs to a specific scan."""
    _scan_id_ctx.set(scan_id)


def clear_request_context() -> None:
    """Reset all context variables."""
    _request_id_ctx.set("-")
    _user_id_ctx.set(None)
    _username_ctx.set(None)
    _scan_id_ctx.set(None)
    _path_ctx.set("")
    _method_ctx.set("")


# ── JSON Formatter ──────────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON for log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Correlation context
        rid = _request_id_ctx.get("-")
        if rid and rid != "-":
            entry["request_id"] = rid

        uid = _user_id_ctx.get(None)
        if uid is not None:
            entry["user_id"] = uid

        uname = _username_ctx.get(None)
        if uname:
            entry["username"] = uname

        sid = _scan_id_ctx.get(None)
        if sid is not None:
            entry["scan_id"] = sid

        path = _path_ctx.get("")
        if path:
            entry["path"] = path
            entry["method"] = _method_ctx.get("")

        # Duration if present
        duration = getattr(record, "duration", None)
        if duration is not None:
            entry["duration_ms"] = round(duration * 1000, 2)

        # Status code if present
        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            entry["status_code"] = status_code

        # Exception info
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }
            entry["traceback"] = self.formatException(record.exc_info)

        # Extra fields from logger calls
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "module",
            "funcName",
            "lineno",
            "levelname",
            "levelno",
            "pathname",
            "process",
            "processName",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "message",
            "msecs",
            "relativeCreated",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in standard_attrs:
                continue
            if key in entry:
                continue
            entry[key] = value

        return json.dumps(entry, default=str, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Fallback human-readable formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        rid = _request_id_ctx.get("-")
        uid = _user_id_ctx.get(None)
        ts = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
        parts = [f"[{ts}]"]
        parts.append(f"{record.levelname:8s}")
        if rid and rid != "-":
            parts.append(f"[{rid[:8]}]")
        if uid is not None:
            parts.append(f"[u:{uid}]")
        parts.append(f"{record.name}: {record.getMessage()}")
        return " ".join(parts)


# ── Logger Setup ────────────────────────────────────────────────────


def _use_json_logging() -> bool:
    """Determine if JSON logging should be used."""
    env = os.environ.get("SENTINEL_LOG_FORMAT", "").lower()
    if env == "json":
        return True
    if env == "text":
        return False
    # Default: JSON in production (Render, Docker, k8s), text in local dev
    return bool(
        os.environ.get("RENDER")
        or os.environ.get("DOCKER")
        or os.environ.get("KUBERNETES_SERVICE_HOST")
    )


def setup_logging() -> logging.Logger:
    """Configure structured logging with JSON output."""
    root = logging.getLogger("sentinelai")
    root.setLevel(logging.INFO)

    if root.handlers:
        root.handlers.clear()

    # Console handler (stdout)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)

    if _use_json_logging():
        console.setFormatter(JSONFormatter())
    else:
        console.setFormatter(HumanFormatter())

    root.addHandler(console)

    # File handler (warnings+) for persistent log
    try:
        file_handler = logging.FileHandler("sentinelai.log", encoding="utf-8")
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(JSONFormatter() if _use_json_logging() else HumanFormatter())
        root.addHandler(file_handler)
    except OSError:
        pass  # Read-only filesystem

    # ── Sentry integration (optional) ───────────────────────────────
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_logging = LoggingIntegration(
                level=logging.WARNING,
                event_level=logging.ERROR,
            )
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[sentry_logging],
                traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                environment=os.environ.get("SENTINEL_ENV", "development"),
                release=f"sentinelai@{os.environ.get('SENTINEL_VERSION', '1.0.0')}",
            )
            root.info("Sentry error tracking initialized")
        except ImportError:
            root.warning("sentry-sdk not installed; Sentry integration disabled")
        except Exception as e:
            root.warning(f"Sentry init failed: {e}")

    return root


logger = setup_logging()
