"""SaaS platform service — backward-compatible shim.

This module re-exports all functions from the domain-specific modules
under app.services.saas.*. New code should import directly from the
domain modules instead.

Domain modules:
- plan_service: Subscription plan CRUD
- subscription_service: Subscription lifecycle
- usage_service: Usage tracking and quotas
- feature_flag_service: Feature flags
- licensing_service: License management
- onboarding_service: Onboarding wizard
- branding_service: White-label branding
- feedback_service: User feedback
- analytics_service: Product analytics
- email_service: Email templates and notifications
"""

from app.services.saas.plan_service import (
    create_plan,
    get_all_plans,
    get_plan_by_slug,
    seed_default_plans,
    update_plan,
)
from app.services.saas.subscription_service import (
    cancel_subscription,
    check_trial_expiration,
    create_subscription,
    expire_trials,
    get_organization_plan,
    get_organization_subscription,
    start_trial,
)
from app.services.saas.usage_service import (
    check_quota,
    enforce_quotas,
    get_usage_summary,
    get_usage_total,
    record_usage,
)
from app.services.saas.feature_flag_service import (
    create_feature_flag,
    get_org_features,
    is_feature_enabled,
    seed_feature_flags,
    set_org_feature_override,
)
from app.services.saas.licensing_service import (
    activate_license,
    create_license,
    validate_license,
)
from app.services.saas.onboarding_service import (
    ONBOARDING_STEPS,
    complete_onboarding_step,
    get_onboarding_progress,
)
from app.services.saas.branding_service import (
    get_branding,
    upsert_branding,
    verify_custom_domain,
)
from app.services.saas.feedback_service import (
    get_feedback_list,
    submit_feedback,
    triage_feedback,
)
from app.services.saas.analytics_service import (
    get_analytics_summary,
    track_event,
)
from app.services.saas.email_service import (
    get_email_template,
    get_notification_preferences,
    render_email_template,
    seed_email_templates,
    set_notification_preference,
)

from app.models.models import Organization
from app.services.saas.plan_service import get_plan_by_slug as _get_plan
from app.services.saas.subscription_service import get_organization_subscription as _get_sub
from app.services.saas.feature_flag_service import get_org_features as _get_features
from app.services.saas.branding_service import get_branding as _get_branding


def get_saa_dashboard(db, org_id: int) -> dict:
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


__all__ = [
    # Plans
    "get_all_plans", "get_plan_by_slug", "create_plan", "update_plan", "seed_default_plans",
    # Subscriptions
    "get_organization_subscription", "get_organization_plan", "create_subscription",
    "cancel_subscription", "start_trial", "check_trial_expiration", "expire_trials",
    # Usage
    "record_usage", "get_usage_total", "check_quota", "get_usage_summary", "enforce_quotas",
    # Feature flags
    "is_feature_enabled", "get_org_features", "create_feature_flag",
    "set_org_feature_override", "seed_feature_flags",
    # Licensing
    "validate_license", "activate_license", "create_license",
    # Onboarding
    "ONBOARDING_STEPS", "get_onboarding_progress", "complete_onboarding_step",
    # Branding
    "get_branding", "upsert_branding", "verify_custom_domain",
    # Feedback
    "submit_feedback", "get_feedback_list", "triage_feedback",
    # Analytics
    "track_event", "get_analytics_summary",
    # Email
    "get_email_template", "render_email_template", "seed_email_templates",
    "get_notification_preferences", "set_notification_preference",
    # Dashboard
    "get_saa_dashboard",
]
