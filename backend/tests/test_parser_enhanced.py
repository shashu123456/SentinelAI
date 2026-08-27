import pytest

from app.core.security_engine.errors import SpecParseError, WarningSink
from app.core.security_engine.parser import parse_openapi_spec
from app.core.security_engine.ref_resolver import RefResolver
from app.core.security_engine.schemas import iter_schema_properties, resolve_schema
from app.core.security_engine.security import analyze_endpoint_security


def _endpoint(result, method, path):
    matches = [e for e in result["endpoints"] if e["method"] == method and e["path"] == path]
    assert len(matches) == 1, f"Expected exactly one {method} {path}, got {matches}"
    return matches[0]


class TestSpecDetection:
    def test_detects_openapi(self):
        result = parse_openapi_spec({"openapi": "3.0.3", "info": {}, "paths": {}})
        assert result["spec_type"] == "openapi"
        assert result["spec_version"] == "3.0.3"

    def test_detects_swagger(self):
        result = parse_openapi_spec({"swagger": "2.0", "info": {}, "paths": {}})
        assert result["spec_type"] == "swagger"
        assert result["spec_version"] == "2.0"

    def test_missing_version_key_raises(self):
        with pytest.raises(SpecParseError) as exc:
            parse_openapi_spec({"info": {}})
        assert "openapi" in str(exc.value)

    def test_unsupported_openapi_version_raises(self):
        with pytest.raises(SpecParseError):
            parse_openapi_spec({"openapi": "2.0", "paths": {}})

    def test_unsupported_swagger_version_raises(self):
        with pytest.raises(SpecParseError):
            parse_openapi_spec({"swagger": "1.2", "paths": {}})

    def test_paths_not_object_raises(self):
        with pytest.raises(SpecParseError):
            parse_openapi_spec({"openapi": "3.0.0", "paths": "nope"})

    def test_swagger_paths_not_object_raises(self):
        with pytest.raises(SpecParseError):
            parse_openapi_spec({"swagger": "2.0", "paths": []})

    def test_non_dict_spec_raises(self):
        with pytest.raises(SpecParseError):
            parse_openapi_spec("not a dict")

    def test_missing_info_stays_graceful(self):
        result = parse_openapi_spec({"openapi": "3.0.0", "paths": {}})
        assert result["title"] == "Unknown API"
        assert result["total_endpoints"] == 0

    def test_warnings_key_present(self):
        result = parse_openapi_spec({"openapi": "3.0.0", "paths": {}})
        assert "warnings" in result
        assert isinstance(result["warnings"], list)


