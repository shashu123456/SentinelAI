import logging
import os
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Determine if we're using SQLite (which doesn't support connection pooling)
is_sqlite = "sqlite" in settings.DATABASE_URL

# ── Engine & Connection Pool ──────────────────────────────────────────
# Production-grade pool: 20 base + 10 overflow = 30 max connections.
# For SQLite: WAL mode + busy timeout for concurrent reads.
if is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=False,
    )

    # Enable WAL mode for better concurrent read performance
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB page cache
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

else:
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Performance Monitoring ────────────────────────────────────────────
_query_log: list[dict] = []
_query_log_max = 500


def get_query_stats() -> dict:
    """Return aggregate query performance statistics."""
    if not _query_log:
        return {"total": 0, "avg_ms": 0, "slow_count": 0, "p95_ms": 0}
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


if is_sqlite:

    @event.listens_for(engine, "before_cursor_execute")
    def _before_exec(conn, cursor, stmt, parameters, context, executemany):
        conn.info.setdefault("query_start", []).append(time.monotonic())

    @event.listens_for(engine, "after_cursor_execute")
    def _after_exec(conn, cursor, stmt, parameters, context, executemany):
        starts = conn.info.get("query_start", [])
        if starts:
            start = starts.pop()
            duration = (time.monotonic() - start) * 1000
            if duration > 50:  # Log queries > 50ms
                logger.debug(f"Slow query ({duration:.1f}ms): {stmt[:200]}")
            with _lock:
                _query_log.append({"duration_ms": duration, "stmt": stmt[:100]})
                if len(_query_log) > _query_log_max:
                    _query_log[:] = _query_log[-_query_log_max:]


import threading

_lock = threading.Lock()


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaction(db: Session):
    """Run a block in a single atomic transaction.

    Commits on success, rolls back on any exception, and never leaves the
    session in a partial state.
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def _alembic_config():
    """Build an Alembic Config bound to the application DATABASE_URL."""
    from alembic.config import Config

    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cfg = Config(os.path.join(backend_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_root, "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return cfg


def _run_migrations():
    """Apply pending Alembic migrations (idempotent: a no-op when current)."""
    from alembic import command

    command.upgrade(_alembic_config(), "head")


def _baseline_tables_exist() -> bool:
    """True when every application table already exists in the target schema.

    Used to skip slow Alembic stamping during fast test runs that already
    created the schema via `Base.metadata.create_all`.
    """
    inspector = inspect(engine)
    required = {table.name for table in Base.metadata.sorted_tables}
    return required.issubset(set(inspector.get_table_names()))


def init_db():
    """Initialize the schema.

    - Production / normal startup: apply Alembic migrations to `head`.
    - Test environments that already built the schema via create_all: the
      migrations are still applied, but Alembic detects them as current and
      performs no work.
    """
    import app.models.models  # noqa: F401 - populate Base.metadata

    if _baseline_tables_exist():
        _stamp_if_needed()
        return
    _run_migrations()


def _stamp_if_needed():
    """Record the current head revision without re-running DDL.

    Only relevant when the schema was created outside Alembic (e.g. tests that
    call `create_all`). Purely incremental — never downgrades or rewrites.
    """
    try:
        from alembic.util import CommandError

        from alembic import command

        command.stamp(_alembic_config(), "head")
    except CommandError:
        pass
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Alembic stamp skipped: %s", exc)
