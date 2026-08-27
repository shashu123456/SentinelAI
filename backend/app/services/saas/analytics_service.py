"""Product analytics event tracking and aggregation."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.saas import AnalyticsEvent


def track_event(
    db: Session, *, event_name: str, event_type: str = "product",
    user_id: int | None = None, organization_id: int | None = None,
    project_id: int | None = None, properties: dict | None = None,
    session_id: str | None = None, ip_address: str | None = None,
    user_agent: str | None = None,
) -> AnalyticsEvent:
    """Track a product analytics event."""
    event = AnalyticsEvent(
        event_name=event_name, event_type=event_type, user_id=user_id,
        organization_id=organization_id, project_id=project_id,
        properties=properties, session_id=session_id,
        ip_address=ip_address, user_agent=user_agent,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_analytics_summary(db: Session, *, organization_id: int, days: int = 30) -> dict:
    """Get analytics summary for an organization."""
    since = datetime.now(UTC) - timedelta(days=days)

    event_counts = (
        db.query(AnalyticsEvent.event_name, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.organization_id == organization_id, AnalyticsEvent.created_at >= since)
        .group_by(AnalyticsEvent.event_name)
        .all()
    )

    daily_users = (
        db.query(func.date(AnalyticsEvent.created_at).label("day"), func.count(func.distinct(AnalyticsEvent.user_id)))
        .filter(AnalyticsEvent.organization_id == organization_id, AnalyticsEvent.created_at >= since)
        .group_by("day").order_by("day").all()
    )

    return {
        "period_days": days,
        "event_counts": {name: count for name, count in event_counts},
        "daily_active_users": [{"date": str(day), "users": count} for day, count in daily_users],
        "total_events": sum(count for _, count in event_counts),
    }
