from app.core.security_engine.scanner import run_owasp_scan, OWASP_CATEGORIES
from app.core.security_engine.parser import parse_openapi_spec


class TestOWASPCategories:
    def test_all_10_categories_defined(self):
        assert len(OWASP_CATEGORIES) == 10
        for i in range(1, 11):
            key = f"API{i}"
            assert key in OWASP_CATEGORIES

    def test_category_names_correct(self):
        assert OWASP_CATEGORIES["API1"] == "Broken Object Level Authorization"
        assert OWASP_CATEGORIES["API2"] == "Broken Authentication"
        assert OWASP_CATEGORIES["API7"] == "Server Side Request Forgery"
        assert OWASP_CATEGORIES["API10"] == "Unsafe Consumption of APIs"


class TestAPI1BrokenObjectLevelAuthorization:
    def test_detects_id_without_user_scoping(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api1 = [f for f in findings if f["owasp_category"] == "API1"]
        assert len(api1) > 0

    def test_no_false_positive_with_user_scoping(self, secure_spec):
        parsed = parse_openapi_spec(secure_spec)
        findings = run_owasp_scan(parsed)
        api1 = [f for f in findings if f["owasp_category"] == "API1"]
        assert len(api1) == 0


class TestAPI2BrokenAuthentication:
    def test_detects_unauthenticated_endpoints(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api2 = [f for f in findings if f["owasp_category"] == "API2"]
        assert len(api2) > 0

    def test_no_false_positive_when_authenticated(self, secure_spec):
        parsed = parse_openapi_spec(secure_spec)
        findings = run_owasp_scan(parsed)
        api2 = [f for f in findings if f["owasp_category"] == "API2"]
        assert len(api2) == 0

    def test_detects_unauthenticated_mutating_methods(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api2_delete = [f for f in findings if f["owasp_category"] == "API2" and f.get("affected_method") == "DELETE"]
        assert len(api2_delete) > 0


class TestAPI3BrokenObjectPropertyLevelAuthorization:
    def test_detects_sensitive_properties(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api3 = [f for f in findings if f["owasp_category"] == "API3"]
        assert len(api3) > 0
        sensitive_names = [f["vulnerability_name"] for f in api3]
        assert any("password" in name.lower() or "admin" in name.lower() for name in sensitive_names)


class TestAPI4UnrestrictedResourceConsumption:
    def test_detects_missing_pagination(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api4 = [f for f in findings if f["owasp_category"] == "API4"]
        assert len(api4) > 0

    def test_no_false_positive_with_pagination(self, secure_spec):
        parsed = parse_openapi_spec(secure_spec)
        findings = run_owasp_scan(parsed)
        api4 = [f for f in findings if f["owasp_category"] == "API4"]
        assert len(api4) == 0


class TestAPI5BrokenFunctionLevelAuthorization:
    def test_detects_admin_endpoints(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api5 = [f for f in findings if f["owasp_category"] == "API5"]
        assert len(api5) > 0


class TestAPI7SSRF:
    def test_detects_webhook_urls(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api7 = [f for f in findings if f["owasp_category"] == "API7"]
        assert len(api7) > 0
        assert any("webhook" in f["evidence"].lower() or "url" in f["evidence"].lower() for f in api7)


class TestAPI8SecurityMisconfiguration:
    def test_detects_no_security_schemes(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api8 = [f for f in findings if f["owasp_category"] == "API8"]
        assert len(api8) > 0
        assert any("No Security Schemes" in f["vulnerability_name"] for f in api8)

    def test_no_false_positive_with_schemes(self, secure_spec):
        parsed = parse_openapi_spec(secure_spec)
        findings = run_owasp_scan(parsed)
        api8_no_scheme = [f for f in findings if "No Security Schemes" in f["vulnerability_name"]]
        assert len(api8_no_scheme) == 0


class TestAPI10UnsafeConsumption:
    def test_detects_external_urls(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        api10 = [f for f in findings if f["owasp_category"] == "API10"]
        assert len(api10) > 0


class TestFindingStructure:
    def test_all_findings_have_required_fields(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        required = ["vulnerability_name", "owasp_category", "severity", "description", "evidence", "impact", "remediation"]
        for f in findings:
            for field in required:
                assert field in f, f"Missing '{field}' in finding: {f.get('vulnerability_name', '?')}"

    def test_severity_values_valid(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        valid_severities = {"Critical", "High", "Medium", "Low", "Info"}
        for f in findings:
            assert f["severity"] in valid_severities, f"Invalid severity: {f['severity']}"

    def test_owasp_category_valid(self, sample_petstore_spec):
        parsed = parse_openapi_spec(sample_petstore_spec)
        findings = run_owasp_scan(parsed)
        for f in findings:
            assert f["owasp_category"].startswith("API")
            assert f["owasp_category"] in OWASP_CATEGORIES
