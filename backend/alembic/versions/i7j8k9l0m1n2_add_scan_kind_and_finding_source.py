"""add scan.kind and finding.source

Revision ID: i7j8k9l0m1n2
Revises: h6i7j8k9l0m1
Create Date: 2026-11-15

Every scan and every finding now records which engine produced it:
``spec`` (OpenAPI), ``deps`` (dependency manifests) or ``code`` (SAST).
Existing rows default to ``spec``, which is what they are.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i7j8k9l0m1n2"
down_revision: str | None = "h6i7j8k9l0m1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column("kind", sa.String(length=10), nullable=False, server_default="spec"),
    )
    op.create_index("ix_scans_kind", "scans", ["kind"])

    op.add_column(
        "findings",
        sa.Column("source", sa.String(length=10), nullable=False, server_default="spec"),
    )
    op.create_index("ix_findings_source", "findings", ["source"])


def downgrade() -> None:
    op.drop_index("ix_findings_source", table_name="findings")
    op.drop_column("findings", "source")

    op.drop_index("ix_scans_kind", table_name="scans")
    op.drop_column("scans", "kind")
