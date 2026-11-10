"""add transition_history column to scans table

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-10-24 16:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h6i7j8k9l0m1'
down_revision = 'g5h6i7j8k9l0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('scans', sa.Column('transition_history', sa.JSON(), nullable=True, server_default='[]'))


def downgrade() -> None:
    op.drop_column('scans', 'transition_history')