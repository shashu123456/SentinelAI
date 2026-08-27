"""baseline schema

Idempotent baseline migration: creates the full SentinelAI schema. It is
written defensively so it can run on a fresh database (all tables created),
on a database previously built by `Base.metadata.create_all` (tables already
present are left untouched, only missing columns/indexes are added), and on
SQLite or PostgreSQL alike.

Revision ID: 0001
Revises:
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "users",
    "refresh_tokens",
    "password_reset_tokens",
    "scans",
    "findings",
    "ai_analysis",
    "audit_logs",
    "reports",
)


def _bind():
    return op.get_bind()


def _table_exists(name: str) -> bool:
    return _bind().dialect.has_table(_bind(), name)


def _columns(name: str) -> set[str]:
    from sqlalchemy import inspect

    inspector = inspect(_bind())
    return {col["name"] for col in inspector.get_columns(name)}


def _create_table_if_missing(name: str, *args) -> None:
    if _table_exists(name):
        return
    op.create_table(name, *args)


def _ensure_column(table: str, name: str, ddl: str) -> None:
    if _table_exists(table) and name not in _columns(table):
        op.execute(f'ALTER TABLE {table} ADD COLUMN "{name}" {ddl}')


def _ensure_index(table: str, name: str, columns) -> None:
    if not _table_exists(table):
        return
    if name in {ix["name"] for ix in sa.inspect(_bind()).get_indexes(table)}:
        return
    op.create_index(name, table, columns, if_not_exists=True)


def _ensure_unique(table: str, name: str, column: str) -> None:
    if not _table_exists(table):
        return
    if name in {ix["name"] for ix in sa.inspect(_bind()).get_indexes(table)}:
        return
    op.create_index(name, table, [column], unique=True, if_not_exists=True)


def _ensure_unique_constraint(table: str, name: str, columns) -> None:
    """Add a UNIQUE constraint to an existing table (no-op on SQLite, which
    cannot add constraints via ALTER)."""
    if not _table_exists(table):
        return
    if "sqlite" in _bind().dialect.name:
        return
    constraints = {uc["name"] for uc in sa.inspect(_bind()).get_unique_constraints(table)}
    if name in constraints:
        return
    op.create_unique_constraint(name, table, columns)


def upgrade() -> None:
    # ------------------------------------------------------------------ users
    _create_table_if_missing(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    _ensure_index("users", "ix_users_username", ["username"])
    _ensure_index("users", "ix_users_email", ["email"])

    # ---------------------------------------------------------- refresh_tokens
    _create_table_if_missing(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_by", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    _ensure_index("refresh_tokens", "ix_refresh_tokens_token_hash", ["token_hash"])
    _ensure_index("refresh_tokens", "ix_refresh_tokens_user_id", ["user_id"])

    # ---------------------------------------------------- password_reset_tokens
    _create_table_if_missing(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    _ensure_index("password_reset_tokens", "ix_password_reset_tokens_token_hash", ["token_hash"])
    _ensure_index("password_reset_tokens", "ix_password_reset_tokens_user_id", ["user_id"])

    # ------------------------------------------------------------------- scans
    _create_table_if_missing(
        "scans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("api_name", sa.String(length=200), nullable=False),
        sa.Column("api_title", sa.String(length=200), nullable=True),
        sa.Column("api_version", sa.String(length=20), nullable=True),
        sa.Column("total_endpoints", sa.Integer(), server_default="0"),
        sa.Column("total_vulnerabilities", sa.Integer(), server_default="0"),
        sa.Column("risk_score", sa.Integer(), server_default="0"),
        sa.Column("risk_level", sa.String(length=20), server_default="Unknown"),
        sa.Column("status", sa.String(length=20), server_default="pending"),
        sa.Column("source_spec", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.CheckConstraint(
            "total_vulnerabilities >= 0",
            name="ck_scans_total_vulnerabilities_nonneg",
        ),
    )
    _ensure_index("scans", "ix_scans_user_created", ["user_id", "created_at"])
    _ensure_index("scans", "ix_scans_status", ["status"])

    # ---------------------------------------------------------------- findings
    _create_table_if_missing(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("vulnerability_name", sa.String(length=200), nullable=False),
        sa.Column("owasp_category", sa.String(length=50), nullable=False),
        sa.Column("cwe_id", sa.String(length=20), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Integer(), server_default="85"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("affected_endpoint", sa.String(length=500), nullable=True),
        sa.Column("affected_method", sa.String(length=10), nullable=True),
        sa.Column("detection_reason", sa.Text(), nullable=True),
        sa.Column("false_positive_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"]),
        sa.CheckConstraint(
            "severity IN ('Critical', 'High', 'Medium', 'Low', 'Info')",
            name="ck_findings_severity",
        ),
    )
    _ensure_index("findings", "ix_findings_scan_severity", ["scan_id", "severity"])

    # Enriched finding columns (added to both fresh and pre-existing tables)
    _ensure_column("findings", "technical_impact", "TEXT")
    _ensure_column("findings", "business_impact", "TEXT")
    _ensure_column("findings", "request_example", "TEXT")
    _ensure_column("findings", "response_example", "TEXT")
    _ensure_column("findings", "fix_recommendation", "TEXT")
    _ensure_column("findings", "references", "JSON")
    _ensure_column("findings", "cvss_score", "FLOAT")
    _ensure_column("findings", "cvss_vector", "VARCHAR(64)")

    # ------------------------------------------------------------- ai_analysis
    _create_table_if_missing(
        "ai_analysis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("technical_explanation", sa.Text(), nullable=True),
        sa.Column("business_impact", sa.Text(), nullable=True),
        sa.Column("attack_scenario", sa.Text(), nullable=True),
        sa.Column("recommended_mitigation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"]),
    )
    _ensure_unique("ai_analysis", "ix_ai_analysis_scan_id", "scan_id")

    # -------------------------------------------------------------- audit_logs
    _create_table_if_missing(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    _ensure_index("audit_logs", "ix_audit_logs_created_at", ["created_at"])
    _ensure_index("audit_logs", "ix_audit_logs_user_created", ["user_id", "created_at"])
    _ensure_index("audit_logs", "ix_audit_logs_entity", ["entity_type", "entity_id"])

    # ---------------------------------------------------------------- reports
    _create_table_if_missing(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"]),
    )
    _ensure_index("reports", "ix_reports_created_at", ["created_at"])
    _ensure_unique_constraint("reports", "uq_reports_scan_format", ["scan_id", "format"])

    # Scans/findings migration columns for pre-existing databases
    _ensure_column("scans", "source_spec", "JSON")
    _ensure_column("scans", "deleted_at", "DATETIME")


def downgrade() -> None:
    # Baseline migration — downgrade drops the newer tables and columns that
    # did not exist before this revision.
    for table in ("reports", "audit_logs"):
        if _table_exists(table):
            op.drop_table(table)

    for table, column in (
        ("findings", "cvss_vector"),
        ("findings", "cvss_score"),
        ("findings", "references"),
        ("findings", "fix_recommendation"),
        ("findings", "response_example"),
        ("findings", "request_example"),
        ("findings", "business_impact"),
        ("findings", "technical_impact"),
        ("scans", "deleted_at"),
        ("scans", "source_spec"),
    ):
        if _table_exists(table) and column in _columns(table):
            op.drop_column(table, column)
