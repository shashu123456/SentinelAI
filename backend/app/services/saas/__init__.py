"""SaaS platform services.

Domain modules:
- plan_service: Subscription plan CRUD and seeding
- subscription_service: Subscription lifecycle management
- usage_service: Usage tracking and quota enforcement
- feature_flag_service: Feature flag management
- licensing_service: License creation and validation
- onboarding_service: User onboarding wizard
- branding_service: White-label branding
- feedback_service: User feedback collection
- analytics_service: Product analytics
- email_service: Email templates and notification preferences

All functions are re-exported here for backward compatibility.
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

# Lazy imports for modules not yet split
def _get_licensing():
    from app.services.saas import licensing_service
    return licensing_service

def _get_onboarding():
    from app.services.saas import onboarding_service
    return onboarding_service

def _get_branding():
    from app.services.saas import branding_service
    return branding_service

def _get_feedback():
    from app.services.saas import feedback_service
    return feedback_service

def _get_analytics():
    from app.services.saas import analytics_service
    return analytics_service

def _get_email():
    from app.services.saas import email_service
    return email_service

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
]
