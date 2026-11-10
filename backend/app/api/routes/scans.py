import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import yaml
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.database import SessionLocal, get_db
from app.models.models import Finding, Scan, User
from app.reports.generator import generate_json_report, generate_pdf_report
from app.repositories.reports import ReportRepository
from app.repositories.scans import ScanRepository
from app.schemas.schemas import (
    AIAnalysisResponse,
    AnalyticsResponse,
    DashboardStats,
    FindingResponse,
    RiskTrendItem,
    ScanActivityItem,
    ScanDetailResponse,
    ScanResponse,
    OwaspCategoryItem,
)
from app.services.audit_service import record_report_export, record_scan_event
from app.services.scan_service import build_report_data, execute_scan
from app.tasks import create_scan_task, get_task
from app.utils.cache import cache
from app.utils.logger import logger
from app.utils.security import get_current_user

settings = get_settings()
router = APIRouter(prefix="/api/scans", tags=["Scans"])

MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
VALID_SPEC_EXTENSIONS = (".json", ".yaml", ".yml")


def _read_and_validate_spec(file: UploadFile, api_name: str) -> tuple[str, dict]:
    """Validate an uploaded OpenAPI/Swagger spec and return (api_name, spec)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(VALID_SPEC_EXTENSIONS):
        raise HTTPException(
            status_code=400, detail=f"Invalid file type. Allowed: {VALID_SPEC_EXTENSIONS}"
        )

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, detail=f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded") from None

    try:
        if file.filename.lower().endswith((".yaml", ".yml")):
            spec = yaml.safe_load(content_str)
        else:
            spec = json.loads(content_str)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid specification format: {e}") from None

    if not isinstance(spec, dict):
        raise HTTPException(status_code=400, detail="Specification must be a JSON/YAML object")

    if "openapi" not in spec and "swagger" not in spec:
        raise HTTPException(
            status_code=400,
            detail="Not a valid openapi/swagger specification: missing 'openapi' or 'swagger' version key",
        )

    if not api_name:
        api_name = spec.get("info", {}).get("title", file.filename)

    return api_name, spec


def _get_owned_scan(db: Session, scan_id: int, user_id: int):
    scan = ScanRepository(db).get_owned(scan_id, user_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.post("/upload", response_model=ScanResponse)
async def upload_and_scan(
    file: UploadFile = File(...),
    api_name: str = Form(""),
    organization_id: int | None = Form(None),
    project_id: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_name, spec = _read_and_validate_spec(file, api_name)

    # Validate org/project membership if provided
    if organization_id is not None:
        from app.repositories.organizations import OrganizationRepository

        org_repo = OrganizationRepository(db)
        if not org_repo.is_member(organization_id, current_user.id):
            raise HTTPException(status_code=403, detail="Not a member of this organization")

    if project_id is not None:
        from app.models.models import Project

        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if organization_id is None:
            organization_id = project.organization_id

    try:
        scan = execute_scan(db, current_user.id, api_name, spec)
        # Associate with organization/project if provided
        if organization_id is not None:
            scan.organization_id = organization_id
        if project_id is not None:
            scan.project_id = project_id
        db.commit()
    except Exception as e:
        logger.error(f"Scan execution failed: {e}")
        raise HTTPException(status_code=500, detail="Scan execution failed") from None

    # Invalidate dashboard/analytics cache
    cache.invalidate_prefix(f"dashboard:{current_user.id}")
    cache.invalidate_prefix(f"analytics:{current_user.id}")
    if organization_id:
        cache.invalidate_prefix(f"org_dashboard:{organization_id}")
        cache.invalidate_prefix(f"org_analytics:{organization_id}")

    return scan


@router.post("/upload/async")
async def upload_and_scan_async(
    file: UploadFile = File(...),
    api_name: str = Form(""),
    enable_ai: bool = Form(True),
    organization_id: int | None = Form(None),
    project_id: int | None = Form(None),
    current_user: User = Depends(get_current_user),
):
    api_name, spec = _read_and_validate_spec(file, api_name)

    task_id = create_scan_task(
        spec=spec,
        user_id=current_user.id,
        api_name=api_name,
        db_session_factory=SessionLocal,
        enable_ai=enable_ai,
    )

    return {
        "task_id": task_id,
        "message": "Scan started",
        "organization_id": organization_id,
        "project_id": project_id,
    }


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
    return ScanRepository(db).list_by_user(current_user.id, limit=50)


@router.get("/org/{organization_id}", response_model=list[ScanResponse])
def list_scans_by_org(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List scans for a specific organization. Requires org membership."""
    from app.repositories.organizations import OrganizationRepository

    org_repo = OrganizationRepository(db)
    if not org_repo.is_member(organization_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    scan_repo = ScanRepository(db)
    from app.models.models import Scan

    scans = scan_repo.list(
        Scan.organization_id == organization_id,
        Scan.deleted_at.is_(None),
        order_by=Scan.created_at.desc(),
        limit=50,
    )
    return scans


@router.get("/project/{project_id}", response_model=list[ScanResponse])
def list_scans_by_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List scans for a specific project. Requires project/organization membership."""
    from app.models.models import Project

    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.repositories.organizations import OrganizationRepository

    org_repo = OrganizationRepository(db)
    if not org_repo.is_member(project.organization_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this project's organization")

    scan_repo = ScanRepository(db)
    from app.models.models import Scan

    scans = scan_repo.list(
        Scan.project_id == project_id,
        Scan.deleted_at.is_(None),
        order_by=Scan.created_at.desc(),
        limit=50,
    )
    return scans


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check cache first
    cache_key = f"dashboard:{current_user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return DashboardStats(**cached)

    scan_repo = ScanRepository(db)

    total_scans = scan_repo.count_for_user(current_user.id)
    total_vulns = scan_repo.total_vulnerabilities_for_user(current_user.id)
    avg_score = scan_repo.average_risk_for_user(current_user.id)
    recent = scan_repo.recent_for_user(current_user.id, limit=10)
    severity_dist = scan_repo.severity_distribution_for_user(current_user.id)

    stats = DashboardStats(
        total_scans=total_scans,
        total_vulnerabilities=total_vulns,
        average_risk_score=round(avg_score, 1),
        recent_scans=[ScanResponse.model_validate(s) for s in recent],
        severity_distribution=severity_dist,
    )

    # Cache for configured TTL
    cache.set(cache_key, stats.model_dump(), ttl=settings.DASHBOARD_CACHE_TTL)
    return stats


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return time-series analytics data for dashboard charts."""
    # Check cache first
    cache_key = f"analytics:{current_user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return AnalyticsResponse(**cached)

    user_id = current_user.id
    now = datetime.now(UTC)

    # Scan activity over last 30 days — single aggregate query instead of 30 individual queries
    thirty_days_ago = now - timedelta(days=29)
    day_start = datetime.combine(thirty_days_ago.date(), datetime.min.time()).replace(tzinfo=UTC)

    activity_rows = db.execute(
        select(
            func.date(Scan.created_at).label("day"),
            func.count(Scan.id).label("count"),
        )
        .where(
            Scan.user_id == user_id,
            Scan.created_at >= day_start,
            Scan.deleted_at.is_(None),
        )
        .group_by(func.date(Scan.created_at))
        .order_by(func.date(Scan.created_at).asc())
    ).all()
    activity_map = {str(row.day): row.count for row in activity_rows}

    scan_activity = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).date()
        scans_count = activity_map.get(day.isoformat(), 0)
        scan_activity.append(
            ScanActivityItem(date=day.isoformat(), scans=scans_count if isinstance(scans_count, int) else 0)
        )

    # Risk score trend over time
    risk_trend = []
    rows = db.execute(
        select(Scan.created_at, Scan.risk_score)
        .where(
            Scan.user_id == user_id,
            Scan.status == "completed",
            Scan.deleted_at.is_(None),
        )
        .order_by(Scan.created_at.asc())
    ).all()
    for created_at, risk_score in rows:
        risk_trend.append(
            RiskTrendItem(date=(
                created_at.date().isoformat()
                if hasattr(created_at, "date")
                else str(created_at)
            ), score=risk_score)
        )

    # Findings by OWASP category
    owasp_stmt = (
        select(Finding.owasp_category, func.count(Finding.id))
        .join(Scan, Finding.scan_id == Scan.id)
        .where(Scan.user_id == user_id, Scan.deleted_at.is_(None))
        .group_by(Finding.owasp_category)
        .order_by(func.count(Finding.id).desc())
    )
    owasp_dist = [OwaspCategoryItem(category=cat, count=cnt) for cat, cnt in db.execute(owasp_stmt).all()]

    response = AnalyticsResponse(
        scan_activity=scan_activity,
        risk_trend=risk_trend,
        owasp_distribution=owasp_dist,
    )

    # Cache for configured TTL
    cache.set(cache_key, response.model_dump(), ttl=settings.ANALYTICS_CACHE_TTL)
    return response


