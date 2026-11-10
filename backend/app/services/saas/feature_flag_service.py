"""Feature flag management.

Three-tier override system: global → plan → organization.
"""

from sqlalchemy.orm import Session

from app.models.saas import FeatureFlag, FeatureFlagOverride
from app.services.saas.subscription_service import get_organization_plan
from app.utils.logger import logger


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
    if plan_slug and flag.plan_overrides and plan_slug in flag.plan_overrides:
        return flag.plan_overrides[plan_slug]

    return flag.is_enabled


def get_org_features(db: Session, org_id: int) -> dict[str, bool]:
    """Get all feature flags resolved for an organization."""
    plan = get_organization_plan(db, org_id)
    plan_slug = plan.slug if plan else "free"

    flags = db.query(FeatureFlag).all()
    return {
        flag.key: is_feature_enabled(
            db, feature_key=flag.key, organization_id=org_id, plan_slug=plan_slug
        )
        for flag in flags
    }


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
    logger.info("Feature flag created: %s", key)
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
