import re
from typing import Any


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
    findings.extend(_check_api1_broken_object_level_authorization(parsed_api))
    findings.extend(_check_api2_broken_authentication(parsed_api))
    findings.extend(_check_api3_broken_object_property_level_authorization(parsed_api))
    findings.extend(_check_api4_unrestricted_resource_consumption(parsed_api))
    findings.extend(_check_api5_broken_function_level_authorization(parsed_api))
    findings.extend(_check_api6_unrestricted_access_to_sensitive_business_flows(parsed_api))
    findings.extend(_check_api7_server_side_request_forgery(parsed_api))
    findings.extend(_check_api8_security_misconfiguration(parsed_api))
    findings.extend(_check_api9_improper_inventory_management(parsed_api))
    findings.extend(_check_api10_unsafe_consumption_of_apis(parsed_api))
    return findings


def _make_finding(
    vuln_name: str,
    owasp_cat: str,
    severity: str,
    description: str,
    evidence: str,
    impact: str,
    remediation: str,
    endpoint: str = None,
    method: str = None,
    confidence: int = 85,
    detection_reason: str = "",
) -> dict:
    return {
        "vulnerability_name": vuln_name,
        "owasp_category": owasp_cat,
        "cwe_id": OWASP_TO_CWE.get(owasp_cat, "N/A"),
        "severity": severity,
        "confidence": confidence,
        "description": description,
        "evidence": evidence,
        "impact": impact,
        "remediation": remediation,
        "affected_endpoint": endpoint,
        "affected_method": method,
        "detection_reason": detection_reason,
        "false_positive_note": "This is a potential vulnerability identified through static analysis of the API specification. Manual verification is recommended to confirm exploitability in the deployed environment.",
    }


def _check_api1_broken_object_level_authorization(parsed_api: dict) -> list[dict]:
    findings = []
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
            findings.append(_make_finding(
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
            ))

    return findings


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
        findings.append(_make_finding(
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
        ))

    return findings


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
        sensitive_patterns = [
            "password", "secret", "token", "api_key", "apikey",
            "admin", "role", "permission", "is_admin", "is_superuser",
            "internal", "debug", "credit_card", "ssn", "salary",
        ]

        for prop_name, prop_def in properties.items():
            prop_lower = prop_name.lower()
            for pattern in sensitive_patterns:
                if pattern in prop_lower:
                    findings.append(_make_finding(
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
                    ))
                    break

    return findings


