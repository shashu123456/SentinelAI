"""Subscription lifecycle management.

Handles subscription creation, trials, cancellation, and plan changes.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import Organization
from app.models.saas import Plan, Subscription
from app.services.saas.plan_service import get_plan_by_slug
from app.utils.logger import logger


def get_organization_subscription(db: Session, org_id: int) -> Subscription | None:
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
        trial_end if is_trial else now + timedelta(days=30 if billing_cycle == "monthly" else 365)
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
        "Subscription created: org=%s plan=%s trial=%s",
        organization_id,
        plan_slug,
        is_trial,
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
    logger.info("Subscription canceled: org=%s", org_id)
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


def check_trial_expiration(db: Session) -> list[Subscription]:
    """Find subscriptions whose trials have expired."""
    now = datetime.now(UTC)
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
        org = db.query(Organization).filter(Organization.id == sub.organization_id).first()
        if org:
            free_plan = db.query(Plan).filter(Plan.slug == "free").first()
            if free_plan:
                org.subscription_tier = "free"
                org.max_members = free_plan.max_members
                org.max_projects = free_plan.max_projects
                org.max_scans_per_month = free_plan.max_scans_per_month
                org.updated_at = datetime.now(UTC)
        logger.info("Trial expired: org=%s", sub.organization_id)
    db.commit()
    return len(expired)
