"""System metrics collector for SentinelAI observability.

Collects CPU, memory, disk usage, database latency, Redis status,
uptime, and environment information. Used by the health endpoints
and the System Health dashboard.

Thread-safe and non-blocking: all expensive checks have timeouts.
"""

from __future__ import annotations

import os
import platform
import threading
import time

from sqlalchemy.pool import QueuePool

try:
    import resource
except ImportError:
    resource = None  # Windows doesn't have resource module
from typing import Any

# ── Uptime tracking ─────────────────────────────────────────────────
_START_TIME: float = time.time()


def get_uptime() -> float:
    """Seconds since the process started."""
    return time.time() - _START_TIME


def get_uptime_human() -> str:
    """Human-readable uptime string."""
    secs = int(get_uptime())
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    minutes, _ = divmod(secs, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


# ── CPU ─────────────────────────────────────────────────────────────


def get_cpu_info() -> dict[str, Any]:
    """CPU usage percentage and core count."""
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.05)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        return {
            "usage_percent": cpu_percent,
            "cores": cpu_count,
            "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
        }
    except ImportError:
        # Fallback without psutil
        try:
            load_avg = os.getloadavg()
            cores = os.cpu_count() or 1
            return {
                "usage_percent": round((load_avg[0] / cores) * 100, 1),
                "cores": cores,
                "frequency_mhz": None,
            }
        except (AttributeError, OSError):
            return {"usage_percent": None, "cores": os.cpu_count() or 1, "frequency_mhz": None}


# ── Memory ──────────────────────────────────────────────────────────


def get_memory_info() -> dict[str, Any]:
    """Memory usage: process RSS and system total."""
    try:
        import psutil

        proc = psutil.Process()
        mem = proc.memory_info()
        sys_mem = psutil.virtual_memory()
        return {
            "process_rss_mb": round(mem.rss / (1024 * 1024), 1),
            "process_vms_mb": round(mem.vms / (1024 * 1024), 1),
            "system_total_mb": round(sys_mem.total / (1024 * 1024), 0),
            "system_used_percent": sys_mem.percent,
            "system_available_mb": round(sys_mem.available / (1024 * 1024), 0),
        }
    except ImportError:
        # Fallback: use resource module
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "process_rss_mb": (
                round(usage.ru_maxrss / 1024, 1)
                if platform.system() != "Windows"
                else round(usage.ru_maxrss / 1024, 1)
            ),
            "process_vms_mb": None,
            "system_total_mb": None,
            "system_used_percent": None,
            "system_available_mb": None,
        }


# ── Disk ────────────────────────────────────────────────────────────


def get_disk_info() -> dict[str, Any]:
    """Disk usage for the data directory."""
    try:
        import psutil

        usage = psutil.disk_usage("/")
        return {
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "usage_percent": round(usage.percent, 1),
        }
    except ImportError:
        return {"total_gb": None, "used_gb": None, "free_gb": None, "usage_percent": None}


# ── Database Latency ───────────────────────────────────────────────


def get_db_latency() -> dict[str, Any]:
    """Measure database query latency with a SELECT 1 probe."""
    try:
        from sqlalchemy import text

        from app.database.database import engine

        start = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start) * 1000, 2)

        # Get pool status if available
        pool = engine.pool
        pool_info = {}
        if isinstance(pool, QueuePool):
            pool_info = {
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checkedin": pool.checkedin(),
            }

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "engine": str(engine.url.drivername),
            **pool_info,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "latency_ms": None}


# ── Redis Status ────────────────────────────────────────────────────


def get_redis_status() -> dict[str, Any]:
    """Check Redis connectivity and latency."""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return {"status": "not_configured", "url": ""}

    try:
        import redis

        start = time.time()
        client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2)
        client.ping()
        latency_ms = round((time.time() - start) * 1000, 2)

        info = client.info("memory")
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
        }
    except ImportError:
        return {"status": "not_installed", "error": "redis package not installed"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ── AI Engine Status ────────────────────────────────────────────────


def get_ai_status() -> dict[str, Any]:
    """Check if the AI engine (Ollama) is reachable."""
    from app.config import get_settings

    settings = get_settings()

    try:
        import urllib.error
        import urllib.request
        from urllib.parse import urlsplit

        # Probe the Ollama origin. OLLAMA_URL points at a path (/api/generate),
        # so string surgery on it previously produced http://host:port/api/. A
        # short timeout keeps a down or slow Ollama from stalling the probe.
        parsed = urlsplit(settings.OLLAMA_URL)
        health_url = f"{parsed.scheme}://{parsed.netloc}/"

        start = time.time()
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=0.5):
            latency_ms = round((time.time() - start) * 1000, 2)
            return {
                "status": "healthy",
                "model": settings.OLLAMA_MODEL,
                "latency_ms": latency_ms,
                "fallback": "rule-based",
            }
    except Exception:
        return {
            "status": "unavailable",
            "model": settings.OLLAMA_MODEL,
            "fallback": "rule-based (Ollama not running)",
        }


# ── Environment ─────────────────────────────────────────────────────


