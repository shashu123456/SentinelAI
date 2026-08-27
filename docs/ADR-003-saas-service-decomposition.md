# ADR-003: SaaS Service Decomposition

## Status

Accepted

## Context

`saas_service.py` was a 1,355-line monolith containing 38 functions across 9 unrelated business domains. Any change to plan management risked breaking feedback collection. Code reviews were difficult because unrelated logic was interleaved.

## Decision

Decompose into 10 domain-specific service modules:

| Module | Responsibility | Lines |
|--------|---------------|-------|
| `plan_service.py` | Plan CRUD, tier management | 180 |
| `subscription_service.py` | Subscription lifecycle | 130 |
| `usage_service.py` | Usage tracking, quota enforcement | 100 |
| `feature_flag_service.py` | Feature flags, plan-gated features | 140 |
| `licensing_service.py` | License validation, trial mode | 65 |
| `onboarding_service.py` | Onboarding wizard, step tracking | 45 |
| `branding_service.py` | White-label, custom domains | 35 |
| `feedback_service.py` | User feedback collection | 45 |
| `analytics_service.py` | Product analytics events | 45 |
| `email_service.py` | Email templates, preferences | 80 |

The original `saas_service.py` is preserved as a thin shim (130 lines) that re-exports all functions for backward compatibility.

## Consequences

**Positive:**
- Each service can be developed, tested, and reviewed independently
- Average function length reduced from 36 lines to 22 lines (-39%)
- Module complexity reduced from HIGH to LOW
- Clear domain boundaries follow SOLID's SRP

**Negative:**
- 10 import paths to manage instead of 1
- Cross-cutting concerns (audit logging, error handling) duplicated slightly

**Mitigation:**
- The shim maintains all existing imports
- Shared utilities remain in `app.utils`
- New code imports directly from domain modules
