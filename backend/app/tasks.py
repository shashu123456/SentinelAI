import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.ai_engine.analyzer import analyze_vulnerabilities
from app.core.risk_engine.scorer import calculate_risk_score
from app.core.security_engine.parser import parse_openapi_spec
from app.core.security_engine.scanner import CHECK_REGISTRY, run_owasp_scan
from app.models.models import AIAnalysis, Scan
from app.repositories.findings import FindingRepository
from app.repositories.scans import ScanRepository
from app.services.audit_service import record_scan_event
from app.utils.logger import logger


@dataclass
class ScanTask:
    task_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "Queued"
    scan_id: int | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    subscribers: list = field(default_factory=list)


_tasks: dict[str, ScanTask] = {}


def get_task(task_id: str) -> ScanTask | None:
    return _tasks.get(task_id)


def get_task_stats() -> dict[str, Any]:
    """Return aggregate task queue statistics."""
    active = sum(1 for t in _tasks.values() if t.status == "running")
    queued = sum(1 for t in _tasks.values() if t.status == "queued")
    completed = sum(1 for t in _tasks.values() if t.status == "completed")
    failed = sum(1 for t in _tasks.values() if t.status == "failed")
    return {
        "active": active,
        "queued": queued,
        "completed": completed,
        "failed": failed,
        "total": len(_tasks),
    }


def get_task_by_scan_id(scan_id: int) -> ScanTask | None:
    for task in _tasks.values():
        if task.scan_id == scan_id:
            return task
    return None


async def publish_progress(task: ScanTask):
    dead = []
    for ws in task.subscribers:
        try:
            await ws.send_json(
                {
                    "task_id": task.task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "message": task.message,
                    "scan_id": task.scan_id,
                }
            )
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
    task.transition_history = []
    await publish_progress(task)

    try:
        db = db_session_factory()

        scan_repo = ScanRepository(db)
        finding_repo = FindingRepository(db)

        scan = scan_repo.create_scan(user_id=user_id, api_name=api_name, source_spec=spec)
        scan_repo.add(scan)
        scan_repo.commit()
        scan_repo.refresh(scan)
        task.scan_id = scan.id

        record_scan_event(
            db, "scan.started", user_id=user_id, scan_id=scan.id, detail={"api_name": api_name}
        )
        scan_repo.commit()

        task.message = "Parsing OpenAPI specification..."
        task.progress = 15
        await publish_progress(task)
        await asyncio.sleep(0.1)

        parsed_api = parse_openapi_spec(spec)
        scan.api_title = parsed_api["title"]
        scan.api_version = parsed_api["version"]
        scan.total_endpoints = parsed_api["total_endpoints"]
        scan_repo.commit()

        # Show parsed API info and record transition
        task.message = f"API: {parsed_api['title']} v{parsed_api['version']}"
        task.progress = 18
        task.transition_history.append(
            {"from": "parsing", "to": "endpoints", "at": time.time(), "reason": "api_parsed"}
        )
        await publish_progress(task)
        await asyncio.sleep(0.05)

        # Show each discovered endpoint and track transition history
        endpoints = parsed_api.get("endpoints", [])
        for i, ep in enumerate(endpoints):
            method = ep["method"]
            path = ep["path"]
            task.message = f"  [{method}] {path}"
            task.progress = 18 + int((i / max(len(endpoints), 1)) * 12)
            task.transition_history.append(
                {
                    "from": "endpoints",
                    "to": "checking",
                    "at": time.time(),
                    "reason": f"endpoint_discovered[{method}] {path}",
                }
            )
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

        task.message = (
            f"Running OWASP Top 10 checks on {parsed_api['total_endpoints']} endpoints..."
        )
        task.progress = 32
        await publish_progress(task)

        owasp_checks = []
        total_checks = len(CHECK_REGISTRY)
        progress_start, progress_end = 35, 74
        for i, check in enumerate(CHECK_REGISTRY):
            progress = progress_start + int(
                (i / max(total_checks, 1)) * (progress_end - progress_start)
            )
            owasp_checks.append((check["category"], check["name"], progress))

        findings = run_owasp_scan(parsed_api)

        check_findings_map: dict[str, list[dict]] = {}
        for f in findings:
            cat = f.get("owasp_category", "")
            check_findings_map.setdefault(cat, []).append(f)

        for check_id, check_name, progress in owasp_checks:
            task.message = f"  [{check_id}] {check_name}..."
            task.progress = progress
            await publish_progress(task)
            await asyncio.sleep(0.03)

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

        task.transition_history.append(
            {"from": "checking", "to": "risk", "at": time.time(), "reason": "owasp_checks_complete"}
        )

        finding_repo.bulk_add_from_scan(scan.id, findings)

        task.message = "Completed OWASP checks. Calculating risk score..."
        task.progress = 75
        await publish_progress(task)
        await asyncio.sleep(0.1)

        risk = calculate_risk_score(findings)
        task.transition_history.append(
            {"from": "risk", "to": "completed", "at": time.time(), "reason": "risk_calculated"}
        )
        scan_repo.complete(scan, risk, task.transition_history)
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
        scan_repo.commit()

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
        scan_repo.commit()

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

        logger.info(
            f"Background scan {scan.id} completed: {risk['total_vulnerabilities']} findings"
        )

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
                scan = db.query(Scan).filter(Scan.id == task.scan_id).first()
                if scan:
                    scan.status = "failed"
                    db.commit()
                    record_scan_event(
                        db,
                        "scan.failed",
                        user_id=user_id,
                        scan_id=scan.id,
                        detail={"error": str(e)},
                    )
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
