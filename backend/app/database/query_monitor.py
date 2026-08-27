"""Query performance monitoring.

Responsibilities:
- Track query execution times
- Detect slow queries (>50ms)
- Provide aggregate statistics (p95, avg, max)
"""

import logging
import threading
import time
from collections import deque

from sqlalchemy import event

logger = logging.getLogger(__name__)

_query_log: deque = deque(maxlen=500)
_lock = threading.Lock()


def get_query_stats() -> dict:
    """Return aggregate query performance statistics."""
    with _lock:
        if not _query_log:
            return {"total": 0, "avg_ms": 0, "slow_count": 0, "p95_ms": 0, "max_ms": 0}
        times = [q["duration_ms"] for q in _query_log]

    times_sorted = sorted(times)
    p95_idx = int(len(times_sorted) * 0.95)
    return {
        "total": len(times),
        "avg_ms": round(sum(times) / len(times), 2),
        "slow_count": sum(1 for t in times if t > 100),
        "p95_ms": round(times_sorted[min(p95_idx, len(times_sorted) - 1)], 2),
        "max_ms": round(max(times), 2),
    }


def install_query_monitoring(engine) -> None:
    """Install SQLAlchemy event listeners for query monitoring.

    Only active for SQLite (PostgreSQL monitoring is done via pg_stat_statements).
    """

    @event.listens_for(engine, "before_cursor_execute")
    def _before_exec(conn, cursor, stmt, parameters, context, executemany):
        conn.info.setdefault("query_start", []).append(time.monotonic())

    @event.listens_for(engine, "after_cursor_execute")
    def _after_exec(conn, cursor, stmt, parameters, context, executemany):
        starts = conn.info.get("query_start", [])
        if starts:
            start = starts.pop()
            duration = (time.monotonic() - start) * 1000
            if duration > 50:
                logger.debug("Slow query (%.1fms): %s", duration, stmt[:200])
            with _lock:
                _query_log.append({"duration_ms": duration, "stmt": stmt[:100]})
