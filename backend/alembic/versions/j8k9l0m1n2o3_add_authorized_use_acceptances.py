"""Add authorized_use_acceptances table (trust gate).

Revision ID: j8k9l0m1n2o3
Revises: i7j8k9l0m1n2
Create Date: 2026-11-16

Records that a user accepted the authorized-use terms before their first scan.
Additive only: safe to apply and to roll back.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "j8k9l0m1n2o3"
down_revision: str | None = "i7j8k9l0m1n2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authorized_use_acceptances",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("version", sa.String(length=20), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", name="uq_authorized_use_user"),
    )
    op.create_index(
        "ix_authorized_use_acceptances_user_id",
        "authorized_use_acceptances",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_authorized_use_acceptances_user_id", table_name="authorized_use_acceptances")
    op.drop_table("authorized_use_acceptances")
