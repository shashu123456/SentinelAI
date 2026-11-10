"""Tests for the enterprise audit logging system.

Covers:
    - Audit service risk classification
    - Audit service module extraction
    - Audit API pagination and filtering
    - Audit API RBAC (viewer vs admin)
    - Audit log creation with all fields
    - CSV export
"""

import pytest
from fastapi.testclient import TestClient

from app.database.database import Base, get_db
from app.main import app
from app.models.models import User
from app.services.audit_service import (
    _classify_risk,
    _extract_module,
    record_action,
)

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture()
def client(tmp_path):
    """Create a test client with a fresh database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    url = f"sqlite:///{tmp_path / 'test_audit.db'}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    def override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override

    # Also patch SessionLocal so direct imports use the test DB
    import app.database.database as db_mod

    original_session_factory = db_mod.SessionLocal
    db_mod.SessionLocal = TestSession

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    db_mod.SessionLocal = original_session_factory
    engine.dispose()


@pytest.fixture()
def admin_user(client):
    """Register an admin user and return (user_data, auth_headers)."""
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "audit_admin",
            "email": "admin@sentinelai.example.com",
            "password": "Admin123!@#",
        },
    )
    if resp.status_code != 201:
        print(f"REGISTER FAILED: {resp.status_code} {resp.json()}")
    assert resp.status_code == 201
    user_data = resp.json()["user"]

    # Promote to admin
    from app.database.database import SessionLocal

    db = SessionLocal()
    user = db.query(User).filter(User.id == user_data["id"]).first()
    user.role = "admin"
    db.commit()
    db.close()

    token = resp.json()["access_token"]
    return user_data, {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def regular_user(client):
    """Register a regular user and return (user_data, auth_headers)."""
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "audit_viewer",
            "email": "viewer@sentinelai.example.com",
            "password": "Viewer123!@#",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return resp.json()["user"], {"Authorization": f"Bearer {token}"}


# ── Risk classification tests ─────────────────────────────────────


class TestRiskClassification:
    def test_high_risk_actions(self):
        assert _classify_risk("auth.login_failed") == "high"
        assert _classify_risk("auth.password_reset") == "high"
        assert _classify_risk("auth.account_locked") == "high"
        assert _classify_risk("scan.deleted") == "high"
        assert _classify_risk("org.member_removed") == "high"
        assert _classify_risk("user.role_changed") == "high"

    def test_medium_risk_actions(self):
        assert _classify_risk("auth.login") == "medium"
        assert _classify_risk("auth.register") == "medium"
        assert _classify_risk("scan.completed") == "medium"
        assert _classify_risk("org.member_added") == "medium"

    def test_info_risk_actions(self):
        assert _classify_risk("auth.logout") == "info"
        assert _classify_risk("copilot.chat") == "medium"

    def test_heuristic_delete_is_high(self):
        assert _classify_risk("scan.delete") == "high"
        assert _classify_risk("custom.resource_deleted") == "high"

    def test_heuristic_unknown_is_info(self):
        assert _classify_risk("custom.unknown_action") == "info"


# ── Module extraction tests ───────────────────────────────────────


class TestModuleExtraction:
    def test_known_modules(self):
        assert _extract_module("auth.login") == "authentication"
        assert _extract_module("scan.completed") == "scanning"
        assert _extract_module("org.created") == "organization"
        assert _extract_module("report.exported.pdf") == "reporting"
        assert _extract_module("user.role_changed") == "user_management"
        assert _extract_module("copilot.chat") == "ai_copilot"

    def test_unknown_module(self):
        assert _extract_module("foo.bar") == "foo"


# ── Audit log creation tests ──────────────────────────────────────


class TestAuditLogCreation:
    def test_create_with_all_fields(self, client, admin_user):
        user_data, headers = admin_user
        from app.database.database import SessionLocal

        db = SessionLocal()

        record_action(
            db,
            "test.full_event",
            user_id=user_data["id"],
            username=user_data["username"],
            entity_type="test",
            entity_id=42,
            resource="test resource",
            old_value={"key": "old"},
            new_value={"key": "new"},
            detail={"extra": "data"},
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            request_id="req-123",
            status="success",
            risk_level="high",
        )
        db.commit()
        db.close()

        # Fetch via API
        resp = client.get("/api/audit/logs?page_size=1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = data["items"][0]
        assert item["action"] == "test.full_event"
        assert item["username"] == user_data["username"]
        assert item["entity_type"] == "test"
        assert item["entity_id"] == 42
        assert item["resource"] == "test resource"
        assert item["old_value"] == {"key": "old"}
        assert item["new_value"] == {"key": "new"}
        assert item["ip_address"] == "127.0.0.1"
        assert item["user_agent"] == "TestAgent/1.0"
        assert item["request_id"] == "req-123"
        assert item["risk_level"] == "high"
        assert item["status"] == "success"

    def test_auto_risk_classification(self, client, admin_user):
        user_data, headers = admin_user
        from app.database.database import SessionLocal

        db = SessionLocal()

        record_action(db, "auth.login_failed", user_id=user_data["id"])
        db.commit()
        db.close()

        resp = client.get("/api/audit/logs?page_size=1", headers=headers)
        item = resp.json()["items"][0]
        assert item["risk_level"] == "high"
        assert item["module"] == "authentication"


# ── Pagination and filtering tests ────────────────────────────────


class TestAuditFiltering:
    @pytest.fixture(autouse=True)
    def seed_events(self, client, admin_user):
        """Create several audit events for filtering tests."""
        user_data, _ = admin_user
        from app.database.database import SessionLocal

        db = SessionLocal()

        actions = [
            ("auth.login", "authentication", "medium"),
            ("auth.login_failed", "authentication", "high"),
            ("auth.logout", "authentication", "info"),
            ("scan.completed", "scanning", "medium"),
            ("scan.failed", "scanning", "high"),
            ("org.created", "organization", "medium"),
        ]
        for action, _mod, _risk in actions:
            record_action(db, action, user_id=user_data["id"], username=user_data["username"])
        db.commit()
        db.close()

    def test_list_all(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/logs", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 6

    def test_filter_by_module(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/logs?module=authentication", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["module"] == "authentication" for item in items)

    def test_filter_by_risk_level(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/logs?risk_level=high", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["risk_level"] == "high" for item in items)

    def test_filter_by_action_prefix(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/logs?action_prefix=auth", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["action"].startswith("auth") for item in items)

    def test_search(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/logs?search=logout", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any("logout" in item["action"] for item in items)

    def test_pagination(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/logs?page=1&page_size=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] >= 3

    def test_single_event_detail(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/logs", headers=headers)
        event_id = resp.json()["items"][0]["id"]

        detail_resp = client.get(f"/api/audit/logs/{event_id}", headers=headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == event_id

    def test_nonexistent_event_returns_404(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/logs/999999", headers=headers)
        assert resp.status_code == 404


# ── RBAC tests ────────────────────────────────────────────────────


class TestAuditRBAC:
    def test_regular_user_can_list_logs(self, client, regular_user):
        _, headers = regular_user
        resp = client.get("/api/audit/logs", headers=headers)
        assert resp.status_code == 200

    def test_regular_user_can_get_event_detail(self, client, regular_user, admin_user):
        _, admin_headers = admin_user
        viewer_headers = regular_user[1]

        # Create an event as admin
        resp = client.get("/api/audit/logs", headers=admin_headers)
        event_id = resp.json()["items"][0]["id"]

        # Viewer can read it
        resp = client.get(f"/api/audit/logs/{event_id}", headers=viewer_headers)
        assert resp.status_code == 200

    def test_regular_user_cannot_access_stats(self, client, regular_user):
        _, headers = regular_user
        resp = client.get("/api/audit/stats", headers=headers)
        assert resp.status_code == 403

    def test_admin_can_access_stats(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "by_module" in data
        assert "by_risk_level" in data

    def test_regular_user_cannot_export(self, client, regular_user):
        _, headers = regular_user
        resp = client.get("/api/audit/export", headers=headers)
        assert resp.status_code == 403

    def test_admin_can_export(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/export", headers=headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_unauthenticated_cannot_access(self, client):
        resp = client.get("/api/audit/logs")
        assert resp.status_code in (401, 403)


# ── Module and action listing ─────────────────────────────────────


class TestAuditMetadata:
    def test_list_modules(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/modules", headers=headers)
        assert resp.status_code == 200
        modules = resp.json()
        assert isinstance(modules, list)

    def test_list_actions(self, client, admin_user):
        _, headers = admin_user
        resp = client.get("/api/audit/actions", headers=headers)
        assert resp.status_code == 200
        actions = resp.json()
        assert isinstance(actions, list)
