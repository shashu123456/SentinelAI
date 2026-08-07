"""Integration tests for PDF/JSON report generation endpoints."""

import json


def _create_scan(client, headers, petstore_spec) -> int:
    resp = client.post(
        "/api/scans/upload",
        files={"file": ("petstore.json", json.dumps(petstore_spec), "application/json")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


class TestPdfReport:
    def test_download_pdf(self, client, auth_headers, petstore_spec):
        scan_id = _create_scan(client, auth_headers, petstore_spec)
        resp = client.get(f"/api/scans/{scan_id}/report/pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert f"sentinelai-report-{scan_id}.pdf" in resp.headers["content-disposition"]
        assert len(resp.content) > 0

    def test_pdf_for_nonexistent_scan(self, client, auth_headers):
        resp = client.get("/api/scans/99999/report/pdf", headers=auth_headers)
        assert resp.status_code == 404

    def test_pdf_requires_auth(self, client):
        assert client.get("/api/scans/1/report/pdf").status_code == 401


class TestJsonReport:
    def test_download_json(self, client, auth_headers, petstore_spec):
        scan_id = _create_scan(client, auth_headers, petstore_spec)
        resp = client.get(f"/api/scans/{scan_id}/report/json", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert f"sentinelai-report-{scan_id}.json" in resp.headers["content-disposition"]
        report = resp.json()
        assert report["api_name"] == "Petstore"
        assert report["total_endpoints"] == 4
        assert len(report["findings"]) > 0

    def test_json_for_nonexistent_scan(self, client, auth_headers):
        resp = client.get("/api/scans/99999/report/json", headers=auth_headers)
        assert resp.status_code == 404

    def test_json_requires_auth(self, client):
        assert client.get("/api/scans/1/report/json").status_code == 401
