"""Versioned findings endpoint: paginated, filtered findings for a scan."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import api_response, page_meta
from app.database.database import get_db
from app.models.models import User
from app.repositories.findings import FindingRepository
from app.repositories.scans import ScanRepository
from app.schemas.schemas import FindingListParams, FindingResponse
from app.utils.security import get_current_user

router = APIRouter(prefix="/scans", tags=["v1: Findings"])


@router.get("/{scan_id}/findings")
def list_findings(
    scan_id: int,
    params: FindingListParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan_repo = ScanRepository(db)
    scan_repo.get_owned_or_404(scan_id, current_user.id)

    items, total = FindingRepository(db).paginate_for_scan(scan_id, params)
    return api_response(
        [FindingResponse.model_validate(f) for f in items],
        page_meta(params.page, params.page_size, total),
    )
