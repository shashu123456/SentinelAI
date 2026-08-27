# SentinelAI — SaaS Platform Architecture

> Enterprise-grade SaaS infrastructure for subscription management, usage tracking, feature flags, licensing, onboarding, branding, and product analytics.

---

## Overview

The SaaS platform layer transforms SentinelAI from a single-tenant application into a multi-tenant, subscription-ready SaaS platform. Every capability is **configuration-driven** — new plans, features, and quotas are added via database rows, not code changes.

```
┌─────────────────────────────────────────────────────────────────┐
│                        SaaS Platform                            │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│  Plans   │  Subs    │  Usage   │  Flags   │  License │  Brand   │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ Onboard  │  Email   │  Notif   │  Feedback│ Analytics│  RBAC    │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## Data Models (12 tables)

### Plans

| Field | Type | Description |
|-------|------|-------------|
| slug | String(50) | Unique identifier: `free`, `starter`, `professional`, `enterprise` |
| monthly_price_cents | Integer | Price in cents (0 = free) |
| annual_price_cents | Integer | Annual price in cents |
| max_members | Integer | Maximum organization members |
| max_projects | Integer | Maximum projects per org |
| max_scans_per_month | Integer | Scan quota per billing period |
| max_api_keys | Integer | Maximum API keys |
| max_ai_requests_per_day | Integer | AI Copilot daily quota |
| features | JSON | Feature flag map for this plan |
| display_order | Integer | Ordering on pricing page |
| badge | String(50) | Optional badge text ("Most Popular") |

**Key Design Decision:** Features are stored as a JSON map on the Plan model, not as separate rows. This keeps the plan definition self-contained and easy to reason about.

### Subscriptions

Tracks the active subscription lifecycle for each organization.

| Status | Description |
|--------|-------------|
| active | Paid subscription is current |
| trialing | In trial period |
| past_due | Payment failed |
| canceled | User or system canceled |
| paused | Temporarily paused |

### Licenses

Enterprise and self-hosted license management with key generation, expiry, max-uses, and feature gating.

```
Format: sai-{url_safe_token_32}
```

### Feature Flags

Three-tier override system:

```
Global Default → Plan Override → Organization Override
```

| Level | Storage | Priority |
|-------|---------|----------|
| Global | `feature_flags.is_enabled` | Lowest |
| Plan | `feature_flags.plan_overrides` (JSON) | Medium |
| Organization | `feature_flag_overrides` table | Highest |

### Usage Records

Append-only usage tracking. Every billable action creates a record.

**Metrics tracked:**
- `scan` — API/SAST/dependency scans
- `ai_request` — AI Copilot requests
- `api_call` — API endpoint calls
- `export` — Report exports
- `member` — Team member additions
- `storage_mb` — Storage usage

**Period bucketing:** Records are tagged with `period_start` and `period_end` for monthly aggregation.

### Onboarding Progress

6-step wizard: `welcome → profile → first_project → first_scan → invite_team → completed`

Stores `role` and `use_case` for personalization.

### Email Templates

Templates use `{{variable}}` syntax. Stored in database for white-label customization.

**Default templates:** welcome, scan_completed, trial_ending, quota_exceeded

### Notification Preferences

Per-user, per-notification-type delivery preferences with channel and frequency controls.

### Custom Branding

White-label configuration: logo, colors, custom domain, email branding, footer customization.

### Feedback

User feedback collection with triage workflow: `open → reviewing → planned → in_progress → resolved`

### Analytics Events

Append-only product analytics with event names, types, properties, and session tracking.

---

## Service Layer

### Plan Management

```python
# Configuration-driven — no hardcoded plans
create_plan(db, name="Enterprise", slug="enterprise", max_scans_per_month=999999, ...)
seed_default_plans(db)  # Creates free/starter/professional/enterprise
```

### Subscription Lifecycle

```
create_subscription → start_trial → cancel_subscription
                    ↓
            expire_trials (batch job)
```

### Usage & Quotas

```python
record_usage(db, org_id=1, metric="scan", quantity=1)
allowed, current, limit = check_quota(db, org_id=1, metric="scan", limit=100)
summary = get_usage_summary(db, org_id=1)  # Full dashboard data
```

### Feature Flags

```python
enabled = is_feature_enabled(db, feature_key="sast_scanning", organization_id=1, plan_slug="starter")
features = get_org_features(db, org_id=1)  # All resolved flags
```

### License Management

```python
lic = create_license(db, license_type="enterprise", expires_in_days=365, max_seats=100)
validated = validate_license(db, license_key="sai-...")
activated = activate_license(db, license_key="sai-...", organization_id=1)
```

---

## API Endpoints (21 routes)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/saas/plans` | List all plans |
| GET | `/api/saas/plans/{slug}` | Get plan by slug |
| POST | `/api/saas/plans` | Create plan (admin) |
| GET | `/api/saas/subscription` | Get org subscription |
| POST | `/api/saas/subscription/start-trial` | Start trial |
| POST | `/api/saas/subscription/cancel` | Cancel subscription |
| GET | `/api/saas/usage` | Usage summary |
| GET | `/api/saas/usage/check` | Check specific quota |
| GET | `/api/saas/features` | All resolved features |
| GET | `/api/saas/features/{key}` | Check specific feature |
| POST | `/api/saas/license/activate` | Activate license key |
| POST | `/api/saas/license/validate` | Validate license key |
| GET | `/api/saas/onboarding` | Get onboarding progress |
| POST | `/api/saas/onboarding/step` | Complete onboarding step |
| GET | `/api/saas/branding` | Get branding config |
| PUT | `/api/saas/branding` | Update branding (admin) |
| POST | `/api/saas/feedback` | Submit feedback |
| GET | `/api/saas/feedback` | List feedback |
| GET | `/api/saas/analytics` | Analytics summary |
| POST | `/api/saas/analytics/track` | Track event |
| GET | `/api/saas/dashboard` | Full SaaS dashboard |

