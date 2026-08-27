"""Prometheus-compatible metrics endpoint.

Exposes application metrics in Prometheus text format for monitoring,
alerting, and dashboard integration with Grafana, Datadog, etc.

Metrics categories:
- HTTP: request count, latency, status distribution
- Auth: login attempts, failures, token refreshes
- Scanner: scan count, duration, findings per scan
- AI: copilot requests, latency, fallback rate
- System: CPU, memory, DB latency, uptime, task queue
"""

from fastapi import APIRouter, Depends, Request
from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.utils.ratelimit import limiter
from app.utils.system_metrics import (
    get_cpu_info,
    get_db_latency,
    get_memory_info,
    get_uptime,
)

router = APIRouter(tags=["Observability"])

# ═══════════════════════════════════════════════════════════════════════
# HTTP Metrics
# ═══════════════════════════════════════════════════════════════════════

REQUEST_COUNT = Counter(
    "sentinelai_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "sentinelai_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

REQUESTS_IN_PROGRESS = Gauge(
    "sentinelai_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"],
)

# ═══════════════════════════════════════════════════════════════════════
# Auth Metrics
# ═══════════════════════════════════════════════════════════════════════

AUTH_LOGIN_TOTAL = Counter(
    "sentinelai_auth_login_total",
    "Total login attempts",
    ["status"],  # success, failure, locked
)

AUTH_REGISTER_TOTAL = Counter(
    "sentinelai_auth_register_total",
    "Total user registrations",
)

AUTH_TOKEN_REFRESH_TOTAL = Counter(
    "sentinelai_auth_token_refresh_total",
    "Total token refresh attempts",
    ["status"],  # success, failure
)

AUTH_LOGOUT_TOTAL = Counter(
    "sentinelai_auth_logout_total",
    "Total logout events",
)

# ═══════════════════════════════════════════════════════════════════════
# Scanner Metrics
# ═══════════════════════════════════════════════════════════════════════

SCANS_TOTAL = Counter(
    "sentinelai_scans_total",
    "Total scans initiated",
    ["type"],  # api, sast, dep
)

SCANS_ACTIVE = Gauge(
    "sentinelai_scans_active",
    "Number of currently running scans",
)

SCANS_COMPLETED = Counter(
    "sentinelai_scans_completed_total",
    "Total scans completed",
    ["status"],  # completed, failed
)

SCANS_DURATION = Histogram(
    "sentinelai_scan_duration_seconds",
    "Scan execution duration in seconds",
    ["type"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

FINDINGS_TOTAL = Counter(
    "sentinelai_findings_total",
    "Total findings generated",
    ["severity"],
)

# ═══════════════════════════════════════════════════════════════════════
# AI Metrics
# ═══════════════════════════════════════════════════════════════════════

AI_REQUESTS_TOTAL = Counter(
    "sentinelai_ai_requests_total",
    "Total AI copilot requests",
    ["intent"],
)

AI_LATENCY = Histogram(
    "sentinelai_ai_request_duration_seconds",
    "AI copilot request latency",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

AI_FALLBACK_TOTAL = Counter(
    "sentinelai_ai_fallback_total",
    "AI requests falling back to rule-based analysis",
)

# ═══════════════════════════════════════════════════════════════════════
# System / Infrastructure Metrics
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_UPTIME = Gauge(
    "sentinelai_uptime_seconds",
    "Application uptime in seconds",
)

SYSTEM_CPU_USAGE = Gauge(
    "sentinelai_cpu_usage_percent",
    "CPU usage percentage",
)

SYSTEM_MEMORY_RSS = Gauge(
    "sentinelai_memory_rss_bytes",
    "Process resident memory in bytes",
)

SYSTEM_MEMORY_USED_PCT = Gauge(
    "sentinelai_memory_used_percent",
    "System memory usage percentage",
)

DB_LATENCY_SECONDS = Gauge(
    "sentinelai_db_latency_seconds",
    "Database query latency in seconds",
)

# ═══════════════════════════════════════════════════════════════════════
# Legacy gauges (backward compatible)
# ═══════════════════════════════════════════════════════════════════════

TOTAL_SCANS = Gauge("sentinelai_total_scans", "Total scans executed")
TOTAL_USERS = Gauge("sentinelai_total_users", "Total registered users")
ACTIVE_SCANS_GAUGE = Gauge("sentinelai_active_scans", "Number of currently running scans")
FINDINGS_BY_SEVERITY = Gauge(
    "sentinelai_findings_by_severity", "Findings by severity", ["severity"]
)
SCANS_BY_STATUS = Gauge("sentinelai_scans_by_status", "Scans by status", ["status"])


def _update_system_gauges():
    """Update system-level gauge metrics."""
    try:
        SYSTEM_UPTIME.set(get_uptime())
    except Exception:
        pass

    try:
        cpu = get_cpu_info()
        if cpu.get("usage_percent") is not None:
            SYSTEM_CPU_USAGE.set(cpu["usage_percent"])
    except Exception:
        pass

    try:
        mem = get_memory_info()
        if mem.get("process_rss_mb") is not None:
            SYSTEM_MEMORY_RSS.set(mem["process_rss_mb"] * 1024 * 1024)
        if mem.get("system_used_percent") is not None:
            SYSTEM_MEMORY_USED_PCT.set(mem["system_used_percent"])
    except Exception:
        pass

    try:
        db = get_db_latency()
        if db.get("latency_ms") is not None:
            DB_LATENCY_SECONDS.set(db["latency_ms"] / 1000)
    except Exception:
        pass


@router.get("/metrics")
@limiter.exempt
def prometheus_metrics(request: Request, db: Session = Depends(get_db)):
    """Expose Prometheus metrics in text format."""
    _update_system_gauges()

    try:
        from app.models.models import Finding, Scan, User
        from app.tasks import get_task_stats

        TOTAL_SCANS.set(db.query(Scan).count())
        TOTAL_USERS.set(db.query(User).count())

        task_stats = get_task_stats()
        ACTIVE_SCANS_GAUGE.set(task_stats.get("active", 0))
        SCANS_ACTIVE.set(task_stats.get("active", 0))

        for status in ("pending", "running", "completed", "failed"):
            count = db.query(Scan).filter(Scan.status == status).count()
            SCANS_BY_STATUS.labels(status=status).set(count)

        for severity in ("Critical", "High", "Medium", "Low", "Info"):
            count = db.query(Finding).filter(Finding.severity == severity).count()
            FINDINGS_BY_SEVERITY.labels(severity=severity).set(count)
    except Exception:
        pass

    return generate_latest(REGISTRY)


@router.get("/health/detailed")
@limiter.exempt
def detailed_health(db: Session = Depends(get_db)):
    """Detailed health check with database connectivity and system metrics."""
    from app.utils.system_metrics import collect_all_health

    health = collect_all_health()
    return health