def get_environment_info() -> dict[str, Any]:
    """Collect runtime environment metadata."""
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "pid": os.getpid(),
        "sentinel_version": os.environ.get("SENTINEL_VERSION", "1.0.0"),
        "environment": os.environ.get("SENTINEL_ENV", "development"),
        "database_url": _safe_db_url(),
        "redis_configured": bool(os.environ.get("REDIS_URL")),
        "sentry_configured": bool(os.environ.get("SENTRY_DSN")),
        "ollama_model": os.environ.get("OLLAMA_MODEL", "mistral"),
        "uptime_seconds": round(get_uptime(), 0),
        "uptime_human": get_uptime_human(),
    }


def _safe_db_url() -> str:
    """Return a sanitized database URL (no password)."""
    from app.config import get_settings

    url = get_settings().DATABASE_URL
    # Redact credentials
    if "@" in url:
        prefix = url.split("@", 1)[0]
        suffix = url.split("@", 1)[1]
        if "://" in prefix:
            scheme, userinfo = prefix.split("://", 1)
            if ":" in userinfo:
                username = userinfo.split(":")[0]
                return f"{scheme}://{username}:***@{suffix}"
    return url.split("?")[0]  # Strip query params


# ── Worker / Queue Status ───────────────────────────────────────────


def get_worker_status() -> dict[str, Any]:
    """Check background worker and task queue status."""
    from app.tasks import get_task_stats

    stats = get_task_stats()
    return {
        "status": "healthy",
        "active_tasks": stats.get("active", 0),
        "queued_tasks": stats.get("queued", 0),
        "completed_tasks": stats.get("completed", 0),
        "failed_tasks": stats.get("failed", 0),
    }


# ── Full Health Check ───────────────────────────────────────────────


_health_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_health_cache_lock = threading.Lock()
_health_refreshing = False
_HEALTH_CACHE_TTL = 10  # seconds — health endpoint called frequently


def collect_all_health() -> dict[str, Any]:
    """Return the most recent health snapshot, refreshing it out of band.

    The probes touch the database, Redis and Ollama, and any of them can block
    for seconds when a dependency is down, so they must not run on a request
    thread: a stale snapshot is served immediately while one background thread
    recomputes it. ``warm_health_cache`` fills the cache at startup so the very
    first probe is already fast.
    """
    global _health_refreshing

    with _health_cache_lock:
        snapshot = _health_cache["data"]
        stale = snapshot is None or (time.time() - _health_cache["ts"]) >= _HEALTH_CACHE_TTL
        start_background = stale and snapshot is not None and not _health_refreshing
        if start_background:
            _health_refreshing = True

    if snapshot is None:
        return _refresh_health()

    if start_background:
        threading.Thread(target=_refresh_health, name="health-refresh", daemon=True).start()

    return snapshot


def warm_health_cache() -> dict[str, Any]:
    """Compute the health snapshot once so the first request is served from cache."""
    return _refresh_health()


def _refresh_health() -> dict[str, Any]:
    """Recompute the snapshot and store it, releasing the refresh guard."""
    global _health_refreshing
    try:
        result = _compute_health()
        with _health_cache_lock:
            _health_cache["data"] = result
            _health_cache["ts"] = time.time()
        return result
    finally:
        with _health_cache_lock:
            _health_refreshing = False


def _compute_health() -> dict[str, Any]:
    """Run every health check in parallel and assemble the response."""
    # Run independent checks in parallel (they are all I/O-bound)
    from concurrent.futures import ThreadPoolExecutor, as_completed

    _checks = {
        "database": get_db_latency,
        "redis": get_redis_status,
        "ai_engine": get_ai_status,
        "workers": get_worker_status,
        "cpu": get_cpu_info,
        "memory": get_memory_info,
        "disk": get_disk_info,
        "environment": get_environment_info,
    }

    results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fn): name for name, fn in _checks.items()}
        for future in as_completed(futures, timeout=5):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = {"status": "error"}

    db = results.get("database", {"status": "unknown"})
    redis_st = results.get("redis", {"status": "unknown"})
    ai = results.get("ai_engine", {"status": "unknown"})
    worker = results.get("workers", {"status": "unknown"})
    cpu = results.get("cpu", {})
    memory = results.get("memory", {})
    disk = results.get("disk", {})
    env = results.get("environment", {})

    # Determine overall status — only the database check matters.
    # Redis/not_configured, ai_engine/unavailable, workers do NOT lower the status.
    db_status = db.get("status", "unknown")
    if db_status == "healthy":
        overall = "healthy"
    elif db_status == "degraded":
        overall = "degraded"
    else:
        overall = "unhealthy"
    checks = {
        "database": db_status,
        "redis": redis_st.get("status", "unknown"),
        "ai_engine": ai.get("status", "unknown"),
        "workers": worker.get("status", "unknown"),
    }

    result = {
        "status": overall,
        "version": env.get("sentinel_version", "1.0.0"),
        "timestamp": time.time(),
        "uptime_seconds": round(get_uptime(), 0),
        "uptime_human": get_uptime_human(),
        "checks": checks,
        "details": {
            "database": db,
            "redis": redis_st,
            "ai_engine": ai,
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "workers": worker,
            "environment": env,
        },
    }

    return result
