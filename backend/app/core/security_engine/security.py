"""Security scheme extraction and endpoint authentication analysis."""

from __future__ import annotations

from typing import Any

from app.core.security_engine.errors import WarningSink
from app.core.security_engine.ref_resolver import RefResolver

_SWAGGER_FLOW_TO_OAS3 = {
    "implicit": "implicit",
    "password": "password",
    "application": "clientCredentials",
    "accessCode": "authorizationCode",
}


def _normalize_swagger_scheme(name: str, scheme: dict) -> dict:
    """Convert a Swagger 2.0 ``securityDefinitions`` entry to OpenAPI-3 shape."""
    scheme_type = scheme.get("type")
    if scheme_type == "basic":
        return {"type": "http", "scheme": "basic"}
    if scheme_type == "oauth2":
        flow = scheme.get("flow", "")
        flow_name = _SWAGGER_FLOW_TO_OAS3.get(flow, flow)
        flows: dict[str, Any] = {}
        flow_obj: dict[str, Any] = {"scopes": scheme.get("scopes", {})}
        if scheme.get("authorizationUrl"):
            flow_obj["authorizationUrl"] = scheme["authorizationUrl"]
        if scheme.get("tokenUrl"):
            flow_obj["tokenUrl"] = scheme["tokenUrl"]
        flows[flow_name] = flow_obj
        return {
            "type": "oauth2",
            "description": scheme.get("description", ""),
            "flows": flows,
        }
    # apiKey passes through unchanged.
    return dict(scheme)


def extract_security_schemes(
    spec: dict,
    *,
    spec_type: str,
    resolver: RefResolver,
    warnings: WarningSink,
) -> dict:
    """Return ``{"schemes": {...}, "global_security": [...]}``.

    ``schemes`` maps scheme name to a normalized, OpenAPI-3-shaped scheme
    object (Swagger 2.0 ``basic`` becomes ``http/basic``, ``oauth2`` gains a
    ``flows`` block). ``global_security`` is the raw top-level ``security``
    list, or ``[]`` when absent.
    """
    raw_schemes: dict[str, Any] = {}
    if spec_type == "swagger":
        raw_schemes = spec.get("securityDefinitions", {}) or {}
    else:
        raw_schemes = (spec.get("components", {}) or {}).get("securitySchemes", {}) or {}

    schemes: dict[str, Any] = {}
    for name, scheme in raw_schemes.items():
        if not isinstance(scheme, dict):
            continue
        if "$ref" in scheme:
            resolved = resolver.get(scheme["$ref"], location=f"securitySchemes.{name}")
            if isinstance(resolved, dict):
                scheme = resolved
            else:
                continue
        normalized = (
            _normalize_swagger_scheme(name, scheme) if spec_type == "swagger" else dict(scheme)
        )
        schemes[name] = normalized

    return {
        "schemes": schemes,
        "global_security": list(spec.get("security", []) or []),
    }


def _auth_type_for_scheme(scheme: dict | None) -> str:
    """Derive a readable authentication type from a scheme object."""
    if not isinstance(scheme, dict):
        return "unknown"
    scheme_type = scheme.get("type")
    if scheme_type == "http":
        scheme_name = str(scheme.get("scheme", "")).lower()
        return f"http_{scheme_name}" if scheme_name else "http"
    if scheme_type == "apiKey":
        location = scheme.get("in", "unknown")
        return f"api_key_{location}"
    if scheme_type in ("oauth2", "openIdConnect", "mutualTLS"):
        return scheme_type
    return scheme_type if isinstance(scheme_type, str) else "unknown"


def analyze_endpoint_security(
    security: list,
    security_schemes: dict,
    *,
    has_operation_security: bool,
) -> dict:
    """Determine an operation's effective authentication posture.

    Per the OpenAPI specification an operation-level ``security`` key is
    authoritative: ``[]`` explicitly disables authentication for that
    operation, a non-empty list requires one of the listed requirements, and
    an absent key falls back to the global ``security`` requirements.
    """
    requirements = list(security) if security is not None else []

    if has_operation_security:
        for req in requirements:
            if isinstance(req, dict) and req:
                return _resolve_requirement(req, security_schemes)
        return {
            "auth_required": False,
            "auth_type": None,
            "security_requirements": requirements,
            "auth_schemes": [],
        }

    for req in security_schemes.get("global_security", []) or []:
        if isinstance(req, dict) and req:
            return _resolve_requirement(req, security_schemes)

    return {
        "auth_required": False,
        "auth_type": None,
        "security_requirements": requirements,
        "auth_schemes": [],
    }


def _resolve_requirement(req: dict, security_schemes: dict) -> dict:
    schemes_by_name = security_schemes.get("schemes", {}) or {}
    scheme_names = [name for name in req if isinstance(name, str)]
    applied: list[str] = []

    for name in scheme_names:
        if name in schemes_by_name:
            applied.append(name)
            scheme = schemes_by_name[name]
            return {
                "auth_required": True,
                "auth_type": _auth_type_for_scheme(scheme),
                "security_requirements": [dict(req)],
                "auth_schemes": [name],
            }

    if scheme_names:
        return {
            "auth_required": True,
            "auth_type": "unknown",
            "security_requirements": [dict(req)],
            "auth_schemes": scheme_names,
        }

    return {
        "auth_required": False,
        "auth_type": None,
        "security_requirements": [dict(req)],
        "auth_schemes": [],
    }