class TestSwaggerTwoPointZero:
    def _spec(self):
        return {
            "swagger": "2.0",
            "info": {"title": "Swagger Petstore", "version": "1.0.0"},
            "host": "petstore.example.com",
            "basePath": "/v1",
            "schemes": ["https", "http"],
            "consumes": ["application/json"],
            "produces": ["application/json"],
            "security": [{"api_key": []}],
            "securityDefinitions": {
                "api_key": {"type": "apiKey", "name": "api_key", "in": "header"},
                "basic_auth": {"type": "basic"},
                "oauth": {
                    "type": "oauth2",
                    "flow": "accessCode",
                    "authorizationUrl": "https://auth.example.com/auth",
                    "tokenUrl": "https://auth.example.com/token",
                    "scopes": {"read": "read access"},
                },
            },
            "definitions": {
                "Pet": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                },
                "NewPet": {
                    "allOf": [
                        {"$ref": "#/definitions/Pet"},
                        {
                            "type": "object",
                            "required": ["name"],
                            "properties": {"tag": {"type": "string"}},
                        },
                    ]
                },
            },
            "parameters": {
                "petId": {"name": "petId", "in": "path", "required": True, "type": "integer"},
            },
            "paths": {
                "/pets": {
                    "post": {
                        "operationId": "createPet",
                        "parameters": [
                            {
                                "name": "body",
                                "in": "body",
                                "required": True,
                                "schema": {"$ref": "#/definitions/NewPet"},
                            }
                        ],
                        "responses": {
                            "201": {
                                "description": "Created",
                                "schema": {"$ref": "#/definitions/Pet"},
                            }
                        },
                    }
                },
                "/pets/{petId}": {
                    "parameters": [{"$ref": "#/parameters/petId"}],
                    "get": {
                        "operationId": "getPet",
                        "responses": {
                            "200": {"description": "OK", "schema": {"$ref": "#/definitions/Pet"}}
                        },
                    },
                },
            },
        }

    def test_builds_servers_from_host_basepath_schemes(self):
        result = parse_openapi_spec(self._spec())
        urls = [s["url"] for s in result["servers"]]
        assert urls == ["https://petstore.example.com/v1", "http://petstore.example.com/v1"]

    def test_normalizes_basic_security_definition(self):
        result = parse_openapi_spec(self._spec())
        schemes = result["security_schemes"]["schemes"]
        assert schemes["basic_auth"] == {"type": "http", "scheme": "basic"}

    def test_keeps_api_key_definition(self):
        result = parse_openapi_spec(self._spec())
        schemes = result["security_schemes"]["schemes"]
        assert schemes["api_key"]["type"] == "apiKey"
        assert schemes["api_key"]["in"] == "header"

    def test_normalizes_oauth2_flows(self):
        result = parse_openapi_spec(self._spec())
        schemes = result["security_schemes"]["schemes"]
        assert schemes["oauth"]["type"] == "oauth2"
        assert "authorizationCode" in schemes["oauth"]["flows"]
        assert schemes["oauth"]["flows"]["authorizationCode"]["tokenUrl"].endswith("/token")

    def test_body_parameter_becomes_request_body(self):
        result = parse_openapi_spec(self._spec())
        ep = _endpoint(result, "POST", "/pets")
        assert ep["request_body"] is not None
        assert ep["request_body"]["required"] is True
        schema = ep["request_body"]["content"]["application/json"]["schema"]
        assert schema["type"] == "object"
        assert set(schema["properties"]) == {"id", "name", "tag"}
        assert schema["required"] == ["name"]

    def test_path_level_parameter_ref_resolved(self):
        result = parse_openapi_spec(self._spec())
        ep = _endpoint(result, "GET", "/pets/{petId}")
        assert ep["parameters"][0]["name"] == "petId"
        assert ep["parameters"][0]["in"] == "path"

    def test_response_schema_resolved(self):
        result = parse_openapi_spec(self._spec())
        ep = _endpoint(result, "GET", "/pets/{petId}")
        assert ep["response_schemas"][0]["status_code"] == "200"
        assert set(ep["response_schemas"][0]["schema"]["properties"]) == {"id", "name"}

    def test_global_security_applies(self):
        result = parse_openapi_spec(self._spec())
        ep = _endpoint(result, "POST", "/pets")
        assert ep["auth_required"] is True
        assert ep["auth_type"] == "api_key_header"
        assert ep["auth_schemes"] == ["api_key"]


