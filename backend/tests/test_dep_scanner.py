"""Tests for the dependency security scanner."""

import os
import json
import tempfile
import shutil
import pytest
from app.core.dep_scanner.scanner import (
    run_dep_scan, _parse_requirements_txt, _parse_package_json,
    _parse_pom_xml, _is_version_affected, _check_vulnerabilities,
    DependencyInfo,
)
from app.core.dep_scanner.vulnerability_db import (
    PYTHON_VULNERABILITIES, JAVASCRIPT_VULNERABILITIES, JAVA_VULNERABILITIES,
    Vulnerability,
)


def _write_temp(content: str, filename: str) -> str:
    """Write content to a temp file with the given name and return path."""
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _write_temp_dir(directory: str, content: str, filename: str) -> str:
    """Write content to a file in a specific directory."""
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestVersionParsing:
    """Test version comparison logic."""

    def test_exact_version_match(self):
        assert _is_version_affected("2.0.0", "2.1.0") is True
        assert _is_version_affected("2.1.0", "2.1.0") is False

    def test_version_with_prefix(self):
        assert _is_version_affected("1.0.0", "1.0.1") is True
        assert _is_version_affected("1.0.2", "1.0.1") is False

    def test_wildcard_version(self):
        assert _is_version_affected("1.0.0", "*") is True

    def test_empty_version_range(self):
        assert _is_version_affected("1.0.0", "") is True


class TestRequirementsTxtParsing:
    """Test requirements.txt parsing."""

    def test_parse_exact_version(self):
        path = _write_temp("flask==2.3.2\nrequests==2.31.0\n", "requirements.txt")
        try:
            deps = _parse_requirements_txt(path)
            assert len(deps) == 2
            assert deps[0].name == "flask"
            assert deps[0].version == "2.3.2"
            assert deps[0].ecosystem == "python"
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    def test_parse_minimum_version(self):
        path = _write_temp("django>=4.2.0\ncryptography>=41.0.0\n", "requirements.txt")
        try:
            deps = _parse_requirements_txt(path)
            assert len(deps) == 2
            assert deps[0].name == "django"
            assert deps[0].version == "4.2.0"
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    def test_parse_without_version(self):
        path = _write_temp("flask\nrequests\n", "requirements.txt")
        try:
            deps = _parse_requirements_txt(path)
            assert len(deps) == 2
            assert deps[0].version == "unknown"
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    def test_skip_comments(self):
        path = _write_temp("# This is a comment\nflask==2.3.2\n# Another comment\n", "requirements.txt")
        try:
            deps = _parse_requirements_txt(path)
            assert len(deps) == 1
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    def test_skip_options(self):
        path = _write_temp("-r requirements-base.txt\n--index-url https://pypi.org/simple\nflask==2.3.2\n", "requirements.txt")
        try:
            deps = _parse_requirements_txt(path)
            assert len(deps) == 1
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)


class TestPackageJsonParsing:
    """Test package.json parsing."""

    def test_parse_dependencies(self):
        pkg = {
            "name": "test-app",
            "dependencies": {
                "lodash": "^4.17.21",
                "axios": "^0.21.0",
            }
        }
        path = _write_temp(json.dumps(pkg), "package.json")
        try:
            deps = _parse_package_json(path)
            assert len(deps) == 2
            names = {d.name for d in deps}
            assert "lodash" in names
            assert "axios" in names
            for d in deps:
                assert d.ecosystem == "javascript"
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    def test_parse_dev_dependencies(self):
        pkg = {
            "name": "test-app",
            "dependencies": {"lodash": "^4.17.21"},
            "devDependencies": {"jest": "^29.0.0"},
        }
        path = _write_temp(json.dumps(pkg), "package.json")
        try:
            deps = _parse_package_json(path)
            assert len(deps) == 2
            jest = [d for d in deps if d.name == "jest"][0]
            assert jest.is_dev is True
            lodash = [d for d in deps if d.name == "lodash"][0]
            assert lodash.is_dev is False
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    def test_handle_invalid_json(self):
        path = _write_temp("not valid json {{{", "package.json")
        try:
            deps = _parse_package_json(path)
            assert len(deps) == 0
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)


