"""Database migration management.

Responsibilities:
- Alembic configuration
- Migration execution
- Schema stamping for test environments
"""

import logging
import os

from sqlalchemy import inspect

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _alembic_config():
    """Build an Alembic Config bound to the application DATABASE_URL."""
    from alembic.config import Config

    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cfg = Config(os.path.join(backend_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_root, "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return cfg


def run_migrations() -> None:
    """Apply pending Alembic migrations (idempotent: a no-op when current)."""
    from alembic import command

    command.upgrade(_alembic_config(), "head")


def stamp_head() -> None:
    """Record the current head revision without re-running DDL.

    Only relevant when the schema was created outside Alembic (e.g. tests that
    call `create_all`). Purely incremental — never downgrades or rewrites.
    """
    try:
        from alembic import command
        from alembic.util import CommandError

        command.stamp(_alembic_config(), "head")
    except CommandError:
        pass
    except Exception as exc:
        logger.warning("Alembic stamp skipped: %s", exc)


def recorded_revision(engine) -> str | None:
    """Return the revision stored in ``alembic_version``, or None if untracked.

    A non-None value means Alembic owns this schema, so pending revisions must
    be *applied*. Stamping in that case would silently skip new migrations.
    """
    from sqlalchemy import inspect, text

    if "alembic_version" not in inspect(engine).get_table_names():
        return None
    try:
        with engine.connect() as connection:
            row = connection.execute(text("SELECT version_num FROM alembic_version")).first()
    except Exception:  # pragma: no cover - unreadable version table
        return None
    return row[0] if row else None


def baseline_tables_exist(engine, metadata) -> bool:
    """True when every application table already exists in the target schema."""
    inspector = inspect(engine)
    required = {table.name for table in metadata.sorted_tables}
    return required.issubset(set(inspector.get_table_names()))