class TestRefResolution:
    def _spec(self):
        return {
            "openapi": "3.0.3",
            "info": {"title": "Refs", "version": "1.0.0"},
            "components": {
                "schemas": {
                    "Address": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}, "zip": {"type": "string"}},
                    },
                    "Pet": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "address": {"$ref": "#/components/schemas/Address"},
                            "tags": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Address"},
                            },
                        },
                    },
                    "SearchResult": {
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {"id": {"type": "string"}},
                            },
                            {
                                "type": "object",
                                "properties": {"token": {"type": "string"}},
                            },
                        ]
                    },
                    "AdminUser": {
                        "allOf": [
                            {
                                "type": "object",
                                "required": ["id"],
                                "properties": {
                                    "id": {"type": "integer"},
                                    "name": {"type": "string"},
                                },
                            },
                            {
                                "type": "object",
                                "required": ["role"],
                                "properties": {
                                    "role": {"type": "string"},
                                    "name": {"type": "string"},
                                },
                            },
                        ]
                    },
                },
                "parameters": {
                    "limitParam": {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                },
                "responses": {
                    "PetResponse": {
                        "description": "A pet",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                        },
                    }
                },
                "requestBodies": {
                    "PetBody": {
                        "required": True,
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                        },
                    }
                },
            },
            "paths": {
                "/pets": {
                    "get": {
                        "parameters": [{"$ref": "#/components/parameters/limitParam"}],
                        "responses": {"200": {"$ref": "#/components/responses/PetResponse"}},
                    },
                    "post": {"requestBody": {"$ref": "#/components/requestBodies/PetBody"}},
                }
            },
        }

    def test_parameter_ref_resolved(self):
        result = parse_openapi_spec(self._spec())
        ep = _endpoint(result, "GET", "/pets")
        assert ep["parameters"][0]["name"] == "limit"
        assert ep["parameters"][0]["schema"]["type"] == "integer"

    def test_response_ref_resolved_nested(self):
        result = parse_openapi_spec(self._spec())
        ep = _endpoint(result, "GET", "/pets")
        schema = ep["response_schemas"][0]["schema"]
        assert schema["properties"]["address"]["properties"]["city"]["type"] == "string"
        assert schema["properties"]["tags"]["items"]["properties"]["zip"]["type"] == "string"

    def test_request_body_ref_resolved(self):
        result = parse_openapi_spec(self._spec())
        ep = _endpoint(result, "POST", "/pets")
        schema = ep["request_body"]["content"]["application/json"]["schema"]
        assert schema["properties"]["id"]["type"] == "integer"
        assert schema["properties"]["address"]["properties"]["city"] == {"type": "string"}

    def test_allof_merge(self):
        resolver = RefResolver(
            {
                "components": {
                    "schemas": {
                        "AdminUser": {
                            "allOf": [
                                {
                                    "type": "object",
                                    "required": ["id"],
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                    },
                                },
                                {
                                    "type": "object",
                                    "required": ["role"],
                                    "properties": {
                                        "role": {"type": "string"},
                                        "name": {"type": "string"},
                                    },
                                },
                            ]
                        }
                    }
                }
            },
            WarningSink(),
        )
        resolved = resolve_schema(
            {"$ref": "#/components/schemas/AdminUser"}, resolver, WarningSink()
        )
        assert set(resolved["properties"]) == {"id", "name", "role"}
        assert set(resolved["required"]) == {"id", "role"}

    def test_oneof_properties_iterable(self):
        sink = WarningSink()
        resolver = RefResolver(
            {
                "components": {
                    "schemas": {
                        "SearchResult": {
                            "oneOf": [
                                {"type": "object", "properties": {"id": {"type": "string"}}},
                                {"type": "object", "properties": {"token": {"type": "string"}}},
                            ]
                        }
                    }
                }
            },
            sink,
        )
        resolved = resolve_schema({"$ref": "#/components/schemas/SearchResult"}, resolver, sink)
        names = [name for name, _ in iter_schema_properties(resolved)]
        assert "id" in names
        assert "token" in names

    def test_recursive_schema_cycle_guard(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "Tree", "version": "1.0.0"},
                "components": {
                    "schemas": {
                        "Node": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string"},
                                "children": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Node"},
                                },
                            },
                        }
                    }
                },
                "paths": {
                    "/nodes": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "OK",
                                    "content": {
                                        "application/json": {
                                            "schema": {"$ref": "#/components/schemas/Node"}
                                        }
                                    },
                                }
                            }
                        }
                    }
                },
            }
        )
        schema = result["endpoints"][0]["response_schemas"][0]["schema"]
        assert schema["properties"]["value"]["type"] == "string"
        children_items = schema["properties"]["children"]["items"]
        assert isinstance(children_items, dict)
        assert children_items.get("$ref") == "#/components/schemas/Node" or (
            "properties" in children_items
        )


class TestAdditionalProperties:
    def test_additional_properties_bool_form_preserved(self):
        sink = WarningSink()
        resolved = resolve_schema(
            {"type": "object", "additionalProperties": True}, RefResolver({}, sink), sink
        )
        assert resolved["additionalProperties"] is True

    def test_additional_properties_schema_form_iterable(self):
        sink = WarningSink()
        resolved = resolve_schema(
            {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {"secret": {"type": "string"}},
                },
            },
            RefResolver({}, sink),
            sink,
        )
        names = [name for name, _ in iter_schema_properties(resolved)]
        assert "secret" in names


