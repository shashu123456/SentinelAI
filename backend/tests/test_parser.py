from app.core.security_engine.parser import parse_openapi_spec


class TestOpenAPIParser:
    def test_parses_basic_spec(self, minimal_spec):
        result = parse_openapi_spec(minimal_spec)
        assert result["title"] == "Minimal API"
        assert result["version"] == "1.0.0"
        assert result["total_endpoints"] == 0
        assert result["endpoints"] == []

    def test_extracts_endpoints(self, sample_petstore_spec):
        result = parse_openapi_spec(sample_petstore_spec)
        assert result["total_endpoints"] == 7
        assert result["title"] == "Petstore"

    def test_extracts_methods(self, sample_petstore_spec):
        result = parse_openapi_spec(sample_petstore_spec)
        pets_endpoints = [e for e in result["endpoints"] if e["path"] == "/pets"]
        methods = [e["method"] for e in pets_endpoints]
        assert "GET" in methods
        assert "POST" in methods

    def test_detects_no_auth(self, sample_petstore_spec):
        result = parse_openapi_spec(sample_petstore_spec)
        unauth = [e for e in result["endpoints"] if not e["auth_required"]]
        assert len(unauth) > 0

    def test_detects_auth(self, secure_spec):
        result = parse_openapi_spec(secure_spec)
        auth_endpoints = [e for e in result["endpoints"] if e["auth_required"]]
        assert len(auth_endpoints) == 1

    def test_extracts_request_body(self, sample_petstore_spec):
        result = parse_openapi_spec(sample_petstore_spec)
        post_pets = [e for e in result["endpoints"] if e["path"] == "/pets" and e["method"] == "POST"]
        assert len(post_pets) == 1
        assert post_pets[0]["request_body"] is not None

    def test_extracts_path_parameters(self, sample_petstore_spec):
        result = parse_openapi_spec(sample_petstore_spec)
        get_pet = [e for e in result["endpoints"] if e["path"] == "/pets/{petId}" and e["method"] == "GET"]
        assert len(get_pet) == 1
        assert len(get_pet[0]["parameters"]) == 1
        assert get_pet[0]["parameters"][0]["name"] == "petId"

    def test_global_security_detection(self, secure_spec):
        result = parse_openapi_spec(secure_spec)
        assert len(result["security_schemes"]["schemes"]) == 1

    def test_handles_empty_paths(self):
        spec = {"openapi": "3.0.0", "info": {"title": "Empty", "version": "1.0"}, "paths": {}}
        result = parse_openapi_spec(spec)
        assert result["total_endpoints"] == 0

    def test_handles_missing_info(self):
        spec = {"openapi": "3.0.0", "paths": {}}
        result = parse_openapi_spec(spec)
        assert result["title"] == "Unknown API"
