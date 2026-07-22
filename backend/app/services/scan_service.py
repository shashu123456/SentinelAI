import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import Scan, Finding, AIAnalysis
from app.core.security_engine.parser import parse_openapi_spec
from app.core.security_engine.scanner import run_owasp_scan
from app.core.risk_engine.scorer import calculate_risk_score
from app.core.ai_engine.analyzer import analyze_vulnerabilities
from app.utils.logger import logger


def execute_scan(db: Session, user_id: int, api_name: str, spec: dict) -> Scan:
    scan = Scan(
        user_id=user_id,
        api_name=api_name,
        status="running",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        parsed_api = parse_openapi_spec(spec)

        scan.api_title = parsed_api["title"]
        scan.api_version = parsed_api["version"]
        scan.total_endpoints = parsed_api["total_endpoints"]
        db.commit()

        findings = run_owasp_scan(parsed_api)

        for f in findings:
            db_finding = Finding(
                scan_id=scan.id,
                vulnerability_name=f["vulnerability_name"],
                owasp_category=f["owasp_category"],
                cwe_id=f.get("cwe_id"),
                severity=f["severity"],
                confidence=f.get("confidence", 85),
                description=f["description"],
                evidence=f.get("evidence", ""),
                impact=f["impact"],
                remediation=f["remediation"],
                affected_endpoint=f.get("affected_endpoint"),
                affected_method=f.get("affected_method"),
                detection_reason=f.get("detection_reason", ""),
                false_positive_note=f.get("false_positive_note", ""),
            )
            db.add(db_finding)

        risk = calculate_risk_score(findings)
        scan.total_vulnerabilities = risk["total_vulnerabilities"]
        scan.risk_score = risk["score"]
        scan.risk_level = risk["level"]

        try:
            ai_result = analyze_vulnerabilities(findings, parsed_api)
            if ai_result:
                db_analysis = AIAnalysis(
                    scan_id=scan.id,
                    executive_summary=ai_result.get("executive_summary", ""),
                    technical_explanation=ai_result.get("technical_explanation", ""),
                    business_impact=ai_result.get("business_impact", ""),
                    attack_scenario=ai_result.get("attack_scenario", ""),
                    recommended_mitigation=ai_result.get("recommended_mitigation", ""),
                )
                db.add(db_analysis)
        except Exception as e:
            logger.warning(f"AI analysis failed for scan {scan.id}: {e}")

        scan.status = "completed"
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)

        logger.info(f"Scan {scan.id} completed: {risk['total_vulnerabilities']} findings, score {risk['score']}/100")

    except Exception as e:
        scan.status = "failed"
        db.commit()
        logger.error(f"Scan {scan.id} failed: {e}")
        raise

    return scan


def build_report_data(scan: Scan) -> dict:
    findings_data = []
    for f in scan.findings:
        findings_data.append({
            "vulnerability_name": f.vulnerability_name,
            "owasp_category": f.owasp_category,
            "cwe_id": f.cwe_id,
            "severity": f.severity,
            "confidence": f.confidence,
            "description": f.description,
            "evidence": f.evidence,
            "impact": f.impact,
            "remediation": f.remediation,
            "affected_endpoint": f.affected_endpoint,
            "affected_method": f.affected_method,
            "detection_reason": f.detection_reason,
            "false_positive_note": f.false_positive_note,
        })

    ai_data = None
    if scan.ai_analysis:
        ai_data = {
            "executive_summary": scan.ai_analysis.executive_summary,
            "technical_explanation": scan.ai_analysis.technical_explanation,
            "business_impact": scan.ai_analysis.business_impact,
            "attack_scenario": scan.ai_analysis.attack_scenario,
            "recommended_mitigation": scan.ai_analysis.recommended_mitigation,
        }

    return {
        "api_name": scan.api_name,
        "api_version": scan.api_version or "N/A",
        "scan_date": scan.created_at.strftime("%Y-%m-%d %H:%M UTC") if scan.created_at else "N/A",
        "total_endpoints": scan.total_endpoints,
        "risk_score": scan.risk_score,
        "risk_level": scan.risk_level,
        "findings": findings_data,
        "ai_analysis": ai_data,
    }