class TestSecurityAnalysis:
    def _spec(self, paths, global_security=None, schemes=None):
        return {
            "openapi": "3.0.3",
            "info": {"title": "Sec", "version": "1.0.0"},
            "security": global_security,
            "components": {
                "securitySchemes": schemes
                or {
                    "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                }
            },
            "paths": paths,
        }

    def test_empty_operation_security_overrides_global(self):
        result = parse_openapi_spec(
            self._spec(
                global_security=[{"bearerAuth": []}],
                paths={
                    "/public": {
                        "get": {"security": [], "responses": {"200": {"description": "OK"}}}
                    },
                    "/private": {"get": {"responses": {"200": {"description": "OK"}}}},
                    "/admin": {
                        "get": {
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    },
                },
            )
        )
        assert _endpoint(result, "GET", "/public")["auth_required"] is False
        assert _endpoint(result, "GET", "/private")["auth_required"] is True
        assert _endpoint(result, "GET", "/admin")["auth_required"] is True

    def test_http_bearer_auth_type(self):
        result = parse_openapi_spec(
            self._spec(
                paths={
                    "/x": {
                        "get": {
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                }
            )
        )
        ep = _endpoint(result, "GET", "/x")
        assert ep["auth_required"] is True
        assert ep["auth_type"] == "http_bearer"
        assert ep["auth_schemes"] == ["bearerAuth"]

    def test_http_basic_and_digest_auth_types(self):
        schemes = {
            "basic": {"type": "http", "scheme": "basic"},
            "digest": {"type": "http", "scheme": "digest"},
        }
        paths = {
            f"/{name}": {
                "get": {
                    "security": [{name: []}],
                    "responses": {"200": {"description": "OK"}},
                }
            }
            for name in schemes
        }
        result = parse_openapi_spec(self._spec(paths=paths, schemes=schemes))
        assert _endpoint(result, "GET", "/basic")["auth_type"] == "http_basic"
        assert _endpoint(result, "GET", "/digest")["auth_type"] == "http_digest"

    def test_api_key_cookie_auth_type(self):
        schemes = {"session": {"type": "apiKey", "in": "cookie", "name": "session_id"}}
        result = parse_openapi_spec(
            self._spec(
                schemes=schemes,
                paths={
                    "/x": {
                        "get": {
                            "security": [{"session": []}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            )
        )
        ep = _endpoint(result, "GET", "/x")
        assert ep["auth_type"] == "api_key_cookie"
        assert result["security_schemes"]["schemes"]["session"]["name"] == "session_id"

    def test_oauth2_openid_mutual_tls_types(self):
        schemes = {
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://auth.example.com/auth",
                        "tokenUrl": "https://auth.example.com/token",
                        "scopes": {"read": "read"},
                    }
                },
            },
            "oidc": {
                "type": "openIdConnect",
                "openIdConnectUrl": "https://issuer.example.com/.well-known",
            },
            "mtls": {"type": "mutualTLS"},
        }
        paths = {
            f"/{name}": {
                "get": {
                    "security": [{name: []}],
                    "responses": {"200": {"description": "OK"}},
                }
            }
            for name in schemes
        }
        result = parse_openapi_spec(self._spec(paths=paths, schemes=schemes))
        assert _endpoint(result, "GET", "/oauth2")["auth_type"] == "oauth2"
        assert _endpoint(result, "GET", "/oidc")["auth_type"] == "openIdConnect"
        assert _endpoint(result, "GET", "/mtls")["auth_type"] == "mutualTLS"
        assert "authorizationCode" in result["security_schemes"]["schemes"]["oauth2"]["flows"]

    def test_undefined_scheme_name_still_requires_auth(self):
        result = parse_openapi_spec(
            self._spec(
                paths={
                    "/x": {
                        "get": {
                            "security": [{"missingScheme": []}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                }
            )
        )
        ep = _endpoint(result, "GET", "/x")
        assert ep["auth_required"] is True
        assert ep["auth_type"] == "unknown"


class TestParameterMerging:
    def test_operation_parameter_overrides_path_parameter(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "Merge", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "parameters": [
                            {"name": "limit", "in": "query", "schema": {"type": "string"}}
                        ],
                        "get": {
                            "parameters": [
                                {"name": "limit", "in": "query", "schema": {"type": "integer"}}
                            ],
                            "responses": {"200": {"description": "OK"}},
                        },
                    }
                },
            }
        )
        ep = _endpoint(result, "GET", "/pets")
        assert len(ep["parameters"]) == 1
        assert ep["parameters"][0]["schema"]["type"] == "integer"


class TestEndpointEnrichment:
    def test_operation_level_servers_override(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "Srv", "version": "1.0.0"},
                "servers": [{"url": "https://public.example.com"}],
                "paths": {
                    "/internal": {
                        "get": {
                            "servers": [{"url": "https://internal.example.com"}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        ep = _endpoint(result, "GET", "/internal")
        assert ep["servers"][0]["url"] == "https://internal.example.com"

    def test_response_schema_has_content_type_and_description(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "CT", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "A list of pets",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {"name": {"type": "string"}},
                                            }
                                        }
                                    },
                                }
                            }
                        }
                    }
                },
            }
        )
        rs = _endpoint(result, "GET", "/pets")["response_schemas"][0]
        assert rs["content_type"] == "application/json"
        assert rs["description"] == "A list of pets"

    def test_parameter_extra_fields_preserved(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {
                            "parameters": [
                                {
                                    "name": "limit",
                                    "in": "query",
                                    "description": "Max results",
                                    "style": "form",
                                    "explode": True,
                                    "example": 10,
                                    "schema": {"type": "integer"},
                                }
                            ],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        p = _endpoint(result, "GET", "/pets")["parameters"][0]
        assert p["description"] == "Max results"
        assert p["style"] == "form"
        assert p["explode"] is True
        assert p["example"] == 10


class TestWarnings:
    def test_external_ref_warning(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "W", "version": "1.0.0"},
                "paths": {
                    "/x": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "OK",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "./other.yaml#/components/schemas/Foo"
                                            }
                                        }
                                    },
                                }
                            }
                        }
                    }
                },
            }
        )
        codes = [w["code"] for w in result["warnings"]]
        assert "external_ref" in codes

    def test_unresolved_ref_warning(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "W", "version": "1.0.0"},
                "paths": {
                    "/x": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "OK",
                                    "content": {
                                        "application/json": {
                                            "schema": {"$ref": "#/components/schemas/Missing"}
                                        }
                                    },
                                }
                            }
                        }
                    }
                },
            }
        )
        codes = [w["code"] for w in result["warnings"]]
        assert "unresolved_ref" in codes

    def test_invalid_path_item_warning(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "W", "version": "1.0.0"},
                "paths": {"/broken": "not-a-dict"},
            }
        )
        codes = [w["code"] for w in result["warnings"]]
        assert "invalid_path_item" in codes
        assert result["total_endpoints"] == 0


