from typing import Any


def parse_openapi_spec(spec: dict) -> dict:
    info = spec.get("info", {})
    endpoints = []
    security_schemes = _extract_security_schemes(spec)

    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue

        for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue

            operation_id = operation.get("operationId", "")
            tags = operation.get("tags", [])
            summary = operation.get("summary", "")
            parameters = _extract_parameters(operation, spec)
            request_body = _extract_request_body(operation, spec)
            responses = operation.get("responses", {})
            security = operation.get("security", [])
            deprecated = operation.get("deprecated", False)

            endpoint_security = _analyze_endpoint_security(security, security_schemes)

            endpoints.append({
                "path": path,
                "method": method.upper(),
                "operation_id": operation_id,
                "tags": tags,
                "summary": summary,
                "parameters": parameters,
                "request_body": request_body,
                "responses": responses,
                "security": security,
                "deprecated": deprecated,
                "auth_required": endpoint_security["auth_required"],
                "auth_type": endpoint_security["auth_type"],
            })

    return {
        "title": info.get("title", "Unknown API"),
        "version": info.get("version", "unknown"),
        "description": info.get("description", ""),
        "endpoints": endpoints,
        "security_schemes": security_schemes,
        "total_endpoints": len(endpoints),
    }


def _extract_security_schemes(spec: dict) -> dict:
    components = spec.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    global_security = spec.get("security", [])
    return {"schemes": security_schemes, "global_security": global_security}


def _extract_parameters(operation: dict, spec: dict) -> list[dict]:
    parameters = []
    for param in operation.get("parameters", []):
        if "$ref" in param:
            param = _resolve_ref(param["$ref"], spec)
        parameters.append({
            "name": param.get("name", ""),
            "in": param.get("in", ""),
            "required": param.get("required", False),
            "schema": param.get("schema", {}),
        })
    return parameters


def _extract_request_body(operation: dict, spec: dict) -> dict | None:
    request_body = operation.get("requestBody")
    if not request_body:
        return None
    if "$ref" in request_body:
        request_body = _resolve_ref(request_body["$ref"], spec)
    return request_body


def _analyze_endpoint_security(security: list, security_schemes: dict) -> dict:
    if security:
        for sec in security:
            if sec:
                scheme_name = list(sec.keys())[0]
                scheme = security_schemes.get("schemes", {}).get(scheme_name, {})
                return {"auth_required": True, "auth_type": scheme.get("type", "unknown")}

    global_sec = security_schemes.get("global_security", [])
    if global_sec:
        for sec in global_sec:
            if sec:
                scheme_name = list(sec.keys())[0]
                scheme = security_schemes.get("schemes", {}).get(scheme_name, {})
                return {"auth_required": True, "auth_type": scheme.get("type", "unknown")}

    return {"auth_required": False, "auth_type": None}


def _resolve_ref(ref: str, spec: dict) -> Any:
    parts = ref.lstrip("#/").split("/")
    current = spec
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, {})
        else:
            return {}
    return current