class TestVulnerabilityDetection:
    """Test vulnerability detection against the database."""

    def test_detects_vulnerable_flask(self):
        dep = DependencyInfo(name="flask", version="2.3.1", ecosystem="python", file_path="requirements.txt")
        findings = _check_vulnerabilities(dep, PYTHON_VULNERABILITIES)
        assert len(findings) >= 1
        assert findings[0].cve_id == "CVE-2023-30861"

    def test_no_vulnerability_for_fixed_version(self):
        dep = DependencyInfo(name="flask", version="2.3.2", ecosystem="python", file_path="requirements.txt")
        findings = _check_vulnerabilities(dep, PYTHON_VULNERABILITIES)
        assert len(findings) == 0

    def test_detects_vulnerable_cryptography(self):
        dep = DependencyInfo(name="cryptography", version="41.0.0", ecosystem="python", file_path="requirements.txt")
        findings = _check_vulnerabilities(dep, PYTHON_VULNERABILITIES)
        assert len(findings) >= 1
        assert findings[0].severity == "Critical"

    def test_detects_vulnerable_lodash(self):
        dep = DependencyInfo(name="lodash", version="4.17.20", ecosystem="javascript", file_path="package.json")
        findings = _check_vulnerabilities(dep, JAVASCRIPT_VULNERABILITIES)
        assert len(findings) >= 1
        assert findings[0].cve_id == "CVE-2021-23337"

    def test_no_vulnerability_for_unknown_package(self):
        dep = DependencyInfo(name="nonexistent-pkg", version="1.0.0", ecosystem="python", file_path="requirements.txt")
        findings = _check_vulnerabilities(dep, PYTHON_VULNERABILITIES)
        assert len(findings) == 0

    def test_detects_vulnerable_pyyaml(self):
        dep = DependencyInfo(name="pyyaml", version="5.3", ecosystem="python", file_path="requirements.txt")
        findings = _check_vulnerabilities(dep, PYTHON_VULNERABILITIES)
        assert len(findings) >= 1
        assert findings[0].severity == "Critical"


class TestDependencyScanResult:
    """Test the full dependency scan flow."""

    def test_scan_nonexistent_path(self):
        result = run_dep_scan("/nonexistent/path")
        assert result.total_dependencies == 0
        assert len(result.errors) > 0

    def test_scan_requirements_txt(self):
        path = _write_temp("flask==2.3.1\ncryptography==41.0.0\nrequests==2.28.0\n", "requirements.txt")
        try:
            result = run_dep_scan(path)
            assert result.total_dependencies == 3
            assert "python" in result.ecosystems_detected
            assert len(result.findings) >= 1
            assert result.summary["total_vulnerabilities"] >= 1
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    def test_scan_package_json(self):
        pkg = {
            "name": "vulnerable-app",
            "dependencies": {
                "lodash": "4.17.20",
                "jsonwebtoken": "8.5.1",
            }
        }
        path = _write_temp(json.dumps(pkg), "package.json")
        try:
            result = run_dep_scan(path)
            assert result.total_dependencies == 2
            assert "javascript" in result.ecosystems_detected
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    def test_scan_directory_with_multiple_manifests(self):
        tmpdir = tempfile.mkdtemp()
        try:
            _write_temp_dir(tmpdir, "flask==2.3.1\n", "requirements.txt")
            _write_temp_dir(tmpdir, json.dumps({"dependencies": {"lodash": "4.17.20"}}), "package.json")

            result = run_dep_scan(tmpdir)
            assert result.total_files_scanned == 2
            assert result.total_dependencies == 2
            assert "python" in result.ecosystems_detected
            assert "javascript" in result.ecosystems_detected
        finally:
            shutil.rmtree(tmpdir)

    def test_finding_to_dict(self):
        finding = Vulnerability(
            cve_id="CVE-2023-1234",
            severity="High",
            cvss_score=8.0,
            description="Test vulnerability",
            fixed_in="2.0.0",
        )
        assert finding.cve_id == "CVE-2023-1234"
        assert finding.severity == "High"


class TestVulnerabilityDatabase:
    """Test vulnerability database completeness."""

    def test_python_vulns_have_required_fields(self):
        for pkg, vulns in PYTHON_VULNERABILITIES.items():
            for v in vulns:
                assert v.cve_id.startswith("CVE-"), f"{pkg} has invalid CVE"
                assert v.severity in ("Critical", "High", "Medium", "Low"), f"{pkg} has invalid severity"
                assert v.fixed_in, f"{pkg} missing fixed_in"
                assert v.cwe_id.startswith("CWE-"), f"{pkg} has invalid CWE"

    def test_javascript_vulns_have_required_fields(self):
        for pkg, vulns in JAVASCRIPT_VULNERABILITIES.items():
            for v in vulns:
                assert v.cve_id.startswith("CVE-"), f"{pkg} has invalid CVE"
                assert v.severity in ("Critical", "High", "Medium", "Low"), f"{pkg} has invalid severity"
                assert v.fixed_in, f"{pkg} missing fixed_in"

    def test_java_vulns_have_required_fields(self):
        for pkg, vulns in JAVA_VULNERABILITIES.items():
            for v in vulns:
                assert v.cve_id.startswith("CVE-"), f"{pkg} has invalid CVE"
                assert v.severity in ("Critical", "High", "Medium", "Low"), f"{pkg} has invalid severity"
                assert v.fixed_in, f"{pkg} missing fixed_in"

    def test_database_covers_critical_packages(self):
        critical_python = ["django", "flask", "requests", "cryptography", "pyyaml"]
        for pkg in critical_python:
            assert pkg in PYTHON_VULNERABILITIES, f"Missing critical Python package: {pkg}"

        critical_js = ["lodash", "axios", "express", "jsonwebtoken"]
        for pkg in critical_js:
            assert pkg in JAVASCRIPT_VULNERABILITIES, f"Missing critical JS package: {pkg}"