class TestSpecParseErrorDetails:
    def test_str_includes_endpoint(self):
        err = SpecParseError("bad", spec_type="openapi", version="3.0.0", endpoint="GET /x")
        assert str(err) == "bad at GET /x"
        assert err.spec_type == "openapi"
        assert err.version == "3.0.0"

    def test_str_without_endpoint(self):
        assert str(SpecParseError("plain")) == "plain"


class TestWarningSink:
    def test_warnings_property_returns_copies(self):
        sink = WarningSink()
        sink.add("code", "msg")
        first = sink.warnings
        first.clear()
        assert len(sink.warnings) == 1
        assert sink.warnings[0].code == "code"
        assert sink.to_list() == [
            {"message": "msg", "code": "code", "location": None, "detail": None}
        ]


class TestAllOfMerging:
    def test_type_conflict_merged_to_list(self):
        sink = WarningSink()
        resolved = resolve_schema(
            {"allOf": [{"type": "string"}, {"type": "integer"}]}, RefResolver({}, sink), sink
        )
        assert resolved["type"] == ["string", "integer"]

    def test_scalar_conflict_overlay_wins(self):
        sink = WarningSink()
        resolved = resolve_schema(
            {"allOf": [{"minimum": 0}, {"minimum": 5}]}, RefResolver({}, sink), sink
        )
        assert resolved["minimum"] == 5


