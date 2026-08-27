"""Soft-delete behavior across the API and copilot tools."""

import json
import uuid

from app.core.copilot import tools as copilot_tools
from app.database.database import SessionLocal
from app.models.models import Scan

SAMPLE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "SoftDelete API", "version": "1.0"},
    "paths": {"/health": {"get": {"responses": {"200": {"description": "ok"}}}}},
}


def _upload(client, headers, name="SoftDelete API"):
    resp = client.post(
        "/api/scans/upload",
        headers=headers,
        files={"file": ("spec.json", json.dumps(SAMPLE_SPEC), "application/json")},
        data={"api_name": name},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _register_second_user(client, prefix):
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestSoftDelete:
    def test_delete_hides_scan_everywhere(self, client, auth_headers):
        scan = _upload(client, auth_headers)
        scan_id = scan["id"]

        assert len(client.get("/api/scans/", headers=auth_headers).json()) == 1

        resp = client.delete(f"/api/scans/{scan_id}", headers=auth_headers)
        assert resp.status_code == 204

        # list excludes it
        assert client.get("/api/scans/", headers=auth_headers).json() == []

        # detail 404s
        assert client.get(f"/api/scans/{scan_id}", headers=auth_headers).status_code == 404

        # dashboard counts drop
        dash = client.get("/api/scans/dashboard", headers=auth_headers).json()
        assert dash["total_scans"] == 0
        assert dash["recent_scans"] == []

        # row is still present, soft-deleted (history preserved)
        db = SessionLocal()
        try:
            row = db.get(Scan, scan_id)
            assert row is not None
            assert row.deleted_at is not None
            user_id = row.user_id

            # copilot tools exclude it
            assert copilot_tools.get_latest_scan(db, user_id) is None
            assert copilot_tools.get_scan_history(db, user_id) == []
            assert copilot_tools.get_all_findings(db, user_id) == []
        finally:
            db.close()

    def test_delete_other_users_scan_is_404(self, client, auth_headers):
        scan = _upload(client, auth_headers)
        scan_id = scan["id"]
        other_headers = _register_second_user(client, "intruder")

        assert client.delete(f"/api/scans/{scan_id}", headers=other_headers).status_code == 404
        assert client.get(f"/api/scans/{scan_id}", headers=other_headers).status_code == 404

    def test_reports_unreachable_after_delete(self, client, auth_headers):
        scan = _upload(client, auth_headers)
        scan_id = scan["id"]

        # report exists before delete
        assert (
            client.get(f"/api/scans/{scan_id}/report/json", headers=auth_headers).status_code == 200
        )

        assert client.delete(f"/api/scans/{scan_id}", headers=auth_headers).status_code == 204

        # deleted scans are unreachable for reports too
        assert (
            client.get(f"/api/scans/{scan_id}/report/json", headers=auth_headers).status_code == 404
        )
        assert (
            client.get(f"/api/scans/{scan_id}/report/pdf", headers=auth_headers).status_code == 404
        )
