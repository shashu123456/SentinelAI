"""enterprise audit logging

Revision ID: 0df17cd389f6
Revises: f9bc77febc0a
Create Date: 2026-08-20 22:31:59.651485

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0df17cd389f6'
down_revision: Union[str, None] = 'f9bc77febc0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def _index_exists(name: str) -> bool:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    return name in {i["name"] for i in inspector.get_indexes("audit_logs")}


def upgrade() -> None:
    nullable_cols = [
        ('username', sa.String(50)),
        ('module', sa.String(50)),
        ('resource', sa.String(200)),
        ('old_value', sa.JSON()),
        ('new_value', sa.JSON()),
        ('user_agent', sa.String(500)),
        ('request_id', sa.String(64)),
    ]
    for name, typ in nullable_cols:
        if not _column_exists('audit_logs', name):
            op.add_column('audit_logs', sa.Column(name, typ, nullable=True))

    for name, typ, default in [('status', sa.String(20), 'success'), ('risk_level', sa.String(20), 'info')]:
        if not _column_exists('audit_logs', name):
            op.add_column('audit_logs', sa.Column(name, typ, server_default=default, nullable=False))

    for name, cols in [
        ('ix_audit_logs_action_created', ['action', 'created_at']),
        ('ix_audit_logs_module', ['module']),
        ('ix_audit_logs_risk_level', ['risk_level']),
        ('ix_audit_logs_status', ['status']),
    ]:
        if not _index_exists(name):
            op.create_index(name, 'audit_logs', cols, unique=False)


def downgrade() -> None:
    for name in ['ix_audit_logs_status', 'ix_audit_logs_risk_level', 'ix_audit_logs_module', 'ix_audit_logs_action_created']:
        op.drop_index(name, table_name='audit_logs')
    for name in ['risk_level', 'status', 'request_id', 'user_agent', 'new_value', 'old_value', 'resource', 'module', 'username']:
        op.drop_column('audit_logs', name)