@router.get("/{scan_id}", response_model=ScanDetailResponse)
def get_scan_detail(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = _get_owned_scan(db, scan_id, current_user.id)

    response = ScanDetailResponse.model_validate(scan)
    response.findings = [FindingResponse.model_validate(f) for f in scan.findings]
    if scan.ai_analysis:
        response.ai_analysis = AIAnalysisResponse.model_validate(scan.ai_analysis)
    response.transition_history = scan.transition_history or []
    return response


def _get_or_create_report(
    db: Session,
    scan,
    format: str,
    current_user: User,
    generate: Callable[[dict], bytes],
) -> tuple[bytes, bool]:
    """Return (report_bytes, generated_now). Reads a stored report when present."""
    report_repo = ReportRepository(db)
    existing = report_repo.get_for_scan(scan.id, format)
    if existing is not None:
        return existing.content, False

    report_data = build_report_data(scan)
    content = generate(report_data)
    report_repo.create(scan, format, content)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = report_repo.get_for_scan(scan.id, format)
        if existing is not None:
            return existing.content, False
        raise

    record_report_export(db, user_id=current_user.id, scan_id=scan.id, format=format)
    db.commit()

    return content, True


@router.get("/{scan_id}/report/pdf")
def download_pdf_report(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = _get_owned_scan(db, scan_id, current_user.id)
    content, _ = _get_or_create_report(db, scan, "pdf", current_user, generate_pdf_report)

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sentinelai-report-{scan_id}.pdf"'},
    )


@router.get("/{scan_id}/report/json")
def download_json_report(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = _get_owned_scan(db, scan_id, current_user.id)

    def _generate(data: dict) -> bytes:
        return generate_json_report(data).encode("utf-8")

    content, _ = _get_or_create_report(db, scan, "json", current_user, _generate)

    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="sentinelai-report-{scan_id}.json"'},
    )


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = _get_owned_scan(db, scan_id, current_user.id)

    scan_repo = ScanRepository(db)
    scan_repo.soft_delete(scan)
    scan_repo.commit()

    record_scan_event(db, "scan.deleted", user_id=current_user.id, scan_id=scan.id)
    scan_repo.commit()

    # Invalidate cache after deletion
    cache.invalidate_prefix(f"dashboard:{current_user.id}")
    cache.invalidate_prefix(f"analytics:{current_user.id}")
