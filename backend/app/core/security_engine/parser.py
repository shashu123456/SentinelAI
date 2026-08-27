"""OpenAPI 3.x and Swagger 2.0 parser for the SentinelAI security engine.

``parse_openapi_spec`` normalizes a raw specification dict into a structured,
fully ``$ref``-resolved model consumed by the scanner, task runner, and
reporting layers. Swagger 2.0 documents are transparently normalized to an
OpenAPI-3-like shape before extraction.
"""

from __future__ import annotations

from typing import Any

from app.core.security_engine.errors import SpecParseError, WarningSink
from app.core.security_engine.ref_resolver import RefResolver
from app.core.security_engine.schemas import resolve_schema
from app.core.security_engine.security import analyze_endpoint_security, extract_security_schemes

HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options", "trace"]

_DEFAULT_MEDIA_TYPE = "application/json"


def _detect_spec_version(spec: dict) -> tuple[str, str]:
    """Return ``(spec_type, version)`` or raise :class:`SpecParseError`."""
    if "openapi" in spec:
        version = spec["openapi"]
        if isinstance(version, str) and version.startswith("3."):
            return "openapi", version
        raise SpecParseError(
            f"Unsupported OpenAPI version: {version!r}. Expected a 3.x version string.",
            spec_type="openapi",
            version=str(version),
        )
    if "swagger" in spec:
        version = spec["swagger"]
        if version == "2.0":
            return "swagger", version
        raise SpecParseError(
            f"Unsupported Swagger version: {version!r}. Only '2.0' is supported.",
            spec_type="swagger",
            version=str(version),
        )
    raise SpecParseError(
        "Not a valid openapi/swagger specification: missing 'openapi' or 'swagger' version key"
    )


def _normalize_spec(spec: dict, spec_type: str) -> dict:
    """Return a spec dict suitable for ``$ref`` resolution.

    OpenAPI 3 documents pass through. Swagger 2.0 documents gain an
    OpenAPI-3-shaped ``components`` section while keeping the original
    top-level ``definitions``/``parameters``/``responses``/
    ``securityDefinitions`` keys so existing ``#/...`` JSON pointers still
    resolve.
    """
    if spec_type == "openapi":
        return spec

    return {
        "openapi": "3.0.0",
        "info": spec.get("info", {}),
        "paths": spec.get("paths", {}),
        "security": spec.get("security", []) or [],
        "consumes": spec.get("consumes"),
        "produces": spec.get("produces"),
        "host": spec.get("host"),
        "basePath": spec.get("basePath"),
        "schemes": spec.get("schemes"),
        "components": {
            "schemas": spec.get("definitions", {}) or {},
            "securitySchemes": spec.get("securityDefinitions", {}) or {},
            "responses": spec.get("responses", {}) or {},
            "parameters": spec.get("parameters", {}) or {},
        },
        "swagger": "2.0",
        "definitions": spec.get("definitions", {}) or {},
        "parameters": spec.get("parameters", {}) or {},
        "responses": spec.get("responses", {}) or {},
        "securityDefinitions": spec.get("securityDefinitions", {}) or {},
    }


def _extract_servers(spec: dict, spec_type: str) -> list[dict]:
    """Extract the effective server list for the specification."""
    if spec_type == "openapi":
        return list(spec.get("servers", []) or [])

    servers: list[dict] = []
    host = spec.get("host")
    base_path = spec.get("basePath", "") or ""
    schemes = spec.get("schemes") or (["https", "http"] if host else [])
    if host and schemes:
        for scheme in schemes:
            servers.append({"url": f"{scheme}://{host}{base_path}"})
    return servers


def _merge_parameters(path_params: list, operation_params: list) -> list[dict]:
    """Merge path-level and operation-level parameters, operation wins."""
    merged: dict[tuple, dict] = {}
    for param in [*path_params, *operation_params]:
        if not isinstance(param, dict):
            continue
        merged[(param.get("in"), param.get("name"))] = param
    return list(merged.values())


