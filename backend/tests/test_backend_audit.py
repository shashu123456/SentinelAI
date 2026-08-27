"""Backend engineering audit tests.

Covers:
- Config validation (production readiness warnings)
- Enterprise service generic CRUD helpers
- Audit service risk classification
- Risk engine assessment
- Security utilities
- RBAC hierarchy
- Base repository patterns
- Cache utility
"""

import pytest


# ── Config Validation Tests ──────────────────────────────────────────────


class TestConfigValidation:
    """Verify production readiness validation catches unsafe defaults."""

    def test_default_secret_key_warns(self):
        from app.config import Settings

        s = Settings()
        warnings = s.validate_production_readiness()
        assert any("SECRET_KEY" in w for w in warnings)

    def test_custom_secret_key_no_warning(self):
        from app.config import Settings

        s = Settings(SECRET_KEY="a-secure-random-key-12345")
        warnings = s.validate_production_readiness()
        assert not any("SECRET_KEY" in w for w in warnings)

    def test_cors_allow_all_warns(self):
        from app.config import Settings

        s = Settings(CORS_ALLOW_ALL=True)
        warnings = s.validate_production_readiness()
        assert any("CORS_ALLOW_ALL" in w for w in warnings)

    def test_insecure_refresh_cookie_warns(self):
        from app.config import Settings

        s = Settings(REFRESH_TOKEN_COOKIE_SECURE=False)
        warnings = s.validate_production_readiness()
        assert any("REFRESH_TOKEN_COOKIE_SECURE" in w for w in warnings)

    def test_production_sqlite_warns(self):
        from app.config import Settings

        s = Settings(SENTINEL_ENV="production", DATABASE_URL="sqlite:///./prod.db")
        warnings = s.validate_production_readiness()
        assert any("SQLite" in w for w in warnings)

    def test_validate_secret_key_method(self):
        from app.config import Settings

        assert Settings().validate_secret_key() is False
        assert Settings(SECRET_KEY="custom-key").validate_secret_key() is True


# ── Enterprise Service CRUD Tests ─────────────────────────────────────────


class TestEnterpriseCRUD:
    """Test the generic CRUD helpers for enterprise services."""

    def test_list_scheduled_scans_empty(self, db_session):
        from app.services.enterprise_service import list_scheduled_scans

        items, total = list_scheduled_scans(db_session, 99999)
        assert isinstance(items, list)
        assert total == 0

    def test_list_templates_empty(self, db_session):
        from app.services.enterprise_service import list_templates

        items, total = list_templates(db_session, 99999)
        assert isinstance(items, list)
        assert total == 0

    def test_list_policies_empty(self, db_session):
        from app.services.enterprise_service import list_policies

        items, total = list_policies(db_session, 99999)
        assert isinstance(items, list)
        assert total == 0

    def test_list_webhooks_empty(self, db_session):
        from app.services.enterprise_service import list_webhooks

        items, total = list_webhooks(db_session, 99999)
        assert isinstance(items, list)
        assert total == 0

    def test_list_export_jobs_empty(self, db_session):
        from app.services.enterprise_service import list_export_jobs

        items, total = list_export_jobs(db_session, 99999)
        assert isinstance(items, list)
        assert total == 0

    def test_list_frameworks(self, db_session):
        from app.services.enterprise_service import list_frameworks

        fws = list_frameworks(db_session)
        assert isinstance(fws, list)

    def test_compare_scans_returns_none_for_missing(self, db_session):
        from app.services.enterprise_service import compare_scans

        result = compare_scans(db_session, 99998, 99999)
        assert result is None

    def test_generate_sarif_empty(self, db_session):
        from app.services.enterprise_service import generate_sarif_export

        sarif = generate_sarif_export(db_session, [])
        assert sarif["version"] == "2.1.0"
        assert sarif["runs"] == []

    def test_get_framework_detail_missing(self, db_session):
        from app.services.enterprise_service import get_framework_detail

        result = get_framework_detail(db_session, "nonexistent-slug", 99999)
        assert result is None


# ── Audit Service Tests ──────────────────────────────────────────────────


