import re
from collections.abc import Callable
from typing import TypedDict

OWASP_CATEGORIES = {
    "API1": "Broken Object Level Authorization",
    "API2": "Broken Authentication",
    "API3": "Broken Object Property Level Authorization",
    "API4": "Unrestricted Resource Consumption",
    "API5": "Broken Function Level Authorization",
    "API6": "Unrestricted Access to Sensitive Business Flows",
    "API7": "Server Side Request Forgery",
    "API8": "Security Misconfiguration",
    "API9": "Improper Inventory Management",
    "API10": "Unsafe Consumption of APIs",
}

OWASP_TO_CWE = {
    "API1": "CWE-639",
    "API2": "CWE-287",
    "API3": "CWE-200",
    "API4": "CWE-770",
    "API5": "CWE-862",
    "API6": "CWE-284",
    "API7": "CWE-918",
    "API8": "CWE-16",
    "API9": "CWE-200",
    "API10": "CWE-918",
}


def run_owasp_scan(parsed_api: dict) -> list[dict]:
    findings = []
    executed = set()
    for check in CHECK_REGISTRY:
        fn = check["check"]
        if fn in executed:
            continue
        executed.add(fn)
        findings.extend(fn(parsed_api))
    return findings


def _make_finding(
    vuln_name: str,
    owasp_cat: str,
    severity: str,
    description: str,
    evidence: str,
    impact: str,
    remediation: str,
    endpoint: str | None = None,
    method: str | None = None,
    confidence: int = 85,
    detection_reason: str = "",
    cwe_id: str | None = None,
) -> dict:
    from app.utils.cvss import compute_cvss_score

    cvss_score, cvss_vector = compute_cvss_score(
        severity=severity,
        owasp_category=owasp_cat,
        confidence=confidence,
    )

    return {
        "vulnerability_name": vuln_name,
        "owasp_category": owasp_cat,
        "cwe_id": cwe_id or OWASP_TO_CWE.get(owasp_cat, "N/A"),
        "severity": severity,
        "confidence": confidence,
        "description": description,
        "evidence": evidence,
        "impact": impact,
        "remediation": remediation,
        "affected_endpoint": endpoint,
        "affected_method": method,
        "detection_reason": detection_reason,
        "cvss_score": cvss_score,
        "cvss_vector": cvss_vector,
        "false_positive_note": "This is a potential vulnerability identified through static analysis of the API specification. Manual verification is recommended to confirm exploitability in the deployed environment.",
    }


# =============================================================================
# API1 — Broken Object Level Authorization
# =============================================================================


def _check_api1_broken_object_level_authorization(parsed_api: dict) -> list[dict]:
    findings: list[dict] = []
    paths_with_ids = []

    for ep in parsed_api["endpoints"]:
        path = ep["path"]
        if re.search(r"/\{.*id\}|/\{.*_id\}|/\{.*Id\}", path):
            paths_with_ids.append(ep)

    if not paths_with_ids:
        return findings

    for ep in paths_with_ids:
        params = ep.get("parameters", [])
        path_params = [p for p in params if p.get("in") == "path"]
        has_user_scoping = any(
            "user" in p.get("name", "").lower() or "tenant" in p.get("name", "").lower()
            for p in params
        )

        if not has_user_scoping:
            findings.append(
                _make_finding(
                    vuln_name="Potential Object Level Authorization Bypass",
                    owasp_cat="API1",
                    severity="High",
                    description=(
                        f"Endpoint '{ep['method']} {ep['path']}' accesses resources by ID "
                        "but lacks explicit user-scoped authorization checks. Attackers may "
                        "manipulate object IDs to access unauthorized data."
                    ),
                    evidence=f"Path parameter(s) found without user-scoping: {[p['name'] for p in path_params]}",
                    impact="Unauthorized access to other users' data, leading to data breaches and privacy violations.",
                    remediation=(
                        "Implement object-level authorization checks for every request. "
                        "Use indirect object references and verify the authenticated user "
                        "owns or is authorized to access the requested resource."
                    ),
                    endpoint=ep["path"],
                    method=ep["method"],
                    confidence=75,
                    detection_reason="Path parameter with 'id' pattern detected without user-scoping authorization context in the endpoint security definition.",
                )
            )

    return findings


# =============================================================================
# API2 — Broken Authentication
# =============================================================================


