"""add saas platform tables

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6g7
Create Date: 2026-08-27
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plans
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("monthly_price_cents", sa.Integer(), server_default="0", nullable=False),
        sa.Column("annual_price_cents", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD", nullable=False),
        sa.Column("max_members", sa.Integer(), server_default="5", nullable=False),
        sa.Column("max_projects", sa.Integer(), server_default="3", nullable=False),
        sa.Column("max_scans_per_month", sa.Integer(), server_default="25", nullable=False),
        sa.Column("max_api_keys", sa.Integer(), server_default="2", nullable=False),
        sa.Column("max_scheduled_scans", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_webhooks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_storage_mb", sa.Integer(), server_default="100", nullable=False),
        sa.Column("max_ai_requests_per_day", sa.Integer(), server_default="10", nullable=False),
        sa.Column("max_team_members", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retention_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("features", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("max_export_formats", sa.JSON(), nullable=True),
        sa.Column("max_scan_history_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("is_public", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("badge", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_plans_is_active", "plans", ["is_active"])
    op.create_index("ix_plans_display_order", "plans", ["display_order"])

    # Subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("billing_cycle", sa.String(10), server_default="monthly", nullable=False),
        sa.Column("is_trial", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("trial_starts_at", sa.DateTime(), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True),
        sa.Column("current_period_start", sa.DateTime(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("pause_starts_at", sa.DateTime(), nullable=True),
        sa.Column("external_subscription_id", sa.String(200), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_subscriptions_org_id", "subscriptions", ["organization_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index("ix_subscriptions_trial_end", "subscriptions", ["trial_ends_at"])

    # Licenses
    op.create_table(
        "licenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("license_key", sa.String(200), unique=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("license_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("current_uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("features", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("max_seats", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_licenses_org_id", "licenses", ["organization_id"])
    op.create_index("ix_licenses_status", "licenses", ["status"])

    # Feature Flags
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("plan_overrides", sa.JSON(), nullable=True),
        sa.Column("category", sa.String(50), server_default="general", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Feature Flag Overrides
    op.create_table(
        "feature_flag_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("flag_id", sa.Integer(), sa.ForeignKey("feature_flags.id"), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("organization_id", "flag_id", name="uq_org_flag_override"),
    )

    # Usage Records
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_usage_records_org_period", "usage_records", ["organization_id", "period_start"])
    op.create_index("ix_usage_records_metric", "usage_records", ["metric"])
    op.create_index("ix_usage_records_created_at", "usage_records", ["created_at"])

    # Onboarding Progress
    op.create_table(
        "onboarding_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("completed_steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("current_step", sa.String(50), server_default="welcome", nullable=False),
        sa.Column("is_complete", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("use_case", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", name="uq_onboarding_user"),
    )

    # Email Templates
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=False),
        sa.Column("body_html_template", sa.Text(), nullable=False),
        sa.Column("body_text_template", sa.Text(), nullable=True),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_email_templates_category", "email_templates", ["category"])

    # Notification Preferences
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("webhook_enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("slack_enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("frequency", sa.String(20), server_default="immediate", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "notification_type", name="uq_notif_pref_user_type"),
    )

    # Custom Branding
    op.create_table(
        "custom_branding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("org_display_name", sa.String(200), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("favicon_url", sa.String(500), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=True),
        sa.Column("secondary_color", sa.String(7), nullable=True),
        sa.Column("accent_color", sa.String(7), nullable=True),
        sa.Column("background_color", sa.String(7), nullable=True),
        sa.Column("text_color", sa.String(7), nullable=True),
        sa.Column("custom_domain", sa.String(255), nullable=True),
        sa.Column("domain_verified", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("domain_verification_token", sa.String(200), nullable=True),
        sa.Column("footer_text", sa.String(500), nullable=True),
        sa.Column("footer_links", sa.JSON(), nullable=True),
        sa.Column("email_from_name", sa.String(200), nullable=True),
        sa.Column("email_from_address", sa.String(200), nullable=True),
        sa.Column("email_reply_to", sa.String(200), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("organization_id", name="uq_branding_org"),
    )

    # Feedback
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(20), server_default="neutral", nullable=False),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column("browser_info", sa.String(200), nullable=True),
        sa.Column("severity", sa.String(20), server_default="low", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_feedback_org_id", "feedback", ["organization_id"])
    op.create_index("ix_feedback_category", "feedback", ["category"])
    op.create_index("ix_feedback_sentiment", "feedback", ["sentiment"])

    # Analytics Events
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_name", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_analytics_events_org_id", "analytics_events", ["organization_id"])
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"])
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])
    op.create_index("ix_analytics_events_name_time", "analytics_events", ["event_name", "created_at"])


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_table("feedback")
    op.drop_table("custom_branding")
    op.drop_table("notification_preferences")
    op.drop_table("email_templates")
    op.drop_table("onboarding_progress")
    op.drop_table("usage_records")
    op.drop_table("feature_flag_overrides")
    op.drop_table("feature_flags")
    op.drop_table("licenses")
    op.drop_table("subscriptions")
    op.drop_table("plans")
