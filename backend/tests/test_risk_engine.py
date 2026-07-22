from app.core.risk_engine.scorer import calculate_risk_score, get_severity_distribution


class TestRiskScoring:
    def test_empty_findings(self):
        result = calculate_risk_score([])
        assert result["score"] == 0
        assert result["level"] == "Low Risk"
        assert result["total_vulnerabilities"] == 0

    def test_critical_findings_high_score(self):
        findings = [
            {"severity": "Critical"},
            {"severity": "Critical"},
        ]
        result = calculate_risk_score(findings)
        assert result["score"] >= 80
        assert result["level"] == "Critical"
        assert result["critical_count"] == 2

    def test_single_high_finding(self):
        findings = [{"severity": "High"}]
        result = calculate_risk_score(findings)
        assert result["score"] >= 60

    def test_only_info_findings_low_score(self):
        findings = [
            {"severity": "Info"},
            {"severity": "Info"},
            {"severity": "Info"},
        ]
        result = calculate_risk_score(findings)
        assert result["score"] <= 30

    def test_mixed_severities(self):
        findings = [
            {"severity": "Critical"},
            {"severity": "High"},
            {"severity": "Medium"},
            {"severity": "Low"},
            {"severity": "Info"},
        ]
        result = calculate_risk_score(findings)
        assert result["total_vulnerabilities"] == 5
        assert result["critical_count"] == 1
        assert result["high_count"] == 1
        assert result["medium_count"] == 1
        assert result["low_count"] == 1
        assert result["info_count"] == 1
        assert result["score"] >= 80

    def test_score_never_exceeds_100(self):
        findings = [{"severity": "Critical"} for _ in range(20)]
        result = calculate_risk_score(findings)
        assert result["score"] <= 100

    def test_critical_floor_rule(self):
        findings = [
            {"severity": "Critical"},
            {"severity": "Info"},
            {"severity": "Info"},
        ]
        result = calculate_risk_score(findings)
        assert result["score"] >= 80

    def test_high_floor_rule(self):
        findings = [
            {"severity": "High"},
            {"severity": "Info"},
            {"severity": "Info"},
            {"severity": "Info"},
        ]
        result = calculate_risk_score(findings)
        assert result["score"] >= 60


class TestSeverityDistribution:
    def test_empty_findings(self):
        result = get_severity_distribution([])
        assert all(v == 0 for v in result.values())

    def test_counts_correctly(self):
        findings = [
            {"severity": "Critical"},
            {"severity": "Critical"},
            {"severity": "High"},
            {"severity": "Medium"},
            {"severity": "Medium"},
            {"severity": "Medium"},
        ]
        result = get_severity_distribution(findings)
        assert result["Critical"] == 2
        assert result["High"] == 1
        assert result["Medium"] == 3
        assert result["Low"] == 0
        assert result["Info"] == 0