def _check_api2_broken_authentication(parsed_api: dict) -> list[dict]:
    findings = []
    unauthenticated_endpoints = []
    sensitive_methods = {"POST", "PUT", "DELETE", "PATCH"}

    for ep in parsed_api["endpoints"]:
        if not ep.get("auth_required"):
            if ep["method"] in sensitive_methods:
                unauthenticated_endpoints.append(ep)
            if _is_sensitive_path(ep["path"]):
                unauthenticated_endpoints.append(ep)

    seen = set()
    for ep in unauthenticated_endpoints:
        key = (ep["path"], ep["method"])
        if key in seen:
            continue
        seen.add(key)

        severity = "Critical" if ep["method"] in sensitive_methods else "High"
        is_sensitive_method = ep["method"] in sensitive_methods
        findings.append(
            _make_finding(
                vuln_name="Broken Authentication – Unprotected Endpoint",
                owasp_cat="API2",
                severity=severity,
                description=(
                    f"Endpoint '{ep['method']} {ep['path']}' does not require authentication. "
                    "This allows anonymous access to potentially sensitive operations."
                ),
                evidence=f"No security requirements defined. Auth type: {ep.get('auth_type', 'None')}",
                impact=(
                    "Attackers can perform unauthorized actions, access sensitive data, "
                    "and potentially take over accounts."
                ),
                remediation=(
                    "Enforce authentication on all endpoints that require user identification. "
                    "Use industry-standard authentication mechanisms (OAuth 2.0, JWT). "
                    "Implement proper token validation and expiration."
                ),
                endpoint=ep["path"],
                method=ep["method"],
                confidence=90 if is_sensitive_method else 80,
                detection_reason=(
                    f"Endpoint accepts state-changing HTTP methods ({ep['method']}) without any security requirements defined in the OpenAPI specification."
                    if is_sensitive_method
                    else f"Path '{ep['path']}' matches known sensitive resource patterns but lacks authentication requirements."
                ),
            )
        )

    return findings


def _check_weak_auth_scheme(parsed_api: dict) -> list[dict]:
    findings = []
    schemes = parsed_api.get("security_schemes", {}).get("schemes", {}) or {}

    for name, scheme in schemes.items():
        if not isinstance(scheme, dict):
            continue
        scheme_type = scheme.get("type", "")
        scheme_name = str(scheme.get("scheme", "")).lower()

        if scheme_type == "http" and scheme_name in ("basic", "digest"):
            findings.append(
                _make_finding(
                    vuln_name="Weak Authentication Scheme (HTTP Basic)",
                    owasp_cat="API2",
                    severity="High",
                    description=(
                        f"Security scheme '{name}' relies on HTTP {scheme.get('scheme')} authentication, "
                        "which transmits credentials in a weak, replayable encoding."
                    ),
                    evidence=f"Security scheme '{name}' uses type=http scheme={scheme.get('scheme')}",
                    impact=(
                        "Credentials sent via HTTP Basic are trivially base64-decoded and can be "
                        "replayed or brute-forced, leading to account takeover."
                    ),
                    remediation=(
                        "Replace HTTP Basic/Digest authentication with OAuth 2.0, OpenID Connect, "
                        "or signed token (JWT) mechanisms enforced over TLS."
                    ),
                    confidence=80,
                    detection_reason=f"Security scheme '{name}' is defined with the weak HTTP Basic/Digest authentication protocol.",
                    cwe_id="CWE-287",
                )
            )
        elif scheme_type == "apiKey" and scheme.get("in") == "query":
            findings.append(
                _make_finding(
                    vuln_name=f"API Key in Query String: '{name}'",
                    owasp_cat="API2",
                    severity="Medium",
                    description=(
                        f"Security scheme '{name}' passes API keys via query parameters, which "
                        "leak secrets into logs, browser history, and proxies."
                    ),
                    evidence=f"Security scheme '{name}' uses apiKey in=query",
                    impact="API keys can be exposed in access logs, browser history, referrer headers, and shared URLs.",
                    remediation="Transmit API keys via the Authorization header instead of the query string.",
                    confidence=85,
                    detection_reason=f"Security scheme '{name}' is defined as an apiKey transported in the query string.",
                    cwe_id="CWE-598",
                )
            )

    return findings


# =============================================================================
# API3 — Broken Object Property Level Authorization
# =============================================================================

SENSITIVE_PROPERTY_PATTERNS = [
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "admin",
    "role",
    "permission",
    "is_admin",
    "is_superuser",
    "internal",
    "debug",
    "credit_card",
    "ssn",
    "salary",
    "card_number",
    "cvv",
    "private_key",
    "client_secret",
    "otp",
    "pin",
]

SENSITIVE_QUERY_PARAMS = [
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "auth_token",
    "api_key",
    "apikey",
    "secret",
    "session",
    "session_id",
    "credential",
    "pin",
    "otp",
    "private_key",
]

SENSITIVE_RESPONSE_PROPERTIES = [
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "card_number",
    "cardnumber",
    "cvv",
    "ssn",
    "credit_card",
    "private_key",
    "client_secret",
    "internal_note",
    "otp",
]


