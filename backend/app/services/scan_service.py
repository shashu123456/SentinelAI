"""Scan execution service.

Orchestrates the full scan lifecycle:
  1. Parse OpenAPI spec
  2. Run OWASP security scan
  3. Compute risk score and assessment
  4. Run AI analysis (optional)
  5. Record audit events

Transaction strategy:
  - The scan record is committed immediately so the user gets a scan ID and
    the record survives if the worker crashes mid-scan.
  - All subsequent mutations (findings, AI analysis, risk score, audit events)
    are batched into a single commit at the end.  On failure, only the scan
    status is updated to 'failed' and committed separately.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.ai_engine.analyzer import analyze_vulnerabilities
from app.core.risk_engine.scorer import calculate_risk_score
from app.core.security_engine.parser import parse_openapi_spec
from app.core.security_engine.scanner import run_owasp_scan
from app.models.models import AIAnalysis, Scan
from app.repositories.findings import FindingRepository
from app.repositories.scans import ScanRepository
from app.services.audit_service import record_scan_event
from app.services.risk_engine import compute_risk_assessment
from app.utils.logger import logger


def execute_scan(db: Session, user_id: int, api_name: str, spec: dict) -> Scan:
    """Execute a synchronous scan and persist all results.

    The scan record is committed immediately (so the user can poll status),
    then findings, risk data, AI analysis, and audit events are committed
    together in one transaction.
    """
    scan_repo = ScanRepository(db)
    finding_repo = FindingRepository(db)

    # --- Phase 1: create scan record (committed immediately) ---
    scan = scan_repo.create_scan(user_id=user_id, api_name=api_name, source_spec=spec)
    scan_repo.add(scan)
    db.commit()
    db.refresh(scan)

    record_scan_event(
        db, "scan.started", user_id=user_id, scan_id=scan.id, detail={"api_name": api_name}
    )
    db.commit()

    # --- Phase 2: execute scan and persist results ---
    try:
        parsed_api = parse_openapi_spec(spec)

        scan.api_title = parsed_api["title"]
        scan.api_version = parsed_api["version"]
        scan.total_endpoints = parsed_api["total_endpoints"]

        findings = run_owasp_scan(parsed_api)
        finding_repo.bulk_add_from_scan(scan.id, findings)

        risk = calculate_risk_score(findings)

        # Enhanced risk assessment
        try:
            assessment = compute_risk_assessment(findings)
            risk["security_grade"] = assessment.security_grade
            risk["confidence_score"] = assessment.confidence_score
            risk["priority"] = assessment.priority
            risk["business_risk"] = assessment.business_risk
            risk["top_cwes"] = assessment.top_cwes
            risk["top_owasp"] = assessment.top_owasp
            risk["recommendations"] = assessment.recommendations
        except Exception as e:
            logger.warning(f"Risk assessment failed for scan {scan.id}: {e}")

        scan_repo.complete(scan, risk, scan.transition_history)

        # AI analysis (best-effort, non-blocking)
        try:
            ai_result = analyze_vulnerabilities(findings, parsed_api)
            if ai_result:
                db.add(
                    AIAnalysis(
                        scan_id=scan.id,
                        executive_summary=ai_result.get("executive_summary", ""),
                        technical_explanation=ai_result.get("technical_explanation", ""),
                        business_impact=ai_result.get("business_impact", ""),
                        attack_scenario=ai_result.get("attack_scenario", ""),
                        recommended_mitigation=ai_result.get("recommended_mitigation", ""),
                    )
                )
        except Exception as e:
            logger.warning(f"AI analysis failed for scan {scan.id}: {e}")

        scan.status = "completed"
        scan.completed_at = datetime.now(UTC)

        # Single commit for findings + risk + AI + status
        db.commit()

        record_scan_event(
            db,
            "scan.completed",
            user_id=user_id,
            scan_id=scan.id,
            detail={
                "total_vulnerabilities": risk["total_vulnerabilities"],
                "risk_score": risk["score"],
                "risk_level": risk["level"],
            },
        )
        db.commit()

        logger.info(
            f"Scan {scan.id} completed: {risk['total_vulnerabilities']} findings, "
            f"score {risk['score']}/100"
        )

    except Exception as e:
        # Minimal recovery: mark scan as failed and record the event
        try:
            scan.status = "failed"
            db.commit()
            record_scan_event(
                db, "scan.failed", user_id=user_id, scan_id=scan.id, detail={"error": str(e)}
            )
            db.commit()
        except Exception:
            logger.error(f"Failed to record scan failure for scan {scan.id}: {e}")
            db.rollback()
        logger.error(f"Scan {scan.id} failed: {e}")
        raise

    return scan


def build_report_data(scan: Scan) -> dict:
    """Build a serialisable dict for report generation.

    Uses ``scan.findings`` which is expected to be eagerly loaded or already
    populated (e.g. after ``execute_scan``).  If the relationship is not yet
    loaded, this triggers one query via the lazy loader — acceptable for a
    report-generation path.
    """
    findings_data = [
        {
            "vulnerability_name": f.vulnerability_name,
            "owasp_category": f.owasp_category,
            "cwe_id": f.cwe_id,
            "severity": f.severity,
            "confidence": f.confidence,
            "description": f.description,
            "evidence": f.evidence,
            "impact": f.impact,
            "remediation": f.remediation,
            "technical_impact": f.technical_impact,
            "business_impact": f.business_impact,
            "request_example": f.request_example,
            "response_example": f.response_example,
            "fix_recommendation": f.fix_recommendation,
            "references": f.references,
            "cvss_score": f.cvss_score,
            "cvss_vector": f.cvss_vector,
            "affected_endpoint": f.affected_endpoint,
            "affected_method": f.affected_method,
            "detection_reason": f.detection_reason,
            "false_positive_note": f.false_positive_note,
        }
        for f in scan.findings
    ]

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
