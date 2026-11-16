"""Report and aggregate endpoints for all three scan kinds.

The PDF used to describe every scan as an API specification with endpoints, so a
dependency or source-code scan produced a report that was 200/valid-PDF but
wrong about what had been scanned. These tests assert the PDF's text (pypdf),
not just its status code.
"""

import io
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.reports.generator import _distinct_locations, _scan_kind, _scope_metric

SAMPLES = Path(__file__).resolve().parents[2] / "samples"

DEPS_FINDINGS = [
    {"source": "deps", "severity": "Medium", "affected_endpoint": "django==4.2.9"},
    {"source": "deps", "severity": "High", "affected_endpoint": "django==4.2.9"},
    {"source": "deps", "severity": "High", "affected_endpoint": "flask==2.3.1"},
]

CODE_FINDINGS = [
    {"source": "code", "severity": "High", "affected_endpoint": "app.py:9"},
    {"source": "code", "severity": "Low", "affected_endpoint": "app.py:12"},
    {"source": "code", "severity": "High", "affected_endpoint": "pkg/api.js:3"},
]

INSECURE_PY = b"""import subprocess

def run(cmd):
    return subprocess.check_output(cmd, shell=True)
"""


def _upload(client, headers, filename, payload, kind):
    return client.post(
        "/api/scans/upload",
        files={"file": (filename, payload, "application/octet-stream")},
        data={"kind": kind},
        headers=headers,
    )


def _pdf_text(payload: bytes) -> str:
    reader = PdfReader(io.BytesIO(payload))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


@pytest.fixture()
def scans_by_kind(client, auth_headers):
    ids = {}
    for kind, name in (
        ("spec", "demo-openapi.yaml"),
        ("deps", "demo-requirements.txt"),
        ("code", "demo-code.zip"),
    ):
        sample = SAMPLES / name
        assert sample.is_file(), sample
        resp = _upload(client, auth_headers, name, sample.read_bytes(), kind)
        assert resp.status_code == 200, resp.text
        ids[kind] = resp.json()["id"]
    return ids


class TestPdfForEveryKind:
    @pytest.mark.parametrize("kind", ["spec", "deps", "code"])
    def test_pdf_is_real_and_non_trivial(self, client, auth_headers, scans_by_kind, kind):
        resp = client.get(f"/api/scans/{scans_by_kind[kind]}/report/pdf", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content.startswith(b"%PDF")
        assert len(resp.content) > 1000

    def test_spec_pdf_keeps_endpoint_wording(self, client, auth_headers, scans_by_kind):
        resp = client.get(f"/api/scans/{scans_by_kind['spec']}/report/pdf", headers=auth_headers)
        text = _pdf_text(resp.content)
        assert "Endpoints Scanned" in text
        assert "API Specification" in text
        assert "Findings by Source" not in text

    def test_deps_pdf_reports_packages_not_endpoints(self, client, auth_headers, scans_by_kind):
        resp = client.get(f"/api/scans/{scans_by_kind['deps']}/report/pdf", headers=auth_headers)
        text = _pdf_text(resp.content)
        assert "Dependency Manifest" in text
        assert "Findings by Source" in text
        assert "Vulnerable Packages" in text
        assert "Endpoints Scanned" not in text
        # The old template claimed every scan covered the OWASP API Top 10.
        assert "OWASP API Security Top 10" not in text
        assert "OWASP: N/A" not in text

    def test_code_pdf_reports_files_and_locations(self, client, auth_headers, scans_by_kind):
        resp = client.get(f"/api/scans/{scans_by_kind['code']}/report/pdf", headers=auth_headers)
        text = _pdf_text(resp.content)
        assert "Source Code" in text
        assert "Findings by Source" in text
        assert "Vulnerable Files" in text
        assert "Endpoints Scanned" not in text
        assert "LOCATION" in text
        assert "sentinelai_upload_" not in text


class TestAggregatesWithMixedKinds:
    def test_dashboard_returns_200_and_counts_every_kind(self, client, auth_headers, scans_by_kind):
        resp = client.get("/api/scans/dashboard", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_scans"] >= 3
        assert body["total_vulnerabilities"] > 0
        assert {"spec", "deps", "code"} <= {scan["kind"] for scan in body["recent_scans"]}
        deps_scan = next(s for s in body["recent_scans"] if s["kind"] == "deps")
        assert deps_scan["total_endpoints"] == 0
        assert deps_scan["total_vulnerabilities"] > 0

    def test_analytics_returns_200_and_a_full_window(self, client, auth_headers, scans_by_kind):
        resp = client.get("/api/scans/analytics", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["scan_activity"]) == 30
        assert any(day["scans"] for day in body["scan_activity"])
        assert body["owasp_distribution"]

    def test_empty_account_does_not_divide_by_zero(self, client, auth_headers):
        # A brand-new user has no scans at all: average risk is undefined.
        resp = client.get("/api/scans/dashboard", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        resp = client.get("/api/scans/analytics", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["risk_trend"] == []


class TestCodeFindingsDoNotLeakHostPaths:
    def test_affected_endpoint_is_relative(self, client, auth_headers):
        resp = _upload(client, auth_headers, "app.py", INSECURE_PY, "code")
        assert resp.status_code == 200, resp.text
        scan_id = resp.json()["id"]

        detail = client.get(f"/api/scans/{scan_id}", headers=auth_headers)
        assert detail.status_code == 200
        findings = detail.json()["findings"]
        assert findings
        for finding in findings:
            location = finding["affected_endpoint"]
            assert location.startswith("app.py:"), location
            assert "sentinelai_upload_" not in location
            assert ":\\" not in location and ":/" not in location


class TestScopeMetric:
    @pytest.mark.parametrize(
        ("kind", "endpoints", "findings", "expected"),
        [
            ("spec", 4, [], (4, "Endpoints Scanned")),
            ("deps", 0, DEPS_FINDINGS, (2, "Vulnerable Packages")),
            ("code", 0, CODE_FINDINGS, (2, "Vulnerable Files")),
            ("spec", 0, [], (0, "Endpoints Scanned")),
        ],
    )
    def test_card_says_what_was_scanned(self, kind, endpoints, findings, expected):
        assert _scope_metric(kind, endpoints, findings) == expected

    def test_unknown_kind_is_treated_as_spec(self):
        assert _scan_kind({"kind": "nonsense"}) == "spec"
        assert _scan_kind({}) == "spec"
        assert _scan_kind({"kind": "deps"}) == "deps"

    def test_distinct_locations_ignores_line_numbers(self):
        assert _distinct_locations(CODE_FINDINGS, "code") == 2
        assert _distinct_locations(DEPS_FINDINGS, "deps") == 2
