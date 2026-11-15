"""Tests for POST /api/scans/upload with kind=spec|deps|code.

No network: the dependency scanner reads its offline vulnerability database and
the SAST engine uses its bundled rules.
"""

import io
import json
import zipfile
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[2] / "samples"

PETSTORE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Petstore", "version": "1.0.0"},
    "servers": [{"url": "http://api.example.com"}],
    "paths": {
        "/pets/{petId}": {
            "get": {
                "operationId": "getPet",
                "parameters": [
                    {"name": "petId", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}

REQUIREMENTS = b"django==4.2.9\nflask==2.3.1\nrequests==2.30.0\nclick==8.1.7\n"

INSECURE_PY = b"""import subprocess

def run(cmd):
    return subprocess.check_output(cmd, shell=True)

def calc(expr):
    return eval(expr)
"""

UNSAFE_JS = b"""export function render(el, data) {
  el.innerHTML = data.body;
}
"""


def _zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def _upload(client, headers, filename, payload, kind=None, content_type="application/octet-stream"):
    data = {} if kind is None else {"kind": kind}
    return client.post(
        "/api/scans/upload",
        files={"file": (filename, payload, content_type)},
        data=data,
        headers=headers,
    )


class TestKindsSucceed:
    def test_spec_kind_is_unchanged(self, client, auth_headers):
        resp = _upload(
            client,
            auth_headers,
            "petstore.json",
            json.dumps(PETSTORE_SPEC).encode(),
            kind="spec",
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["kind"] == "spec"
        assert body["partial"] is False
        assert body["counts_by_source"].get("spec", 0) >= 1

    def test_spec_kind_is_the_default(self, client, auth_headers):
        resp = _upload(
            client,
            auth_headers,
            "petstore.json",
            json.dumps(PETSTORE_SPEC).encode(),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["kind"] == "spec"

    def test_deps_kind_requirements(self, client, auth_headers):
        resp = _upload(client, auth_headers, "requirements.txt", REQUIREMENTS, kind="deps")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["kind"] == "deps"
        assert body["counts_by_source"].get("deps", 0) >= 1

    def test_deps_kind_package_json(self, client, auth_headers):
        payload = (SAMPLES / "demo-package.json").read_bytes()
        resp = _upload(client, auth_headers, "package.json", payload, kind="deps")
        assert resp.status_code == 200, resp.text
        assert resp.json()["counts_by_source"].get("deps", 0) >= 1

    def test_code_kind_single_file(self, client, auth_headers):
        resp = _upload(client, auth_headers, "app.py", INSECURE_PY, kind="code")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["kind"] == "code"
        assert body["counts_by_source"].get("code", 0) >= 1

    def test_code_kind_zip(self, client, auth_headers):
        payload = _zip({"app.py": INSECURE_PY, "api.js": UNSAFE_JS})
        resp = _upload(client, auth_headers, "demo-code.zip", payload, kind="code")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["counts_by_source"].get("code", 0) >= 1
        assert body["partial"] is False

    def test_findings_carry_their_source(self, client, auth_headers):
        created = _upload(client, auth_headers, "requirements.txt", REQUIREMENTS, kind="deps")
        assert created.status_code == 200, created.text
        detail = client.get(f"/api/scans/{created.json()['id']}", headers=auth_headers)
        assert detail.status_code == 200, detail.text
        sources = {f["source"] for f in detail.json()["findings"]}
        assert sources == {"deps"}

    def test_json_report_reports_kind_and_counts(self, client, auth_headers):
        created = _upload(client, auth_headers, "requirements.txt", REQUIREMENTS, kind="deps")
        assert created.status_code == 200, created.text
        scan_id = created.json()["id"]
        report = client.get(f"/api/scans/{scan_id}/report/json", headers=auth_headers)
        assert report.status_code == 200, report.text
        data = json.loads(report.text) if report.headers["content-type"].startswith("application/json") else report.json()
        payload = data if isinstance(data, dict) else json.loads(data)
        assert payload["kind"] == "deps"
        assert payload["counts_by_source"]["deps"] >= 1
        assert all("source" in f for f in payload["findings"])


class TestReports:
    def test_pdf_report_does_not_crash_on_deps_scan(self, client, auth_headers):
        created = _upload(client, auth_headers, "requirements.txt", REQUIREMENTS, kind="deps")
        assert created.status_code == 200, created.text
        pdf = client.get(f"/api/scans/{created.json()['id']}/report/pdf", headers=auth_headers)
        assert pdf.status_code == 200, pdf.text
        assert pdf.content[:4] == b"%PDF"

    def test_pdf_report_does_not_crash_on_code_scan(self, client, auth_headers):
        payload = _zip({"app.py": INSECURE_PY, "api.js": UNSAFE_JS})
        created = _upload(client, auth_headers, "demo.zip", payload, kind="code")
        assert created.status_code == 200, created.text
        pdf = client.get(f"/api/scans/{created.json()['id']}/report/pdf", headers=auth_headers)
        assert pdf.status_code == 200, pdf.text
        assert pdf.content[:4] == b"%PDF"


class TestRejections:
    def test_wrong_extension_for_kind_is_422(self, client, auth_headers):
        resp = _upload(client, auth_headers, "app.py", INSECURE_PY, kind="deps")
        assert resp.status_code == 422, resp.text
        assert ".txt" in resp.json()["detail"]

    def test_unknown_kind_is_422(self, client, auth_headers):
        resp = _upload(client, auth_headers, "requirements.txt", REQUIREMENTS, kind="nope")
        assert resp.status_code == 422, resp.text
        assert "spec" in resp.json()["detail"]

    def test_oversize_upload_is_413(self, client, auth_headers):
        payload = b"x" * (6 * 1024 * 1024)
        resp = _upload(client, auth_headers, "app.py", payload, kind="code")
        assert resp.status_code == 413, resp.text
        assert "too large" in resp.json()["detail"].lower()

    def test_zip_with_path_traversal_is_422(self, client, auth_headers):
        payload = _zip({"../etc/passwd": b"root:x:0:0\n", "app.py": INSECURE_PY})
        resp = _upload(client, auth_headers, "evil.zip", payload, kind="code")
        assert resp.status_code == 422, resp.text
        assert "archive rejected" in resp.json()["detail"]

    def test_zip_with_absolute_path_is_422(self, client, auth_headers):
        payload = _zip({"/etc/cron.d/job": b"* * * * * root true\n"})
        resp = _upload(client, auth_headers, "evil.zip", payload, kind="code")
        assert resp.status_code == 422, resp.text
        assert "archive rejected" in resp.json()["detail"]

    def test_zip_bomb_ratio_is_422(self, client, auth_headers):
        payload = _zip({"bomb.py": b"\0" * (2 * 1024 * 1024)})
        resp = _upload(client, auth_headers, "bomb.zip", payload, kind="code")
        assert resp.status_code == 422, resp.text
        assert "ratio" in resp.json()["detail"]

    def test_not_a_zip_is_422(self, client, auth_headers):
        resp = _upload(client, auth_headers, "notreally.zip", b"plain text", kind="code")
        assert resp.status_code == 422, resp.text
        assert "zip" in resp.json()["detail"]

    def test_archive_without_scannable_file_is_422(self, client, auth_headers):
        payload = _zip({"notes.md": b"# nothing to scan\n"})
        resp = _upload(client, auth_headers, "empty.zip", payload, kind="code")
        assert resp.status_code == 422, resp.text
        assert "no scannable file" in resp.json()["detail"]


class TestPartialResults:
    def test_more_than_200_files_sets_partial(self, client, auth_headers):
        entries = {f"module_{i:03d}.py": b"VALUE = 1\n" for i in range(250)}
        entries["danger.py"] = INSECURE_PY
        payload = _zip(entries)

        resp = _upload(client, auth_headers, "many.zip", payload, kind="code")
        assert resp.status_code == 200, resp.text
        assert resp.json()["partial"] is True


class TestSamplesExist:
    @pytest.mark.parametrize(
        "name",
        ["demo-openapi.yaml", "demo-requirements.txt", "demo-package.json", "demo-code.zip"],
    )
    def test_sample_file_present(self, name):
        path = SAMPLES / name
        assert path.is_file(), path
        assert path.stat().st_size > 0