class TestResolveSchemaEdgeCases:
    def test_depth_limit_truncates(self):
        sink = WarningSink()
        schema = {"type": "object", "properties": {}}
        node = schema
        for _ in range(105):
            node["properties"] = {"child": {"type": "object"}}
            node = node["properties"]["child"]
        resolved = resolve_schema(schema, RefResolver({}, sink), sink)
        assert isinstance(resolved, dict)
        assert any(w.code == "schema_depth" for w in sink.warnings)

    def test_top_level_list_schema(self):
        sink = WarningSink()
        resolved = resolve_schema(
            [{"type": "object", "properties": {"id": {"type": "string"}}}],
            RefResolver({}, sink),
            sink,
        )
        assert resolved[0]["properties"]["id"] == {"type": "string"}

    def test_top_level_scalar_schema(self):
        sink = WarningSink()
        assert resolve_schema("just-a-string", RefResolver({}, sink), sink) == "just-a-string"

    def test_ref_to_non_dict_target(self):
        sink = WarningSink()
        resolver = RefResolver({"components": {"schemas": {"S": "plain string"}}}, sink)
        assert resolve_schema({"$ref": "#/components/schemas/S"}, resolver, sink) == "plain string"

    def test_properties_not_a_dict_preserved(self):
        sink = WarningSink()
        resolved = resolve_schema(
            {"type": "object", "properties": "nope"}, RefResolver({}, sink), sink
        )
        assert resolved["properties"] == "nope"

    def test_composition_key_not_a_list_preserved(self):
        sink = WarningSink()
        resolved = resolve_schema({"oneOf": "nope"}, RefResolver({}, sink), sink)
        assert resolved["oneOf"] == "nope"


class TestIterSchemaProperties:
    def test_non_dict_schema_yields_nothing(self):
        assert list(iter_schema_properties("nope")) == []

    def test_repeated_node_yielded_once(self):
        prop = {"type": "object", "properties": {"x": {"type": "string"}}}
        schema = {"properties": {"a": prop}, "additionalProperties": prop}
        names = [name for name, _ in iter_schema_properties(schema)]
        assert names == ["a", "a.x"]

    def test_non_dict_property_value_tolerated(self):
        names = [name for name, _ in iter_schema_properties({"properties": {"a": "string-schema"}})]
        assert names == ["a"]

    def test_array_items_with_prefix(self):
        schema = {
            "type": "array",
            "items": {"type": "object", "properties": {"city": {"type": "string"}}},
        }
        names = [name for name, _ in iter_schema_properties(schema, prefix="root")]
        assert names == ["root[].city"]


class TestSecuritySchemeRefs:
    def _spec(self, schemes):
        return {
            "openapi": "3.0.3",
            "info": {"title": "Sec", "version": "1.0.0"},
            "components": {"securitySchemes": schemes},
            "paths": {},
        }

    def test_non_dict_scheme_skipped(self):
        result = parse_openapi_spec(self._spec({"weird": "not-a-dict"}))
        assert "weird" not in result["security_schemes"]

    def test_ref_scheme_resolved(self):
        result = parse_openapi_spec(
            self._spec(
                {
                    "bearerAuth": {"type": "http", "scheme": "bearer"},
                    "alias": {"$ref": "#/components/securitySchemes/bearerAuth"},
                }
            )
        )
        assert result["security_schemes"]["schemes"]["alias"] == {
            "type": "http",
            "scheme": "bearer",
        }

    def test_unresolved_ref_scheme_skipped(self):
        result = parse_openapi_spec(
            self._spec({"alias": {"$ref": "#/components/securitySchemes/Missing"}})
        )
        assert "alias" not in result["security_schemes"]


class TestAuthTypeFallbacks:
    def test_none_scheme_reports_unknown(self):
        report = analyze_endpoint_security(
            [{"weird": []}],
            {"schemes": {"weird": None}},
            has_operation_security=True,
        )
        assert report["auth_required"] is True
        assert report["auth_type"] == "unknown"

    def test_non_str_scheme_type_reports_unknown(self):
        report = analyze_endpoint_security(
            [{"odd": []}],
            {"schemes": {"odd": {"type": 123}}},
            has_operation_security=True,
        )
        assert report["auth_type"] == "unknown"

    def test_empty_requirement_disables_auth(self):
        report = analyze_endpoint_security([{}], {"schemes": {}}, has_operation_security=True)
        assert report["auth_required"] is False
        assert report["auth_schemes"] == []

    def test_non_string_requirement_key_is_inert(self):
        report = analyze_endpoint_security(
            [{123: []}], {"schemes": {}}, has_operation_security=True
        )
        assert report["auth_required"] is False
        assert report["security_requirements"] == [{123: []}]


