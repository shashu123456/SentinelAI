"""Plan management service.

Handles subscription plan CRUD and seeding.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.saas import Plan
from app.utils.logger import logger


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
    logger.info("Plan created: %s", slug)
    return plan


def update_plan(db: Session, plan_id: int, **fields: Any) -> Plan | None:
    """Update plan configuration. Quota changes take effect on next renewal."""
    from datetime import UTC, datetime

    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        return None
    for key, value in fields.items():
        if hasattr(plan, key):
            setattr(plan, key, value)
    plan.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(plan)
    logger.info("Plan updated: %s", plan.slug)
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
