"""User feedback collection and triage."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.saas import Feedback
from app.utils.logger import logger


def submit_feedback(
    db: Session, *, user_id: int, organization_id: int | None, category: str,
    title: str, description: str, page_url: str | None = None,
    browser_info: str | None = None, severity: str = "low",
) -> Feedback:
    """Submit user feedback."""
    fb = Feedback(
        user_id=user_id, organization_id=organization_id, category=category,
        title=title, description=description, page_url=page_url,
        browser_info=browser_info, severity=severity,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    logger.info("Feedback submitted: category=%s title=%s", category, title)
    return fb


def get_feedback_list(
    db: Session, *, organization_id: int | None = None, status: str | None = None,
    category: str | None = None, limit: int = 50,
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
    db: Session, *, feedback_id: int, status: str, admin_notes: str | None = None,
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
