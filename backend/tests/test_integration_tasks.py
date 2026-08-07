"""Integration tests for the async background scan task flow."""

import json


class TestAsyncUpload:
    def test_async_upload_creates_task(self, client, auth_headers, petstore_spec):
        resp = client.post(
            "/api/scans/upload/async",
            files={"file": ("petstore.json", json.dumps(petstore_spec), "application/json")},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["task_id"]
        assert data["message"] == "Scan started"

    def test_async_task_completes(self, client, auth_headers, petstore_spec, wait_for_task):
        resp = client.post(
            "/api/scans/upload/async",
            files={"file": ("petstore.json", json.dumps(petstore_spec), "application/json")},
            headers=auth_headers,
        )
        task = wait_for_task(resp.json()["task_id"], headers=auth_headers)
        assert task["status"] == "completed", task
        assert task["progress"] == 100
        assert task["scan_id"] is not None
        assert task["result"]["total_vulnerabilities"] > 0
        assert task["result"]["risk_score"] > 0

    def test_async_scan_persisted(self, client, auth_headers, petstore_spec, wait_for_task):
        resp = client.post(
            "/api/scans/upload/async",
            files={"file": ("petstore.json", json.dumps(petstore_spec), "application/json")},
            headers=auth_headers,
        )
        task = wait_for_task(resp.json()["task_id"], headers=auth_headers)
        detail = client.get(f"/api/scans/{task['scan_id']}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"
        assert len(detail.json()["findings"]) > 0

    def test_async_upload_invalid_spec(self, client, auth_headers):
        resp = client.post(
            "/api/scans/upload/async",
            files={"file": ("spec.json", json.dumps({"not": "openapi"}), "application/json")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_async_upload_requires_auth(self, client, petstore_spec):
        resp = client.post(
            "/api/scans/upload/async",
            files={"file": ("petstore.json", json.dumps(petstore_spec), "application/json")},
        )
        assert resp.status_code == 401


class TestTaskStatus:
    def test_get_nonexistent_task(self, client, auth_headers):
        resp = client.get("/api/scans/task/does-not-exist", headers=auth_headers)
        assert resp.status_code == 404

    def test_task_status_requires_auth(self, client):
        assert client.get("/api/scans/task/some-task").status_code == 401
