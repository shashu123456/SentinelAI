"""Security tools that the copilot agent can invoke.

Each tool queries the database or analyzes data to provide
real security context for the agent's responses.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, case as sa_case
from app.models.models import Scan, Finding, AIAnalysis


def get_latest_scan(db: Session, user_id: int) -> dict | None:
    """Get the most recent completed scan for a user."""
    scan = (
        db.query(Scan)
        .filter(Scan.user_id == user_id, Scan.status == "completed")
        .order_by(desc(Scan.created_at))
        .first()
    )
    if not scan:
        return None
    return _scan_to_dict(scan)


def get_scan_history(db: Session, user_id: int, limit: int = 10) -> list[dict]:
    """Get recent scan history for a user."""
    scans = (
        db.query(Scan)
        .filter(Scan.user_id == user_id, Scan.status == "completed")
        .order_by(desc(Scan.created_at))
        .limit(limit)
        .all()
    )
    return [_scan_summary(s) for s in scans]


def get_critical_findings(db: Session, user_id: int, scan_id: int = None) -> list[dict]:
    """Get Critical and High severity findings, optionally filtered by scan."""
    query = (
        db.query(Finding)
        .join(Scan)
        .filter(Scan.user_id == user_id)
    )
    if scan_id:
        query = query.filter(Finding.scan_id == scan_id)
    query = query.filter(Finding.severity.in_(["Critical", "High"]))
    query = query.order_by(
        sa_case(
            (Finding.severity == "Critical", 0),
            (Finding.severity == "High", 1),
            else_=2,
        )
    )
    findings = query.all()
    return [_finding_to_dict(f) for f in findings]


def get_all_findings(db: Session, user_id: int, scan_id: int = None) -> list[dict]:
    """Get all findings for a user, optionally filtered by scan."""
    query = (
        db.query(Finding)
        .join(Scan)
        .filter(Scan.user_id == user_id)
    )
    if scan_id:
        query = query.filter(Finding.scan_id == scan_id)
    query = query.order_by(
        sa_case(
            (Finding.severity == "Critical", 0),
            (Finding.severity == "High", 1),
            (Finding.severity == "Medium", 2),
            (Finding.severity == "Low", 3),
            else_=4,
        )
    )
    return [_finding_to_dict(f) for f in query.all()]


def get_vulnerability_details(db: Session, user_id: int, finding_id: int) -> dict | None:
    """Get full details of a specific vulnerability."""
    finding = (
        db.query(Finding)
        .join(Scan)
        .filter(Finding.id == finding_id, Scan.user_id == user_id)
        .first()
    )
    if not finding:
        return None
    return {
        **_finding_to_dict(finding),
        "evidence": finding.evidence,
        "detection_reason": finding.detection_reason,
        "false_positive_note": finding.false_positive_note,
    }


def get_findings_by_category(db: Session, user_id: int) -> dict:
    """Group findings by OWASP category."""
    findings = get_all_findings(db, user_id)
    categories = {}
    for f in findings:
        cat = f.get("owasp_category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)
    return categories


def get_findings_by_cwe(db: Session, user_id: int) -> dict:
    """Group findings by CWE ID."""
    findings = get_all_findings(db, user_id)
    cwes = {}
    for f in findings:
        cwe = f.get("cwe_id", "Unknown")
        if cwe not in cwes:
            cwes[cwe] = []
        cwes[cwe].append(f)
    return cwes


def get_ai_analysis(db: Session, scan_id: int) -> dict | None:
    """Get AI-generated analysis for a scan."""
    analysis = db.query(AIAnalysis).filter(AIAnalysis.scan_id == scan_id).first()
    if not analysis:
        return None
    return {
        "executive_summary": analysis.executive_summary,
        "technical_explanation": analysis.technical_explanation,
        "business_impact": analysis.business_impact,
        "attack_scenario": analysis.attack_scenario,
        "recommended_mitigation": analysis.recommended_mitigation,
    }


def get_risk_summary(db: Session, user_id: int) -> dict:
    """Get overall risk summary across all scans."""
    scans = (
        db.query(Scan)
        .filter(Scan.user_id == user_id, Scan.status == "completed")
        .order_by(desc(Scan.created_at))
        .all()
    )
    if not scans:
        return {"total_scans": 0, "risk_score": 0, "risk_level": "Unknown", "total_findings": 0}

    latest = scans[0]
    all_findings = []
    for s in scans:
        all_findings.extend(s.findings)

    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in all_findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

    return {
        "total_scans": len(scans),
        "risk_score": latest.risk_score,
        "risk_level": latest.risk_level,
        "total_findings": len(all_findings),
        "severity_counts": severity_counts,
        "latest_scan": _scan_summary(latest),
    }


def compare_scans(db: Session, user_id: int) -> dict | None:
    """Compare the two most recent scans."""
    scans = (
        db.query(Scan)
        .filter(Scan.user_id == user_id, Scan.status == "completed")
        .order_by(desc(Scan.created_at))
        .limit(2)
        .all()
    )
    if len(scans) < 2:
        return None

    current, previous = scans[0], scans[1]
    current_findings = [_finding_to_dict(f) for f in current.findings]
    previous_findings = [_finding_to_dict(f) for f in previous.findings]

    current_sev = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    previous_sev = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in current_findings:
        current_sev[f["severity"]] = current_sev.get(f["severity"], 0) + 1
    for f in previous_findings:
        previous_sev[f["severity"]] = previous_sev.get(f["severity"], 0) + 1

    return {
        "current": _scan_to_dict(current),
        "previous": _scan_to_dict(previous),
        "score_change": current.risk_score - previous.risk_score,
        "finding_change": len(current_findings) - len(previous_findings),
        "current_severity": current_sev,
        "previous_severity": previous_sev,
        "improved": current.risk_score < previous.risk_score,
    }


def generate_executive_summary(db: Session, user_id: int) -> str:
    """Generate a rule-based executive summary from scan data."""
    risk = get_risk_summary(db, user_id)
    if risk["total_scans"] == 0:
        return "No scans have been performed yet. Run a security scan to get an executive summary."

    sev = risk.get("severity_counts", {})
    critical_high = sev.get("Critical", 0) + sev.get("High", 0)

    lines = [
        f"**Executive Security Assessment**",
        f"",
        f"**Risk Level:** {risk['risk_level']} (Score: {risk['risk_score']}/100)",
        f"**Total Findings:** {risk['total_findings']} across {risk['total_scans']} scan(s)",
        f"",
        f"**Severity Breakdown:**",
        f"- Critical: {sev.get('Critical', 0)}",
        f"- High: {sev.get('High', 0)}",
        f"- Medium: {sev.get('Medium', 0)}",
        f"- Low: {sev.get('Low', 0)}",
        f"- Informational: {sev.get('Info', 0)}",
        f"",
    ]

    if critical_high > 0:
        lines.append(f"**Immediate Action Required:** {critical_high} Critical/High findings must be remediated before production deployment.")
    else:
        lines.append(f"**Status:** No Critical or High findings. Security posture is acceptable.")

    return "\n".join(lines)


def generate_remediation_plan(db: Session, user_id: int, scan_id: int = None) -> str:
    """Generate a prioritized remediation plan."""
    findings = get_critical_findings(db, user_id, scan_id)
    all_findings = get_all_findings(db, user_id, scan_id)

    if not all_findings:
        return "No findings to remediate. Run a scan first."

    lines = ["**Prioritized Remediation Plan**", ""]

    if findings:
        lines.append("### Immediate (Critical/High)")
        lines.append("")
        for i, f in enumerate(findings, 1):
            lines.append(f"**{i}. {f['vulnerability_name']}** ({f['severity']})")
            lines.append(f"- Endpoint: {f.get('affected_endpoint', 'N/A')}")
            lines.append(f"- CWE: {f.get('cwe_id', 'N/A')}")
            lines.append(f"- Fix: {f.get('remediation', 'See OWASP guidelines')}")
            lines.append("")

    medium = [f for f in all_findings if f.get("severity") == "Medium"]
    if medium:
        lines.append("### Next Sprint (Medium)")
        lines.append("")
        for f in medium[:5]:
            lines.append(f"- {f['vulnerability_name']} ({f.get('cwe_id', '')}): {f.get('remediation', '')[:80]}")
        lines.append("")

    low = [f for f in all_findings if f.get("severity") in ("Low", "Info")]
    if low:
        lines.append("### Backlog (Low/Info)")
        lines.append("")
        lines.append(f"- {len(low)} informational findings for regular maintenance")

    return "\n".join(lines)


def explain_attack_path(db: Session, user_id: int) -> str:
    """Analyze potential attack paths from findings."""
    findings = get_critical_findings(db, user_id)
    if not findings:
        return "No critical findings to analyze for attack paths."

    lines = ["**Attack Path Analysis**", ""]

    auth_findings = [f for f in findings if any(w in f.get("vulnerability_name", "").lower() for w in ["auth", "session", "token", "password", "credential"])]
    injection_findings = [f for f in findings if any(w in f.get("vulnerability_name", "").lower() for w in ["injection", "sql", "xss", "command"])]
    access_findings = [f for f in findings if any(w in f.get("vulnerability_name", "").lower() for w in ["idor", "access", "authorization", "bypass"])]

    if auth_findings:
        lines.append("### Phase 1: Authentication Bypass")
        lines.append("An attacker would first target authentication weaknesses:")
        for f in auth_findings:
            lines.append(f"- {f['vulnerability_name']} at {f.get('affected_endpoint', 'N/A')}")
        lines.append("")

    if injection_findings:
        lines.append("### Phase 2: Data Extraction")
        lines.append("With access obtained, injection vulnerabilities enable data extraction:")
        for f in injection_findings:
            lines.append(f"- {f['vulnerability_name']} at {f.get('affected_endpoint', 'N/A')}")
        lines.append("")

    if access_findings:
        lines.append("### Phase 3: Privilege Escalation")
        lines.append("Access control flaws allow lateral movement:")
        for f in access_findings:
            lines.append(f"- {f['vulnerability_name']} at {f.get('affected_endpoint', 'N/A')}")
        lines.append("")

    lines.append("**Data at Risk:** User credentials, personal data, business logic, and system configuration.")

    return "\n".join(lines)


def _scan_to_dict(scan: Scan) -> dict:
    return {
        "id": scan.id,
        "api_name": scan.api_name,
        "api_title": scan.api_title,
        "api_version": scan.api_version,
        "risk_score": scan.risk_score,
        "risk_level": scan.risk_level,
        "total_endpoints": scan.total_endpoints,
        "total_vulnerabilities": scan.total_vulnerabilities,
        "status": scan.status,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "finding_count": len(scan.findings) if scan.findings else 0,
    }


def _scan_summary(scan: Scan) -> dict:
    return {
        "id": scan.id,
        "api_name": scan.api_name,
        "risk_score": scan.risk_score,
        "risk_level": scan.risk_level,
        "total_vulnerabilities": scan.total_vulnerabilities,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
    }


def _finding_to_dict(finding: Finding) -> dict:
    return {
        "id": finding.id,
        "vulnerability_name": finding.vulnerability_name,
        "owasp_category": finding.owasp_category,
        "cwe_id": finding.cwe_id,
        "severity": finding.severity,
        "confidence": finding.confidence,
        "description": finding.description,
        "impact": finding.impact,
        "remediation": finding.remediation,
        "affected_endpoint": finding.affected_endpoint,
        "affected_method": finding.affected_method,
    }
