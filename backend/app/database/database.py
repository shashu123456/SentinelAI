"""Database session and schema management.

Composes focused modules:
- engine.py: Connection pool and engine creation
- query_monitor.py: Slow query detection and statistics
- migrations.py: Alembic migration management

This module provides the public API for the rest of the application.
"""

import logging
from contextlib import contextmanager

from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.database.engine import engine, is_sqlite
from app.database.migrations import (
    baseline_tables_exist,
    recorded_revision,
    run_migrations,
    stamp_head,
)
from app.database.query_monitor import get_query_stats, install_query_monitoring

logger = logging.getLogger(__name__)

# Install query monitoring for SQLite
if is_sqlite:
    install_query_monitoring(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
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


def init_db():
    """Initialize the schema.

    - Production / normal startup: apply Alembic migrations to `head`.
    - Test environments that already built the schema via create_all: the
      migrations are still applied, but Alembic detects them as current and
      performs no work.
    """
    import app.models.models  # noqa: F401 - populate Base.metadata

    # If Alembic already owns this schema, pending revisions must be APPLIED.
    # Stamping here (the previous behaviour) recorded head without running the
    # DDL, so a newly added migration never reached an existing database — the
    # new kind/source columns were missing while alembic_version claimed head.
    if recorded_revision(engine) is not None:
        run_migrations()
        return

    if baseline_tables_exist(engine, Base.metadata):
        # Schema built by Base.metadata.create_all (tests): no DDL to run, just
        # record where we are.
        stamp_head()
        return
    run_migrations()


# Re-export for backward compatibility
__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "transaction",
    "init_db",
    "get_query_stats",
    "is_sqlite",
]
