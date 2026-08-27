"""Integration tests for SAST, dependency scanning, and security copilot APIs."""

import json

VULNERABLE_PYTHON = """
import os
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = " + user_id)
    return cur.fetchone()

password = "hunter2secret"

def run(cmd):
    os.system(cmd)
"""

SAFE_PYTHON = """
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()
"""


class TestSASTTextScan:
    def test_scan_vulnerable_code(self, client, auth_headers):
        resp = client.post(
            "/api/security/sast/scan/text",
            data={"code": VULNERABLE_PYTHON, "filename": "app.py"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["summary"]["total_findings"] > 0
        assert data["summary"]["files_scanned"] == 1
        assert "python" in data["summary"]["languages_detected"]
        rule_ids = {f["rule_id"] for f in data["findings"]}
        assert "SAST-PY-002" in rule_ids
        assert "SAST-PY-020" in rule_ids

    def test_scan_safe_code(self, client, auth_headers):
        resp = client.post(
            "/api/security/sast/scan/text",
            data={"code": SAFE_PYTHON, "filename": "app.py"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["summary"]["total_findings"] == 0

    def test_empty_code_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/security/sast/scan/text",
            data={"code": "   ", "filename": "app.py"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_scan_requires_auth(self, client):
        resp = client.post(
            "/api/security/sast/scan/text",
            data={"code": VULNERABLE_PYTHON, "filename": "app.py"},
        )
        assert resp.status_code == 401


class TestSASTFileScan:
    def test_scan_uploaded_file(self, client, auth_headers):
        resp = client.post(
            "/api/security/sast/scan",
            files={"file": ("app.py", VULNERABLE_PYTHON, "text/x-python")},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["summary"]["total_findings"] > 0
        assert data["target_path"] == "app.py"

    def test_scan_unsupported_file_type(self, client, auth_headers):
        resp = client.post(
            "/api/security/sast/scan",
            files={"file": ("notes.txt", "hello", "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestDepScan:
    def test_scan_requirements_txt(self, client, auth_headers):
        content = "flask==2.3.1\ncryptography==41.0.0\nrequests==2.28.0\n"
        resp = client.post(
            "/api/security/deps/scan",
            files={"file": ("requirements.txt", content, "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["summary"]["total_dependencies"] == 3
        assert data["summary"]["total_vulnerabilities"] >= 1
        assert "python" in data["summary"]["ecosystems_detected"]
        cve_ids = {f["cve_id"] for f in data["findings"]}
        assert "CVE-2023-30861" in cve_ids

    def test_scan_package_json(self, client, auth_headers):
        content = json.dumps({"dependencies": {"lodash": "4.17.20"}})
        resp = client.post(
            "/api/security/deps/scan",
            files={"file": ("package.json", content, "application/json")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["summary"]["total_vulnerabilities"] >= 1

    def test_scan_clean_manifest(self, client, auth_headers):
        content = "requests==2.32.3\n"
        resp = client.post(
            "/api/security/deps/scan",
            files={"file": ("requirements.txt", content, "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["summary"]["total_vulnerabilities"] == 0

    def test_scan_unsupported_filename(self, client, auth_headers):
        resp = client.post(
            "/api/security/deps/scan",
            files={"file": ("manifest.txt", "hello", "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_scan_requires_auth(self, client):
        resp = client.post(
            "/api/security/deps/scan",
            files={"file": ("requirements.txt", "flask==2.3.1\n", "text/plain")},
        )
        assert resp.status_code == 401


class TestCopilot:
    def test_chat(self, client, auth_headers):
        resp = client.post(
            "/api/security/copilot/chat",
            json={"message": "hello", "scan_id": None},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["response"]
        assert data["intent"]
        assert "has_context" in data

    def test_chat_empty_message_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/security/copilot/chat",
            json={"message": "", "scan_id": None},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_sidebar(self, client, auth_headers):
        resp = client.get("/api/security/copilot/sidebar", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_score"] == 0
        assert data["total_scans"] == 0
        assert "severity_counts" in data

    def test_commands(self, client, auth_headers):
        resp = client.get("/api/security/copilot/commands", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["capabilities"]) >= 1

    def test_clear(self, client, auth_headers):
        resp = client.post("/api/security/copilot/clear", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cleared"

    def test_load_context(self, client, auth_headers):
        resp = client.post(
            "/api/security/copilot/context", json={"scan_id": None}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "loaded"

    def test_chat_requires_auth(self, client):
        assert client.post("/api/security/copilot/chat", json={"message": "hi"}).status_code == 401
