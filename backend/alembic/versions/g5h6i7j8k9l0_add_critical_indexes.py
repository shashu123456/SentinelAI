"""add critical missing indexes

Revision ID: g5h6i7j8k9l0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g5h6i7j8k9l0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Scans: most-queried table ──────────────────────────────────────
    # Org listing: organization_id + deleted_at
    op.create_index('ix_scans_org_deleted', 'scans', ['organization_id', 'deleted_at'], unique=False)
    # Time-range queries: created_at
    op.create_index('ix_scans_created_at', 'scans', ['created_at'], unique=False)
    # Search by api_name
    op.create_index('ix_scans_api_name', 'scans', ['api_name'], unique=False)

    # ── Findings: OWASP distribution queries ───────────────────────────
    op.create_index('ix_findings_owasp_scan', 'findings', ['owasp_category', 'scan_id'], unique=False)

    # ── Audit Logs: request correlation ────────────────────────────────
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'], unique=False)
    # Module filtering: module + created_at
    op.create_index('ix_audit_logs_module_created', 'audit_logs', ['module', 'created_at'], unique=False)

    # ── Refresh Tokens: security-critical lookups ──────────────────────
    op.create_index('ix_refresh_tokens_user_revoked', 'refresh_tokens', ['user_id', 'revoked_at'], unique=False)

    # ── Usage Records: quota enforcement ───────────────────────────────
    op.create_index('ix_usage_org_metric_period', 'usage_records', ['organization_id', 'metric', 'period_start'], unique=False)

    # ── Scheduled Scans: scheduler lookups ─────────────────────────────
    op.create_index('ix_scheduled_active_next_run', 'scheduled_scans', ['is_active', 'next_run_at'], unique=False)

    # ── Policies: evaluation queries ───────────────────────────────────
    op.create_index('ix_policies_org_active', 'policies', ['organization_id', 'is_active'], unique=False)

    # ── Webhooks: trigger queries ──────────────────────────────────────
    op.create_index('ix_webhooks_org_active', 'webhooks', ['organization_id', 'is_active'], unique=False)

    # ── Subscriptions: lookup queries ──────────────────────────────────
    op.create_index('ix_subscriptions_org_status', 'subscriptions', ['organization_id', 'status'], unique=False)

    # ── Licenses: validation queries ───────────────────────────────────
    op.create_index('ix_licenses_org_status', 'licenses', ['organization_id', 'status'], unique=False)

    # ── Feature Flags: evaluation queries ──────────────────────────────
    op.create_index('ix_feature_flags_enabled_cat', 'feature_flags', ['is_enabled', 'category'], unique=False)

    # ── Plans: listing queries ─────────────────────────────────────────
    op.create_index('ix_plans_active_order', 'plans', ['is_active', 'display_order'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_plans_active_order', table_name='plans')
    op.drop_index('ix_feature_flags_enabled_cat', table_name='feature_flags')
    op.drop_index('ix_licenses_org_status', table_name='licenses')
    op.drop_index('ix_subscriptions_org_status', table_name='subscriptions')
    op.drop_index('ix_webhooks_org_active', table_name='webhooks')
    op.drop_index('ix_policies_org_active', table_name='policies')
    op.drop_index('ix_scheduled_active_next_run', table_name='scheduled_scans')
    op.drop_index('ix_usage_org_metric_period', table_name='usage_records')
    op.drop_index('ix_refresh_tokens_user_revoked', table_name='refresh_tokens')
    op.drop_index('ix_audit_logs_module_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_request_id', table_name='audit_logs')
    op.drop_index('ix_findings_owasp_scan', table_name='findings')
    op.drop_index('ix_scans_api_name', table_name='scans')
    op.drop_index('ix_scans_created_at', table_name='scans')
    op.drop_index('ix_scans_org_deleted', table_name='scans')
