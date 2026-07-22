import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from app.core.security_engine.parser import parse_openapi_spec
from app.core.security_engine.scanner import run_owasp_scan
from app.core.risk_engine.scorer import calculate_risk_score
from app.core.ai_engine.analyzer import analyze_vulnerabilities
from app.utils.logger import logger


@dataclass
class ScanTask:
    task_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "Queued"
    scan_id: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    subscribers: list = field(default_factory=list)


_tasks: Dict[str, ScanTask] = {}


def get_task(task_id: str) -> Optional[ScanTask]:
    return _tasks.get(task_id)


def get_task_by_scan_id(scan_id: int) -> Optional[ScanTask]:
    for task in _tasks.values():
        if task.scan_id == scan_id:
            return task
    return None


async def publish_progress(task: ScanTask):
    dead = []
    for ws in task.subscribers:
        try:
            await ws.send_json({
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "scan_id": task.scan_id,
            })
        except Exception:
            dead.append(ws)
    for ws in dead:
        task.subscribers.remove(ws)


async def run_scan_task(
    task_id: str,
    spec: dict,
    user_id: int,
    api_name: str,
    db_session_factory: Callable,
    enable_ai: bool = True,
):
    task = _tasks.get(task_id)
    if not task:
        return

    task.status = "running"
    task.message = "Initializing scan engine..."
    task.progress = 5
    await publish_progress(task)

    try:
        db = db_session_factory()

        from app.models.models import Scan, Finding, AIAnalysis

        scan = Scan(user_id=user_id, api_name=api_name, status="running")
        db.add(scan)
        db.commit()
        db.refresh(scan)
        task.scan_id = scan.id

        task.message = "Parsing OpenAPI specification..."
        task.progress = 15
        await publish_progress(task)
        await asyncio.sleep(0.1)

        parsed_api = parse_openapi_spec(spec)
        scan.api_title = parsed_api["title"]
        scan.api_version = parsed_api["version"]
        scan.total_endpoints = parsed_api["total_endpoints"]
        db.commit()

        # Show parsed API info
        task.message = f"API: {parsed_api['title']} v{parsed_api['version']}"
        task.progress = 18
        await publish_progress(task)
        await asyncio.sleep(0.05)

        # Show each discovered endpoint
        endpoints = parsed_api.get("endpoints", [])
        for i, ep in enumerate(endpoints):
            method = ep["method"]
            path = ep["path"]
            task.message = f"  [{method}] {path}"
            task.progress = 18 + int((i / max(len(endpoints), 1)) * 12)
            await publish_progress(task)
            await asyncio.sleep(0.03)

        # Show security scheme info
        schemes = parsed_api.get("security_schemes", {}).get("schemes", {})
        if schemes:
            scheme_names = ", ".join(schemes.keys())
            task.message = f"Security schemes: {scheme_names}"
        else:
            task.message = "No security schemes defined"
        task.progress = 30
        await publish_progress(task)
        await asyncio.sleep(0.05)

        task.message = f"Running OWASP Top 10 checks on {parsed_api['total_endpoints']} endpoints..."
        task.progress = 32
        await publish_progress(task)

        owasp_checks = [
            ("API1", "Broken Object Level Authorization", 35),
            ("API2", "Broken Authentication", 40),
            ("API3", "Broken Object Property Level Authorization", 45),
            ("API4", "Unrestricted Resource Consumption", 50),
            ("API5", "Broken Function Level Authorization", 55),
            ("API6", "Unrestricted Access to Sensitive Business Flows", 60),
            ("API7", "Server Side Request Forgery", 63),
            ("API8", "Security Misconfiguration", 66),
            ("API9", "Improper Inventory Management", 69),
            ("API10", "Unsafe Consumption of APIs", 72),
        ]

        findings = run_owasp_scan(parsed_api)

        check_findings_map = {}
        for f in findings:
            cat = f.get("owasp_category", "")
            check_findings_map.setdefault(cat, []).append(f)

        for check_id, check_name, progress in owasp_checks:
            task.message = f"  [{check_id}] {check_name}..."
            task.progress = progress
            await publish_progress(task)
            await asyncio.sleep(0.05)

            cat_findings = check_findings_map.get(check_id, [])
            for f in cat_findings:
                method = f.get("affected_method", "N/A")
                endpoint = f.get("affected_endpoint", "N/A")
                severity = f["severity"]
                vuln = f["vulnerability_name"]
                task.message = f"    [{severity.upper()}] {method} {endpoint} - {vuln}"
                task.progress = min(progress + 1, 74)
                await publish_progress(task)
                await asyncio.sleep(0.03)

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

        task.message = f"Completed OWASP checks. Calculating risk score..."
        task.progress = 75
        await publish_progress(task)
        await asyncio.sleep(0.1)

        risk = calculate_risk_score(findings)
        scan.total_vulnerabilities = risk["total_vulnerabilities"]
        scan.risk_score = risk["score"]
        scan.risk_level = risk["level"]

        task.message = f"Risk Score: {risk['score']}/100 ({risk['level']})"
        task.progress = 80
        await publish_progress(task)
        await asyncio.sleep(0.05)

        if enable_ai and findings:
            task.message = "Running AI security analysis (Ollama)..."
            task.progress = 85
            await publish_progress(task)

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

        task.status = "completed"
        task.progress = 100
        task.message = f"{'─' * 50}"
        await publish_progress(task)
        task.message = f"Scan complete: {risk['total_vulnerabilities']} vulnerabilities, risk {risk['score']}/100"
        task.result = {
            "scan_id": scan.id,
            "total_vulnerabilities": risk["total_vulnerabilities"],
            "risk_score": risk["score"],
            "risk_level": risk["level"],
        }
        await publish_progress(task)

        logger.info(f"Background scan {scan.id} completed: {risk['total_vulnerabilities']} findings")

        db.close()

    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        task.message = f"Scan failed: {e}"
        await publish_progress(task)
        logger.error(f"Background scan task {task_id} failed: {e}")

        if task.scan_id:
            try:
                db = db_session_factory()
                from app.models.models import Scan
                scan = db.query(Scan).filter(Scan.id == task.scan_id).first()
                if scan:
                    scan.status = "failed"
                    db.commit()
                db.close()
            except Exception:
                pass


def create_scan_task(
    spec: dict,
    user_id: int,
    api_name: str,
    db_session_factory: Callable,
    enable_ai: bool = True,
) -> str:
    task_id = str(uuid.uuid4())
    task = ScanTask(task_id=task_id, status="queued")
    _tasks[task_id] = task

    asyncio.create_task(
        run_scan_task(task_id, spec, user_id, api_name, db_session_factory, enable_ai)
    )

    return task_id
