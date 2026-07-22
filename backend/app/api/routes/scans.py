import json
import yaml
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.database import get_db, SessionLocal
from app.models.models import User, Scan, Finding
from app.schemas.schemas import (
    ScanCreate, ScanResponse, ScanDetailResponse,
    FindingResponse, AIAnalysisResponse, RiskScoreResponse, DashboardStats,
)
from app.services.scan_service import execute_scan, build_report_data
from app.reports.generator import generate_pdf_report, generate_json_report
from app.utils.security import get_current_user
from app.utils.logger import logger
from app.config import get_settings
from app.tasks import create_scan_task, get_task
from fastapi.responses import Response

settings = get_settings()
router = APIRouter(prefix="/api/scans", tags=["Scans"])

MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=ScanResponse)
async def upload_and_scan(
    file: UploadFile = File(...),
    api_name: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    valid_extensions = (".json", ".yaml", ".yml")
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {valid_extensions}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB}MB")

    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    try:
        if file.filename.lower().endswith((".yaml", ".yml")):
            spec = yaml.safe_load(content_str)
        else:
            spec = json.loads(content_str)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid specification format: {e}")

    if not isinstance(spec, dict):
        raise HTTPException(status_code=400, detail="Specification must be a JSON/YAML object")

    if "openapi" not in spec and "swagger" not in spec:
        raise HTTPException(status_code=400, detail="Not a valid OpenAPI/Swagger specification (missing 'openapi' or 'swagger' field)")

    if not api_name:
        api_name = spec.get("info", {}).get("title", file.filename)

    try:
        scan = execute_scan(db, current_user.id, api_name, spec)
    except Exception as e:
        logger.error(f"Scan execution failed: {e}")
        raise HTTPException(status_code=500, detail="Scan execution failed")

    return scan


@router.post("/upload/async")
async def upload_and_scan_async(
    file: UploadFile = File(...),
    api_name: str = Form(""),
    enable_ai: bool = Form(True),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    valid_extensions = (".json", ".yaml", ".yml")
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {valid_extensions}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB}MB")

    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    try:
        if file.filename.lower().endswith((".yaml", ".yml")):
            spec = yaml.safe_load(content_str)
        else:
            spec = json.loads(content_str)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid specification format: {e}")

    if not isinstance(spec, dict):
        raise HTTPException(status_code=400, detail="Specification must be a JSON/YAML object")

    if "openapi" not in spec and "swagger" not in spec:
        raise HTTPException(status_code=400, detail="Not a valid OpenAPI/Swagger specification")

    if not api_name:
        api_name = spec.get("info", {}).get("title", file.filename)

    task_id = create_scan_task(
        spec=spec,
        user_id=current_user.id,
        api_name=api_name,
        db_session_factory=SessionLocal,
        enable_ai=enable_ai,
    )

    return {"task_id": task_id, "message": "Scan started"}


@router.get("/task/{task_id}")
def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "scan_id": task.scan_id,
        "result": task.result,
        "error": task.error,
    }


@router.get("/", response_model=list[ScanResponse])
def list_scans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scans = (
        db.query(Scan)
        .filter(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
        .limit(50)
        .all()
    )
    return scans


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_scans = db.query(Scan).filter(Scan.user_id == current_user.id).count()
    total_vulns = (
        db.query(func.coalesce(func.sum(Scan.total_vulnerabilities), 0))
        .filter(Scan.user_id == current_user.id)
        .scalar()
    )
    avg_score = (
        db.query(func.coalesce(func.avg(Scan.risk_score), 0))
        .filter(Scan.user_id == current_user.id, Scan.status == "completed")
        .scalar()
    )

    recent = (
        db.query(Scan)
        .filter(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
        .limit(10)
        .all()
    )

    severity_dist = dict(
        db.query(Finding.severity, func.count(Finding.id))
        .join(Scan)
        .filter(Scan.user_id == current_user.id)
        .group_by(Finding.severity)
        .all()
    )
    for sev in ["Critical", "High", "Medium", "Low", "Info"]:
        severity_dist.setdefault(sev, 0)

    return DashboardStats(
        total_scans=total_scans,
        total_vulnerabilities=total_vulns,
        average_risk_score=round(float(avg_score), 1),
        recent_scans=[ScanResponse.model_validate(s) for s in recent],
        severity_distribution=severity_dist,
    )


@router.get("/{scan_id}", response_model=ScanDetailResponse)
def get_scan_detail(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == current_user.id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    response = ScanDetailResponse.model_validate(scan)
    response.findings = [FindingResponse.model_validate(f) for f in scan.findings]
    if scan.ai_analysis:
        response.ai_analysis = AIAnalysisResponse.model_validate(scan.ai_analysis)
    return response


@router.get("/{scan_id}/report/pdf")
def download_pdf_report(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == current_user.id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    report_data = build_report_data(scan)
    pdf_bytes = generate_pdf_report(report_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sentinelai-report-{scan_id}.pdf"'},
    )


@router.get("/{scan_id}/report/json")
def download_json_report(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == current_user.id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    report_data = build_report_data(scan)
    json_str = generate_json_report(report_data)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="sentinelai-report-{scan_id}.json"'},
    )


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == current_user.id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    db.delete(scan)
    db.commit()
