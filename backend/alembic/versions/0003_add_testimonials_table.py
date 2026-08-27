"""Add testimonials table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "testimonials",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(100), nullable=False),
        sa.Column("author_role", sa.String(100), nullable=False),
        sa.Column("author_company", sa.String(100), nullable=False),
        sa.Column("avatar_letter", sa.String(1), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_testimonials_active_order", "testimonials", ["is_active", "display_order"])


def downgrade() -> None:
    op.drop_index("ix_testimonials_active_order", table_name="testimonials")
    op.drop_table("testimonials")