def _extract_parameters(
    operation: dict,
    path_params: list,
    resolver: RefResolver,
    warnings: WarningSink,
    location: str,
) -> list[dict]:
    params = _merge_parameters(path_params, operation.get("parameters", []) or [])
    extracted: list[dict] = []
    for param in params:
        if "$ref" in param:
            resolved = resolver.get(param["$ref"], location=location)
            if isinstance(resolved, dict):
                param = resolved
            else:
                continue

        schema = param.get("schema", {})
        if isinstance(schema, dict):
            schema = resolve_schema(schema, resolver, warnings, location=location)

        entry: dict[str, Any] = {
            "name": param.get("name", ""),
            "in": param.get("in", ""),
            "required": param.get("required", False),
            "schema": schema,
        }
        for key in ("description", "style", "explode", "example", "examples", "deprecated"):
            if key in param:
                entry[key] = param[key]
        extracted.append(entry)
    return extracted


def _extract_request_body(
    operation: dict,
    spec: dict,
    spec_type: str,
    resolver: RefResolver,
    warnings: WarningSink,
    location: str,
) -> dict | None:
    if spec_type == "swagger":
        body_param: dict[str, Any] | None = None
        for p in operation.get("parameters", []) or []:
            if not isinstance(p, dict):
                continue
            candidate = p
            if "$ref" in candidate:
                resolved = resolver.get(candidate["$ref"], location=location)
                candidate = resolved if isinstance(resolved, dict) else {}
            if candidate.get("in") == "body":
                body_param = candidate
                break
        if body_param is None:
            return None
        schema = body_param.get("schema", {})
        if isinstance(schema, dict):
            schema = resolve_schema(schema, resolver, warnings, location=location)
        consumes = operation.get("consumes") or spec.get("consumes") or [_DEFAULT_MEDIA_TYPE]
        content = {media_type: {"schema": schema} for media_type in consumes}
        return {
            "required": body_param.get("required", False),
            "description": body_param.get("description", ""),
            "content": content,
        }

    request_body = operation.get("requestBody")
    if not request_body:
        return None
    if isinstance(request_body, dict) and "$ref" in request_body:
        resolved = resolver.get(request_body["$ref"], location=location)
        if not isinstance(resolved, dict):
            return None
        request_body = resolved
    if not isinstance(request_body, dict):
        return None

    result: dict[str, Any] = dict(request_body)
    content = request_body.get("content", {})
    if isinstance(content, dict):
        result["content"] = {
            media_type: {
                **(media if isinstance(media, dict) else {}),
                "schema": resolve_schema(
                    media.get("schema", {}) if isinstance(media, dict) else {},
                    resolver,
                    warnings,
                    location=location,
                ),
            }
            for media_type, media in content.items()
            if isinstance(media, dict)
        }
    return result


def _extract_response_schemas(
    operation: dict,
    spec: dict,
    spec_type: str,
    resolver: RefResolver,
    warnings: WarningSink,
    location: str,
) -> list[dict]:
    responses = operation.get("responses", {}) or {}
    schemas: list[dict] = []

    for status_code, response in responses.items():
        if not isinstance(response, dict):
            continue
        if "$ref" in response:
            resolved = resolver.get(response["$ref"], location=location)
            if not isinstance(resolved, dict):
                continue
            response = resolved

        if spec_type == "swagger":
            produces = operation.get("produces") or spec.get("produces") or [_DEFAULT_MEDIA_TYPE]
            content: dict[str, Any] = {
                media_type: {"schema": response.get("schema", {})} for media_type in produces
            }
        else:
            content = response.get("content", {}) or {}

        for media_type, media in content.items():
            if not isinstance(media, dict) or "schema" not in media:
                continue
            schema = resolve_schema(media["schema"], resolver, warnings, location=location)
            entry: dict[str, Any] = {
                "status_code": status_code,
                "schema": schema,
                "content_type": media_type,
            }
            if response.get("description"):
                entry["description"] = response["description"]
            schemas.append(entry)

    return schemas


