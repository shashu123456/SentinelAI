"""Comprehensive SaaS platform tests.

Tests cover:
- Plan management (CRUD, seeding, configuration-driven)
- Subscription lifecycle (create, trial, cancel, plan changes)
- Usage tracking (record, query, quota enforcement)
- Feature flags (global, plan-based, org-based overrides)
- License management (create, validate, activate, expiry)
- Onboarding wizard (step progression, completion)
- Email templates (rendering, variable substitution)
- Notification preferences (CRUD)
- Custom branding (upsert, domain verification)
- Feedback (submit, list, triage)
- Product analytics (tracking, aggregation)
- Dashboard aggregation
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.database.database import Base, engine
from app.models.models import Organization, User
from app.models.saas import (
    FeatureFlag,
)
from app.services import saas_service


@pytest.fixture(autouse=True)
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import Session

    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password_123",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def org(db_session, user):
    """Create a test organization."""
    org = Organization(
        name="Test Org",
        slug="test-org",
        owner_id=user.id,
        subscription_tier="free",
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


# ── Plan Tests ─────────────────────────────────────────────────────────


class TestPlanManagement:
    """Test plan CRUD and seeding operations."""

    def test_create_plan(self, db_session):
        plan = saas_service.create_plan(
            db_session,
            name="Test Plan",
            slug="test-plan",
            monthly_price_cents=9900,
            max_members=10,
            max_scans_per_month=100,
            features={"api_scanning": True, "sast_scanning": False},
        )
        assert plan.slug == "test-plan"
        assert plan.monthly_price_cents == 9900
        assert plan.features["api_scanning"] is True
        assert plan.features["sast_scanning"] is False

    def test_get_plan_by_slug(self, db_session):
        saas_service.create_plan(db_session, name="Pro", slug="pro")
        found = saas_service.get_plan_by_slug(db_session, "pro")
        assert found is not None
        assert found.name == "Pro"

    def test_get_plan_not_found(self, db_session):
        found = saas_service.get_plan_by_slug(db_session, "nonexistent")
        assert found is None

    def test_list_plans(self, db_session):
        saas_service.create_plan(db_session, name="A", slug="a", display_order=2)
        saas_service.create_plan(db_session, name="B", slug="b", display_order=1)
        plans = saas_service.get_all_plans(db_session)
        assert len(plans) == 2
        # Ordered by display_order
        assert plans[0].slug == "b"

    def test_update_plan(self, db_session):
        plan = saas_service.create_plan(db_session, name="Old", slug="old")
        updated = saas_service.update_plan(db_session, plan.id, name="New", max_members=50)
        assert updated.name == "New"
        assert updated.max_members == 50

    def test_update_plan_not_found(self, db_session):
        result = saas_service.update_plan(db_session, 999, name="X")
        assert result is None

    def test_seed_default_plans(self, db_session):
        created = saas_service.seed_default_plans(db_session)
        assert len(created) == 4
        slugs = {p.slug for p in created}
        assert slugs == {"free", "starter", "professional", "enterprise"}

    def test_seed_default_plans_idempotent(self, db_session):
        saas_service.seed_default_plans(db_session)
        second = saas_service.seed_default_plans(db_session)
        assert len(second) == 0  # No duplicates

    def test_free_plan_has_correct_limits(self, db_session):
        saas_service.seed_default_plans(db_session)
        free = saas_service.get_plan_by_slug(db_session, "free")
        assert free.max_members == 3
        assert free.max_scans_per_month == 10
        assert free.monthly_price_cents == 0

    def test_enterprise_plan_has_unlimited(self, db_session):
        saas_service.seed_default_plans(db_session)
        ent = saas_service.get_plan_by_slug(db_session, "enterprise")
        assert ent.max_scans_per_month == 999999
        assert ent.features.get("white_label") is True
        assert ent.features.get("sso") is True


# ── Subscription Tests ─────────────────────────────────────────────────


class TestSubscriptionLifecycle:
    """Test subscription creation, trials, cancellation."""

    def _setup_plans(self, db_session):
        saas_service.seed_default_plans(db_session)

    def test_create_subscription(self, db_session, org):
        self._setup_plans(db_session)
        sub = saas_service.create_subscription(
            db_session,
            organization_id=org.id,
            plan_slug="professional",
            billing_cycle="monthly",
        )
        assert sub is not None
        assert sub.status == "active"
        assert sub.billing_cycle == "monthly"

    def test_create_trial_subscription(self, db_session, org):
        self._setup_plans(db_session)
        sub = saas_service.create_subscription(
            db_session,
            organization_id=org.id,
            plan_slug="professional",
            is_trial=True,
            trial_days=14,
        )
        assert sub.status == "trialing"
        assert sub.is_trial is True
        assert sub.trial_ends_at is not None

    def test_create_subscription_invalid_plan(self, db_session, org):
        self._setup_plans(db_session)
        sub = saas_service.create_subscription(
            db_session,
            organization_id=org.id,
            plan_slug="nonexistent",
        )
        assert sub is None

    def test_get_subscription(self, db_session, org):
        self._setup_plans(db_session)
        saas_service.create_subscription(db_session, organization_id=org.id, plan_slug="starter")
        sub = saas_service.get_organization_subscription(db_session, org.id)
        assert sub is not None
        assert sub.plan.slug == "starter"

    def test_cancel_subscription(self, db_session, org):
        self._setup_plans(db_session)
        saas_service.create_subscription(db_session, organization_id=org.id, plan_slug="starter")
        canceled = saas_service.cancel_subscription(db_session, org.id)
        assert canceled.status == "canceled"
        assert canceled.canceled_at is not None

    def test_cancel_nonexistent_subscription(self, db_session, org):
        result = saas_service.cancel_subscription(db_session, org.id)
        assert result is None

    def test_get_org_plan(self, db_session, org):
        self._setup_plans(db_session)
        saas_service.create_subscription(db_session, organization_id=org.id, plan_slug="enterprise")
        plan = saas_service.get_organization_plan(db_session, org.id)
        assert plan.slug == "enterprise"

    def test_get_org_plan_defaults_to_free(self, db_session, org):
        self._setup_plans(db_session)
        plan = saas_service.get_organization_plan(db_session, org.id)
        assert plan.slug == "free"

    def test_start_trial(self, db_session, org):
        self._setup_plans(db_session)
        sub = saas_service.start_trial(db_session, org.id, plan_slug="professional")
        assert sub.status == "trialing"
        assert sub.is_trial is True

    def test_subscription_cancels_existing(self, db_session, org):
        self._setup_plans(db_session)
        saas_service.create_subscription(db_session, organization_id=org.id, plan_slug="starter")
        new_sub = saas_service.create_subscription(
            db_session, organization_id=org.id, plan_slug="professional"
        )
        assert new_sub.status == "active"
        old_sub = saas_service.get_organization_subscription(db_session, org.id)
        assert old_sub.plan.slug == "professional"


# ── Usage Tracking Tests ───────────────────────────────────────────────


class TestUsageTracking:
    """Test usage recording, querying, and quota enforcement."""

    def test_record_usage(self, db_session, org):
        record = saas_service.record_usage(
            db_session,
            organization_id=org.id,
            metric="scan",
            quantity=1,
        )
        assert record.metric == "scan"
        assert record.quantity == 1

    def test_get_usage_total(self, db_session, org):
        for _ in range(5):
            saas_service.record_usage(db_session, organization_id=org.id, metric="scan")
        total = saas_service.get_usage_total(db_session, organization_id=org.id, metric="scan")
        assert total == 5

    def test_check_quota_within_limit(self, db_session, org):
        for _ in range(3):
            saas_service.record_usage(db_session, organization_id=org.id, metric="scan")
        allowed, current, limit = saas_service.check_quota(
            db_session, organization_id=org.id, metric="scan", limit=10
        )
        assert allowed is True
        assert current == 3
        assert limit == 10

    def test_check_quota_exceeded(self, db_session, org):
        for _ in range(10):
            saas_service.record_usage(db_session, organization_id=org.id, metric="scan")
        allowed, current, limit = saas_service.check_quota(
            db_session, organization_id=org.id, metric="scan", limit=10
        )
        assert allowed is False
        assert current == 10

    def test_usage_summary(self, db_session, org):
        saas_service.seed_default_plans(db_session)
        saas_service.record_usage(db_session, organization_id=org.id, metric="scan")
        summary = saas_service.get_usage_summary(db_session, org.id)
        assert "period_start" in summary
        assert "usage" in summary
        assert summary["usage"]["scan"]["current"] == 1


# ── Feature Flag Tests ────────────────────────────────────────────────


class TestFeatureFlags:
    """Test feature flag system with global, plan, and org overrides."""

    def test_create_flag(self, db_session):
        flag = saas_service.create_feature_flag(
            db_session,
            key="test_feature",
            name="Test Feature",
            is_enabled=True,
            category="scanning",
        )
        assert flag.key == "test_feature"
        assert flag.is_enabled is True

    def test_global_flag_enabled(self, db_session):
        saas_service.create_feature_flag(
            db_session, key="api_scanning", name="API Scanning", is_enabled=True
        )
        assert saas_service.is_feature_enabled(db_session, feature_key="api_scanning") is True

    def test_global_flag_disabled(self, db_session):
        saas_service.create_feature_flag(
            db_session, key="experimental", name="Experimental", is_enabled=False
        )
        assert saas_service.is_feature_enabled(db_session, feature_key="experimental") is False

    def test_plan_override(self, db_session):
        saas_service.create_feature_flag(
            db_session,
            key="sast",
            name="SAST",
            is_enabled=True,
            plan_overrides={"free": False, "starter": True},
        )
        assert (
            saas_service.is_feature_enabled(db_session, feature_key="sast", plan_slug="free")
            is False
        )
        assert (
            saas_service.is_feature_enabled(db_session, feature_key="sast", plan_slug="starter")
            is True
        )

    def test_org_override_takes_priority(self, db_session, org):
        saas_service.create_feature_flag(
            db_session,
            key="custom_feature",
            name="Custom",
            is_enabled=False,
        )
        db_session.query(FeatureFlag).filter(FeatureFlag.key == "custom_feature").first()
        saas_service.set_org_feature_override(
            db_session, organization_id=org.id, feature_key="custom_feature", is_enabled=True
        )
        assert (
            saas_service.is_feature_enabled(
                db_session, feature_key="custom_feature", organization_id=org.id
            )
            is True
        )

    def test_get_org_features(self, db_session, org):
        saas_service.seed_feature_flags(db_session)
        features = saas_service.get_org_features(db_session, org.id)
        assert isinstance(features, dict)
        assert "api_scanning" in features

    def test_set_override_invalid_flag(self, db_session, org):
        with pytest.raises(ValueError, match="not found"):
            saas_service.set_org_feature_override(
                db_session, organization_id=org.id, feature_key="nonexistent", is_enabled=True
            )

    def test_seed_feature_flags(self, db_session):
        created = saas_service.seed_feature_flags(db_session)
        assert len(created) >= 10


# ── License Tests ─────────────────────────────────────────────────────


class TestLicenseManagement:
    """Test license creation, validation, and activation."""

    def test_create_license(self, db_session):
        lic = saas_service.create_license(
            db_session,
            license_type="trial",
            expires_in_days=14,
            max_uses=1,
        )
        assert lic.license_key.startswith("sai-")
        assert lic.status == "active"

    def test_validate_license(self, db_session):
        lic = saas_service.create_license(db_session, license_type="enterprise", expires_in_days=30)
        validated = saas_service.validate_license(db_session, lic.license_key)
        assert validated is not None
        assert validated.status == "active"

    def test_validate_expired_license(self, db_session):
        lic = saas_service.create_license(db_session, license_type="trial", expires_in_days=0)
        # Manually expire
        lic.expires_at = datetime.now(UTC) - timedelta(days=1)
        db_session.commit()
        validated = saas_service.validate_license(db_session, lic.license_key)
        assert validated is None

    def test_activate_license(self, db_session, org):
        lic = saas_service.create_license(db_session, license_type="enterprise", expires_in_days=30)
        activated = saas_service.activate_license(
            db_session, license_key=lic.license_key, organization_id=org.id
        )
        assert activated is not None
        assert activated.organization_id == org.id
        assert activated.current_uses == 1

    def test_validate_nonexistent_license(self, db_session):
        result = saas_service.validate_license(db_session, "sai-invalid")
        assert result is None


# ── Onboarding Tests ──────────────────────────────────────────────────


class TestOnboardingWizard:
    """Test onboarding step progression and completion."""

    def test_get_onboarding_creates_default(self, db_session, user):
        progress = saas_service.get_onboarding_progress(db_session, user.id)
        assert progress.current_step == "welcome"
        assert progress.completed_steps == []
        assert progress.is_complete is False

    def test_complete_step(self, db_session, user):
        progress = saas_service.complete_onboarding_step(
            db_session, user_id=user.id, step="welcome"
        )
        assert "welcome" in progress.completed_steps
        assert progress.current_step == "profile"

    def test_complete_all_steps(self, db_session, user):
        for step in [
            "welcome",
            "profile",
            "first_project",
            "first_scan",
            "invite_team",
            "completed",
        ]:
            progress = saas_service.complete_onboarding_step(db_session, user_id=user.id, step=step)
        assert progress.is_complete is True
        assert progress.current_step == "completed"

    def test_invalid_step_raises(self, db_session, user):
        with pytest.raises(ValueError, match="Invalid onboarding step"):
            saas_service.complete_onboarding_step(db_session, user_id=user.id, step="nonexistent")

    def test_onboarding_with_role(self, db_session, user):
        progress = saas_service.complete_onboarding_step(
            db_session, user_id=user.id, step="welcome", role="security_engineer"
        )
        assert progress.role == "security_engineer"

    def test_onboarding_with_use_case(self, db_session, user):
        progress = saas_service.complete_onboarding_step(
            db_session, user_id=user.id, step="welcome", use_case="api_security"
        )
        assert progress.use_case == "api_security"


# ── Email Template Tests ──────────────────────────────────────────────


class TestEmailTemplates:
    """Test email template rendering and variable substitution."""

    def test_render_template(self, db_session):
        saas_service.seed_email_templates(db_session)
        tpl = saas_service.get_email_template(db_session, "welcome")
        assert tpl is not None

        rendered = saas_service.render_email_template(
            tpl, {"user_name": "Alice", "org_name": "Acme Corp"}
        )
        assert "Alice" in rendered["subject"]
        assert "Acme Corp" in rendered["body_html"]

    def test_template_not_found(self, db_session):
        tpl = saas_service.get_email_template(db_session, "nonexistent")
        assert tpl is None

    def test_seed_templates(self, db_session):
        created = saas_service.seed_email_templates(db_session)
        assert len(created) == 4

    def test_seed_templates_idempotent(self, db_session):
        saas_service.seed_email_templates(db_session)
        second = saas_service.seed_email_templates(db_session)
        assert len(second) == 0


# ── Notification Preference Tests ─────────────────────────────────────


class TestNotificationPreferences:
    """Test notification preference management."""

    def test_set_preference(self, db_session, user):
        pref = saas_service.set_notification_preference(
            db_session,
            user_id=user.id,
            notification_type="scan_completed",
            email_enabled=True,
            in_app_enabled=True,
            frequency="daily_digest",
        )
        assert pref.email_enabled is True
        assert pref.frequency == "daily_digest"

    def test_update_preference(self, db_session, user):
        saas_service.set_notification_preference(
            db_session,
            user_id=user.id,
            notification_type="scan_completed",
            email_enabled=True,
        )
        updated = saas_service.set_notification_preference(
            db_session,
            user_id=user.id,
            notification_type="scan_completed",
            email_enabled=False,
        )
        assert updated.email_enabled is False

    def test_get_preferences(self, db_session, user):
        saas_service.set_notification_preference(
            db_session,
            user_id=user.id,
            notification_type="scan_completed",
        )
        prefs = saas_service.get_notification_preferences(db_session, user.id)
        assert len(prefs) == 1


# ── Branding Tests ────────────────────────────────────────────────────


class TestCustomBranding:
    """Test white-label branding configuration."""

    def test_upsert_branding(self, db_session, org):
        branding = saas_service.upsert_branding(
            db_session,
            organization_id=org.id,
            org_display_name="Acme Security",
            primary_color="#FF0000",
            is_enabled=True,
        )
        assert branding.org_display_name == "Acme Security"
        assert branding.primary_color == "#FF0000"
        assert branding.is_enabled is True

    def test_update_branding(self, db_session, org):
        saas_service.upsert_branding(db_session, organization_id=org.id, primary_color="#0000FF")
        updated = saas_service.upsert_branding(
            db_session, organization_id=org.id, primary_color="#00FF00"
        )
        assert updated.primary_color == "#00FF00"

    def test_get_branding(self, db_session, org):
        saas_service.upsert_branding(db_session, organization_id=org.id, is_enabled=True)
        branding = saas_service.get_branding(db_session, org.id)
        assert branding is not None
        assert branding.is_enabled is True

    def test_get_branding_none(self, db_session, org):
        branding = saas_service.get_branding(db_session, org.id)
        assert branding is None

    def test_verify_custom_domain(self, db_session, org):
        saas_service.upsert_branding(
            db_session,
            organization_id=org.id,
            custom_domain="security.acme.com",
            domain_verification_token="verify-token-123",
        )
        result = saas_service.verify_custom_domain(db_session, org.id, "verify-token-123")
        assert result is True
        updated = saas_service.get_branding(db_session, org.id)
        assert updated.domain_verified is True

    def test_verify_wrong_token(self, db_session, org):
        saas_service.upsert_branding(
            db_session,
            organization_id=org.id,
            domain_verification_token="correct-token",
        )
        result = saas_service.verify_custom_domain(db_session, org.id, "wrong-token")
        assert result is False


# ── Feedback Tests ────────────────────────────────────────────────────


class TestFeedback:
    """Test feedback submission, listing, and triage."""

    def test_submit_feedback(self, db_session, user):
        fb = saas_service.submit_feedback(
            db_session,
            user_id=user.id,
            organization_id=None,
            category="bug",
            title="Login broken",
            description="Login fails with 500 error",
            severity="high",
        )
        assert fb.category == "bug"
        assert fb.status == "open"

    def test_list_feedback(self, db_session, user):
        saas_service.submit_feedback(
            db_session,
            user_id=user.id,
            organization_id=None,
            category="feature_request",
            title="Want dark mode",
            description="Please add dark mode",
        )
        items = saas_service.get_feedback_list(db_session)
        assert len(items) == 1

    def test_triage_feedback(self, db_session, user):
        fb = saas_service.submit_feedback(
            db_session,
            user_id=user.id,
            organization_id=None,
            category="bug",
            title="Bug",
            description="Something broke",
        )
        triaged = saas_service.triage_feedback(
            db_session, feedback_id=fb.id, status="resolved", admin_notes="Fixed in v1.1"
        )
        assert triaged.status == "resolved"
        assert triaged.resolved_at is not None

    def test_triage_not_found(self, db_session):
        result = saas_service.triage_feedback(db_session, feedback_id=999, status="resolved")
        assert result is None

    def test_list_with_filters(self, db_session, user):
        saas_service.submit_feedback(
            db_session,
            user_id=user.id,
            organization_id=None,
            category="bug",
            title="Bug 1",
            description="desc",
        )
        saas_service.submit_feedback(
            db_session,
            user_id=user.id,
            organization_id=None,
            category="praise",
            title="Great!",
            description="Love it",
        )
        bugs = saas_service.get_feedback_list(db_session, category="bug")
        assert len(bugs) == 1


# ── Analytics Tests ───────────────────────────────────────────────────


class TestProductAnalytics:
    """Test analytics event tracking and aggregation."""

    def test_track_event(self, db_session, user):
        event = saas_service.track_event(
            db_session,
            event_name="scan_started",
            event_type="product",
            user_id=user.id,
            properties={"scan_type": "api"},
        )
        assert event.event_name == "scan_started"
        assert event.properties["scan_type"] == "api"

    def test_analytics_summary(self, db_session, user, org):
        for _ in range(3):
            saas_service.track_event(
                db_session,
                event_name="scan_completed",
                event_type="product",
                user_id=user.id,
                organization_id=org.id,
            )
        summary = saas_service.get_analytics_summary(db_session, organization_id=org.id)
        assert summary["total_events"] == 3
        assert "scan_completed" in summary["event_counts"]


# ── Dashboard Tests ───────────────────────────────────────────────────


class TestSAASDashboard:
    """Test SaaS dashboard aggregation."""

    def test_dashboard(self, db_session, user, org):
        from app.models.models import OrganizationMember

        member = OrganizationMember(organization_id=org.id, user_id=user.id, role="owner")
        db_session.add(member)
        db_session.commit()

        saas_service.seed_default_plans(db_session)
        dashboard = saas_service.get_saa_dashboard(db_session, org.id)
        assert "plan" in dashboard
        assert "subscription" in dashboard
        assert "usage" in dashboard
        assert "features" in dashboard


# ── Quota Enforcement Tests ───────────────────────────────────────────


class TestQuotaEnforcement:
    """Test quota enforcement across all metrics."""

    def test_enforce_quotas(self, db_session, org):
        saas_service.seed_default_plans(db_session)
        results = saas_service.enforce_quotas(db_session, org.id)
        assert "scans" in results
        assert "ai_requests" in results
        assert results["scans"]["allowed"] is True  # 0 < 10

    def test_enforce_quotas_exhausted(self, db_session, org):
        saas_service.seed_default_plans(db_session)
        for _ in range(10):
            saas_service.record_usage(db_session, organization_id=org.id, metric="scan")
        results = saas_service.enforce_quotas(db_session, org.id)
        assert results["scans"]["exhausted"] is True
