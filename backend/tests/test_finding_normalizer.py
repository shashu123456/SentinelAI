"""Unit tests for app.services.finding_normalizer.

Pure functions only: no database, no network, no filesystem.
"""

import pytest

from app.repositories.findings import FindingRepository
from app.services.finding_normalizer import (
    ALLOWED_SEVERITIES,
    dedupe_findings,
    dedupe_key,
    normalize_confidence,
    normalize_dep,
    normalize_sast,
    normalize_severity,
    strip_internal,
)

REQUIRED_KEYS = (
    "source",
    "vulnerability_name",
    "owasp_category",
    "severity",
    "description",
    "impact",
    "remediation",
    "confidence",
)


def _dep(**overrides):
    base = {
        "package": "django",
        "installed_version": "4.2.9",
        "severity": "Medium",
        "cvss_score": 5.6,
        "cve_id": "CVE-2024-24680",
        "cwe_id": "CWE-400",
        "description": "Denial of service via urlquote().",
        "fixed_in": "4.2.10",
        "ecosystem": "pypi",
        "file_path": "requirements.txt",
        "url": "https://example.test/CVE-2024-24680",
        "confidence": 1.0,
    }
    base.update(overrides)
    return base


def _sast(**overrides):
    base = {
        "rule_id": "PY001",
        "rule_name": "Use of eval",
        "severity": "High",
        "cwe_id": "CWE-95",
        "owasp_category": None,
        "language": "python",
        "file_path": "app.py",
        "line_number": 12,
        "line_content": "    return eval(expression)",
        "description": "eval() executes untrusted input.",
        "remediation": "Use ast.literal_eval or a parser.",
        "confidence": 0.9,
        "tags": ["injection"],
    }
    base.update(overrides)
    return base


class TestDepNormalization:
    def test_all_required_keys_present_and_non_empty(self):
        result = normalize_dep(_dep())
        for key in REQUIRED_KEYS:
            assert key in result, key
            assert result[key] is not None, key
            assert str(result[key]).strip() != "", key
        assert result["source"] == "deps"

    def test_identity_includes_package_and_cve(self):
        result = normalize_dep(_dep())
        assert "django" in result["vulnerability_name"]
        assert "CVE-2024-24680" in result["vulnerability_name"]

    def test_remediation_names_the_fixed_version(self):
        assert "4.2.10" in normalize_dep(_dep())["remediation"]

    def test_remediation_without_fixed_version_still_written(self):
        result = normalize_dep(_dep(fixed_in=""))
        assert result["remediation"]
        assert result["remediation"].lower().startswith("upgrade")

    def test_missing_description_gets_a_generated_one(self):
        result = normalize_dep(_dep(description=None))
        assert result["description"]
        assert "django" in result["description"]

    def test_impact_is_generated_when_engine_has_none(self):
        # DepFinding has no impact field at all.
        result = normalize_dep(_dep())
        assert result["impact"]
        assert "impact" not in _dep()

    def test_package_arguments_override_the_finding(self):
        result = normalize_dep(_dep(), package_name="Flask", package_version="2.3.1")
        assert "Flask 2.3.1" in result["vulnerability_name"]

    def test_accepts_objects_as_well_as_dicts(self):
        class Obj:
            package = "requests"
            installed_version = "2.30.0"
            severity = "High"
            cvss_score = 8.0
            cve_id = "CVE-2023-32681"
            cwe_id = "CWE-200"
            description = "Proxy-Authorization leaked on redirect."
            fixed_in = "2.31.0"
            ecosystem = "pypi"
            file_path = "requirements.txt"
            url = ""
            confidence = 1.0

        result = normalize_dep(Obj())
        assert result["source"] == "deps"
        assert result["severity"] == "High"
        assert result["confidence"] == 100

    def test_works_with_the_real_dep_scanner_finding(self):
        """The dict shape produced by DepFinding.to_dict() must normalize."""
        from app.core.dep_scanner.scanner import DepFinding

        finding = DepFinding(
            package="django",
            installed_version="4.2.9",
            severity="Medium",
            cvss_score=5.6,
            cve_id="CVE-2024-24680",
            cwe_id="CWE-400",
            description="DoS via urlquote().",
            fixed_in="4.2.10",
            ecosystem="pypi",
            file_path="requirements.txt",
        )
        result = normalize_dep(finding.to_dict())
        assert result["source"] == "deps"
        assert result["severity"] in ALLOWED_SEVERITIES


