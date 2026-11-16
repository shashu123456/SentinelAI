"""Account-scoped trust endpoints.

* ``GET  /api/account/authorized-use``  — has the caller accepted the terms?
* ``POST /api/account/authorized-use``  — record acceptance (idempotent).
* ``POST /api/account/delete-data``     — delete the caller's scans, findings,
  reports and stored specs, keeping the account itself.

Nothing in this module deletes a user or any other user's data.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import AuthorizedUse, Scan, User
from app.services.audit_service import record_action
from app.utils.logger import logger
from app.utils.security import get_client_ip, get_current_user

router = APIRouter(prefix="/api/account", tags=["Account"])

AUTHORIZED_USE_VERSION = "1"
AUTHORIZED_USE_TEXT = (
    "Only scan material you own or have written permission to test."
)


class AuthorizedUseState(BaseModel):
    accepted: bool
    accepted_at: datetime | None = None
    version: str = AUTHORIZED_USE_VERSION
    text: str = AUTHORIZED_USE_TEXT


class DeleteDataResult(BaseModel):
    deleted_scans: int
    message: str


@router.get("/authorized-use", response_model=AuthorizedUseState)
def get_authorized_use(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthorizedUseState:
    row = db.query(AuthorizedUse).filter(AuthorizedUse.user_id == current_user.id).one_or_none()
    if row is None:
        return AuthorizedUseState(accepted=False)
    return AuthorizedUseState(accepted=True, accepted_at=row.accepted_at, version=row.version)


@router.post("/authorized-use", response_model=AuthorizedUseState)
def accept_authorized_use(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthorizedUseState:
    row = db.query(AuthorizedUse).filter(AuthorizedUse.user_id == current_user.id).one_or_none()
    now = datetime.now(UTC)
    if row is None:
        row = AuthorizedUse(
            user_id=current_user.id,
            accepted_at=now,
            ip_address=get_client_ip(request),
            version=AUTHORIZED_USE_VERSION,
        )
        db.add(row)
    else:
        row.accepted_at = now
        row.ip_address = get_client_ip(request)
        row.version = AUTHORIZED_USE_VERSION
    record_action(
        db,
        "account.authorized_use_accepted",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        resource="authorized-use",
        detail={"version": AUTHORIZED_USE_VERSION},
    )
    db.commit()
    db.refresh(row)
    return AuthorizedUseState(accepted=True, accepted_at=row.accepted_at, version=row.version)


@router.post("/delete-data", response_model=DeleteDataResult)
def delete_my_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteDataResult:
    """Delete every scan (and its findings/reports via cascade) for the caller."""
    scan_ids = [
        row[0]
        for row in db.query(Scan.id).filter(Scan.user_id == current_user.id).all()
    ]
    if scan_ids:
        # Findings, reports and AI analysis cascade from the scan rows.
        db.execute(delete(Scan).where(Scan.user_id == current_user.id))
    record_action(
        db,
        "account.data_deleted",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        resource="account-data",
        detail={"deleted_scans": len(scan_ids)},
    )
    db.commit()
    logger.info("Deleted %d scan(s) for user %s", len(scan_ids), current_user.username)
    return DeleteDataResult(
        deleted_scans=len(scan_ids),
        message="All scans and reports for your account were deleted.",
    )
