"""Migration tests.

Verify the Alembic baseline migration:
- creates the full schema on a fresh database,
- is idempotent (running it twice is a no-op),
- upgrades a pre-existing (legacy) schema without losing data,
- works against PostgreSQL when `TEST_DATABASE_URL` is configured
  (marked `postgres`; skipped otherwise, exercised in CI).
"""

import os

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.database.migrations import _alembic_config

EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "password_reset_tokens",
    "scans",
    "findings",
    "ai_analysis",
    "audit_logs",
    "reports",
    "alembic_version",
}

NEW_FINDING_COLUMNS = {
    "technical_impact",
    "business_impact",
    "request_example",
    "response_example",
    "fix_recommendation",
    "references",
    "cvss_score",
    "cvss_vector",
}

SCAN_COLUMNS = {"source_spec", "deleted_at"}

AUDIT_COLUMNS = {
    "user_id",
    "action",
    "entity_type",
    "entity_id",
    "detail",
    "ip_address",
    "created_at",
}

REPORT_COLUMNS = {"scan_id", "format", "content", "created_at"}


def _upgrade_on(url: str) -> None:
    cfg = _alembic_config()
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _new_engine(url: str):
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    return create_engine(url, connect_args=connect_args)


def _sqlite_url(tmp_path, name: str) -> str:
    return f"sqlite:///{tmp_path / name}"


def _assert_full_schema(url: str) -> None:
    engine = _new_engine(url)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    assert EXPECTED_TABLES.issubset(tables), tables

    finding_cols = {c["name"] for c in insp.get_columns("findings")}
    assert NEW_FINDING_COLUMNS.issubset(finding_cols), finding_cols

    scan_cols = {c["name"] for c in insp.get_columns("scans")}
    assert SCAN_COLUMNS.issubset(scan_cols), scan_cols

    audit_cols = {c["name"] for c in insp.get_columns("audit_logs")}
    assert AUDIT_COLUMNS.issubset(audit_cols), audit_cols

    report_cols = {c["name"] for c in insp.get_columns("reports")}
    assert REPORT_COLUMNS.issubset(report_cols), report_cols

    scan_indexes = {i["name"] for i in insp.get_indexes("scans")}
    assert "ix_scans_user_created" in scan_indexes
    assert "ix_scans_status" in scan_indexes

    finding_indexes = {i["name"] for i in insp.get_indexes("findings")}
    assert "ix_findings_scan_severity" in finding_indexes

    severity_checks = {c.get("name") for c in insp.get_check_constraints("findings")}
    assert "ck_findings_severity" in severity_checks, severity_checks
    engine.dispose()


def test_baseline_migration_creates_full_schema(tmp_path):
    url = _sqlite_url(tmp_path, "fresh.db")
    _upgrade_on(url)
    _assert_full_schema(url)


def test_migration_is_idempotent(tmp_path):
    url = _sqlite_url(tmp_path, "twice.db")
    _upgrade_on(url)
    _upgrade_on(url)
    _assert_full_schema(url)


def test_migration_upgrades_legacy_schema(tmp_path):
    """A database without audit_logs/reports and without the enriched columns
    should be upgraded in place by the baseline migration."""
    url = _sqlite_url(tmp_path, "legacy.db")

    # Build the legacy schema from scratch using raw SQL instead of
    # create_all + DROP, because SQLite's FK constraints prevent
    # DROP COLUMN on tables with FK references.
    legacy_engine = _new_engine(url)
    with legacy_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE refresh_tokens (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token_hash VARCHAR(64) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                revoked_at DATETIME,
                replaced_by VARCHAR(64),
                ip_address VARCHAR(64)
            )
        """))
        conn.execute(text("""
            CREATE TABLE password_reset_tokens (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token_hash VARCHAR(64) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                used_at DATETIME
            )
        """))
        conn.execute(text("""
            CREATE TABLE scans (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                api_name VARCHAR(200) NOT NULL,
                api_title VARCHAR(200),
                api_version VARCHAR(20),
                total_endpoints INTEGER DEFAULT 0,
                total_vulnerabilities INTEGER DEFAULT 0,
                risk_score INTEGER DEFAULT 0,
                risk_level VARCHAR(20) DEFAULT 'Unknown',
                status VARCHAR(20) DEFAULT 'pending',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """))
        conn.execute(text("CREATE INDEX ix_scans_id ON scans(id)"))
        conn.execute(text("""
            CREATE TABLE findings (
                id INTEGER PRIMARY KEY,
                scan_id INTEGER NOT NULL REFERENCES scans(id),
                vulnerability_name VARCHAR(200) NOT NULL,
                owasp_category VARCHAR(50) NOT NULL,
                cwe_id VARCHAR(20),
                severity VARCHAR(20) NOT NULL,
                confidence INTEGER DEFAULT 85,
                description TEXT NOT NULL,
                evidence TEXT,
                impact TEXT NOT NULL,
                remediation TEXT NOT NULL,
                CONSTRAINT ck_findings_severity CHECK (severity IN ('Critical', 'High', 'Medium', 'Low', 'Info'))
            )
        """))
        conn.execute(text("CREATE INDEX ix_findings_id ON findings(id)"))
        conn.execute(text("""
            CREATE TABLE ai_analysis (
                id INTEGER PRIMARY KEY,
                scan_id INTEGER NOT NULL UNIQUE REFERENCES scans(id),
                executive_summary TEXT,
                technical_explanation TEXT,
                business_impact TEXT,
                attack_scenario TEXT,
                recommended_mitigation TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
    legacy_engine.dispose()

    # Migrate the legacy DB forward.
    _upgrade_on(url)
    _assert_full_schema(url)


def test_legacy_data_is_preserved(tmp_path):
    """Existing rows survive the upgrade (columns only ever added)."""
    url = _sqlite_url(tmp_path, "legacy_data.db")
    _upgrade_on(url)

    engine = _new_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (username, email, hashed_password, role, is_active, failed_login_attempts) "
                "VALUES ('legacy_user', 'legacy@example.com', 'x', 'user', 1, 0)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO scans (user_id, api_name, status, total_endpoints, total_vulnerabilities, risk_score) "
                "VALUES (1, 'Legacy API', 'completed', 3, 2, 55)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO findings (scan_id, vulnerability_name, owasp_category, severity, description, impact, remediation) "
                "VALUES (1, 'Old finding', 'API1', 'High', 'd', 'i', 'r')"
            )
        )
    engine.dispose()

    # Re-run migrations (simulates an upgraded deployment booting again).
    _upgrade_on(url)

    engine = _new_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM users")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM scans")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM findings")).scalar() == 1
        scan = conn.execute(text("SELECT source_spec, deleted_at FROM scans")).first()
        assert scan is not None
    engine.dispose()


@pytest.mark.postgres
def test_baseline_migration_on_postgres():
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.startswith("postgres"):
        pytest.skip("TEST_DATABASE_URL is not set to a PostgreSQL database")

    _upgrade_on(url)
    try:
        _assert_full_schema(url)
    finally:
        engine = _new_engine(url)
        engine.dispose()
