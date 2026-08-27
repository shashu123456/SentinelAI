"""SaaS platform service for SentinelAI.

Handles plan management, subscription lifecycle, usage tracking, quota
enforcement, feature flags, licensing, onboarding, branding, feedback,
and analytics.

All plan data is configuration-driven — new plans are added via database
rows, not code changes.
"""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.models import Organization
from app.models.saas import (
    AnalyticsEvent,
    CustomBranding,
    EmailTemplate,
    FeatureFlag,
    FeatureFlagOverride,
    Feedback,
    License,
    NotificationPreference,
    OnboardingProgress,
    Plan,
    Subscription,
    UsageRecord,
)
from app.utils.logger import logger


# ── Plan Management ─────────────────────────────────────────────────────


def get_all_plans(db: Session, include_inactive: bool = False) -> list[Plan]:
    """Return all configured plans ordered by display_order."""
    q = db.query(Plan).order_by(Plan.display_order)
    if not include_inactive:
        q = q.filter(Plan.is_active.is_(True))
    return q.all()


def get_plan_by_slug(db: Session, slug: str) -> Plan | None:
    """Fetch a plan by its unique slug."""
    return db.query(Plan).filter(Plan.slug == slug).first()


def create_plan(
    db: Session,
    *,
    name: str,
    slug: str,
    monthly_price_cents: int = 0,
    annual_price_cents: int = 0,
    max_members: int = 5,
    max_projects: int = 3,
    max_scans_per_month: int = 25,
    features: dict | None = None,
    **kwargs: Any,
) -> Plan:
    """Create a new subscription plan. Fully configuration-driven."""
    plan = Plan(
        name=name,
        slug=slug,
        monthly_price_cents=monthly_price_cents,
        annual_price_cents=annual_price_cents,
        max_members=max_members,
        max_projects=max_projects,
        max_scans_per_month=max_scans_per_month,
        features=features or {},
        **kwargs,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    logger.info(f"Plan created: {slug}")
    return plan


def update_plan(db: Session, plan_id: int, **fields: Any) -> Plan | None:
    """Update plan configuration. Quota changes take effect on next renewal."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        return None
    for key, value in fields.items():
        if hasattr(plan, key):
            setattr(plan, key, value)
    plan.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(plan)
    logger.info(f"Plan updated: {plan.slug}")
    return plan


def seed_default_plans(db: Session) -> list[Plan]:
    """Seed the four default plans if they don't exist."""
    defaults = [
        {
            "name": "Free",
            "slug": "free",
            "monthly_price_cents": 0,
            "annual_price_cents": 0,
            "max_members": 3,
            "max_projects": 2,
            "max_scans_per_month": 10,
            "max_api_keys": 1,
            "max_ai_requests_per_day": 5,
            "retention_days": 14,
            "features": {
                "api_scanning": True,
                "basic_reports": True,
                "dashboard": True,
                "sast_scanning": False,
                "compliance_center": False,
                "ai_copilot": False,
                "scheduled_scans": False,
                "webhooks": False,
                "white_label": False,
                "export_pdf": False,
                "export_sarif": False,
                "team_management": False,
            },
            "display_order": 0,
        },
        {
            "name": "Starter",
            "slug": "starter",
            "monthly_price_cents": 4900,
            "annual_price_cents": 47000,
            "max_members": 10,
            "max_projects": 5,
            "max_scans_per_month": 100,
            "max_api_keys": 3,
            "max_ai_requests_per_day": 25,
            "retention_days": 30,
            "features": {
                "api_scanning": True,
                "basic_reports": True,
                "dashboard": True,
                "sast_scanning": True,
                "compliance_center": False,
                "ai_copilot": True,
                "scheduled_scans": True,
                "webhooks": False,
                "white_label": False,
                "export_pdf": True,
                "export_sarif": False,
                "team_management": True,
            },
            "display_order": 1,
            "badge": None,
        },
        {
            "name": "Professional",
            "slug": "professional",
            "monthly_price_cents": 19900,
            "annual_price_cents": 199000,
            "max_members": 50,
            "max_projects": 20,
            "max_scans_per_month": 500,
            "max_api_keys": 10,
            "max_scheduled_scans": 10,
            "max_webhooks": 5,
            "max_ai_requests_per_day": 100,
            "max_team_members": 20,
            "retention_days": 90,
            "features": {
                "api_scanning": True,
                "basic_reports": True,
                "dashboard": True,
                "sast_scanning": True,
                "compliance_center": True,
                "ai_copilot": True,
                "scheduled_scans": True,
                "webhooks": True,
                "white_label": False,
                "export_pdf": True,
                "export_sarif": True,
                "team_management": True,
            },
            "display_order": 2,
            "badge": "Most Popular",
        },
        {
            "name": "Enterprise",
            "slug": "enterprise",
            "monthly_price_cents": 99900,
            "annual_price_cents": 999000,
            "max_members": 999999,
            "max_projects": 999999,
            "max_scans_per_month": 999999,
            "max_api_keys": 999999,
            "max_scheduled_scans": 999999,
            "max_webhooks": 999999,
            "max_storage_mb": 10240,
            "max_ai_requests_per_day": 999999,
            "max_team_members": 999999,
            "retention_days": 365,
            "features": {
                "api_scanning": True,
                "basic_reports": True,
                "dashboard": True,
                "sast_scanning": True,
                "compliance_center": True,
                "ai_copilot": True,
                "scheduled_scans": True,
                "webhooks": True,
                "white_label": True,
                "export_pdf": True,
                "export_sarif": True,
                "team_management": True,
                "custom_branding": True,
                "sso": True,
                "priority_support": True,
            },
            "display_order": 3,
            "badge": "Enterprise",
        },
    ]

    created = []
    for plan_data in defaults:
        existing = db.query(Plan).filter(Plan.slug == plan_data["slug"]).first()
        if not existing:
            plan = Plan(**plan_data)
            db.add(plan)
            created.append(plan)
    if created:
        db.commit()
        for p in created:
            db.refresh(p)
    return created


# ── Subscription Management ────────────────────────────────────────────


def get_organization_subscription(
    db: Session, org_id: int
) -> Subscription | None:
    """Get the active subscription for an organization."""
    return (
        db.query(Subscription)
        .filter(
            Subscription.organization_id == org_id,
            Subscription.status.in_(["active", "trialing"]),
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )


def get_organization_plan(db: Session, org_id: int) -> Plan | None:
    """Get the effective plan for an organization."""
    sub = get_organization_subscription(db, org_id)
    if sub:
        return db.query(Plan).filter(Plan.id == sub.plan_id).first()
    # Fallback to free plan
    return db.query(Plan).filter(Plan.slug == "free").first()


def create_subscription(
    db: Session,
    *,
    organization_id: int,
    plan_slug: str,
    billing_cycle: str = "monthly",
    is_trial: bool = False,
    trial_days: int = 14,
) -> Subscription | None:
    """Create a new subscription for an organization."""
    plan = get_plan_by_slug(db, plan_slug)
    if not plan:
        return None

    now = datetime.now(UTC)
    trial_end = now + timedelta(days=trial_days) if is_trial else None
    period_end = (
        trial_end
        if is_trial
        else now + timedelta(days=30 if billing_cycle == "monthly" else 365)
    )

    # Cancel existing active subscription
    existing = get_organization_subscription(db, organization_id)
    if existing:
        existing.status = "canceled"
        existing.canceled_at = now

    sub = Subscription(
        organization_id=organization_id,
        plan_id=plan.id,
        status="trialing" if is_trial else "active",
        billing_cycle=billing_cycle,
        is_trial=is_trial,
        trial_starts_at=now if is_trial else None,
        trial_ends_at=trial_end,
        current_period_start=now,
        current_period_end=period_end,
    )
    db.add(sub)

    # Update org tier
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org:
        org.subscription_tier = plan.slug
        org.max_members = plan.max_members
        org.max_projects = plan.max_projects
        org.max_scans_per_month = plan.max_scans_per_month
        org.updated_at = now

    db.commit()
    db.refresh(sub)
    logger.info(
        f"Subscription created: org={organization_id} plan={plan_slug} "
        f"trial={is_trial}"
    )
    return sub


def cancel_subscription(db: Session, org_id: int) -> Subscription | None:
    """Cancel the active subscription. Downgrades to free at period end."""
    sub = get_organization_subscription(db, org_id)
    if not sub:
        return None
    sub.status = "canceled"
    sub.canceled_at = datetime.now(UTC)
    db.commit()
    db.refresh(sub)
    logger.info(f"Subscription canceled: org={org_id}")
    return sub


def start_trial(
    db: Session, org_id: int, plan_slug: str = "professional", trial_days: int = 14
) -> Subscription | None:
    """Start a trial subscription."""
    return create_subscription(
        db,
        organization_id=org_id,
        plan_slug=plan_slug,
        is_trial=True,
        trial_days=trial_days,
    )


# ── Usage Tracking & Quota Enforcement ─────────────────────────────────


def _current_period_bounds() -> tuple[datetime, datetime]:
    """Return the current month's period start and end."""
    now = datetime.now(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)
    return period_start, period_end


def record_usage(
    db: Session,
    *,
    organization_id: int,
    metric: str,
    quantity: int = 1,
    resource_id: int | None = None,
    resource_type: str | None = None,
    user_id: int | None = None,
    detail: dict | None = None,
) -> UsageRecord:
    """Record a usage event. Append-only — never modified."""
    period_start, period_end = _current_period_bounds()
    record = UsageRecord(
        organization_id=organization_id,
        metric=metric,
        quantity=quantity,
        period_start=period_start,
        period_end=period_end,
        resource_id=resource_id,
        resource_type=resource_type,
        user_id=user_id,
        detail=detail,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_usage_total(
    db: Session,
    *,
    organization_id: int,
    metric: str,
    period_start: datetime | None = None,
) -> int:
    """Get total usage for a metric in the current period."""
    if period_start is None:
        period_start, _ = _current_period_bounds()
    result = (
        db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
        .filter(
            UsageRecord.organization_id == organization_id,
            UsageRecord.metric == metric,
            UsageRecord.created_at >= period_start,
        )
        .scalar()
    )
    return int(result)


def check_quota(
    db: Session,
    *,
    organization_id: int,
    metric: str,
    limit: int,
) -> tuple[bool, int, int]:
    """Check if org is within quota. Returns (allowed, current, limit)."""
    current = get_usage_total(db, organization_id=organization_id, metric=metric)
    return current < limit, current, limit


def get_usage_summary(db: Session, org_id: int) -> dict[str, Any]:
    """Get comprehensive usage summary for an organization."""
    plan = get_organization_plan(db, org_id)
    period_start, period_end = _current_period_bounds()

    metrics = [
        "scan",
        "ai_request",
        "api_call",
        "export",
        "member",
        "storage_mb",
    ]

    usage = {}
    for metric in metrics:
        current = get_usage_total(
            db, organization_id=org_id, metric=metric, period_start=period_start
        )
        limit_attr = f"max_{metric}s_per_month" if metric != "storage_mb" else "max_storage_mb"
        if metric == "ai_request":
            limit_attr = "max_ai_requests_per_day"
        limit = getattr(plan, limit_attr, 0) if plan else 0
        usage[metric] = {
            "current": current,
            "limit": limit,
            "percentage": round((current / limit * 100) if limit > 0 else 0, 1),
        }

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "plan": plan.slug if plan else "free",
        "usage": usage,
    }


# ── Feature Flags ──────────────────────────────────────────────────────


def is_feature_enabled(
    db: Session,
    *,
    feature_key: str,
    organization_id: int | None = None,
    plan_slug: str | None = None,
) -> bool:
    """Check if a feature is enabled for a given org/plan.

    Priority: org override > plan override > global default.
    """
    flag = db.query(FeatureFlag).filter(FeatureFlag.key == feature_key).first()
    if not flag:
        return False

    # Check org-level override first
    if organization_id:
        override = (
            db.query(FeatureFlagOverride)
            .filter(
                FeatureFlagOverride.organization_id == organization_id,
                FeatureFlagOverride.flag_id == flag.id,
            )
            .first()
        )
        if override:
            return override.is_enabled

    # Check plan-level override
    if plan_slug and flag.plan_overrides:
        if plan_slug in flag.plan_overrides:
            return flag.plan_overrides[plan_slug]

    # Fall back to global default
    return flag.is_enabled


def get_org_features(db: Session, org_id: int) -> dict[str, bool]:
    """Get all feature flags resolved for an organization."""
    plan = get_organization_plan(db, org_id)
    plan_slug = plan.slug if plan else "free"

    flags = db.query(FeatureFlag).all()
    result = {}
    for flag in flags:
        result[flag.key] = is_feature_enabled(
            db,
            feature_key=flag.key,
            organization_id=org_id,
            plan_slug=plan_slug,
        )
    return result


def create_feature_flag(
    db: Session,
    *,
    key: str,
    name: str,
    description: str | None = None,
    is_enabled: bool = False,
    plan_overrides: dict | None = None,
    category: str = "general",
) -> FeatureFlag:
    """Register a new feature flag."""
    flag = FeatureFlag(
        key=key,
        name=name,
        description=description,
        is_enabled=is_enabled,
        plan_overrides=plan_overrides or {},
        category=category,
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    logger.info(f"Feature flag created: {key}")
    return flag


def set_org_feature_override(
    db: Session,
    *,
    organization_id: int,
    feature_key: str,
    is_enabled: bool,
) -> FeatureFlagOverride:
    """Set or update a per-organization feature flag override."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.key == feature_key).first()
    if not flag:
        raise ValueError(f"Feature flag '{feature_key}' not found")

    existing = (
        db.query(FeatureFlagOverride)
        .filter(
            FeatureFlagOverride.organization_id == organization_id,
            FeatureFlagOverride.flag_id == flag.id,
        )
        .first()
    )
    if existing:
        existing.is_enabled = is_enabled
    else:
        existing = FeatureFlagOverride(
            organization_id=organization_id,
            flag_id=flag.id,
            is_enabled=is_enabled,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def seed_feature_flags(db: Session) -> list[FeatureFlag]:
    """Seed default feature flags if they don't exist."""
    defaults = [
        {
            "key": "api_scanning",
            "name": "API Security Scanning",
            "description": "Scan OpenAPI specs for OWASP API Top 10 vulnerabilities",
            "is_enabled": True,
            "category": "scanning",
        },
        {
            "key": "sast_scanning",
            "name": "Static Application Security Testing",
            "description": "Analyze source code for security vulnerabilities",
            "is_enabled": True,
            "category": "scanning",
            "plan_overrides": {
                "free": False,
                "starter": True,
                "professional": True,
                "enterprise": True,
            },
        },
        {
            "key": "ai_copilot",
            "name": "AI Security Copilot",
            "description": "AI-powered vulnerability analysis and remediation",
            "is_enabled": True,
            "category": "ai",
            "plan_overrides": {
                "free": False,
                "starter": True,
                "professional": True,
                "enterprise": True,
            },
        },
        {
            "key": "compliance_center",
            "name": "Compliance Center",
            "description": "OWASP, PCI-DSS, SOC2, ISO27001 compliance tracking",
            "is_enabled": True,
            "category": "compliance",
            "plan_overrides": {
                "free": False,
                "starter": False,
                "professional": True,
                "enterprise": True,
            },
        },
        {
            "key": "scheduled_scans",
            "name": "Scheduled Scans",
            "description": "Automated recurring scan scheduling",
            "is_enabled": True,
            "category": "automation",
            "plan_overrides": {
                "free": False,
                "starter": True,
                "professional": True,
                "enterprise": True,
            },
        },
        {
            "key": "webhooks",
            "name": "Webhook Integrations",
            "description": "Send notifications to Slack, Teams, Discord, Email",
            "is_enabled": True,
            "category": "integration",
            "plan_overrides": {
                "free": False,
                "starter": False,
                "professional": True,
                "enterprise": True,
            },
        },
        {
            "key": "white_label",
            "name": "White-Label Branding",
            "description": "Custom logo, colors, and domain for the platform",
            "is_enabled": True,
            "category": "enterprise",
            "plan_overrides": {
                "free": False,
                "starter": False,
                "professional": False,
                "enterprise": True,
            },
        },
        {
            "key": "export_sarif",
            "name": "SARIF Export",
            "description": "Export findings in SARIF format for CI/CD integration",
            "is_enabled": True,
            "category": "export",
            "plan_overrides": {
                "free": False,
                "starter": False,
                "professional": True,
                "enterprise": True,
            },
        },
        {
            "key": "export_pdf",
            "name": "PDF Export",
            "description": "Export reports as formatted PDF documents",
            "is_enabled": True,
            "category": "export",
            "plan_overrides": {
                "free": False,
                "starter": True,
                "professional": True,
                "enterprise": True,
            },
        },
        {
            "key": "team_management",
            "name": "Team Management",
            "description": "Organize users into teams with role-based access",
            "is_enabled": True,
            "category": "enterprise",
            "plan_overrides": {
                "free": False,
                "starter": True,
                "professional": True,
                "enterprise": True,
            },
        },
        {
            "key": "experimental_threat_intel",
            "name": "Threat Intelligence (Experimental)",
            "description": "Real-time threat intelligence feeds",
            "is_enabled": False,
            "category": "experimental",
        },
    ]

    created = []
    for flag_data in defaults:
        existing = db.query(FeatureFlag).filter(FeatureFlag.key == flag_data["key"]).first()
        if not existing:
            flag = FeatureFlag(**flag_data)
            db.add(flag)
            created.append(flag)
    if created:
        db.commit()
    return created


# ── License Management ─────────────────────────────────────────────────


def validate_license(db: Session, license_key: str) -> License | None:
    """Validate a license key. Returns None if invalid/expired."""
    lic = db.query(License).filter(License.license_key == license_key).first()
    if not lic:
        return None

    now = datetime.now(UTC)

    # Check status
    if lic.status != "active":
        return None

    # Check expiry — handle both naive and aware datetimes (SQLite vs Postgres)
    if lic.expires_at:
        exp = lic.expires_at
        if exp.tzinfo is None and now.tzinfo is not None:
            exp = exp.replace(tzinfo=UTC)
        elif exp.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=None)
        if exp < now:
            lic.status = "expired"
            db.commit()
            return None

    # Check usage limit
    if lic.max_uses and lic.current_uses >= lic.max_uses:
        lic.status = "expired"
        db.commit()
        return None

    return lic


def activate_license(
    db: Session,
    *,
    license_key: str,
    organization_id: int,
) -> License | None:
    """Activate a license key for an organization."""
    lic = validate_license(db, license_key)
    if not lic:
        return None

    lic.organization_id = organization_id
    lic.current_uses += 1
    lic.status = "active"
    db.commit()
    db.refresh(lic)
    logger.info(f"License activated: org={organization_id} type={lic.license_type}")
    return lic


def create_license(
    db: Session,
    *,
    license_type: str = "trial",
    organization_id: int | None = None,
    expires_in_days: int | None = None,
    max_uses: int | None = None,
    features: dict | None = None,
    max_seats: int | None = None,
    metadata: dict | None = None,
) -> License:
    """Create a new license key."""
    now = datetime.now(UTC)
    lic = License(
        license_key=f"sai-{token_urlsafe(32)}",
        organization_id=organization_id,
        license_type=license_type,
        status="active",
        issued_at=now,
        expires_at=now + timedelta(days=expires_in_days) if expires_in_days else None,
        max_uses=max_uses,
        features=features or {},
        max_seats=max_seats,
        metadata=metadata,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    logger.info(f"License created: type={license_type}")
    return lic


# ── Onboarding Wizard ──────────────────────────────────────────────────


ONBOARDING_STEPS = [
    "welcome",
    "profile",
    "first_project",
    "first_scan",
    "invite_team",
    "completed",
]


def get_onboarding_progress(db: Session, user_id: int) -> OnboardingProgress:
    """Get or create onboarding progress for a user."""
    progress = (
        db.query(OnboardingProgress)
        .filter(OnboardingProgress.user_id == user_id)
        .first()
    )
    if not progress:
        progress = OnboardingProgress(
            user_id=user_id,
            completed_steps=[],
            current_step="welcome",
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def complete_onboarding_step(
    db: Session,
    *,
    user_id: int,
    step: str,
    role: str | None = None,
    use_case: str | None = None,
) -> OnboardingProgress:
    """Mark an onboarding step as complete."""
    progress = get_onboarding_progress(db, user_id)

    if step not in ONBOARDING_STEPS:
        raise ValueError(f"Invalid onboarding step: {step}")

    if step not in progress.completed_steps:
        progress.completed_steps = progress.completed_steps + [step]

    # Advance current step
    current_idx = ONBOARDING_STEPS.index(step)
    if current_idx + 1 < len(ONBOARDING_STEPS):
        progress.current_step = ONBOARDING_STEPS[current_idx + 1]
    else:
        progress.current_step = "completed"
        progress.is_complete = True

    if role:
        progress.role = role
    if use_case:
        progress.use_case = use_case

    progress.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(progress)

    logger.info(f"Onboarding step completed: user={user_id} step={step}")
    return progress


# ── Email Templates ────────────────────────────────────────────────────


def get_email_template(db: Session, slug: str) -> EmailTemplate | None:
    """Get an email template by slug."""
    return db.query(EmailTemplate).filter(EmailTemplate.slug == slug).first()


def render_email_template(
    template: EmailTemplate, variables: dict[str, str]
) -> dict[str, str]:
    """Render an email template with variable substitution.

    Uses {{variable}} syntax for simple substitution.
    """
    subject = template.subject_template
    body_html = template.body_html_template
    body_text = template.body_text_template or ""

    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(value))
        body_html = body_html.replace(placeholder, str(value))
        body_text = body_text.replace(placeholder, str(value))

    return {
        "subject": subject,
        "body_html": body_html,
        "body_text": body_text,
    }


def seed_email_templates(db: Session) -> list[EmailTemplate]:
    """Seed default email templates."""
    defaults = [
        {
            "slug": "welcome",
            "name": "Welcome Email",
            "category": "transactional",
            "subject_template": "Welcome to SentinelAI, {{user_name}}!",
            "body_html_template": (
                "<h1>Welcome, {{user_name}}!</h1>"
                "<p>Your organization <strong>{{org_name}}</strong> has been created.</p>"
                "<p>Start by scanning your first API.</p>"
            ),
            "variables": ["user_name", "org_name"],
        },
        {
            "slug": "scan_completed",
            "name": "Scan Completed",
            "category": "notification",
            "subject_template": "Scan Complete: {{scan_name}} — {{finding_count}} findings",
            "body_html_template": (
                "<h2>Scan Complete</h2>"
                "<p>Your scan <strong>{{scan_name}}</strong> found "
                "<strong>{{finding_count}}</strong> vulnerabilities.</p>"
                "<p>Highest severity: <strong>{{highest_severity}}</strong></p>"
            ),
            "variables": ["scan_name", "finding_count", "highest_severity"],
        },
        {
            "slug": "trial_ending",
            "name": "Trial Ending Soon",
            "category": "marketing",
            "subject_template": "Your SentinelAI trial ends in {{days_remaining}} days",
            "body_html_template": (
                "<h2>Your trial is ending</h2>"
                "<p>You have <strong>{{days_remaining}} days</strong> remaining.</p>"
                "<p>Upgrade to keep your security scanning active.</p>"
            ),
            "variables": ["days_remaining", "plan_name"],
        },
        {
            "slug": "quota_exceeded",
            "name": "Quota Exceeded",
            "category": "security",
            "subject_template": "Usage limit reached for {{metric_name}}",
            "body_html_template": (
                "<h2>Usage Limit Reached</h2>"
                "<p>You've reached your <strong>{{metric_name}}</strong> limit "
                "of <strong>{{limit}}</strong>.</p>"
                "<p>Upgrade your plan to continue.</p>"
            ),
            "variables": ["metric_name", "limit", "plan_name"],
        },
    ]

    created = []
    for tpl_data in defaults:
        existing = db.query(EmailTemplate).filter(EmailTemplate.slug == tpl_data["slug"]).first()
        if not existing:
            tpl = EmailTemplate(**tpl_data)
            db.add(tpl)
            created.append(tpl)
    if created:
        db.commit()
    return created


# ── Notification Preferences ───────────────────────────────────────────


def get_notification_preferences(
    db: Session, user_id: int
) -> list[NotificationPreference]:
    """Get all notification preferences for a user."""
    return (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .all()
    )


def set_notification_preference(
    db: Session,
    *,
    user_id: int,
    notification_type: str,
    email_enabled: bool | None = None,
    in_app_enabled: bool | None = None,
    webhook_enabled: bool | None = None,
    slack_enabled: bool | None = None,
    frequency: str | None = None,
) -> NotificationPreference:
    """Set or update a notification preference."""
    pref = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type,
        )
        .first()
    )
    if not pref:
        pref = NotificationPreference(
            user_id=user_id, notification_type=notification_type
        )
        db.add(pref)

    if email_enabled is not None:
        pref.email_enabled = email_enabled
    if in_app_enabled is not None:
        pref.in_app_enabled = in_app_enabled
    if webhook_enabled is not None:
        pref.webhook_enabled = webhook_enabled
    if slack_enabled is not None:
        pref.slack_enabled = slack_enabled
    if frequency is not None:
        pref.frequency = frequency

    db.commit()
    db.refresh(pref)
    return pref


# ── Custom Branding ────────────────────────────────────────────────────


def get_branding(db: Session, org_id: int) -> CustomBranding | None:
    """Get branding configuration for an organization."""
    return (
        db.query(CustomBranding)
        .filter(CustomBranding.organization_id == org_id)
        .first()
    )


def upsert_branding(
    db: Session,
    *,
    organization_id: int,
    **fields: Any,
) -> CustomBranding:
    """Create or update branding for an organization."""
    branding = get_branding(db, organization_id)
    if not branding:
        branding = CustomBranding(organization_id=organization_id)
        db.add(branding)

    for key, value in fields.items():
        if hasattr(branding, key):
            setattr(branding, key, value)

    branding.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(branding)
    logger.info(f"Branding updated: org={organization_id}")
    return branding


def verify_custom_domain(
    db: Session, org_id: int, verification_token: str
) -> bool:
    """Verify ownership of a custom domain."""
    branding = get_branding(db, org_id)
    if not branding:
        return False
    if branding.domain_verification_token == verification_token:
        branding.domain_verified = True
        db.commit()
        return True
    return False


# ── Feedback ───────────────────────────────────────────────────────────


def submit_feedback(
    db: Session,
    *,
    user_id: int,
    organization_id: int | None,
    category: str,
    title: str,
    description: str,
    page_url: str | None = None,
    browser_info: str | None = None,
    severity: str = "low",
) -> Feedback:
    """Submit user feedback."""
    fb = Feedback(
        user_id=user_id,
        organization_id=organization_id,
        category=category,
        title=title,
        description=description,
        page_url=page_url,
        browser_info=browser_info,
        severity=severity,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    logger.info(f"Feedback submitted: category={category} title={title}")
    return fb


def get_feedback_list(
    db: Session,
    *,
    organization_id: int | None = None,
    status: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> list[Feedback]:
    """List feedback with optional filters."""
    q = db.query(Feedback).order_by(Feedback.created_at.desc())
    if organization_id:
        q = q.filter(Feedback.organization_id == organization_id)
    if status:
        q = q.filter(Feedback.status == status)
    if category:
        q = q.filter(Feedback.category == category)
    return q.limit(limit).all()


def triage_feedback(
    db: Session,
    *,
    feedback_id: int,
    status: str,
    admin_notes: str | None = None,
) -> Feedback | None:
    """Update feedback triage status."""
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        return None
    fb.status = status
    fb.admin_notes = admin_notes
    if status == "resolved":
        fb.resolved_at = datetime.now(UTC)
    db.commit()
    db.refresh(fb)
    return fb


# ── Product Analytics ──────────────────────────────────────────────────


def track_event(
    db: Session,
    *,
    event_name: str,
    event_type: str = "product",
    user_id: int | None = None,
    organization_id: int | None = None,
    project_id: int | None = None,
    properties: dict | None = None,
    session_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AnalyticsEvent:
    """Track a product analytics event."""
    event = AnalyticsEvent(
        event_name=event_name,
        event_type=event_type,
        user_id=user_id,
        organization_id=organization_id,
        project_id=project_id,
        properties=properties,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_analytics_summary(
    db: Session,
    *,
    organization_id: int,
    days: int = 30,
) -> dict[str, Any]:
    """Get analytics summary for an organization."""
    since = datetime.now(UTC) - timedelta(days=days)

    # Event counts by name
    event_counts = (
        db.query(
            AnalyticsEvent.event_name,
            func.count(AnalyticsEvent.id),
        )
        .filter(
            AnalyticsEvent.organization_id == organization_id,
            AnalyticsEvent.created_at >= since,
        )
        .group_by(AnalyticsEvent.event_name)
        .all()
    )

    # Daily active users
    daily_users = (
        db.query(
            func.date(AnalyticsEvent.created_at).label("day"),
            func.count(func.distinct(AnalyticsEvent.user_id)),
        )
        .filter(
            AnalyticsEvent.organization_id == organization_id,
            AnalyticsEvent.created_at >= since,
        )
        .group_by("day")
        .order_by("day")
        .all()
    )

    return {
        "period_days": days,
        "event_counts": {name: count for name, count in event_counts},
        "daily_active_users": [
            {"date": str(day), "users": count} for day, count in daily_users
        ],
        "total_events": sum(count for _, count in event_counts),
    }


# ── Subscription Lifecycle ─────────────────────────────────────────────


def check_trial_expiration(db: Session) -> list[Subscription]:
    """Find subscriptions whose trials have expired."""
    now = datetime.now(UTC)
    # Use naive datetime for SQLite compatibility
    now_naive = now.replace(tzinfo=None)
    return (
        db.query(Subscription)
        .filter(
            Subscription.status == "trialing",
            Subscription.trial_ends_at <= now_naive,
        )
        .all()
    )


def expire_trials(db: Session) -> int:
    """Downgrade expired trials to free. Returns count of affected subs."""
    expired = check_trial_expiration(db)
    for sub in expired:
        sub.status = "canceled"
        sub.canceled_at = datetime.now(UTC)
        # Downgrade org to free
        org = db.query(Organization).filter(Organization.id == sub.organization_id).first()
        if org:
            free_plan = db.query(Plan).filter(Plan.slug == "free").first()
            if free_plan:
                org.subscription_tier = "free"
                org.max_members = free_plan.max_members
                org.max_projects = free_plan.max_projects
                org.max_scans_per_month = free_plan.max_scans_per_month
                org.updated_at = datetime.now(UTC)
        logger.info(f"Trial expired: org={sub.organization_id}")
    db.commit()
    return len(expired)


def enforce_quotas(db: Session, org_id: int) -> dict[str, Any]:
    """Check all quotas for an organization and return enforcement status."""
    plan = get_organization_plan(db, org_id)
    if not plan:
        return {"error": "No plan found"}

    checks = {
        "scans": {
            "metric": "scan",
            "limit": plan.max_scans_per_month,
        },
        "ai_requests": {
            "metric": "ai_request",
            "limit": plan.max_ai_requests_per_day,
        },
        "api_calls": {
            "metric": "api_call",
            "limit": plan.max_scans_per_month * 10,  # rough estimate
        },
    }

    results = {}
    for name, check in checks.items():
        allowed, current, limit = check_quota(
            db,
            organization_id=org_id,
            metric=check["metric"],
            limit=check["limit"],
        )
        results[name] = {
            "allowed": allowed,
            "current": current,
            "limit": limit,
            "exhausted": not allowed,
        }

    return results


def get_saa_dashboard(db: Session, org_id: int) -> dict[str, Any]:
    """Get complete SaaS dashboard data for an organization."""
    plan = get_organization_plan(db, org_id)
    sub = get_organization_subscription(db, org_id)
    usage = get_usage_summary(db, org_id)
    features = get_org_features(db, org_id)
    branding = get_branding(db, org_id)

    return {
        "plan": {
            "name": plan.name if plan else "Free",
            "slug": plan.slug if plan else "free",
            "monthly_price_cents": plan.monthly_price_cents if plan else 0,
            "features": plan.features if plan else {},
        },
        "subscription": {
            "status": sub.status if sub else None,
            "is_trial": sub.is_trial if sub else False,
            "trial_ends_at": sub.trial_ends_at.isoformat() if sub and sub.trial_ends_at else None,
            "current_period_end": sub.current_period_end.isoformat() if sub else None,
            "billing_cycle": sub.billing_cycle if sub else None,
        },
        "usage": usage,
        "features": features,
        "branding": {
            "enabled": branding.is_enabled if branding else False,
            "custom_domain": branding.custom_domain if branding else None,
            "domain_verified": branding.domain_verified if branding else False,
        },
    }
