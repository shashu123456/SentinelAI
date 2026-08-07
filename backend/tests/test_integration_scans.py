"""Integration tests for the scan upload, listing, detail, and dashboard APIs."""

import json


def _upload(client, headers, spec, filename="petstore.json"):
    return client.post(
        "/api/scans/upload",
        files={"file": (filename, json.dumps(spec), "application/json")},
        headers=headers,
    )


class TestUploadAndScan:
    def test_upload_valid_spec(self, client, auth_headers, petstore_spec):
        resp = _upload(client, auth_headers, petstore_spec)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "completed"
        assert data["total_endpoints"] == 4
        assert data["total_vulnerabilities"] > 0
        assert data["risk_score"] > 0
        assert data["risk_level"] in ("Critical", "High", "Medium", "Low")

    def test_upload_with_api_name(self, client, auth_headers, petstore_spec):
        resp = client.post(
            "/api/scans/upload",
            files={"file": ("petstore.json", json.dumps(petstore_spec), "application/json")},
            data={"api_name": "My Custom API"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["api_name"] == "My Custom API"

    def test_upload_yaml_spec(self, client, auth_headers):
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "YAML API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {"responses": {"200": {"description": "OK"}}}
                }
            },
        }
        yaml_doc = (
            "openapi: 3.0.0\n"
            "info:\n"
            "  title: YAML API\n"
            "  version: 1.0.0\n"
            "paths:\n"
            "  /items:\n"
            "    get:\n"
            "      responses:\n"
            "        '200':\n"
            "          description: OK\n"
        )
        resp = client.post(
            "/api/scans/upload",
            files={"file": ("spec.yaml", yaml_doc, "application/yaml")},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["api_title"] == "YAML API"

    def test_upload_invalid_file_type(self, client, auth_headers):
        resp = client.post(
            "/api/scans/upload",
            files={"file": ("notes.txt", "hello world", "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_upload_invalid_json(self, client, auth_headers):
        resp = client.post(
            "/api/scans/upload",
            files={"file": ("spec.json", "not valid json {{{", "application/json")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_upload_non_openapi(self, client, auth_headers):
        resp = client.post(
            "/api/scans/upload",
            files={"file": ("spec.json", json.dumps({"hello": "world"}), "application/json")},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "openapi" in resp.json()["detail"]

    def test_upload_requires_auth(self, client, petstore_spec):
        resp = _upload(client, {}, petstore_spec)
        assert resp.status_code == 401


class TestListScans:
    def test_list_scans_empty(self, client, auth_headers):
        resp = client.get("/api/scans/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_scans_after_upload(self, client, auth_headers, petstore_spec):
        _upload(client, auth_headers, petstore_spec)
        resp = client.get("/api/scans/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["total_endpoints"] == 4

    def test_list_scans_requires_auth(self, client):
        assert client.get("/api/scans/").status_code == 401


class TestScanDetail:
    def test_get_scan_detail(self, client, auth_headers, petstore_spec):
        scan = _upload(client, auth_headers, petstore_spec).json()
        resp = client.get(f"/api/scans/{scan['id']}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == scan["id"]
        assert len(data["findings"]) > 0
        finding = data["findings"][0]
        assert finding["vulnerability_name"]
        assert finding["severity"] in ("Critical", "High", "Medium", "Low", "Info")

    def test_get_nonexistent_scan(self, client, auth_headers):
        resp = client.get("/api/scans/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_cannot_access_other_users_scan(self, client, user_token, petstore_spec):
        username_a, token_a = user_token
        scan = _upload(
            client,
            {"Authorization": f"Bearer {token_a}"},
            petstore_spec,
        ).json()

        client.post(
            "/api/auth/register",
            json={
                "username": f"intruder_{username_a}",
                "email": f"intruder_{username_a}@example.com",
                "password": "testpass123",
            },
        )
        login = client.post(
            "/api/auth/login",
            json={"username": f"intruder_{username_a}", "password": "testpass123"},
        ).json()
        headers_b = {"Authorization": f"Bearer {login['access_token']}"}

        assert client.get(f"/api/scans/{scan['id']}", headers=headers_b).status_code == 404

    def test_get_scan_detail_requires_auth(self, client):
        assert client.get("/api/scans/1").status_code == 401


class TestDashboard:
    def test_dashboard_empty(self, client, auth_headers):
        resp = client.get("/api/scans/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_scans"] == 0
        assert data["severity_distribution"]["Critical"] == 0

    def test_dashboard_after_upload(self, client, auth_headers, petstore_spec):
        _upload(client, auth_headers, petstore_spec)
        resp = client.get("/api/scans/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_scans"] == 1
        assert data["total_vulnerabilities"] > 0
        assert len(data["recent_scans"]) == 1
        assert data["average_risk_score"] > 0

    def test_dashboard_requires_auth(self, client):
        assert client.get("/api/scans/dashboard").status_code == 401


class TestDeleteScan:
    def test_delete_scan(self, client, auth_headers, petstore_spec):
        scan = _upload(client, auth_headers, petstore_spec).json()
        resp = client.delete(f"/api/scans/{scan['id']}", headers=auth_headers)
        assert resp.status_code == 204
        assert client.get(f"/api/scans/{scan['id']}", headers=auth_headers).status_code == 404

    def test_delete_nonexistent_scan(self, client, auth_headers):
        assert client.delete("/api/scans/99999", headers=auth_headers).status_code == 404


class TestHealth:
    def test_root_health(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "operational"

    def test_api_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
