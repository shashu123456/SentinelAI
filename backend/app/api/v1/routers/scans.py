"""Versioned scan read endpoints: filtered paginated list + detail."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import api_response, page_meta
from app.database.database import get_db
from app.models.models import User
from app.repositories.scans import ScanRepository
from app.schemas.schemas import (
    AIAnalysisResponse,
    FindingResponse,
    ScanDetailResponse,
    ScanListParams,
    ScanResponse,
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/scans", tags=["v1: Scans"])


@router.get("")
def list_scans(
    params: ScanListParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = ScanRepository(db).list_for_user_filtered(current_user.id, params)
    return api_response(
        [ScanResponse.model_validate(s) for s in items],
        page_meta(params.page, params.page_size, total),
    )


@router.get("/{scan_id}")
def get_scan_detail(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = ScanRepository(db).get_owned_or_404(scan_id, current_user.id)

    response = ScanDetailResponse.model_validate(scan)
    response.findings = [FindingResponse.model_validate(f) for f in scan.findings]
    if scan.ai_analysis:
        response.ai_analysis = AIAnalysisResponse.model_validate(scan.ai_analysis)
    return api_response(response)
