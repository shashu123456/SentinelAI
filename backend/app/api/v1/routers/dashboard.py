"""Versioned dashboard overview endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import api_response
from app.database.database import get_db
from app.models.models import User
from app.repositories.scans import ScanRepository
from app.schemas.schemas import DashboardOverviewResponse, ScanResponse
from app.utils.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["v1: Dashboard"])


@router.get("/overview")
def dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan_repo = ScanRepository(db)
    overview = DashboardOverviewResponse(
        total_scans=scan_repo.count_for_user(current_user.id),
        completed_scans=scan_repo.count_completed_for_user(current_user.id),
        total_vulnerabilities=scan_repo.total_vulnerabilities_for_user(current_user.id),
        average_risk_score=round(scan_repo.average_risk_for_user(current_user.id), 1),
        severity_distribution=scan_repo.severity_distribution_for_user(current_user.id),
        recent_scans=[
            ScanResponse.model_validate(s)
            for s in scan_repo.recent_for_user(current_user.id, limit=5)
        ],
    )
    return api_response(overview)