class TestParserEdgeCases:
    def test_missing_paths_key_ok(self):
        result = parse_openapi_spec(
            {"openapi": "3.0.3", "info": {"title": "P", "version": "1.0.0"}}
        )
        assert result["total_endpoints"] == 0

    def test_non_dict_parameter_skipped(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {
                            "parameters": ["nope", {"name": "limit", "in": "query"}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        params = _endpoint(result, "GET", "/pets")["parameters"]
        assert len(params) == 1
        assert params[0]["name"] == "limit"

    def test_unresolved_parameter_ref_skipped(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {
                            "parameters": [{"$ref": "#/components/parameters/Missing"}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        assert _endpoint(result, "GET", "/pets")["parameters"] == []
        assert any(w["code"] == "unresolved_ref" for w in result["warnings"])

    def test_swagger_body_param_unresolved_ref_omitted(self):
        result = parse_openapi_spec(
            {
                "swagger": "2.0",
                "info": {"title": "S", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "post": {
                            "parameters": [{"$ref": "#/parameters/Missing"}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        assert _endpoint(result, "POST", "/pets")["request_body"] is None
        assert any(w["code"] == "unresolved_ref" for w in result["warnings"])

    def test_swagger_body_param_ref_resolved(self):
        result = parse_openapi_spec(
            {
                "swagger": "2.0",
                "info": {"title": "S", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "post": {
                            "parameters": [{"$ref": "#/parameters/PetBody"}],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
                "parameters": {
                    "PetBody": {
                        "name": "pet",
                        "in": "body",
                        "required": True,
                        "schema": {"$ref": "#/definitions/Pet"},
                    }
                },
                "definitions": {
                    "Pet": {"type": "object", "properties": {"id": {"type": "integer"}}}
                },
            }
        )
        body = _endpoint(result, "POST", "/pets")["request_body"]
        assert body["required"] is True
        assert (
            body["content"]["application/json"]["schema"]["properties"]["id"]["type"] == "integer"
        )

    def test_unresolved_request_body_ref_omitted(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "post": {
                            "requestBody": {"$ref": "#/components/requestBodies/Missing"},
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        assert _endpoint(result, "POST", "/pets")["request_body"] is None

    def test_non_dict_response_skipped(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {"responses": {"200": "oops", "404": {"description": "Missing"}}}
                    }
                },
            }
        )
        schemas = _endpoint(result, "GET", "/pets")["response_schemas"]
        assert len(schemas) == 0

    def test_unresolved_response_ref_skipped(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {"responses": {"200": {"$ref": "#/components/responses/Missing"}}}
                    }
                },
            }
        )
        assert _endpoint(result, "GET", "/pets")["response_schemas"] == []

    def test_media_without_schema_skipped(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "OK",
                                    "content": {"application/json": {"description": "no schema"}},
                                }
                            }
                        }
                    }
                },
            }
        )
        assert _endpoint(result, "GET", "/pets")["response_schemas"] == []

    def test_operation_description_preserved(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {
                            "description": "Lists pets",
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        assert _endpoint(result, "GET", "/pets")["description"] == "Lists pets"

    def test_swagger_non_dict_parameter_ignored(self):
        result = parse_openapi_spec(
            {
                "swagger": "2.0",
                "info": {"title": "S", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "post": {
                            "parameters": ["nope"],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        assert _endpoint(result, "POST", "/pets")["request_body"] is None

    def test_non_dict_request_body_omitted(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "post": {
                            "requestBody": "nope",
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        )
        assert _endpoint(result, "POST", "/pets")["request_body"] is None

    def test_response_ref_to_scalar_skipped(self):
        result = parse_openapi_spec(
            {
                "openapi": "3.0.3",
                "info": {"title": "P", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {"responses": {"200": {"$ref": "#/components/responses/StrR"}}}
                    }
                },
                "components": {"responses": {"StrR": "nope"}},
            }
        )
        assert _endpoint(result, "GET", "/pets")["response_schemas"] == []


class TestDecodeJsonPointer:
    def test_empty_fragment(self):
        from app.core.security_engine.ref_resolver import decode_json_pointer

        assert decode_json_pointer("#/") == []

    def test_escapes_decoded(self):
        from app.core.security_engine.ref_resolver import decode_json_pointer

        assert decode_json_pointer("#/a~1b/~0c") == ["a/b", "~c"]

    def test_plain_segments(self):
        from app.core.security_engine.ref_resolver import decode_json_pointer

        assert decode_json_pointer("#/components/schemas/Pet") == [
            "components",
            "schemas",
            "Pet",
        ]
