# ADR-002: Database Module Decomposition

## Status

Accepted

## Context

`database.py` mixed 5 concerns: engine creation, session management, query monitoring, migration configuration, and public API. At 189 lines, it violated Single Responsibility and made it difficult to test or modify individual concerns.

## Decision

Decompose into 4 focused modules:

| Module | Lines | Responsibility |
|--------|-------|---------------|
| `engine.py` | 45 | SQLAlchemy engine creation, connection pooling, SQLite WAL mode |
| `query_monitor.py` | 55 | Slow query detection, query statistics, performance metrics |
| `migrations.py` | 60 | Alembic configuration, `upgrade_head()`, `stamp_head()` |
| `database.py` | 65 | Public API: `get_db()`, `init_db()`, session factory |

## Consequences

**Positive:**
- Each module is independently testable
- Query monitoring can be toggled without affecting session management
- Engine configuration is isolated from session semantics
- Migration tooling is self-contained

**Negative:**
- One extra import step for code that previously used `from app.database.database import engine`

**Migration:**
- All existing `from app.database.database import get_db, init_db` continue to work
- Engine access moved to `from app.database.engine import engine`
