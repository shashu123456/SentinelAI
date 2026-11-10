"""Example Scanner Plugin — Security Headers Scanner.

Demonstrates how to implement a scanner plugin that checks HTTP security
headers for an API endpoint. This plugin extends the built-in scanning
with header-specific checks.
"""

from __future__ import annotations

from app.core.plugins.sdk import (
    PluginContext,
    PluginManifest,
    PluginPermission,
    ScannerPlugin,
)


class SecurityHeadersScannerPlugin(ScannerPlugin):
    """Scanner plugin that checks API security headers configuration."""

    manifest = PluginManifest(
        id="security-headers-scanner",
        name="Security Headers Scanner",
        version="1.0.0",
        plugin_type="scanner",
        description=(
            "Scans OpenAPI specifications for missing or weak HTTP security "
            "header configurations including CSP, HSTS, X-Frame-Options, "
            "and CORS settings."
        ),
        author="SentinelAI",
        license="MIT",
        min_platform_version="1.0.0",
        permissions=[
            PluginPermission.SCANNER_READ,
            PluginPermission.FINDINGS_WRITE,
        ],
        tags=["security", "headers", "owasp", "csp", "hsts"],
    )

    # Required headers that should be configured
    REQUIRED_HEADERS = {
        "content-security-policy": {
            "severity": "High",
            "cwe": "CWE-693",
            "description": "Content Security Policy not configured",
            "remediation": (
                "Implement a Content-Security-Policy header to prevent XSS, "
                "code injection, and other code injection attacks."
            ),
        },
        "strict-transport-security": {
            "severity": "High",
            "cwe": "CWE-319",
            "description": "HTTP Strict Transport Security not configured",
            "remediation": (
                "Implement HSTS with max-age of at least 31536000 seconds "
                "(1 year) and includeSubDomains."
            ),
        },
        "x-content-type-options": {
            "severity": "Medium",
            "cwe": "CWE-693",
            "description": "X-Content-Type-Options not configured",
            "remediation": "Set X-Content-Type-Options: nosniff to prevent MIME sniffing.",
        },
        "x-frame-options": {
            "severity": "Medium",
            "cwe": "CWE-1021",
            "description": "X-Frame-Options not configured",
            "remediation": "Set X-Frame-Options: DENY or SAMEORIGIN to prevent clickjacking.",
        },
    }

    def scan(self, context: PluginContext) -> list[dict]:
        """Scan for missing security headers in the API specification."""
        findings = []
        parsed_api = context.config.get("parsed_api", {})

        # Check if servers define security headers
        servers = parsed_api.get("servers", [])
        has_https = any(
            s.get("url", "").startswith("https://") if isinstance(s, dict) else False
            for s in servers
        )

        if not has_https:
            findings.append(
                self._make_finding(
                    "HTTPS Not Enforced",
                    "API8",
                    "High",
                    "API servers do not enforce HTTPS. All API communication should use TLS.",
                    "No HTTPS server URLs found in the specification.",
                    "Data in transit can be intercepted and modified by attackers.",
                    "Configure all server URLs to use HTTPS and implement HSTS.",
                )
            )

        # Check for response headers that should be defined
        endpoints = parsed_api.get("endpoints", [])
        auth_endpoints = [
            ep
            for ep in endpoints
            if any(
                kw in ep.get("path", "").lower() for kw in ("login", "auth", "token", "password")
            )
        ]

        if auth_endpoints and not any(
            "429" in str(ep.get("responses", {})) for ep in auth_endpoints
        ):
            findings.append(
                self._make_finding(
                    "Missing Rate Limit Headers on Auth Endpoints",
                    "API4",
                    "Medium",
                    "Authentication endpoints do not define rate limiting headers.",
                    f"{len(auth_endpoints)} auth endpoints found without 429 responses.",
                    "Without rate limiting, brute-force attacks are possible.",
                    "Implement rate limiting with Retry-After and X-RateLimit headers.",
                )
            )

        return findings

    def get_scan_types(self) -> list[str]:
        return ["security_headers"]

    def get_supported_formats(self) -> list[str]:
        return ["openapi", "swagger"]

    def _make_finding(
        self,
        name: str,
        owasp_cat: str,
        severity: str,
        description: str,
        evidence: str,
        impact: str,
        remediation: str,
    ) -> dict:
        from app.utils.cvss import compute_cvss_score

        cvss_score, cvss_vector = compute_cvss_score(
            severity=severity, owasp_category=owasp_cat, confidence=80
        )
        return {
            "vulnerability_name": name,
            "owasp_category": owasp_cat,
            "cwe_id": "N/A",
            "severity": severity,
            "confidence": 80,
            "description": description,
            "evidence": evidence,
            "impact": impact,
            "remediation": remediation,
            "cvss_score": cvss_score,
            "cvss_vector": cvss_vector,
        }
