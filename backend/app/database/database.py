import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_columns(engine_obj):
    if "sqlite" not in settings.DATABASE_URL:
        return
    inspector = inspect(engine_obj)
    migrations = {
        "findings": [
            ("cwe_id", "TEXT"),
            ("confidence", "INTEGER DEFAULT 85"),
            ("detection_reason", "TEXT"),
            ("false_positive_note", "TEXT"),
        ],
    }
    with engine_obj.connect() as conn:
        for table, columns in migrations.items():
            existing = {col["name"] for col in inspector.get_columns(table)} if table in inspector.get_table_names() else set()
            for col_name, col_def in columns:
                if col_name not in existing:
                    try:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                        logger.info("Added column %s.%s", table, col_name)
                    except Exception as e:
                        logger.warning("Migration skip %s.%s: %s", table, col_name, e)
        conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_columns(engine)
