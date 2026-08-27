"""Report persistence: reports are stored in the database and served from it."""

import json
import uuid

from app.database.database import SessionLocal
from app.models.models import AuditLog, Report

SAMPLE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Report Persist API", "version": "1.0"},
    "paths": {"/items": {"get": {"responses": {"200": {"description": "ok"}}}}},
}


def _upload(client, headers):
    resp = client.post(
        "/api/scans/upload",
        headers=headers,
        files={"file": ("spec.json", json.dumps(SAMPLE_SPEC), "application/json")},
        data={"api_name": "Report Persist API"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _register_second_user(client):
    username = f"other_{uuid.uuid4().hex[:8]}"
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


class TestReportPersistence:
    def test_json_report_persisted_and_served(self, client, auth_headers):
        scan_id = _upload(client, auth_headers)["id"]

        first = client.get(f"/api/scans/{scan_id}/report/json", headers=auth_headers)
        assert first.status_code == 200
        assert first.headers["content-type"].startswith("application/json")
        payload = json.loads(first.content)
        assert payload["api_name"] == "Report Persist API"

        # second download is served from the stored row (identical bytes)
        second = client.get(f"/api/scans/{scan_id}/report/json", headers=auth_headers)
        assert second.status_code == 200
        assert second.content == first.content

        db = SessionLocal()
        try:
            report = (
                db.query(Report).filter(Report.scan_id == scan_id, Report.format == "json").one()
            )
            assert report.content == first.content

            # only the first download generates + audits the export
            count = (
                db.query(AuditLog)
                .filter(
                    AuditLog.action == "report.exported.json",
                    AuditLog.entity_id == scan_id,
                )
                .count()
            )
            assert count == 1
        finally:
            db.close()

    def test_pdf_report_persisted(self, client, auth_headers):
        scan_id = _upload(client, auth_headers)["id"]

        first = client.get(f"/api/scans/{scan_id}/report/pdf", headers=auth_headers)
        assert first.status_code == 200
        assert first.headers["content-type"].startswith("application/pdf")
        assert first.content.startswith(b"%PDF")

        second = client.get(f"/api/scans/{scan_id}/report/pdf", headers=auth_headers)
        assert second.content == first.content

        db = SessionLocal()
        try:
            assert (
                db.query(Report).filter(Report.scan_id == scan_id, Report.format == "pdf").count()
                == 1
            )
        finally:
            db.close()

    def test_report_not_accessible_by_other_user(self, client, auth_headers):
        scan_id = _upload(client, auth_headers)["id"]
        other_headers = _register_second_user(client)

        assert (
            client.get(f"/api/scans/{scan_id}/report/json", headers=other_headers).status_code
            == 404
        )
        assert (
            client.get(f"/api/scans/{scan_id}/report/pdf", headers=other_headers).status_code == 404
        )