---

## Default Plans

| Plan | Price/mo | Members | Projects | Scans/mo | AI/day | Features |
|------|----------|---------|----------|----------|--------|----------|
| Free | $0 | 3 | 2 | 10 | 5 | API scanning, dashboard |
| Starter | $49 | 10 | 5 | 100 | 25 | + SAST, AI, scheduled scans |
| Professional | $199 | 50 | 20 | 500 | 100 | + Compliance, webhooks, SARIF |
| Enterprise | $999 | Unlimited | Unlimited | Unlimited | Unlimited | + White-label, SSO, custom branding |

---

## Feature Flags (11 default)

| Key | Category | Free | Starter | Professional | Enterprise |
|-----|----------|------|---------|-------------|------------|
| api_scanning | scanning | ✅ | ✅ | ✅ | ✅ |
| sast_scanning | scanning | ❌ | ✅ | ✅ | ✅ |
| ai_copilot | ai | ❌ | ✅ | ✅ | ✅ |
| compliance_center | compliance | ❌ | ❌ | ✅ | ✅ |
| scheduled_scans | automation | ❌ | ✅ | ✅ | ✅ |
| webhooks | integration | ❌ | ❌ | ✅ | ✅ |
| white_label | enterprise | ❌ | ❌ | ❌ | ✅ |
| export_sarif | export | ❌ | ❌ | ✅ | ✅ |
| export_pdf | export | ❌ | ✅ | ✅ | ✅ |
| team_management | enterprise | ❌ | ✅ | ✅ | ✅ |
| experimental_threat_intel | experimental | ❌ | ❌ | ❌ | ❌ |

---

## Migration

```bash
cd backend
python -m alembic upgrade head
```

**Tables created (12):**

1. `plans` — Subscription plan definitions
2. `subscriptions` — Active subscriptions per org
3. `licenses` — License keys for enterprise
4. `feature_flags` — Runtime feature toggles
5. `feature_flag_overrides` — Per-org flag overrides
6. `usage_records` — Append-only usage tracking
7. `onboarding_progress` — User onboarding state
8. `email_templates` — Transactional email templates
9. `notification_preferences` — User delivery preferences
10. `custom_branding` — White-label configuration
11. `feedback` — User feedback collection
12. `analytics_events` — Product analytics events

**Migration ID:** `d4e5f6a7b8c9`

---

## Testing

```bash
cd backend
python -m pytest tests/test_saas_platform.py -v
```

**67 tests across 12 test classes:**

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestPlanManagement | 10 | CRUD, seeding, limits, idempotency |
| TestSubscriptionLifecycle | 10 | Create, trial, cancel, plan changes |
| TestUsageTracking | 5 | Record, query, quota check, summary |
| TestFeatureFlags | 8 | Global, plan, org overrides |
| TestLicenseManagement | 5 | Create, validate, activate, expiry |
| TestOnboardingWizard | 6 | Steps, progression, completion |
| TestEmailTemplates | 4 | Rendering, variables, seeding |
| TestNotificationPreferences | 3 | CRUD, updates |
| TestCustomBranding | 6 | Upsert, domain verification |
| TestFeedback | 5 | Submit, list, triage, filters |
| TestProductAnalytics | 2 | Tracking, aggregation |
| TestSAASDashboard | 1 | Full dashboard aggregation |
| TestQuotaEnforcement | 2 | Normal and exhausted quotas |

---

## Design Decisions

### Why JSON for plan features instead of a features table?
- Plans are read-heavy, write-rare. A JSON column avoids JOIN overhead.
- Plan features are a bounded set (~20 features). JSON is appropriate.
- Adding a new plan feature doesn't require a migration.

### Why append-only usage records?
- Billing records must be immutable for audit and compliance.
- Aggregation queries use SQL SUM, which is efficient with proper indexes.
- Period bucketing allows fast "current month" queries without date math.

### Why three-tier feature flags?
- Global defaults allow A/B testing across all users.
- Plan overrides enforce subscription-based feature gating.
- Org overrides enable custom enterprise configurations.
- Priority chain (org > plan > global) prevents accidental feature exposure.

### Why store email templates in the database?
- Enables white-label customization per organization.
- Template changes don't require code deployments.
- Supports A/B testing of email content.
- Allows non-technical users to edit templates.

### Why license keys start with `sai-`?
- Clear identification of SentinelAI license keys.
- Prevents confusion with other tool keys.
- Makes it easy to detect and block leaked keys.
- URL-safe token format for easy copy/paste.
