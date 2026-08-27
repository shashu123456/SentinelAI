"""Enterprise multi-tenancy: teams, project members, invitations, API keys, billing

Revision ID: a1b2c3d4e5f6
Revises: 0df17cd389f6
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "0df17cd389f6"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column exists (idempotent for SQLite)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns(table)}
    return column in cols


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    return table in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    # ── Enhanced Organization columns ──
    org_cols = {
        "subscription_tier": sa.String(20),
        "max_members": sa.Integer(),
        "max_projects": sa.Integer(),
        "max_scans_per_month": sa.Integer(),
        "scans_used_this_month": sa.Integer(),
        "default_project_visibility": sa.String(20),
        "enforce_sso": sa.Boolean(),
        "allowed_email_domains": sa.JSON(),
    }
    for col_name, col_type in org_cols.items():
        if not _column_exists("organizations", col_name):
            default_val = {
                "subscription_tier": "free",
                "max_members": 10,
                "max_projects": 5,
                "max_scans_per_month": 50,
                "scans_used_this_month": 0,
                "default_project_visibility": "private",
                "enforce_sso": False,
            }.get(col_name)
            if default_val is not None:
                op.add_column("organizations", sa.Column(col_name, col_type, server_default=str(default_val), nullable=False))
            else:
                op.add_column("organizations", sa.Column(col_name, col_type, nullable=True))

    # ── Enhanced OrganizationMember ──
    if not _column_exists("organization_members", "invited_by"):
        op.add_column("organization_members", sa.Column("invited_by", sa.Integer(), nullable=True))

    # ── Scan organization_id ──
    if not _column_exists("scans", "organization_id"):
        op.add_column("scans", sa.Column("organization_id", sa.Integer(), nullable=True))
        op.create_index("ix_scans_org_id", "scans", ["organization_id"])
        op.create_index("ix_scans_org_status", "scans", ["organization_id", "status"])

    # ── ProjectMember table ──
    if not _table_exists("project_members"):
        op.create_table(
            "project_members",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role", sa.String(30), server_default="developer", nullable=False),
            sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("added_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
            sa.Index("ix_project_member_project_role", "project_id", "role"),
        )

    # ── Team table ──
    if not _table_exists("teams"):
        op.create_table(
            "teams",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("slug", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("organization_id", "slug", name="uq_team_slug"),
            sa.Index("ix_teams_org_id", "organization_id"),
        )

    # ── TeamMember table ──
    if not _table_exists("team_members"):
        op.create_table(
            "team_members",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role", sa.String(30), server_default="member", nullable=False),
            sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("added_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("team_id", "user_id", name="uq_team_member"),
            sa.Index("ix_team_member_team_role", "team_id", "role"),
        )

    # ── Invitation table ──
    if not _table_exists("invitations"):
        op.create_table(
            "invitations",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("email", sa.String(100), nullable=False),
            sa.Column("role", sa.String(30), server_default="developer", nullable=False),
            sa.Column("token", sa.String(128), nullable=False, unique=True),
            sa.Column("invited_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(20), server_default="pending", nullable=False),
            sa.Column("accepted_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Index("ix_invitations_org_id", "organization_id"),
            sa.Index("ix_invitations_email", "email"),
            sa.Index("ix_invitations_token", "token"),
        )

    # ── ApiKey table ──
    if not _table_exists("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("key_prefix", sa.String(12), nullable=False, unique=True),
            sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("scopes", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("key_prefix", name="uq_api_key_prefix"),
            sa.Index("ix_api_keys_org_id", "organization_id"),
            sa.Index("ix_api_keys_user_id", "user_id"),
        )


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("invitations")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("project_members")
    if _column_exists("scans", "organization_id"):
        op.drop_index("ix_scans_org_status", "scans")
        op.drop_index("ix_scans_org_id", "scans")
        op.drop_column("scans", "organization_id")
    if _column_exists("organization_members", "invited_by"):
        op.drop_column("organization_members", "invited_by")
    for col in ("subscription_tier", "max_members", "max_projects", "max_scans_per_month",
                "scans_used_this_month", "default_project_visibility", "enforce_sso", "allowed_email_domains"):
        if _column_exists("organizations", col):
            op.drop_column("organizations", col)
