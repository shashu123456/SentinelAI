"""Tests for the SAST (Static Application Security Testing) engine."""

import os
import tempfile
import shutil
import pytest
from app.core.sast_engine.scanner import run_sast_scan, _scan_file, _collect_files
from app.core.sast_engine.rules import (
    ALL_RULES, PYTHON_RULES, JAVASCRIPT_RULES, JAVA_RULES,
    Severity, Language, get_rules_for_file, get_rules_by_severity,
    SecurityRule, EXTENSION_LANGUAGE_MAP,
)


def _write_temp(code: str, suffix: str) -> str:
    """Write code to a temp file, close it, and return the path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def _write_temp_in_dir(directory: str, code: str, filename: str) -> str:
    """Write code to a specific file in a directory."""
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path


class TestSecurityRules:
    """Test security rule definitions."""

    def test_all_rules_have_required_fields(self):
        for rule in ALL_RULES:
            assert rule.id, f"Rule missing id"
            assert rule.name, f"Rule {rule.id} missing name"
            assert rule.severity in Severity, f"Rule {rule.id} invalid severity"
            assert rule.cwe_id.startswith("CWE-"), f"Rule {rule.id} invalid CWE"
            assert rule.language in Language, f"Rule {rule.id} invalid language"
            assert rule.pattern, f"Rule {rule.id} missing pattern"
            assert rule.description, f"Rule {rule.id} missing description"
            assert rule.remediation, f"Rule {rule.id} missing remediation"
            assert 0 <= rule.confidence <= 1, f"Rule {rule.id} confidence out of range"

    def test_rule_ids_are_unique(self):
        ids = [r.id for r in ALL_RULES]
        assert len(ids) == len(set(ids)), "Duplicate rule IDs found"

    def test_python_rules_count(self):
        assert len(PYTHON_RULES) >= 15, "Expected at least 15 Python rules"

    def test_javascript_rules_count(self):
        assert len(JAVASCRIPT_RULES) >= 8, "Expected at least 8 JavaScript rules"

    def test_java_rules_count(self):
        assert len(JAVA_RULES) >= 8, "Expected at least 8 Java rules"

    def test_severity_distribution(self):
        severities = {r.severity for r in ALL_RULES}
        assert Severity.CRITICAL in severities
        assert Severity.HIGH in severities
        assert Severity.MEDIUM in severities

    def test_get_rules_for_python_file(self):
        rules = get_rules_for_file("app.py")
        assert len(rules) > 0
        assert all(r.language == Language.PYTHON for r in rules)

    def test_get_rules_for_javascript_file(self):
        rules = get_rules_for_file("server.js")
        assert len(rules) > 0
        assert all(r.language == Language.JAVASCRIPT for r in rules)

    def test_get_rules_for_java_file(self):
        rules = get_rules_for_file("Application.java")
        assert len(rules) > 0
        assert all(r.language == Language.JAVA for r in rules)

    def test_get_rules_for_unknown_file(self):
        rules = get_rules_for_file("readme.txt")
        assert len(rules) == 0

    def test_extension_map_covers_all_languages(self):
        assert ".py" in EXTENSION_LANGUAGE_MAP
        assert ".js" in EXTENSION_LANGUAGE_MAP
        assert ".jsx" in EXTENSION_LANGUAGE_MAP
        assert ".ts" in EXTENSION_LANGUAGE_MAP
        assert ".tsx" in EXTENSION_LANGUAGE_MAP
        assert ".java" in EXTENSION_LANGUAGE_MAP

    def test_get_rules_by_severity(self):
        critical = get_rules_by_severity(Severity.CRITICAL)
        assert len(critical) > 0
        assert all(r.severity == Severity.CRITICAL for r in critical)

    def test_rules_compile_as_regex(self):
        import re
        for rule in ALL_RULES:
            try:
                re.compile(rule.pattern)
            except re.error as e:
                pytest.fail(f"Rule {rule.id} has invalid regex: {e}")


class TestSASTFileScanning:
    """Test individual file scanning."""

    def test_detects_sql_injection_fstring(self):
        path = _write_temp('cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n', ".py")
        try:
            findings = _scan_file(path, PYTHON_RULES)
            sql_findings = [f for f in findings if "SQL" in f.rule_name]
            assert len(sql_findings) >= 1, "Should detect f-string SQL injection"
            assert sql_findings[0].cwe_id == "CWE-89"
        finally:
            os.unlink(path)

    def test_detects_hardcoded_password(self):
        path = _write_temp('password = "super_secret_123"\napi_key = "sk_live_abcdef1234567890"\n', ".py")
        try:
            findings = _scan_file(path, PYTHON_RULES)
            secret_findings = [f for f in findings if "Secret" in f.rule_name or "Password" in f.rule_name]
            assert len(secret_findings) >= 1, "Should detect hardcoded secrets"
        finally:
            os.unlink(path)

    def test_detects_pickle_deserialization(self):
        path = _write_temp('data = pickle.loads(user_input)\n', ".py")
        try:
            findings = _scan_file(path, PYTHON_RULES)
            deserial_findings = [f for f in findings if "Deserialization" in f.rule_name]
            assert len(deserial_findings) >= 1
            assert deserial_findings[0].severity == "Critical"
        finally:
            os.unlink(path)

    def test_detects_weak_hash(self):
        path = _write_temp('hash_value = hashlib.md5(password.encode()).hexdigest()\n', ".py")
        try:
            findings = _scan_file(path, PYTHON_RULES)
            crypto_findings = [f for f in findings if "MD5" in f.rule_name or "Weak" in f.rule_name]
            assert len(crypto_findings) >= 1
        finally:
            os.unlink(path)

    def test_detects_js_xss_innerhtml(self):
        path = _write_temp('element.innerHTML = userInput;\n', ".js")
        try:
            findings = _scan_file(path, JAVASCRIPT_RULES)
            xss_findings = [f for f in findings if "XSS" in f.rule_name or "innerHTML" in f.rule_name]
            assert len(xss_findings) >= 1
        finally:
            os.unlink(path)

    def test_detects_java_sql_injection(self):
        code = 'Statement stmt = conn.createStatement();\nResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE name = \'" + userName + "\'");\n'
        path = _write_temp(code, ".java")
        try:
            findings = _scan_file(path, JAVA_RULES)
            sql_findings = [f for f in findings if "SQL" in f.rule_name]
            assert len(sql_findings) >= 1
        finally:
            os.unlink(path)

    def test_no_false_positives_on_clean_code(self):
        path = _write_temp('import os\nimport secrets\ndef secure_function():\n    return secrets.token_hex(32)\n', ".py")
        try:
            findings = _scan_file(path, PYTHON_RULES)
            assert len(findings) == 0, f"Clean code should have no findings, got {len(findings)}"
        finally:
            os.unlink(path)

    def test_finding_has_all_required_fields(self):
        path = _write_temp('cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n', ".py")
        try:
            findings = _scan_file(path, PYTHON_RULES)
            assert len(findings) >= 1
            d = findings[0].to_dict()
            for key in ["rule_id", "severity", "cwe_id", "file_path", "line_number",
                        "description", "remediation", "confidence"]:
                assert key in d, f"Missing key: {key}"
        finally:
            os.unlink(path)


class TestSASTDirectoryScanning:
    """Test directory-level scanning."""

    def test_scan_nonexistent_path(self):
        result = run_sast_scan("/nonexistent/path")
        assert result.total_files_scanned == 0
        assert len(result.errors) > 0

    def test_scan_single_python_file(self):
        path = _write_temp('import os\npassword = "hardcoded_secret"\nos.system("echo " + user_input)\n', ".py")
        try:
            result = run_sast_scan(path)
            assert result.total_files_scanned == 1
            assert len(result.findings) >= 2
            assert "python" in result.languages_detected
        finally:
            os.unlink(path)

    def test_scan_directory_with_multiple_files(self):
        tmpdir = tempfile.mkdtemp()
        try:
            _write_temp_in_dir(tmpdir, 'password = "secret123"\n', "app.py")
            _write_temp_in_dir(tmpdir, 'eval(userInput);\n', "server.js")

            result = run_sast_scan(tmpdir)
            assert result.total_files_scanned == 2
            assert "python" in result.languages_detected
            assert "javascript" in result.languages_detected
            assert len(result.findings) >= 2
        finally:
            shutil.rmtree(tmpdir)

    def test_scan_skips_node_modules(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "node_modules", "pkg"))
            _write_temp_in_dir(os.path.join(tmpdir, "node_modules", "pkg"), 'eval(userInput);\n', "index.js")
            _write_temp_in_dir(tmpdir, 'console.log("hello");\n', "app.js")

            result = run_sast_scan(tmpdir)
            assert result.total_files_scanned == 1
        finally:
            shutil.rmtree(tmpdir)

    def test_scan_skips_venv(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "venv", "lib"))
            _write_temp_in_dir(os.path.join(tmpdir, "venv", "lib"), 'password = "secret"\n', "helper.py")
            _write_temp_in_dir(tmpdir, 'import os\n', "app.py")

            result = run_sast_scan(tmpdir)
            assert result.total_files_scanned == 1
        finally:
            shutil.rmtree(tmpdir)

    def test_findings_sorted_by_severity(self):
        tmpdir = tempfile.mkdtemp()
        try:
            _write_temp_in_dir(tmpdir, 'pickle.loads(data)\nhashlib.md5(value)\n', "mixed.py")

            result = run_sast_scan(tmpdir)
            if len(result.findings) >= 2:
                severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
                for i in range(len(result.findings) - 1):
                    s1 = severity_order.get(result.findings[i].severity, 5)
                    s2 = severity_order.get(result.findings[i+1].severity, 5)
                    assert s1 <= s2, "Findings should be sorted by severity"
        finally:
            shutil.rmtree(tmpdir)

    def test_summary_includes_severity_counts(self):
        path = _write_temp('pickle.loads(data)\nhashlib.md5(value)\npassword = "secret123"\n', ".py")
        try:
            result = run_sast_scan(path)
            summary = result.summary
            assert "total_findings" in summary
            assert "severity_counts" in summary
            assert "files_scanned" in summary
            assert summary["files_scanned"] == 1
        finally:
            os.unlink(path)