def _check_api3_broken_object_property_level_authorization(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        if ep["method"] not in ("POST", "PUT", "PATCH"):
            continue

        request_body = ep.get("request_body")
        if not request_body:
            continue

        schema = _get_request_schema(request_body)
        if not schema:
            continue

        properties = schema.get("properties", {})
        for prop_name, prop_def in properties.items():
            prop_lower = prop_name.lower()
            for pattern in SENSITIVE_PROPERTY_PATTERNS:
                if pattern in prop_lower:
                    findings.append(
                        _make_finding(
                            vuln_name=f"Exposed Sensitive Property: '{prop_name}'",
                            owasp_cat="API3",
                            severity="High",
                            description=(
                                f"Property '{prop_name}' in the request body of "
                                f"'{ep['method']} {ep['path']}' may contain sensitive data "
                                "that should not be exposed to clients."
                            ),
                            evidence=f"Property '{prop_name}' found in request schema with type: {prop_def.get('type', 'unknown')}",
                            impact=(
                                "Over-exposure of object properties allows attackers to "
                                "modify privileged fields such as roles, permissions, or "
                                "internal flags."
                            ),
                            remediation=(
                                "Use response/request DTOs to control which properties are "
                                "exposed. Implement property-level authorization. Validate "
                                "and sanitize all input fields."
                            ),
                            endpoint=ep["path"],
                            method=ep["method"],
                            confidence=70,
                            detection_reason=f"Property '{prop_name}' in the request body schema matches known sensitive data patterns (e.g., credentials, PII, financial data).",
                        )
                    )
                    break

    return findings


def _check_sensitive_query_params(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        for p in ep.get("parameters", []):
            name = p.get("name", "")
            if p.get("in") == "query" and name.lower() in SENSITIVE_QUERY_PARAMS:
                findings.append(
                    _make_finding(
                        vuln_name=f"Sensitive Data in Query Parameter: '{name}'",
                        owasp_cat="API3",
                        severity="Medium",
                        description=(
                            f"Parameter '{name}' on '{ep['method']} {ep['path']}' carries "
                            "sensitive data in the query string."
                        ),
                        evidence=f"Query parameter '{name}' defined on {ep['method']} {ep['path']}",
                        impact=(
                            "Secrets and sensitive data in URLs are logged by servers and proxies "
                            "and exposed in browser history and referrer headers."
                        ),
                        remediation=(
                            "Move sensitive data into the request body or Authorization header; "
                            "enforce TLS and redact query strings in logs."
                        ),
                        endpoint=ep["path"],
                        method=ep["method"],
                        confidence=85,
                        detection_reason=f"Query parameter named '{name}' matches known sensitive-data naming patterns.",
                        cwe_id="CWE-598",
                    )
                )

    return findings


def _check_sensitive_response_fields(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        seen = set()
        for response in ep.get("response_schemas", []):
            schema = response.get("schema", {}) or {}
            properties = schema.get("properties", {}) or {}
            for prop_name in properties:
                prop_lower = prop_name.lower()
                if prop_lower in seen:
                    continue
                seen.add(prop_lower)
                if any(pattern in prop_lower for pattern in SENSITIVE_RESPONSE_PROPERTIES):
                    findings.append(
                        _make_finding(
                            vuln_name=f"Sensitive Data in Response Schema: '{prop_name}'",
                            owasp_cat="API3",
                            severity="High",
                            description=(
                                f"Response schema of '{ep['method']} {ep['path']}' exposes "
                                f"sensitive field '{prop_name}'."
                            ),
                            evidence=f"Property '{prop_name}' in {response.get('status_code', '?')} response",
                            impact=(
                                "Over-exposure of credentials, tokens, or PII in API responses "
                                "enables data theft and privilege escalation."
                            ),
                            remediation=(
                                "Remove sensitive fields from response payloads, return masked or "
                                "truncated values, and scope responses to least privilege."
                            ),
                            endpoint=ep["path"],
                            method=ep["method"],
                            confidence=70,
                            detection_reason=f"Response property '{prop_name}' matches known sensitive-data patterns (credentials, tokens, financial data).",
                            cwe_id="CWE-200",
                        )
                    )

    return findings


# =============================================================================
# API4 — Unrestricted Resource Consumption
# =============================================================================


def _check_api4_unrestricted_resource_consumption(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        params = ep.get("parameters", [])
        has_pagination = any(
            p.get("name", "").lower() in ("limit", "page", "offset", "size", "per_page")
            for p in params
        )

        if ep["method"] == "GET" and not has_pagination and not _is_health_or_meta(ep["path"]):
            findings.append(
                _make_finding(
                    vuln_name="No Pagination / Rate Limiting Detected",
                    owasp_cat="API4",
                    severity="Medium",
                    description=(
                        f"GET endpoint '{ep['path']}' does not define pagination parameters. "
                        "Without limits, clients can request unbounded datasets."
                    ),
                    evidence="No limit/page/offset parameters found in endpoint definition.",
                    impact=(
                        "Denial of service through resource exhaustion. Large data "
                        "retrieval can overwhelm databases and network bandwidth."
                    ),
                    remediation=(
                        "Implement mandatory pagination with configurable page sizes. "
                        "Add rate limiting per user/IP. Enforce maximum result set limits."
                    ),
                    endpoint=ep["path"],
                    method=ep["method"],
                    confidence=65,
                    detection_reason="GET endpoint does not define pagination parameters (limit, page, offset), indicating potential for unbounded data retrieval.",
                )
            )

    return findings


AUTH_PATH_PATTERNS = [
    r"login",
    r"signin",
    r"sign-in",
    r"auth",
    r"token",
    r"oauth",
    r"password",
    r"session",
    r"credential",
    r"register",
    r"signup",
    r"sign-up",
    r"otp",
    r"verify",
]


def _check_auth_rate_limiting(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        if ep["method"] != "POST":
            continue
        if not any(re.search(pattern, ep["path"], re.IGNORECASE) for pattern in AUTH_PATH_PATTERNS):
            continue

        responses = ep.get("responses", {}) or {}
        has_429 = "429" in responses
        if not has_429:
            findings.append(
                _make_finding(
                    vuln_name="Authentication Endpoint Missing Rate Limiting",
                    owasp_cat="API4",
                    severity="Medium",
                    description=(
                        f"Authentication-related endpoint '{ep['method']} {ep['path']}' does not "
                        "define rate limiting (HTTP 429) controls."
                    ),
                    evidence=f"No 429 Too Many Requests response defined on {ep['method']} {ep['path']}",
                    impact="Brute-force attacks on credentials, OTP guessing, and account enumeration are unmitigated.",
                    remediation=(
                        "Enforce per-IP/per-account rate limiting with account lockout, CAPTCHA, "
                        "and monitor for credential stuffing."
                    ),
                    endpoint=ep["path"],
                    method=ep["method"],
                    confidence=65,
                    detection_reason=f"Endpoint '{ep['path']}' is authentication-related and lacks a 429 rate-limit response definition.",
                    cwe_id="CWE-770",
                )
            )

    return findings


def _check_unbounded_body(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        request_body = ep.get("request_body")
        if not request_body:
            continue

        schema = _get_request_schema(request_body)
        if not schema:
            continue

        properties = schema.get("properties", {}) or {}
        unbounded_fields = []
        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                continue
            prop_type = prop_def.get("type")
            if (
                prop_type == "string"
                and "maxLength" not in prop_def
                or (
                    prop_type in ("array", "object")
                    and "maxItems" not in prop_def
                    and "maxProperties" not in prop_def
                )
                or prop_type == "integer"
                and "maximum" not in prop_def
            ):
                unbounded_fields.append(prop_name)

        if unbounded_fields:
            findings.append(
                _make_finding(
                    vuln_name="Unbounded Request Body Fields",
                    owasp_cat="API4",
                    severity="Medium",
                    description=(
                        f"Request body of '{ep['method']} {ep['path']}' defines fields without "
                        f"size or maximum constraints: {unbounded_fields}."
                    ),
                    evidence=f"Unbounded fields: {unbounded_fields}",
                    impact="Oversized or deeply nested payloads can exhaust server memory and CPU, enabling denial of service.",
                    remediation=(
                        "Define maxLength/maxItems/maximum constraints on all input fields and "
                        "enforce payload size limits at the gateway."
                    ),
                    endpoint=ep["path"],
                    method=ep["method"],
                    confidence=60,
                    detection_reason=f"Request body fields {unbounded_fields} lack size constraints (maxLength/maxItems/maximum).",
                    cwe_id="CWE-770",
                )
            )

    return findings


# =============================================================================
# API5 — Broken Function Level Authorization
# =============================================================================

ADMIN_PATH_PATTERNS = [
    r"/admin",
    r"/manage",
    r"/internal",
    r"/system",
    r"/debug",
    r"/_internal",
    r"/console",
    r"/panel",
]

DEBUG_PATH_PATTERNS = [
    r"/debug",
    r"/internal",
    r"/actuator",
    r"/metrics",
    r"/trace",
    r"/env",
    r"/heapdump",
    r"/threaddump",
    r"/console",
    r"/api-docs",
    r"/swagger",
    r"/graphql",
    r"/druid",
    r"/h2-console",
]


def _check_api5_broken_function_level_authorization(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        for pattern in ADMIN_PATH_PATTERNS:
            if re.search(pattern, ep["path"], re.IGNORECASE):
                if not ep.get("auth_required"):
                    findings.append(
                        _make_finding(
                            vuln_name="Admin Endpoint Without Authorization",
                            owasp_cat="API5",
                            severity="Critical",
                            description=(
                                f"Administrative endpoint '{ep['method']} {ep['path']}' "
                                "has no authentication/authorization requirements."
                            ),
                            evidence=f"Path matches admin pattern '{pattern}' with no security definition.",
                            impact="Full system compromise. Attackers can perform administrative actions without credentials.",
                            remediation=(
                                "Enforce role-based access control (RBAC) on all administrative endpoints. "
                                "Require elevated privileges and audit all admin operations."
                            ),
                            endpoint=ep["path"],
                            method=ep["method"],
                            confidence=80,
                            detection_reason=f"Path '{ep['path']}' matches administrative endpoint pattern with no authentication requirement.",
                        )
                    )
                else:
                    findings.append(
                        _make_finding(
                            vuln_name="Admin Endpoint – Verify Role-Based Access",
                            owasp_cat="API5",
                            severity="Medium",
                            description=(
                                f"Endpoint '{ep['method']} {ep['path']}' is an admin endpoint "
                                "with basic authentication. Verify that role-based authorization "
                                "is also enforced."
                            ),
                            evidence="Endpoint has security defined but may lack role verification.",
                            impact="Users with basic authentication may access admin functions.",
                            remediation="Implement role-based authorization checks. Verify user roles before granting access to admin endpoints.",
                            endpoint=ep["path"],
                            method=ep["method"],
                            confidence=70,
                            detection_reason=f"Path '{ep['path']}' matches administrative endpoint pattern. Basic authentication detected but role-based authorization is not verified.",
                        )
                    )
                break

    return findings


def _check_debug_endpoints(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        if ep.get("auth_required"):
            continue
        if not any(
            re.search(pattern, ep["path"], re.IGNORECASE) for pattern in DEBUG_PATH_PATTERNS
        ):
            continue

        findings.append(
            _make_finding(
                vuln_name="Exposed Debug/Info Endpoint",
                owasp_cat="API5",
                severity="High",
                description=(
                    f"Endpoint '{ep['method']} {ep['path']}' is a debug/internal/introspection "
                    "endpoint exposed without authentication."
                ),
                evidence="Path matches debug/introspection pattern and has no security requirements.",
                impact=(
                    "Information disclosure of internals, environment variables, metrics, or schema "
                    "introspection aids reconnaissance and exploitation."
                ),
                remediation=(
                    "Restrict debug and introspection endpoints to authenticated administrators on "
                    "isolated networks, or disable them in production."
                ),
                endpoint=ep["path"],
                method=ep["method"],
                confidence=75,
                detection_reason=f"Path '{ep['path']}' matches debug/internal/introspection patterns and requires no authentication.",
                cwe_id="CWE-200",
            )
        )

    return findings


# =============================================================================
# API6 — Unrestricted Access to Sensitive Business Flows
# =============================================================================


def _check_api6_unrestricted_access_to_sensitive_business_flows(parsed_api: dict) -> list[dict]:
    findings = []
    sensitive_flow_patterns = [
        (r"/(purchase|buy|order|checkout|payment|transfer|withdraw)", "Financial Transaction"),
        (r"/(signup|register|create.*account)", "Account Creation"),
        (r"/(invite|share|grant)", "Access Granting"),
        (r"/(message|send|email|notify)", "Communication Flow"),
    ]

    for ep in parsed_api["endpoints"]:
        if ep["method"] not in ("POST", "PUT", "DELETE"):
            continue

        for pattern, flow_name in sensitive_flow_patterns:
            if re.search(pattern, ep["path"], re.IGNORECASE):
                if not ep.get("auth_required"):
                    findings.append(
                        _make_finding(
                            vuln_name=f"Unprotected {flow_name} Flow",
                            owasp_cat="API6",
                            severity="High",
                            description=(
                                f"Sensitive business flow '{flow_name}' at "
                                f"'{ep['method']} {ep['path']}' lacks authentication. "
                                "Automated bots could abuse this endpoint."
                            ),
                            evidence=f"Path matches sensitive flow pattern '{pattern}' without security.",
                            impact=(
                                "Business logic abuse, automated fraud, data scraping, "
                                "and resource exhaustion through abuse of business flows."
                            ),
                            remediation=(
                                "Implement CAPTCHA, rate limiting, and device fingerprinting "
                                "on sensitive business flows. Require strong authentication. "
                                "Monitor for anomalous usage patterns."
                            ),
                            endpoint=ep["path"],
                            method=ep["method"],
                            confidence=72,
                            detection_reason=f"Path '{ep['path']}' matches sensitive business flow pattern '{flow_name}' without authentication requirements.",
                        )
                    )
                break

    return findings


# =============================================================================
# API7 — Server Side Request Forgery
# =============================================================================

SSRF_URL_KEYWORDS = (
    "url",
    "uri",
    "link",
    "href",
    "webhook",
    "callback",
    "redirect",
    "proxy",
    "target",
    "host",
)
REDIRECT_KEYWORDS = (
    "redirect",
    "return",
    "next",
    "callback",
    "continue",
    "goto",
    "url",
    "dest",
    "target",
    "link",
    "forward",
)


def _check_api7_server_side_request_forgery(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        params = ep.get("parameters", [])
        request_body = ep.get("request_body")

        url_params = []
        for p in params:
            name_lower = p.get("name", "").lower()
            if any(kw in name_lower for kw in SSRF_URL_KEYWORDS):
                url_params.append(p["name"])

        if request_body:
            schema = _get_request_schema(request_body)
            if schema:
                for prop_name, _ in schema.get("properties", {}).items():
                    prop_lower = prop_name.lower()
                    if any(kw in prop_lower for kw in SSRF_URL_KEYWORDS):
                        url_params.append(prop_name)

        if url_params:
            findings.append(
                _make_finding(
                    vuln_name="Potential SSRF via URL Parameter",
                    owasp_cat="API7",
                    severity="High",
                    description=(
                        f"Endpoint '{ep['method']} {ep['path']}' accepts URL-type parameters "
                        f"({url_params}) that could be exploited for Server-Side Request Forgery."
                    ),
                    evidence=f"URL parameters identified: {url_params}",
                    impact=(
                        "Attackers can make the server send requests to internal services, "
                        "access cloud metadata endpoints, or exfiltrate data from internal networks."
                    ),
                    remediation=(
                        "Validate and sanitize all URL inputs against an allowlist. "
                        "Use a dedicated URL validation library. Restrict outbound network "
                        "access. Block internal IP ranges and metadata endpoints."
                    ),
                    endpoint=ep["path"],
                    method=ep["method"],
                    confidence=78,
                    detection_reason=f"Parameter(s) {url_params} accept URL-type input that could be used to make server-side requests to arbitrary destinations.",
                )
            )

    return findings


def _check_open_redirect(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        redirect_params = []
        for p in ep.get("parameters", []):
            name = p.get("name", "").lower()
            if p.get("in") == "query" and any(kw in name for kw in REDIRECT_KEYWORDS):
                redirect_params.append(p["name"])

        request_body = ep.get("request_body")
        if request_body:
            schema = _get_request_schema(request_body)
            if schema:
                for prop_name in schema.get("properties", {}) or {}:
                    if any(kw in prop_name.lower() for kw in REDIRECT_KEYWORDS):
                        redirect_params.append(prop_name)

        if redirect_params:
            findings.append(
                _make_finding(
                    vuln_name="Unvalidated Redirect/Callback URL",
                    owasp_cat="API7",
                    severity="Medium",
                    description=(
                        f"Endpoint '{ep['method']} {ep['path']}' accepts redirect/callback URLs "
                        f"({redirect_params}) without apparent allowlist validation."
                    ),
                    evidence=f"Redirect parameters: {redirect_params}",
                    impact="Open redirects enable phishing, credential harvesting, and OAuth token theft via crafted callback URLs.",
                    remediation=(
                        "Validate redirect targets against an explicit allowlist of trusted origins "
                        "and never trust client-supplied URLs."
                    ),
                    endpoint=ep["path"],
                    method=ep["method"],
                    confidence=68,
                    detection_reason=f"Parameter(s) {redirect_params} accept redirect/return URLs without documented allowlist validation.",
                    cwe_id="CWE-601",
                )
            )

    return findings


# =============================================================================
# API8 — Security Misconfiguration
# =============================================================================


def _check_api8_security_misconfiguration(parsed_api: dict) -> list[dict]:
    findings = []

    if not parsed_api.get("security_schemes", {}).get("schemes"):
        findings.append(
            _make_finding(
                vuln_name="No Security Schemes Defined",
                owasp_cat="API8",
                severity="High",
                description="The API specification does not define any security schemes (authentication mechanisms).",
                evidence="components.securitySchemes is empty or missing.",
                impact="The API may be deployed without proper authentication configuration.",
                remediation=(
                    "Define security schemes in the OpenAPI spec. Use OAuth 2.0, "
                    "API keys, or JWT-based authentication. Apply global security requirements."
                ),
                confidence=85,
                detection_reason="No securitySchemes defined in the API specification components.",
            )
        )

    if not parsed_api.get("security_schemes", {}).get("global_security"):
        findings.append(
            _make_finding(
                vuln_name="No Global Security Requirements",
                owasp_cat="API8",
                severity="Medium",
                description="No global security requirements are defined. Each endpoint must define its own security.",
                evidence="Top-level 'security' field is missing from the specification.",
                impact="Inconsistent authentication enforcement across endpoints.",
                remediation="Define global security requirements and override only where necessary.",
                confidence=70,
                detection_reason="No global security requirement defined at the specification root level.",
            )
        )

    for ep in parsed_api["endpoints"]:
        if ep.get("deprecated"):
            findings.append(
                _make_finding(
                    vuln_name="Deprecated Endpoint Still Exposed",
                    owasp_cat="API8",
                    severity="Low",
                    description=(
                        f"Endpoint '{ep['method']} {ep['path']}' is marked as deprecated "
                        "but is still included in the API specification."
                    ),
                    evidence="deprecated: true in operation definition.",
                    impact="Deprecated endpoints may contain unpatched vulnerabilities.",
                    remediation="Remove deprecated endpoints or redirect to their replacements. Maintain an API deprecation policy.",
                    endpoint=ep["path"],
                    method=ep["method"],
                    confidence=60,
                    detection_reason="Endpoint marked as deprecated but still present in the active specification.",
                )
            )

    return findings


def _check_insecure_transport(parsed_api: dict) -> list[dict]:
    findings = []
    servers = parsed_api.get("servers", []) or []
    insecure = []

    for server in servers:
        url = server.get("url", "") if isinstance(server, dict) else str(server)
        if url.startswith("http://"):
            insecure.append(url)

    if insecure:
        findings.append(
            _make_finding(
                vuln_name="Insecure Transport (HTTP)",
                owasp_cat="API8",
                severity="High",
                description=(
                    f"API server URLs use plain HTTP: {insecure}. "
                    "Traffic is transmitted without TLS encryption."
                ),
                evidence=f"HTTP server URLs: {insecure}",
                impact="API traffic can be intercepted, tampered with, or replayed (MITM), exposing credentials and sensitive data.",
                remediation="Serve the API exclusively over HTTPS/TLS and enforce HTTP Strict Transport Security (HSTS).",
                confidence=80,
                detection_reason=f"Server URL(s) {insecure} use the insecure HTTP scheme.",
                cwe_id="CWE-319",
            )
        )

    return findings


# =============================================================================
# API9 — Improper Inventory Management
# =============================================================================


def _check_api9_improper_inventory_management(parsed_api: dict) -> list[dict]:
    findings = []

    path_versions: dict[str, list[dict]] = {}
    for ep in parsed_api["endpoints"]:
        path = ep["path"]
        version_match = re.match(r"^/(v\d+|api/v\d+)", path)
        if version_match:
            version = version_match.group(1)
            if version not in path_versions:
                path_versions[version] = []
            path_versions[version].append(ep)

    if len(path_versions) > 1:
        findings.append(
            _make_finding(
                vuln_name="Multiple API Versions Exposed",
                owasp_cat="API9",
                severity="Medium",
                description=(
                    f"Multiple API versions detected: {list(path_versions.keys())}. "
                    "Older versions may contain unpatched vulnerabilities."
                ),
                evidence=f"Versions found: {', '.join(f'{v} ({len(eps)} endpoints)' for v, eps in path_versions.items())}",
                impact="Older API versions may expose unpatched security vulnerabilities.",
                remediation=(
                    "Maintain a clear versioning strategy. Deprecate and remove old versions. "
                    "Ensure all versions receive security patches."
                ),
                confidence=75,
                detection_reason="Multiple API version prefixes detected in endpoint paths.",
            )
        )

    deprecated_count = sum(1 for ep in parsed_api["endpoints"] if ep.get("deprecated"))
    if deprecated_count > 0:
        findings.append(
            _make_finding(
                vuln_name="Deprecated Endpoints in Specification",
                owasp_cat="API9",
                severity="Low",
                description=f"{deprecated_count} endpoint(s) are marked as deprecated but remain in the specification.",
                evidence=f"Deprecated endpoints: {deprecated_count}",
                impact="Deprecated endpoints may lack security updates and increase attack surface.",
                remediation="Remove deprecated endpoints from the specification and implement sunset policies.",
                confidence=65,
                detection_reason=f"{deprecated_count} deprecated endpoint(s) remain in the specification.",
            )
        )

    return findings


# =============================================================================
# API10 — Unsafe Consumption of APIs
# =============================================================================


def _check_api10_unsafe_consumption_of_apis(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        request_body = ep.get("request_body")
        if not request_body:
            continue

        schema = _get_request_schema(request_body)
        if not schema:
            continue

        properties = schema.get("properties", {})
        for prop_name, prop_def in properties.items():
            prop_lower = prop_name.lower()
            if any(
                kw in prop_lower for kw in ("url", "endpoint", "api_url", "service_url", "webhook")
            ):
                findings.append(
                    _make_finding(
                        vuln_name=f"Unsafe API Consumption via '{prop_name}'",
                        owasp_cat="API10",
                        severity="Medium",
                        description=(
                            f"Property '{prop_name}' in '{ep['method']} {ep['path']}' accepts "
                            "an external API URL that the server may consume unsafely."
                        ),
                        evidence=f"Property '{prop_name}' of type '{prop_def.get('type', 'unknown')}' accepts external URLs.",
                        impact=(
                            "The server may forward untrusted data to external services, "
                            "leading to data leakage, SSRF, or injection attacks."
                        ),
                        remediation=(
                            "Validate external URLs against an allowlist. Sanitize data "
                            "before forwarding. Use schema validation for all external "
                            "API inputs. Implement timeouts and circuit breakers."
                        ),
                        endpoint=ep["path"],
                        method=ep["method"],
                        confidence=68,
                        detection_reason=f"Property '{prop_name}' accepts an external URL that may be consumed by the server without validation.",
                    )
                )

    return findings


def _get_request_schema(request_body: dict) -> dict | None:
    content = request_body.get("content", {})
    for media_type in ("application/json", "application/x-www-form-urlencoded"):
        if media_type in content:
            return content[media_type].get("schema", {})
    return None


def _is_sensitive_path(path: str) -> bool:
    sensitive = [
        "password",
        "secret",
        "token",
        "key",
        "auth",
        "login",
        "register",
        "admin",
        "config",
        "setting",
        "profile",
    ]
    path_lower = path.lower()
    return any(s in path_lower for s in sensitive)


def _is_health_or_meta(path: str) -> bool:
    meta_paths = ["/health", "/healthz", "/ready", "/version", "/docs", "/openapi.json", "/swagger"]
    return any(path.lower().startswith(m) for m in meta_paths)


# =============================================================================
# Check registry — the authoritative list of every distinct security check.
# =============================================================================


class RegistryEntry(TypedDict):
    id: str
    name: str
    category: str
    cwe_id: str
    description: str
    check: Callable[[dict], list[dict]]


CHECK_REGISTRY: list[RegistryEntry] = [
    {
        "id": "SA-01",
        "name": "Broken Object Level Authorization (BOLA)",
        "category": "API1",
        "cwe_id": "CWE-639",
        "description": "Detects resource-by-ID endpoints without user-scoping authorization checks.",
        "check": _check_api1_broken_object_level_authorization,
    },
    {
        "id": "SA-02",
        "name": "Unauthenticated Endpoint",
        "category": "API2",
        "cwe_id": "CWE-287",
        "description": "Detects state-changing or sensitive endpoints exposed without authentication.",
        "check": _check_api2_broken_authentication,
    },
    {
        "id": "SA-03",
        "name": "Weak Authentication Scheme",
        "category": "API2",
        "cwe_id": "CWE-287",
        "description": "Detects HTTP Basic/Digest authentication or API keys transported in the query string.",
        "check": _check_weak_auth_scheme,
    },
    {
        "id": "SA-04",
        "name": "Sensitive Property in Request Body",
        "category": "API3",
        "cwe_id": "CWE-200",
        "description": "Detects over-exposed sensitive properties in request schemas (credentials, roles, PII).",
        "check": _check_api3_broken_object_property_level_authorization,
    },
    {
        "id": "SA-05",
        "name": "Sensitive Data in Query Parameters",
        "category": "API3",
        "cwe_id": "CWE-598",
        "description": "Detects credentials and secrets passed as query string parameters.",
        "check": _check_sensitive_query_params,
    },
    {
        "id": "SA-06",
        "name": "Sensitive Data in Response Schema",
        "category": "API3",
        "cwe_id": "CWE-200",
        "description": "Detects sensitive fields exposed in response schemas.",
        "check": _check_sensitive_response_fields,
    },
    {
        "id": "SA-07",
        "name": "Missing Pagination / Resource Limits",
        "category": "API4",
        "cwe_id": "CWE-770",
        "description": "Detects GET endpoints without pagination or rate-limit controls.",
        "check": _check_api4_unrestricted_resource_consumption,
    },
    {
        "id": "SA-08",
        "name": "Auth Endpoint Missing Rate Limiting",
        "category": "API4",
        "cwe_id": "CWE-770",
        "description": "Detects authentication endpoints lacking HTTP 429 rate-limit controls.",
        "check": _check_auth_rate_limiting,
    },
    {
        "id": "SA-09",
        "name": "Unbounded Request Body",
        "category": "API4",
        "cwe_id": "CWE-770",
        "description": "Detects request body fields without maxLength/maxItems/maximum constraints.",
        "check": _check_unbounded_body,
    },
    {
        "id": "SA-10",
        "name": "Admin Endpoint Authorization",
        "category": "API5",
        "cwe_id": "CWE-862",
        "description": "Detects administrative endpoints without authentication or role verification.",
        "check": _check_api5_broken_function_level_authorization,
    },
    {
        "id": "SA-11",
        "name": "Exposed Debug/Internal Endpoint",
        "category": "API5",
        "cwe_id": "CWE-200",
        "description": "Detects debug, introspection, and management endpoints exposed without auth.",
        "check": _check_debug_endpoints,
    },
    {
        "id": "SA-12",
        "name": "Unprotected Sensitive Business Flow",
        "category": "API6",
        "cwe_id": "CWE-284",
        "description": "Detects authentication gaps in financial, account-creation, and communication flows.",
        "check": _check_api6_unrestricted_access_to_sensitive_business_flows,
    },
    {
        "id": "SA-13",
        "name": "SSRF via URL Parameter",
        "category": "API7",
        "cwe_id": "CWE-918",
        "description": "Detects URL-type inputs that could enable Server-Side Request Forgery.",
        "check": _check_api7_server_side_request_forgery,
    },
    {
        "id": "SA-14",
        "name": "Unvalidated Redirect/Callback URL",
        "category": "API7",
        "cwe_id": "CWE-601",
        "description": "Detects open-redirect and unvalidated callback parameters.",
        "check": _check_open_redirect,
    },
    {
        "id": "SA-15",
        "name": "No Security Schemes Defined",
        "category": "API8",
        "cwe_id": "CWE-16",
        "description": "Detects specs with no authentication mechanisms defined.",
        "check": _check_api8_security_misconfiguration,
    },
    {
        "id": "SA-16",
        "name": "No Global Security Requirements",
        "category": "API8",
        "cwe_id": "CWE-16",
        "description": "Detects specs without root-level security requirements.",
        "check": _check_api8_security_misconfiguration,
    },
    {
        "id": "SA-17",
        "name": "Insecure Transport (HTTP)",
        "category": "API8",
        "cwe_id": "CWE-319",
        "description": "Detects API server URLs served over plain HTTP without TLS.",
        "check": _check_insecure_transport,
    },
    {
        "id": "SA-18",
        "name": "Deprecated Endpoint Exposed",
        "category": "API8",
        "cwe_id": "CWE-16",
        "description": "Detects deprecated endpoints still present in the active specification.",
        "check": _check_api8_security_misconfiguration,
    },
    {
        "id": "SA-19",
        "name": "Multiple API Versions Exposed",
        "category": "API9",
        "cwe_id": "CWE-200",
        "description": "Detects concurrent exposure of multiple API versions.",
        "check": _check_api9_improper_inventory_management,
    },
    {
        "id": "SA-20",
        "name": "Deprecated Endpoints in Specification",
        "category": "API9",
        "cwe_id": "CWE-200",
        "description": "Counts deprecated endpoints that remain declared in the specification.",
        "check": _check_api9_improper_inventory_management,
    },
    {
        "id": "SA-21",
        "name": "Unsafe API Consumption",
        "category": "API10",
        "cwe_id": "CWE-918",
        "description": "Detects external API URLs consumed by the server without validation.",
        "check": _check_api10_unsafe_consumption_of_apis,
    },
]
