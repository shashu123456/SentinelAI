"""Enterprise features: scheduled scans, templates, policies, webhooks, compliance, exports.

Revision ID: b2c3d4e5f6g7
Create Date: 2025-08-27
"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6g7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Scheduled Scans
    op.create_table(
        "scheduled_scans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("scan_templates.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="weekly"),
        sa.Column("cron_expression", sa.String(100), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("hour", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("scan_type", sa.String(30), nullable=False, server_default="api"),
        sa.Column("scan_config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_scan_id", sa.Integer(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scheduled_scans_org_id", "scheduled_scans", ["organization_id"])
    op.create_index("ix_scheduled_scans_next_run", "scheduled_scans", ["next_run_at"])
    op.create_index("ix_scheduled_scans_active", "scheduled_scans", ["is_active", "next_run_at"])

    # Scan Templates
    op.create_table(
        "scan_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scan_type", sa.String(30), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("compliance_frameworks", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "name", name="uq_scan_template_name_org"),
    )
    op.create_index("ix_scan_templates_org_id", "scan_templates", ["organization_id"])

    # Policies
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("policy_type", sa.String(30), nullable=False, server_default="finding_gate"),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="high"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("enforce_on_scans", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("notify_on_violation", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("evaluation_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("violation_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_evaluated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_policies_org_id", "policies", ["organization_id"])
    op.create_index("ix_policies_is_active", "policies", ["is_active"])

    # Webhooks
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("webhook_type", sa.String(30), nullable=False),
        sa.Column("url", sa.String(2000), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("secret", sa.String(200), nullable=True),
        sa.Column("delivery_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_webhooks_org_id", "webhooks", ["organization_id"])
    op.create_index("ix_webhooks_is_active", "webhooks", ["is_active"])

    # Compliance Frameworks
    op.create_table(
        "compliance_frameworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("controls", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_compliance_frameworks_slug", "compliance_frameworks", ["slug"])

    # Organization Compliance
    op.create_table(
        "org_compliance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("framework_id", sa.Integer(), sa.ForeignKey("compliance_frameworks.id"), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("controls_passed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("controls_failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("controls_na", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("controls_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("control_status", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_assessed_at", sa.DateTime(), nullable=True),
        sa.Column("next_assessment_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "framework_id", name="uq_org_framework"),
    )

    # Export Jobs
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("export_type", sa.String(30), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_export_jobs_org_id", "export_jobs", ["organization_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])

    # Webhook Delivery Log
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("webhook_id", sa.Integer(), sa.ForeignKey("webhooks.id"), nullable=False),
        sa.Column("event", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])
    op.create_index("ix_webhook_deliveries_created_at", "webhook_deliveries", ["created_at"])


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("export_jobs")
    op.drop_table("org_compliance")
    op.drop_table("compliance_frameworks")
    op.drop_table("webhooks")
    op.drop_table("policies")
    op.drop_table("scan_templates")
    op.drop_table("scheduled_scans")
