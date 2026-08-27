"""Usage tracking and quota enforcement.

Handles usage recording, querying, and quota checks.
"""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.saas import UsageRecord
from app.services.saas.subscription_service import get_organization_plan


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


def get_usage_summary(db: Session, org_id: int) -> dict:
    """Get comprehensive usage summary for an organization."""
    plan = get_organization_plan(db, org_id)
    period_start, period_end = _current_period_bounds()

    metrics = ["scan", "ai_request", "api_call", "export", "member", "storage_mb"]

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


def enforce_quotas(db: Session, org_id: int) -> dict:
    """Check all quotas for an organization."""
    plan = get_organization_plan(db, org_id)
    if not plan:
        return {"error": "No plan found"}

    checks = {
        "scans": {"metric": "scan", "limit": plan.max_scans_per_month},
        "ai_requests": {"metric": "ai_request", "limit": plan.max_ai_requests_per_day},
        "api_calls": {"metric": "api_call", "limit": plan.max_scans_per_month * 10},
    }

    results = {}
    for name, check in checks.items():
        allowed, current, limit = check_quota(
            db, organization_id=org_id, metric=check["metric"], limit=check["limit"]
        )
        results[name] = {
            "allowed": allowed,
            "current": current,
            "limit": limit,
            "exhausted": not allowed,
        }
    return results
