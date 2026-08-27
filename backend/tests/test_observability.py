"""Tests for Phase 11 — Enterprise Monitoring & Observability.

Covers:
    - Health endpoints (/api/v1/health, /ready, /live)
    - System metrics collector
    - Structured logger context binding
    - Task queue stats
"""

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import Base, get_db
from app.utils.system_metrics import (
    get_cpu_info,
    get_memory_info,
    get_disk_info,
    get_db_latency,
    get_redis_status,
    get_ai_status,
    get_uptime,
    get_uptime_human,
    get_environment_info,
    collect_all_health,
)
from app.utils.logger import (
    bind_request_context,
    clear_request_context,
    bind_scan_context,
    _request_id_ctx,
    _user_id_ctx,
    _scan_id_ctx,
)
from app.tasks import get_task_stats


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture()
def client(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    url = f"sqlite:///{tmp_path / 'test_obs.db'}"
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
    import app.database.database as db_mod
    orig = db_mod.SessionLocal
    db_mod.SessionLocal = TestSession

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    db_mod.SessionLocal = orig
    engine.dispose()


# ── Health Endpoints ──────────────────────────────────────────────


def _unwrap(resp):
    """Extract data from the envelope middleware response."""
    body = resp.json()
    if isinstance(body, dict) and "data" in body and body.get("success"):
        return body["data"]
    return body


class TestHealthEndpoints:
    def test_liveness_returns_200(self, client):
        resp = client.get("/api/v1/live")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["status"] == "alive"
        assert "uptime_seconds" in data

    def test_readiness_returns_200(self, client):
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["status"] == "ready"

    def test_full_health_returns_valid_structure(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code in (200, 207, 503)
        data = _unwrap(resp)
        assert "status" in data
        assert "version" in data
        assert "checks" in data
        assert "details" in data
        assert "uptime_seconds" in data
        assert "uptime_human" in data

    def test_full_health_contains_all_checks(self, client):
        resp = client.get("/api/v1/health")
        data = _unwrap(resp)
        checks = data["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert "ai_engine" in checks
        assert "workers" in checks

    def test_full_health_contains_system_metrics(self, client):
        resp = client.get("/api/v1/health")
        data = _unwrap(resp)
        details = data["details"]
        assert "cpu" in details
        assert "memory" in details
        assert "disk" in details
        assert "database" in details
        assert "environment" in details

    def test_legacy_health_still_works(self, client):
        resp = client.get("/health/detailed")
        assert resp.status_code == 200


# ── System Metrics ────────────────────────────────────────────────


class TestSystemMetrics:
    def test_cpu_info(self):
        info = get_cpu_info()
        assert "usage_percent" in info
        assert "cores" in info
        assert isinstance(info["cores"], int)
        assert info["cores"] >= 1

    def test_memory_info(self):
        info = get_memory_info()
        assert "process_rss_mb" in info
        assert info["process_rss_mb"] is not None
        assert info["process_rss_mb"] > 0

    def test_disk_info(self):
        info = get_disk_info()
        assert "total_gb" in info

    def test_db_latency(self):
        info = get_db_latency()
        assert info["status"] in ("healthy", "unhealthy")
        if info["status"] == "healthy":
            assert info["latency_ms"] >= 0

    def test_redis_status(self):
        info = get_redis_status()
        assert "status" in info
        # In test env, Redis is not configured
        assert info["status"] in ("not_configured", "healthy", "unhealthy", "not_installed")

    def test_ai_status(self):
        info = get_ai_status()
        assert "status" in info
        assert "model" in info

    def test_uptime(self):
        uptime = get_uptime()
        assert uptime >= 0
        assert isinstance(uptime, float)

    def test_uptime_human(self):
        human = get_uptime_human()
        assert isinstance(human, str)
        assert "m" in human

    def test_environment_info(self):
        info = get_environment_info()
        assert "python_version" in info
        assert "platform" in info
        assert "pid" in info
        assert "sentinel_version" in info

    def test_collect_all_health(self):
        health = collect_all_health()
        assert health["status"] in ("healthy", "degraded", "unhealthy")
        assert "checks" in health
        assert "details" in health
        assert "uptime_seconds" in health


# ── Structured Logger Context ─────────────────────────────────────


class TestStructuredLogger:
    def test_bind_request_context(self):
        bind_request_context(
            request_id="test-req-123",
            user_id=42,
            username="testuser",
            path="/api/test",
            method="GET",
        )
        assert _request_id_ctx.get() == "test-req-123"
        assert _user_id_ctx.get() == 42
        assert _scan_id_ctx.get() is None
        clear_request_context()

    def test_bind_scan_context(self):
        bind_scan_context(scan_id=99)
        assert _scan_id_ctx.get() == 99
        clear_request_context()

    def test_clear_request_context(self):
        bind_request_context(request_id="abc", user_id=1)
        clear_request_context()
        assert _request_id_ctx.get() == "-"
        assert _user_id_ctx.get() is None


# ── Task Queue Stats ──────────────────────────────────────────────


class TestTaskStats:
    def test_get_task_stats(self):
        stats = get_task_stats()
        assert "active" in stats
        assert "queued" in stats
        assert "completed" in stats
        assert "failed" in stats
        assert "total" in stats
        assert isinstance(stats["active"], int)
