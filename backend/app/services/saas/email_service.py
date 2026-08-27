"""Email templates and notification preferences."""

from sqlalchemy.orm import Session

from app.models.saas import EmailTemplate, NotificationPreference
from app.utils.logger import logger


def get_email_template(db: Session, slug: str) -> EmailTemplate | None:
    """Get an email template by slug."""
    return db.query(EmailTemplate).filter(EmailTemplate.slug == slug).first()


def render_email_template(template: EmailTemplate, variables: dict[str, str]) -> dict[str, str]:
    """Render an email template with {{variable}} substitution."""
    subject = template.subject_template
    body_html = template.body_html_template
    body_text = template.body_text_template or ""
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(value))
        body_html = body_html.replace(placeholder, str(value))
        body_text = body_text.replace(placeholder, str(value))
    return {"subject": subject, "body_html": body_html, "body_text": body_text}


def seed_email_templates(db: Session) -> list[EmailTemplate]:
    """Seed default email templates."""
    defaults = [
        {
            "slug": "welcome", "name": "Welcome Email", "category": "transactional",
            "subject_template": "Welcome to SentinelAI, {{user_name}}!",
            "body_html_template": "<h1>Welcome, {{user_name}}!</h1><p>Your organization <strong>{{org_name}}</strong> has been created.</p>",
            "variables": ["user_name", "org_name"],
        },
        {
            "slug": "scan_completed", "name": "Scan Completed", "category": "notification",
            "subject_template": "Scan Complete: {{scan_name}} — {{finding_count}} findings",
            "body_html_template": "<h2>Scan Complete</h2><p>Your scan <strong>{{scan_name}}</strong> found <strong>{{finding_count}}</strong> vulnerabilities.</p>",
            "variables": ["scan_name", "finding_count", "highest_severity"],
        },
        {
            "slug": "trial_ending", "name": "Trial Ending Soon", "category": "marketing",
            "subject_template": "Your SentinelAI trial ends in {{days_remaining}} days",
            "body_html_template": "<h2>Your trial is ending</h2><p>You have <strong>{{days_remaining}} days</strong> remaining.</p>",
            "variables": ["days_remaining", "plan_name"],
        },
        {
            "slug": "quota_exceeded", "name": "Quota Exceeded", "category": "security",
            "subject_template": "Usage limit reached for {{metric_name}}",
            "body_html_template": "<h2>Usage Limit Reached</h2><p>You've reached your <strong>{{metric_name}}</strong> limit.</p>",
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


def get_notification_preferences(db: Session, user_id: int) -> list[NotificationPreference]:
    """Get all notification preferences for a user."""
    return db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).all()


def set_notification_preference(
    db: Session, *, user_id: int, notification_type: str,
    email_enabled: bool | None = None, in_app_enabled: bool | None = None,
    webhook_enabled: bool | None = None, slack_enabled: bool | None = None,
    frequency: str | None = None,
) -> NotificationPreference:
    """Set or update a notification preference."""
    pref = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id, NotificationPreference.notification_type == notification_type)
        .first()
    )
    if not pref:
        pref = NotificationPreference(user_id=user_id, notification_type=notification_type)
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
