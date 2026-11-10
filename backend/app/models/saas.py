"""SaaS platform models for SentinelAI.

Configuration-driven subscription plans, usage tracking, feature flags,
license management, onboarding, branding, feedback, and product analytics.
All plans are data-driven — no hardcoded tiers in application logic.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


# ── Plans ─────────────────────────────────────────────────────────────────
class Plan(Base):
    """Subscription plan definition. Fully configuration-driven.

    Plans define quotas, feature access, and pricing. New plans can be added
    via database migration without code changes.
    """

    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_plans_slug"),
        Index("ix_plans_is_active", "is_active"),
        Index("ix_plans_display_order", "display_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Pricing
    monthly_price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    annual_price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Quotas
    max_members: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_projects: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    max_scans_per_month: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    max_api_keys: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    max_scheduled_scans: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_webhooks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_storage_mb: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_ai_requests_per_day: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_team_members: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Feature flags for this plan (JSON map of feature_key -> enabled)
    features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Example: {"sast_scanning": true, "compliance_center": true, "white_label": false}

    # Limits
    max_export_formats: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["csv", "json"] for free, ["csv", "json", "pdf", "sarif"] for enterprise
    max_scan_history_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Display
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    badge: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "Most Popular", "Best Value", "Enterprise"

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="plan"
    )


# ── Subscriptions ────────────────────────────────────────────────────────
class Subscription(Base):
    """Organization subscription to a plan.

    Tracks billing cycle, trial status, and subscription lifecycle.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_org_id", "organization_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_plan_id", "plan_id"),
        Index("ix_subscriptions_trial_end", "trial_ends_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, trialing, past_due, canceled, paused

    # Billing cycle
    billing_cycle: Mapped[str] = mapped_column(
        String(10), default="monthly", nullable=False
    )  # monthly, annual

    # Trial
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Period tracking
    current_period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pause_starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # External billing reference
    external_subscription_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # Stripe subscription ID

    # Metadata
    subscription_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscriptions")


# ── Licenses ─────────────────────────────────────────────────────────────
class License(Base):
    """License keys for enterprise and self-hosted deployments.

    Supports activation keys, expiration, feature gating, and max-uses.
    """

    __tablename__ = "licenses"
    __table_args__ = (
        UniqueConstraint("license_key", name="uq_license_key"),
        Index("ix_licenses_org_id", "organization_id"),
        Index("ix_licenses_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    license_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=True
    )

    # License type
    license_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # trial, professional, enterprise, open_source

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, expired, revoked, suspended

    # Validity
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Features enabled by this license
    features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    max_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # License metadata
    license_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    # {"customer_name": "...", "customer_email": "...", "issued_by": "..."}

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization")


# ── Feature Flags ────────────────────────────────────────────────────────
class FeatureFlag(Base):
    """Runtime feature flags with plan-based and org-based overrides.

    Feature flags control which capabilities are available. They can be
    toggled per-plan, per-organization, or globally.
    """

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("key", name="uq_feature_flag_key"),
        Index("ix_feature_flags_is_enabled", "is_enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Default state
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Plan-based overrides (JSON: {"free": false, "starter": true, "enterprise": true})
    plan_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Organization-level overrides stored separately
    # (org_overrides table handles per-org toggle)

    # Metadata
    category: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False
    )  # scanning, ai, compliance, enterprise, experimental

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class FeatureFlagOverride(Base):
    """Per-organization feature flag overrides."""

    __tablename__ = "feature_flag_overrides"
    __table_args__ = (UniqueConstraint("organization_id", "flag_id", name="uq_org_flag_override"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    flag_id: Mapped[int] = mapped_column(Integer, ForeignKey("feature_flags.id"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


# ── Usage Tracking ──────────────────────────────────────────────────────
class UsageRecord(Base):
    """Immutable usage records for billing and quota enforcement.

    Every billable action creates a usage record. Records are append-only.
    """

    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_records_org_period", "organization_id", "period_start"),
        Index("ix_usage_records_metric", "metric"),
        Index("ix_usage_records_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )

    # What was used
    metric: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # scan, ai_request, api_call, storage_mb, export, member
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Period bucket for aggregation
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Context
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


# ── Onboarding ──────────────────────────────────────────────────────────
class OnboardingProgress(Base):
    """Track user onboarding wizard completion.

    Each step has a completion state. The wizard is personalized based on
    the user's role and plan.
    """

    __tablename__ = "onboarding_progress"
    __table_args__ = (UniqueConstraint("user_id", name="uq_onboarding_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=True
    )

    # Steps completed
    completed_steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # ["welcome", "profile", "first_project", "first_scan", "invite_team", "completed"]

    current_step: Mapped[str] = mapped_column(String(50), default="welcome", nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Personalization
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "developer", "security_engineer", "devsecops", "cto"
    use_case: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # "api_security", "sast", "compliance", "general"

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


# ── Email Templates ─────────────────────────────────────────────────────
class EmailTemplate(Base):
    """Configurable email templates for transactional emails.

    Templates are stored in the database and can be customized per-organization
    for white-label support.
    """

    __tablename__ = "email_templates"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_email_template_slug"),
        Index("ix_email_templates_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # transactional, marketing, notification, security

    subject_template: Mapped[str] = mapped_column(String(500), nullable=False)
    # Uses {{variable}} syntax: "Welcome to {{org_name}}, {{user_name}}!"
    body_html_template: Mapped[str] = mapped_column(Text, nullable=False)
    body_text_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Variables available for this template
    variables: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["user_name", "org_name", "scan_count", "plan_name"]

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


# ── Notification Preferences ────────────────────────────────────────────
class NotificationPreference(Base):
    """Per-user notification delivery preferences."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "notification_type", name="uq_notif_pref_user_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # scan_completed, security_alert, compliance_change, etc.

    # Delivery channels
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    slack_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Frequency
    frequency: Mapped[str] = mapped_column(
        String(20), default="immediate", nullable=False
    )  # immediate, hourly_digest, daily_digest, weekly_digest

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


# ── Custom Branding ─────────────────────────────────────────────────────
class CustomBranding(Base):
    """White-label branding configuration per organization.

    Controls logo, colors, domain, and display name for enterprise customers.
    """

    __tablename__ = "custom_branding"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_branding_org"),
        UniqueConstraint("custom_domain", name="uq_branding_domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )

    # Visual branding
    org_display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Color customization
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    # "#3B82F6"
    secondary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    background_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    text_color: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # Custom domain
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # "security.yourcompany.com"
    domain_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    domain_verification_token: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Footer branding
    footer_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    footer_links: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{"label": "Privacy", "url": "..."}]

    # Email branding
    email_from_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email_from_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email_reply_to: Mapped[str | None] = mapped_column(String(200), nullable=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


# ── Feedback ────────────────────────────────────────────────────────────
class Feedback(Base):
    """User feedback collection for product improvement."""

    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_org_id", "organization_id"),
        Index("ix_feedback_category", "category"),
        Index("ix_feedback_sentiment", "sentiment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=True
    )

    # Feedback content
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # bug, feature_request, improvement, praise, complaint
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str] = mapped_column(
        String(20), default="neutral", nullable=False
    )  # positive, neutral, negative

    # Context
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    browser_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
    severity: Mapped[str] = mapped_column(
        String(20), default="low", nullable=False
    )  # low, medium, high, critical

    # Triage
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False
    )  # open, reviewing, planned, in_progress, resolved, wont_fix
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


# ── Product Analytics Events ────────────────────────────────────────────
class AnalyticsEvent(Base):
    """Product analytics events for understanding usage patterns.

    Tracks feature adoption, user journeys, and product metrics.
    Events are append-only and batched for performance.
    """

    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_events_org_id", "organization_id"),
        Index("ix_analytics_events_user_id", "user_id"),
        Index("ix_analytics_events_event_type", "event_type"),
        Index("ix_analytics_events_created_at", "created_at"),
        Index("ix_analytics_events_name_time", "event_name", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # "scan_started", "scan_completed", "feature_used", "page_viewed",
    # "onboarding_step", "export_downloaded", "ai_request"
    event_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # product, security, engagement, lifecycle

    # Context
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Properties
    properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {"scan_type": "api", "finding_count": 5, "duration_ms": 1200}

    # Session
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
