"""Comprehensive security hardening tests.

Tests cover:
- Input sanitization & XSS protection
- SSRF protection & URL validation
- File upload security
- Threat detection (suspicious login, brute force)
- IP reputation
- Security headers
- WebSocket authentication
- Password reset security
- Session monitoring
"""

import io
import json

import pytest

from app.utils.sanitization import (
    contains_xss,
    detect_path_traversal,
    detect_sql_injection,
    escape_for_attribute,
    escape_for_javascript,
    escape_html,
    sanitize_filename,
    sanitize_input,
    validate_email_domain,
    validate_url,
)
from app.utils.ssrf_protection import (
    is_internal_ip,
    validate_file_upload,
    validate_url_safety,
)
from app.utils.threat_detection import (
    assess_login,
    check_ip_reputation,
    detect_brute_force_pattern,
    get_active_sessions,
    get_security_events,
    get_security_stats,
    is_ip_blocked,
    record_failed_login,
    record_ip_attempt,
    record_successful_login,
    register_session,
)


# ── XSS Protection Tests ──────────────────────────────────────────────


class TestXSSProtection:
    def test_escape_html_basic(self):
        assert escape_html("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_escape_html_quotes(self):
        assert escape_html('"><img onerror=alert(1)>') == "&quot;&gt;&lt;img onerror=alert(1)&gt;"

    def test_escape_html_ampersand(self):
        assert escape_html("a & b") == "a &amp; b"

    def test_escape_html_safe(self):
        assert escape_html("Hello World") == "Hello World"

    def test_escape_html_empty(self):
        assert escape_html("") == ""

    def test_escape_html_none_like(self):
        assert escape_html(None) == "None"

    def test_contains_xss_script_tag(self):
        assert contains_xss("<script>alert(1)</script>") is True

    def test_contains_xss_event_handler(self):
        assert contains_xss('<img onerror="alert(1)">') is True

    def test_contains_xss_javascript_protocol(self):
        assert contains_xss('javascript:alert(1)') is True

    def test_contains_xss_iframe(self):
        assert contains_xss('<iframe src="evil.com">') is True

    def test_contains_xss_data_uri(self):
        assert contains_xss('data:text/html,<script>alert(1)</script>') is True

    def test_contains_xss_svg(self):
        assert contains_xss('<svg onload="alert(1)">') is True

    def test_no_xss_safe_text(self):
        assert contains_xss("Hello World 123") is False

    def test_no_xss_empty(self):
        assert contains_xss("") is False

    def test_escape_for_javascript(self):
        result = escape_for_javascript("it's a \"test\"")
        assert "\\'" in result
        assert '\\"' in result

    def test_escape_for_javascript_xss(self):
        result = escape_for_javascript("<script>")
        assert "\\x3c" in result
        assert "\\x3e" in result

    def test_escape_for_attribute(self):
        result = escape_for_attribute('value" onclick="alert(1)')
        assert "onclick" not in result or "&#x27;" in result or "&quot;" in result


# ── SQL Injection Detection Tests ─────────────────────────────────────


class TestSQLInjection:
    def test_detect_union_select(self):
        assert detect_sql_injection("1 UNION SELECT * FROM users") is True

    def test_detect_drop_table(self):
        assert detect_sql_injection("'; DROP TABLE users; --") is True

    def test_detect_or_1_eq_1(self):
        assert detect_sql_injection("' OR '1'='1") is True

    def test_detect_comment(self):
        assert detect_sql_injection("admin'--") is True

    def test_detect_sleep(self):
        assert detect_sql_injection("1' AND SLEEP(5)--") is True

    def test_no_sql_injection_safe(self):
        assert detect_sql_injection("Hello World") is False

    def test_no_sql_injection_empty(self):
        assert detect_sql_injection("") is False

    def test_detect_benchmark(self):
        assert detect_sql_injection("1' AND BENCHMARK(1000000,SHA1('test'))--") is True


# ── Path Traversal Tests ──────────────────────────────────────────────


class TestPathTraversal:
    def test_detect_dot_dot_slash(self):
        assert detect_path_traversal("../../../etc/passwd") is True

    def test_detect_encoded(self):
        assert detect_path_traversal("%2e%2e%2f") is True

    def test_detect_backslash(self):
        assert detect_path_traversal("..\\..\\windows\\system32") is True

    def test_no_traversal_safe(self):
        assert detect_path_traversal("uploads/file.json") is False

    def test_no_traversal_empty(self):
        assert detect_path_traversal("") is False


# ── Filename Sanitization Tests ───────────────────────────────────────


class TestFilenameSanitization:
    def test_sanitize_path_traversal(self):
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_sanitize_null_bytes(self):
        result = sanitize_filename("file\x00.json")
        assert "\x00" not in result

    def test_sanitize_dangerous_chars(self):
        result = sanitize_filename('file"<>`name.json')
        assert '"' not in result
        assert "<" not in result

    def test_sanitize_empty(self):
        result = sanitize_filename("")
        assert result == "unnamed"

    def test_sanitize_long_name(self):
        long_name = "a" * 300 + ".json"
        result = sanitize_filename(long_name)
        assert len(result) <= 255


# ── URL Validation Tests ──────────────────────────────────────────────


class TestURLValidation:
    def test_valid_http(self):
        assert validate_url("https://example.com/api") is True

    def test_block_javascript(self):
        assert validate_url("javascript:alert(1)") is False

    def test_block_data(self):
        assert validate_url("data:text/html,<script>alert(1)</script>") is False

    def test_block_file(self):
        assert validate_url("file:///etc/passwd") is False

    def test_block_userinfo(self):
        assert validate_url("https://user:pass@example.com") is False

    def test_empty_url(self):
        assert validate_url("") is False

    def test_ftp_blocked(self):
        assert validate_url("ftp://example.com/file") is False


# ── SSRF Protection Tests ─────────────────────────────────────────────


class TestSSRFProtection:
    def test_block_localhost(self):
        assert is_internal_ip("localhost") is True

    def test_block_loopback(self):
        assert is_internal_ip("127.0.0.1") is True

    def test_block_private_10(self):
        assert is_internal_ip("10.0.0.1") is True

    def test_block_private_192(self):
        assert is_internal_ip("192.168.1.1") is True

    def test_block_private_172(self):
        assert is_internal_ip("172.16.0.1") is True

    def test_block_metadata(self):
        assert is_internal_ip("169.254.169.254") is True

    def test_block_gcp_metadata(self):
        assert is_internal_ip("metadata.google.internal") is True

    def test_validate_url_safety_safe(self):
        safe, reason = validate_url_safety("https://example.com")
        assert safe is True

    def test_validate_url_safety_ssrf(self):
        safe, reason = validate_url_safety("http://169.254.169.254/latest/meta-data/")
        assert safe is False
        assert "metadata" in reason.lower() or "internal" in reason.lower()

    def test_validate_url_safety_localhost(self):
        safe, reason = validate_url_safety("http://localhost:8080/admin")
        assert safe is False

    def test_validate_url_safety_empty(self):
        safe, reason = validate_url_safety("")
        assert safe is False


# ── File Upload Security Tests ────────────────────────────────────────


class TestFileUploadSecurity:
    def test_valid_json(self):
        content = json.dumps({"openapi": "3.0.0"}).encode()
        valid, reason = validate_file_upload("spec.json", content)
        assert valid is True

    def test_invalid_extension(self):
        valid, reason = validate_file_upload("malware.exe", b"test")
        assert valid is False
        assert "not allowed" in reason

    def test_oversized_file(self):
        valid, reason = validate_file_upload("big.json", b"x" * 10_000_000, max_size_bytes=5_000_000)
        assert valid is False
        assert "too large" in reason

    def test_empty_file(self):
        valid, reason = validate_file_upload("empty.json", b"")
        assert valid is False
        assert "empty" in reason.lower()

    def test_null_bytes(self):
        valid, reason = validate_file_upload("inject.json", b"{\x00\x00\x00}")
        assert valid is False
        assert "null" in reason

    def test_invalid_utf8(self):
        valid, reason = validate_file_upload("binary.json", b"\xff\xfe\xfd")
        assert valid is False


# ── Threat Detection Tests ────────────────────────────────────────────


class TestThreatDetection:
    def test_assess_login_low_risk(self):
        assessment = assess_login("user1", "1.2.3.4", "Mozilla/5.0")
        assert assessment.risk_level == "low"

    def test_ip_reputation_initial(self):
        rep = check_ip_reputation("1.2.3.4")
        assert rep["status"] == "active"
        assert rep["failures"] == 0

    def test_ip_failure_tracking(self):
        ip = "10.0.0.99"
        for _ in range(5):
            record_ip_attempt(ip, False, "test")
        rep = check_ip_reputation(ip)
        assert rep["failures"] >= 5

    def test_ip_block(self):
        ip = "10.0.0.100"
        for _ in range(12):
            record_ip_attempt(ip, False, "test")
        assert is_ip_blocked(ip) is True

    def test_failed_login_tracking(self):
        record_failed_login("testuser", "1.2.3.4", "Mozilla/5.0")
        analysis = detect_brute_force_pattern("testuser")
        assert analysis["failures_last_hour"] >= 1

    def test_successful_login_tracking(self):
        record_successful_login("testuser2", "5.6.7.8", "Chrome/100")
        sessions = get_active_sessions(999)  # wrong user
        assert len(sessions) == 0  # different user

    def test_security_stats(self):
        stats = get_security_stats()
        assert "total_events" in stats
        assert "blocked_ips" in stats
        assert "active_sessions" in stats

    def test_security_events(self):
        events = get_security_events(limit=10)
        assert isinstance(events, list)

    def test_security_events_filter(self):
        events = get_security_events(severity="critical", limit=10)
        for e in events:
            assert e["severity"] == "critical"

    def test_brute_force_detection(self):
        for _ in range(6):
            record_failed_login("brute_target", "1.2.3.4", "bot")
        analysis = detect_brute_force_pattern("brute_target")
        assert analysis["is_likely_brute_force"] is True


# ── Session Monitoring Tests ──────────────────────────────────────────


class TestSessionMonitoring:
    def test_register_session(self):
        result = register_session("token_hash_abc", 1, "1.2.3.4", "Chrome")
        assert result is True

    def test_get_active_sessions(self):
        register_session("token_hash_def", 2, "5.6.7.8", "Firefox")
        sessions = get_active_sessions(2)
        assert len(sessions) >= 1

    def test_session_different_user(self):
        register_session("token_hash_ghi", 3, "1.2.3.4", "Chrome")
        sessions = get_active_sessions(999)
        assert len(sessions) == 0


# ── Password Reset Security Tests ─────────────────────────────────────


class TestPasswordResetSecurity:
    def test_forgot_password_never_leaks_token(self, client):
        """Verify that forgot-password never returns raw tokens."""
        # Register a user first
        resp = client.post(
            "/api/auth/register",
            json={"username": "resetuser", "email": "reset@test.example.com", "password": "TestPass123!"},
        )
        assert resp.status_code == 201

        # Request password reset
        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "reset@test.example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # The token should NEVER be in the response
        assert data.get("reset_token") is None

    def test_forgot_password_nonexistent_email(self, client):
        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@test.example.com"},
        )
        assert resp.status_code == 200
        # Should not reveal whether email exists
        assert resp.json().get("reset_token") is None


