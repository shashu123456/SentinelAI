"""Performance monitoring for SentinelAI.

Provides:
- Request timing and throughput tracking
- Memory usage monitoring
- Slow query detection
- Performance statistics endpoint
- CPU utilization tracking
"""

import gc
import os
import threading
import time
from collections import deque
from dataclasses import dataclass

# ── Request Metrics ───────────────────────────────────────────────────


@dataclass
class RequestMetric:
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: float
    memory_mb: float = 0.0


_request_buffer: deque[RequestMetric] = deque(maxlen=1000)
_request_lock = threading.Lock()


def record_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Record a request metric."""
    mem = _get_memory_mb()
    metric = RequestMetric(
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        timestamp=time.time(),
        memory_mb=mem,
    )
    with _request_lock:
        _request_buffer.append(metric)


# ── Memory Tracking ───────────────────────────────────────────────────


def _get_memory_mb() -> float:
    """Get current process memory usage in MB."""
    try:
        import psutil

        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        # Fallback: estimate from /proc on Linux
        try:
            with open(f"/proc/{os.getpid()}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024
        except (FileNotFoundError, ValueError):
            pass
    return 0.0


def get_memory_stats() -> dict:
    """Get comprehensive memory statistics."""
    mem_mb = _get_memory_mb()
    gc_stats = gc.get_stats()
    return {
        "process_memory_mb": round(mem_mb, 1),
        "gc_gen0": gc_stats[0] if len(gc_stats) > 0 else {},
        "gc_gen1": gc_stats[1] if len(gc_stats) > 1 else {},
        "gc_gen2": gc_stats[2] if len(gc_stats) > 2 else {},
        "gc_thresholds": gc.get_threshold(),
        "gc_count": gc.get_count(),
        "objects_tracked": len(gc.get_objects()),
    }


# ── Performance Statistics ────────────────────────────────────────────


def get_performance_stats() -> dict:
    """Get comprehensive performance statistics."""
    with _request_lock:
        metrics = list(_request_buffer)

    if not metrics:
        return _empty_stats()

    durations = [m.duration_ms for m in metrics]
    durations_sorted = sorted(durations)
    n = len(durations)

    # Request breakdown
    status_counts = {}
    method_counts = {}
    path_counts = {}
    for m in metrics:
        status_counts[str(m.status_code)] = status_counts.get(str(m.status_code), 0) + 1
        method_counts[m.method] = method_counts.get(m.method, 0) + 1
        # Normalize path (strip IDs)
        normalized = _normalize_path(m.path)
        path_counts[normalized] = path_counts.get(normalized, 0) + 1

    # Slow requests (>500ms)
    slow_requests = [
        {"method": m.method, "path": m.path, "duration_ms": m.duration_ms}
        for m in metrics
        if m.duration_ms > 500
    ]

    # Percentiles
    p50 = durations_sorted[int(n * 0.5)] if n > 0 else 0
    p90 = durations_sorted[int(n * 0.9)] if n > 0 else 0
    p95 = durations_sorted[int(n * 0.95)] if n > 0 else 0
    p99 = durations_sorted[int(n * 0.99)] if n > 0 else 0

    # Throughput (requests per second in last 60s)
    now = time.time()
    recent = [m for m in metrics if now - m.timestamp < 60]
    throughput = len(recent) / 60.0 if recent else 0

    return {
        "total_requests": n,
        "avg_duration_ms": round(sum(durations) / n, 2),
        "p50_ms": round(p50, 2),
        "p90_ms": round(p90, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "max_ms": round(max(durations), 2),
        "min_ms": round(min(durations), 2),
        "throughput_rps": round(throughput, 2),
        "status_distribution": status_counts,
        "method_distribution": method_counts,
        "top_paths": dict(sorted(path_counts.items(), key=lambda x: -x[1])[:10]),
        "slow_requests_count": len(slow_requests),
        "slow_requests": slow_requests[:5],
        "memory": get_memory_stats(),
    }


def _normalize_path(path: str) -> str:
    """Normalize API paths for grouping (replace numeric IDs with :id)."""
    import re

    path = re.sub(r"/\d+", "/:id", path)
    path = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/:uuid", path)
    return path


def _empty_stats() -> dict:
    return {
        "total_requests": 0,
        "avg_duration_ms": 0,
        "p50_ms": 0,
        "p90_ms": 0,
        "p95_ms": 0,
        "p99_ms": 0,
        "max_ms": 0,
        "min_ms": 0,
        "throughput_rps": 0,
        "status_distribution": {},
        "method_distribution": {},
        "top_paths": {},
        "slow_requests_count": 0,
        "slow_requests": [],
        "memory": get_memory_stats(),
    }


# ── CPU Tracking ──────────────────────────────────────────────────────

_cpu_sample_lock = threading.Lock()
_cpu_samples: deque[float] = deque(maxlen=100)


def sample_cpu() -> float:
    """Sample CPU usage and return as percentage."""
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.1)
    except ImportError:
        cpu = 0.0

    with _cpu_sample_lock:
        _cpu_samples.append(cpu)
    return cpu


def get_cpu_stats() -> dict:
    """Get CPU utilization statistics."""
    with _cpu_sample_lock:
        samples = list(_cpu_samples)
    if not samples:
        return {"current": 0, "avg": 0, "max": 0}
    return {
        "current": round(samples[-1], 1) if samples else 0,
        "avg": round(sum(samples) / len(samples), 1),
        "max": round(max(samples), 1),
        "samples": len(samples),
    }


# ── Cache Performance ─────────────────────────────────────────────────

_cache_hits = 0
_cache_misses = 0
_cache_lock = threading.Lock()


def record_cache_hit() -> None:
    global _cache_hits
    with _cache_lock:
        _cache_hits += 1


def record_cache_miss() -> None:
    global _cache_misses
    with _cache_lock:
        _cache_misses += 1


def get_cache_stats() -> dict:
    with _cache_lock:
        hits = _cache_hits
        misses = _cache_misses
    total = hits + misses
    return {
        "hits": hits,
        "misses": misses,
        "total": total,
        "hit_rate": round(hits / total * 100, 1) if total > 0 else 0,
    }