class TestAuditService:
    """Test audit risk classification and module extraction."""

    def test_high_risk_actions(self):
        from app.services.audit_service import _classify_risk

        assert _classify_risk("auth.login_failed") == "high"
        assert _classify_risk("auth.account_locked") == "high"
        assert _classify_risk("user.deleted") == "high"
        assert _classify_risk("scan.deleted") == "high"
        assert _classify_risk("api_key.created") == "high"

    def test_medium_risk_actions(self):
        from app.services.audit_service import _classify_risk

        assert _classify_risk("auth.register") == "medium"
        assert _classify_risk("auth.login") == "medium"
        assert _classify_risk("scan.completed") == "medium"

    def test_heuristic_delete_is_high(self):
        from app.services.audit_service import _classify_risk

        assert _classify_risk("org.remove_member") == "high"
        assert _classify_risk("settings.revoke_token") == "high"

    def test_info_risk_default(self):
        from app.services.audit_service import _classify_risk

        assert _classify_risk("system.health_check") == "info"

    def test_extract_module(self):
        from app.services.audit_service import _extract_module

        assert _extract_module("auth.login") == "authentication"
        assert _extract_module("scan.completed") == "scanning"
        assert _extract_module("user.created") == "user_management"
        assert _extract_module("copilot.chat") == "ai_copilot"
        assert _extract_module("unknown.action") == "unknown"

    def test_record_action_creates_audit_log(self, db_session):
        from app.services.audit_service import record_action
        from app.repositories.audit import AuditLogRepository

        record_action(
            db_session,
            "test.action",
            user_id=1,
            username="tester",
            resource="test resource",
            ip_address="127.0.0.1",
        )
        db_session.commit()

        repo = AuditLogRepository(db_session)
        logs = repo.list(limit=10)
        matching = [l for l in logs if l.action == "test.action"]
        assert len(matching) == 1
        assert matching[0].risk_level == "info"
        assert matching[0].module == "test"


# ── Risk Engine Tests ─────────────────────────────────────────────────────


class TestRiskEngine:
    """Test risk assessment computation."""

    def test_empty_findings(self):
        from app.services.risk_engine import compute_risk_assessment

        assessment = compute_risk_assessment([])
        assert assessment.risk_score == 0
        assert assessment.risk_level == "Clean"
        assert assessment.security_grade == "A"
        assert assessment.priority == "P4"

    def test_critical_findings(self):
        from app.services.risk_engine import compute_risk_assessment

        findings = [
            {"severity": "Critical", "cwe_id": "CWE-89", "owasp_category": "A03", "confidence": 95, "cvss_score": 9.8},
            {"severity": "Critical", "cwe_id": "CWE-78", "owasp_category": "A03", "confidence": 90, "cvss_score": 9.0},
        ]
        assessment = compute_risk_assessment(findings)
        assert assessment.priority == "P1"
        assert assessment.total_findings == 2
        assert len(assessment.top_cwes) > 0
        assert assessment.risk_level in ("Critical", "High")

    def test_mixed_findings(self):
        from app.services.risk_engine import compute_risk_assessment

        findings = [
            {"severity": "High", "cwe_id": "CWE-79", "owasp_category": "A07", "confidence": 85},
            {"severity": "Medium", "cwe_id": "CWE-20", "owasp_category": "A05", "confidence": 80},
            {"severity": "Low", "cwe_id": None, "owasp_category": "A09", "confidence": 70},
        ]
        assessment = compute_risk_assessment(findings)
        assert assessment.total_findings == 3
        assert assessment.priority in ("P1", "P2", "P3")
        assert len(assessment.recommendations) > 0

    def test_recommendations_cap(self):
        from app.services.risk_engine import compute_risk_assessment

        findings = [
            {"severity": "Critical", "cwe_id": f"CWE-{i}", "owasp_category": f"A{i:02d}"}
            for i in range(20)
        ]
        assessment = compute_risk_assessment(findings)
        assert len(assessment.recommendations) <= 8

    def test_severity_breakdown(self):
        from app.services.risk_engine import compute_risk_assessment

        findings = [
            {"severity": "Critical", "owasp_category": "A03"},
            {"severity": "High", "owasp_category": "A07"},
            {"severity": "Medium", "owasp_category": "A05"},
            {"severity": "Low", "owasp_category": "A09"},
            {"severity": "Info", "owasp_category": "A01"},
        ]
        assessment = compute_risk_assessment(findings)
        assert assessment.severity_breakdown == {
            "Critical": 1,
            "High": 1,
            "Medium": 1,
            "Low": 1,
            "Info": 1,
        }

    def test_confidence_adjusts_score(self):
        from app.services.risk_engine import compute_risk_assessment

        high_conf = [{"severity": "High", "owasp_category": "A03", "confidence": 95}]
        low_conf = [{"severity": "High", "owasp_category": "A03", "confidence": 30}]
        a_high = compute_risk_assessment(high_conf)
        a_low = compute_risk_assessment(low_conf)
        assert a_high.risk_score >= a_low.risk_score


