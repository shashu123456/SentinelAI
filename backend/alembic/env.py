"""Alembic environment bound to the application's DATABASE_URL.

Runs against whichever engine `app.config.Settings.DATABASE_URL` points at
(SQLite locally, PostgreSQL in CI / production). Schema metadata is loaded
from `app.models.models` so `--autogenerate` stays accurate.
"""

from logging.config import fileConfig

import app.models.models  # noqa: F401 - register tables on Base.metadata
from alembic import context
from app.config import get_settings
from app.database.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    url = _database_url()
    is_sqlite = "sqlite" in url
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(url, connect_args=connect_args)

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite cannot ALTER constraints in place; batch mode recreates tables.
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