class TestSastNormalization:
    def test_all_required_keys_present_and_non_empty(self):
        result = normalize_sast(_sast())
        for key in REQUIRED_KEYS:
            assert key in result, key
            assert result[key] is not None, key
            assert str(result[key]).strip() != "", key
        assert result["source"] == "code"

    def test_location_in_evidence_and_endpoint(self):
        result = normalize_sast(_sast())
        assert "app.py:12" in result["evidence"]
        assert result["affected_endpoint"] == "app.py:12"

    def test_missing_owasp_category_uses_default(self):
        result = normalize_sast(_sast(owasp_category=None))
        assert result["owasp_category"]
        assert len(result["owasp_category"]) <= 50

    def test_missing_impact_and_remediation_are_generated(self):
        # SASTFinding has no impact field.
        result = normalize_sast(_sast())
        assert result["impact"]
        assert result["remediation"] == "Use ast.literal_eval or a parser."

    def test_works_with_the_real_sast_finding(self):
        from app.core.sast_engine.scanner import SASTFinding

        finding = SASTFinding(
            rule_id="PY001",
            rule_name="Use of eval",
            severity="High",
            cwe_id="CWE-95",
            owasp_category=None,
            language="python",
            file_path="app.py",
            line_number=3,
            line_content="    return eval(x)",
            description="eval on untrusted input.",
            remediation="Use ast.literal_eval.",
            confidence=0.8,
        )
        result = normalize_sast(finding.to_dict())
        assert result["source"] == "code"
        assert result["confidence"] == 80


class TestSeverityMapping:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("critical", "Critical"),
            ("CRITICAL", "Critical"),
            ("High", "High"),
            ("important", "High"),
            ("moderate", "Medium"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("info", "Info"),
            ("informational", "Info"),
            ("none", "Info"),
        ],
    )
    def test_known_aliases(self, raw, expected):
        assert normalize_severity(raw) == expected

    def test_unknown_value_is_medium_not_info(self):
        # Under-reporting an unknown severity would hide a finding.
        assert normalize_severity("banana") == "Medium"
        assert normalize_severity(None) == "Medium"

    def test_every_result_is_in_the_database_vocabulary(self):
        for raw in ("critical", "high", "medium", "low", "info", "weird", None):
            assert normalize_severity(raw) in ALLOWED_SEVERITIES


class TestConfidence:
    @pytest.mark.parametrize(
        "raw,expected",
        [(1.0, 100), (0.9, 90), (0.0, 0), (85, 85), (100, 100), (None, 85), ("0.5", 50)],
    )
    def test_conversion(self, raw, expected):
        assert normalize_confidence(raw) == expected

    def test_clamped_to_0_100(self):
        # A value above 1.0 is read as a percentage, then clamped.
        assert normalize_confidence(250) == 100
        assert normalize_confidence(-1) == 0


class TestDedupe:
    def test_two_identical_dep_findings_collapse(self):
        findings = [normalize_dep(_dep()), normalize_dep(_dep())]
        assert len(dedupe_findings(findings)) == 1

    def test_two_identical_sast_findings_collapse(self):
        findings = [normalize_sast(_sast()), normalize_sast(_sast())]
        assert len(dedupe_findings(findings)) == 1

    def test_different_line_is_a_different_finding(self):
        a = normalize_sast(_sast(line_number=12))
        b = normalize_sast(_sast(line_number=13))
        key_a, key_b = dedupe_key(a), dedupe_key(b)
        assert key_a != key_b
        assert len(dedupe_findings([a, b])) == 2

    def test_different_rule_is_a_different_finding(self):
        a = normalize_sast(_sast(rule_id="PY001"))
        b = normalize_sast(_sast(rule_id="PY002"))
        assert dedupe_key(a) != dedupe_key(b)

    def test_deps_and_code_never_collide(self):
        assert dedupe_key(normalize_dep(_dep()))[0] == "deps"
        assert dedupe_key(normalize_sast(_sast()))[0] == "code"

    def test_order_is_preserved(self):
        first = normalize_sast(_sast(line_number=1))
        second = normalize_sast(_sast(line_number=2))
        assert dedupe_findings([first, second, first]) == [first, second]


class TestPersistenceCompatibility:
    def test_normalized_findings_satisfy_from_scan_data(self):
        """The whole point: normalizer output is persistence-ready."""
        from app.models.models import Finding

        dep = strip_internal(normalize_dep(_dep()))
        sast = strip_internal(normalize_sast(_sast()))

        for data in (dep, sast):
            finding = FindingRepository.from_scan_data(1, data)
            assert isinstance(finding, Finding)
            assert finding.description
            assert finding.impact
            assert finding.remediation
            assert finding.source in ("deps", "code")

    def test_strip_internal_removes_helper_keys(self):
        assert not any(k.startswith("_") for k in strip_internal(normalize_dep(_dep())))