def _extract_endpoint_servers(operation: dict, global_servers: list[dict]) -> list[dict]:
    if "servers" in operation and isinstance(operation["servers"], list):
        return [s for s in operation["servers"] if isinstance(s, dict)]
    return global_servers


def _extract_endpoint(
    path: str,
    method: str,
    operation: dict,
    path_params: list,
    spec: dict,
    spec_type: str,
    resolver: RefResolver,
    warnings: WarningSink,
    security_schemes: dict,
    global_servers: list[dict],
) -> dict:
    location = f"{method.upper()} {path}"
    has_operation_security = "security" in operation
    security = list(operation.get("security", []) or [])
    security_analysis = analyze_endpoint_security(
        security, security_schemes, has_operation_security=has_operation_security
    )

    endpoint: dict[str, Any] = {
        "path": path,
        "method": method.upper(),
        "operation_id": operation.get("operationId", ""),
        "tags": operation.get("tags", []),
        "summary": operation.get("summary", ""),
        "parameters": _extract_parameters(operation, path_params, resolver, warnings, location),
        "request_body": _extract_request_body(
            operation, spec, spec_type, resolver, warnings, location
        ),
        "responses": operation.get("responses", {}),
        "response_schemas": _extract_response_schemas(
            operation, spec, spec_type, resolver, warnings, location
        ),
        "security": security,
        "deprecated": operation.get("deprecated", False),
        "auth_required": security_analysis["auth_required"],
        "auth_type": security_analysis["auth_type"],
        "security_requirements": security_analysis["security_requirements"],
        "auth_schemes": security_analysis["auth_schemes"],
        "servers": _extract_endpoint_servers(operation, global_servers),
    }
    if "description" in operation:
        endpoint["description"] = operation["description"]
    return endpoint


def parse_openapi_spec(spec: dict) -> dict:
    """Parse an OpenAPI 3.x or Swagger 2.0 specification into a structured dict.

    Raises :class:`SpecParseError` for structurally invalid specifications.
    Non-fatal issues are collected under the ``warnings`` key of the result.
    """
    if not isinstance(spec, dict):
        raise SpecParseError("Specification must be a JSON/YAML object.")

    warnings = WarningSink()
    spec_type, version = _detect_spec_version(spec)

    normalized = _normalize_spec(spec, spec_type)
    paths = normalized.get("paths")
    if paths is None:
        paths = {}
    if not isinstance(paths, dict):
        raise SpecParseError(
            "'paths' must be an object mapping paths to path items.",
            spec_type=spec_type,
            version=version,
        )

    resolver = RefResolver(normalized, warnings)
    security_schemes = extract_security_schemes(
        normalized, spec_type=spec_type, resolver=resolver, warnings=warnings
    )
    global_servers = _extract_servers(normalized, spec_type)
    info = normalized.get("info", {}) or {}

    endpoints: list[dict] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            warnings.add(
                "invalid_path_item",
                f"Path '{path}' is not an object and was skipped.",
                location=path,
            )
            continue
        path_params = path_item.get("parameters", []) or []
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            endpoints.append(
                _extract_endpoint(
                    path,
                    method,
                    operation,
                    path_params,
                    normalized,
                    spec_type,
                    resolver,
                    warnings,
                    security_schemes,
                    global_servers,
                )
            )

    return {
        "title": info.get("title", "Unknown API"),
        "version": info.get("version", "unknown"),
        "description": info.get("description", ""),
        "endpoints": endpoints,
        "security_schemes": security_schemes,
        "servers": global_servers,
        "total_endpoints": len(endpoints),
        "spec_type": spec_type,
        "spec_version": version,
        "warnings": warnings.to_list(),
    }