def _check_api4_unrestricted_resource_consumption(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        params = ep.get("parameters", [])
        has_pagination = any(
            p.get("name", "").lower() in ("limit", "page", "offset", "size", "per_page")
            for p in params
        )

        if ep["method"] == "GET" and not has_pagination:
            if not _is_health_or_meta(ep["path"]):
                findings.append(_make_finding(
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
                ))

    return findings


def _check_api5_broken_function_level_authorization(parsed_api: dict) -> list[dict]:
    findings = []
    admin_patterns = [
        r"/admin", r"/manage", r"/internal", r"/system",
        r"/debug", r"/_internal", r"/console", r"/panel",
    ]

    for ep in parsed_api["endpoints"]:
        for pattern in admin_patterns:
            if re.search(pattern, ep["path"], re.IGNORECASE):
                if not ep.get("auth_required"):
                    findings.append(_make_finding(
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
                    ))
                else:
                    findings.append(_make_finding(
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
                    ))
                break

    return findings


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
                    findings.append(_make_finding(
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
                    ))
                break

    return findings


def _check_api7_server_side_request_forgery(parsed_api: dict) -> list[dict]:
    findings = []

    for ep in parsed_api["endpoints"]:
        params = ep.get("parameters", [])
        request_body = ep.get("request_body")

        url_params = []
        for p in params:
            name_lower = p.get("name", "").lower()
            if any(kw in name_lower for kw in ("url", "uri", "link", "href", "webhook", "callback", "redirect", "proxy", "target", "host")):
                url_params.append(p["name"])

        if request_body:
            schema = _get_request_schema(request_body)
            if schema:
                for prop_name, prop_def in schema.get("properties", {}).items():
                    prop_lower = prop_name.lower()
                    if any(kw in prop_lower for kw in ("url", "uri", "link", "webhook", "callback", "redirect")):
                        url_params.append(prop_name)

        if url_params:
            findings.append(_make_finding(
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
            ))

    return findings


def _check_api8_security_misconfiguration(parsed_api: dict) -> list[dict]:
    findings = []

    if not parsed_api.get("security_schemes", {}).get("schemes"):
        findings.append(_make_finding(
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
        ))

    if not parsed_api.get("security_schemes", {}).get("global_security"):
        findings.append(_make_finding(
            vuln_name="No Global Security Requirements",
            owasp_cat="API8",
            severity="Medium",
            description="No global security requirements are defined. Each endpoint must define its own security.",
            evidence="Top-level 'security' field is missing from the specification.",
            impact="Inconsistent authentication enforcement across endpoints.",
            remediation="Define global security requirements and override only where necessary.",
            confidence=70,
            detection_reason="No global security requirement defined at the specification root level.",
        ))

    for ep in parsed_api["endpoints"]:
        if ep.get("deprecated"):
            findings.append(_make_finding(
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
            ))

        if ep["method"] == "OPTIONS":
            findings.append(_make_finding(
                vuln_name="OPTIONS Method Exposed",
                owasp_cat="API8",
                severity="Info",
                description=(
                    f"OPTIONS method is explicitly defined at '{ep['path']}'. "
                    "This may leak CORS configuration details."
                ),
                evidence="OPTIONS method found in path definition.",
                impact="Information disclosure about CORS policies and supported methods.",
                remediation="Remove explicit OPTIONS definitions unless required. Configure CORS at the server level.",
                endpoint=ep["path"],
                method=ep["method"],
                confidence=40,
                detection_reason="OPTIONS method explicitly defined, which may expose CORS configuration.",
            ))

    return findings


def _check_api9_improper_inventory_management(parsed_api: dict) -> list[dict]:
    findings = []

    path_versions = {}
    for ep in parsed_api["endpoints"]:
        path = ep["path"]
        version_match = re.match(r"^/(v\d+|api/v\d+)", path)
        if version_match:
            version = version_match.group(1)
            if version not in path_versions:
                path_versions[version] = []
            path_versions[version].append(ep)

    if len(path_versions) > 1:
        findings.append(_make_finding(
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
        ))

    deprecated_count = sum(1 for ep in parsed_api["endpoints"] if ep.get("deprecated"))
    if deprecated_count > 0:
        findings.append(_make_finding(
            vuln_name="Deprecated Endpoints in Specification",
            owasp_cat="API9",
            severity="Low",
            description=f"{deprecated_count} endpoint(s) are marked as deprecated but remain in the specification.",
            evidence=f"Deprecated endpoints: {deprecated_count}",
            impact="Deprecated endpoints may lack security updates and increase attack surface.",
            remediation="Remove deprecated endpoints from the specification and implement sunset policies.",
            confidence=65,
            detection_reason=f"{deprecated_count} deprecated endpoint(s) remain in the specification.",
        ))

    return findings


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
            if any(kw in prop_lower for kw in ("url", "endpoint", "api_url", "service_url", "webhook")):
                findings.append(_make_finding(
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
                ))

    return findings


def _get_request_schema(request_body: dict) -> dict | None:
    content = request_body.get("content", {})
    for media_type in ("application/json", "application/x-www-form-urlencoded"):
        if media_type in content:
            return content[media_type].get("schema", {})
    return None


def _is_sensitive_path(path: str) -> bool:
    sensitive = [
        "password", "secret", "token", "key", "auth", "login",
        "register", "admin", "config", "setting", "profile",
    ]
    path_lower = path.lower()
    return any(s in path_lower for s in sensitive)


def _is_health_or_meta(path: str) -> bool:
    meta_paths = ["/health", "/healthz", "/ready", "/version", "/docs", "/openapi.json", "/swagger"]
    return any(path.lower().startswith(m) for m in meta_paths)
