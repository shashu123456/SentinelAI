"""Risk Intelligence Engine.

Centralized scoring engine that combines scanner results, SAST findings,
dependency vulnerabilities, and AI confidence into composite risk assessments.
"""

from dataclasses import dataclass
from typing import Any

from app.utils.cvss import (
    compute_cvss_score,
    risk_score_from_severity_distribution,
    security_grade,
)


@dataclass
class RiskAssessment:
    """Complete risk assessment for a scan or project."""

    risk_score: int  # 0-100
    risk_level: str  # Critical, High, Medium, Low, Clean
    security_grade: str  # A, B+, B, C, D, F
    confidence_score: float  # 0.0-1.0
    priority: str  # P1, P2, P3, P4
    business_risk: str  # Critical, High, Medium, Low
    total_findings: int
    severity_breakdown: dict[str, int]
    top_cwes: list[dict[str, Any]]
    top_owasp: list[dict[str, Any]]
    recommendations: list[str]


def compute_risk_assessment(findings: list[dict[str, Any]]) -> RiskAssessment:
    """Compute a comprehensive risk assessment from a list of findings.

    Each finding dict should contain:
        - severity: str
        - cwe_id: str | None
        - owasp_category: str
        - confidence: int | None
        - cvss_score: float | None
    """
    if not findings:
        return RiskAssessment(
            risk_score=0,
            risk_level="Clean",
            security_grade="A",
            confidence_score=1.0,
            priority="P4",
            business_risk="Low",
            total_findings=0,
            severity_breakdown={},
            top_cwes=[],
            top_owasp=[],
            recommendations=["No vulnerabilities detected. Continue monitoring."],
        )

    # Severity breakdown
    severity_breakdown: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "Info")
        severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

    # Compute risk score
    risk_score = risk_score_from_severity_distribution(severity_breakdown)

    # Confidence score (average of all findings)
    confidences = [f.get("confidence", 85) for f in findings if f.get("confidence") is not None]
    confidence_score = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.85

    # Adjust risk score by confidence
    adjusted_score = min(100, round(risk_score * (0.8 + confidence_score * 0.2)))

    # Risk level
    if adjusted_score >= 80:
        risk_level = "Critical"
    elif adjusted_score >= 60:
        risk_level = "High"
    elif adjusted_score >= 30:
        risk_level = "Medium"
    elif adjusted_score > 0:
        risk_level = "Low"
    else:
        risk_level = "Clean"

    # Security grade
    grade = security_grade(adjusted_score)

    # Priority
    crit_count = severity_breakdown.get("Critical", 0)
    high_count = severity_breakdown.get("High", 0)
    if crit_count > 0:
        priority = "P1"
    elif high_count >= 3:
        priority = "P1"
    elif high_count > 0:
        priority = "P2"
    elif severity_breakdown.get("Medium", 0) >= 5:
        priority = "P2"
    elif severity_breakdown.get("Medium", 0) > 0:
        priority = "P3"
    else:
        priority = "P4"

    # Business risk
    if risk_score >= 80:
        business_risk = "Critical"
    elif risk_score >= 60:
        business_risk = "High"
    elif risk_score >= 30:
        business_risk = "Medium"
    else:
        business_risk = "Low"

    # Top CWEs
    cwe_counts: dict[str, int] = {}
    for f in findings:
        cwe = f.get("cwe_id")
        if cwe:
            cwe_counts[cwe] = cwe_counts.get(cwe, 0) + 1
    top_cwes = [
        {"cwe_id": cwe, "count": count}
        for cwe, count in sorted(cwe_counts.items(), key=lambda x: -x[1])[:5]
    ]

    # Top OWASP categories
    owasp_counts: dict[str, int] = {}
    for f in findings:
        owasp = f.get("owasp_category", "Unknown")
        owasp_counts[owasp] = owasp_counts.get(owasp, 0) + 1
    top_owasp = [
        {"category": cat, "count": count}
        for cat, count in sorted(owasp_counts.items(), key=lambda x: -x[1])[:5]
    ]

    # Recommendations
    recommendations = _generate_recommendations(severity_breakdown, top_cwes, top_owasp)

    return RiskAssessment(
        risk_score=adjusted_score,
        risk_level=risk_level,
        security_grade=grade,
        confidence_score=round(confidence_score, 2),
        priority=priority,
        business_risk=business_risk,
        total_findings=len(findings),
        severity_breakdown=severity_breakdown,
        top_cwes=top_cwes,
        top_owasp=top_owasp,
        recommendations=recommendations,
    )


def _generate_recommendations(
    severity_breakdown: dict[str, int],
    top_cwes: list[dict[str, Any]],
    top_owasp: list[dict[str, Any]],
) -> list[str]:
    """Generate actionable security recommendations."""
    recs: list[str] = []

    if severity_breakdown.get("Critical", 0) > 0:
        recs.append(
            f"URGENT: {severity_breakdown['Critical']} critical vulnerabilities require "
            "immediate remediation before deployment."
        )

    if severity_breakdown.get("High", 0) > 0:
        recs.append(
            f"Address {severity_breakdown['High']} high-severity findings within this sprint."
        )

    for cwe in top_cwes[:3]:
        recs.append(f"Review and remediate {cwe['cwe_id']} ({cwe['count']} occurrences).")

    for owasp in top_owasp[:2]:
        recs.append(f"Implement controls for {owasp['category']} " f"({owasp['count']} findings).")

    if not recs:
        recs.append("No immediate action required. Maintain current security posture.")

    return recs[:8]  # Cap at 8 recommendations


def compute_finding_risk(finding: dict[str, Any]) -> dict[str, Any]:
    """Enrich a single finding with computed risk data."""
    score, vector = compute_cvss_score(
        severity=finding.get("severity", "Medium"),
        owasp_category=finding.get("owasp_category"),
        confidence=finding.get("confidence"),
    )
    return {
        "cvss_score": score,
        "cvss_vector": vector,
    }