# ── Security Headers Tests ────────────────────────────────────────────


class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-XSS-Protection") == "0"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in resp.headers

    def test_csp_header(self, client):
        resp = client.get("/dashboard")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp

    def test_cross_origin_headers(self, client):
        resp = client.get("/")
        assert "Cross-Origin-Opener-Policy" in resp.headers
        assert "Cross-Origin-Resource-Policy" in resp.headers

    def test_no_server_header(self, client):
        resp = client.get("/")
        # Server header should be stripped
        assert resp.headers.get("server") is None or resp.headers.get("Server") is None


# ── WebSocket Authentication Tests ────────────────────────────────────


class TestWebSocketSecurity:
    def test_websocket_requires_token(self, client):
        """WebSocket without token should be rejected."""
        with client.websocket_connect("/ws/scan/nonexistent") as ws:
            data = ws.receive_json()
            assert "error" in data or "Authentication" in str(data)

    def test_websocket_invalid_token(self, client):
        """WebSocket with invalid token should be rejected."""
        with client.websocket_connect("/ws/scan/nonexistent?token=invalid") as ws:
            data = ws.receive_json()
            assert "error" in data


# ── Email Validation Tests ────────────────────────────────────────────


class TestEmailValidation:
    def test_valid_email(self):
        assert validate_email_domain("user@example.com") is True

    def test_invalid_email(self):
        assert validate_email_domain("not-an-email") is False

    def test_empty_email(self):
        assert validate_email_domain("") is False

    def test_allowed_domains(self):
        assert validate_email_domain("user@company.com", ["company.com"]) is True
        assert validate_email_domain("user@other.com", ["company.com"]) is False


# ── Input Sanitization Tests ──────────────────────────────────────────


class TestInputSanitization:
    def test_sanitize_basic(self):
        result = sanitize_input("Hello World")
        assert result == "Hello World"

    def test_sanitize_null_bytes(self):
        result = sanitize_input("test\x00input")
        assert "\x00" not in result

    def test_sanitize_max_length(self):
        result = sanitize_input("a" * 2000, max_length=100)
        assert len(result) <= 100

    def test_sanitize_whitespace(self):
        result = sanitize_input("  hello  ")
        assert result == "hello"

    def test_sanitize_empty(self):
        result = sanitize_input("")
        assert result == ""