# ── Security Module Tests ─────────────────────────────────────────────────


class TestSecurityModule:
    """Test security utility functions."""

    def test_password_hash_and_verify(self):
        from app.utils.security import hash_password, verify_password

        hashed = hash_password("TestPassword123!")
        assert verify_password("TestPassword123!", hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_utcnow_returns_naive(self):
        from app.utils.security import utcnow

        now = utcnow()
        assert now.tzinfo is None

    def test_hash_token_deterministic(self):
        from app.utils.security import hash_token

        h1 = hash_token("test-token")
        h2 = hash_token("test-token")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_hash_token_unique_per_input(self):
        from app.utils.security import hash_token

        h1 = hash_token("token-a")
        h2 = hash_token("token-b")
        assert h1 != h2

    def test_dummy_hash_is_consistent(self):
        from app.utils.security import DUMMY_HASH, pwd_context

        assert pwd_context.verify("sentinelai-timing-equalizer", DUMMY_HASH)


# ── RBAC Tests ────────────────────────────────────────────────────────────


class TestRBAC:
    """Test role hierarchy and level comparisons."""

    def test_org_role_levels(self):
        from app.utils.rbac import ORG_ROLE_LEVELS

        assert ORG_ROLE_LEVELS["owner"] > ORG_ROLE_LEVELS["admin"]
        assert ORG_ROLE_LEVELS["admin"] > ORG_ROLE_LEVELS["security_engineer"]
        assert ORG_ROLE_LEVELS["security_engineer"] > ORG_ROLE_LEVELS["developer"]
        assert ORG_ROLE_LEVELS["developer"] > ORG_ROLE_LEVELS["viewer"]

    def test_project_role_levels(self):
        from app.utils.rbac import PROJECT_ROLE_LEVELS

        assert PROJECT_ROLE_LEVELS["admin"] > PROJECT_ROLE_LEVELS["developer"]

    def test_team_role_levels(self):
        from app.utils.rbac import TEAM_ROLE_LEVELS

        assert TEAM_ROLE_LEVELS["admin"] > TEAM_ROLE_LEVELS["member"]


# ── Base Repository Tests ─────────────────────────────────────────────────


class TestBaseRepository:
    """Test base repository CRUD and pagination."""

    def test_get_returns_none_for_missing(self, db_session):
        from app.repositories.scans import ScanRepository

        repo = ScanRepository(db_session)
        assert repo.get(99999) is None

    def test_count_empty(self, db_session):
        from app.repositories.scans import ScanRepository
        from app.models.models import Scan

        repo = ScanRepository(db_session)
        count = repo.count(Scan.user_id == 99999)
        assert count == 0

    def test_paginate_empty(self, db_session):
        from app.repositories.scans import ScanRepository
        from app.models.models import Scan

        repo = ScanRepository(db_session)
        items, total = repo.paginate(Scan.user_id == 99999)
        assert items == []
        assert total == 0

    def test_paginate_respects_limits(self, db_session):
        from app.repositories.scans import ScanRepository
        from app.models.models import Scan

        repo = ScanRepository(db_session)
        # page_size should be clamped to [1, 100]
        items, total = repo.paginate(page=1, page_size=500)
        assert isinstance(items, list)


# ── Cache Utility Tests ───────────────────────────────────────────────────


class TestCache:
    """Test the in-memory cache utility."""

    def test_set_and_get(self):
        from app.utils.cache import cache

        cache.set("test_audit_key", {"foo": "bar"}, ttl=60)
        result = cache.get("test_audit_key")
        assert result == {"foo": "bar"}

    def test_get_missing_key(self):
        from app.utils.cache import cache

        result = cache.get("nonexistent_key_xyz_123_audit")
        assert result is None

    def test_invalidate_prefix(self):
        from app.utils.cache import cache

        cache.set("audit_dash:1:data", "value1", ttl=60)
        cache.set("audit_dash:1:other", "value2", ttl=60)
        cache.invalidate_prefix("audit_dash:1:")
        assert cache.get("audit_dash:1:data") is None
        assert cache.get("audit_dash:1:other") is None
