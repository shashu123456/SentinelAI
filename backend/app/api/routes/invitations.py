"""Enterprise Invitation management routes.

Features:
- Send invitations to join an organization
- Accept invitations
- Revoke pending invitations
- List pending invitations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import User
from app.schemas.schemas import MessageResponse
from app.services.invitation_service import (
    accept_invitation,
    cleanup_expired_invitations,
    create_invitation,
    revoke_invitation,
)
from app.utils.rbac import OrgContext, require_org_role
from app.utils.security import get_current_user

router = APIRouter(
    prefix="/api/organizations/{org_id}/invitations", tags=["Enterprise Invitations"]
)


# ── Schemas ───────────────────────────────────────────────────────────


class InvitationCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    role: str = Field("developer", pattern=r"^(admin|security_engineer|developer|viewer)$")


class InvitationAccept(BaseModel):
    token: str = Field(..., min_length=1)


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
def send_invitation(
    org_id: int,
    data: InvitationCreate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        invitation = create_invitation(
            db,
            org_id=org_id,
            email=data.email,
            role=data.role,
            invited_by=org_ctx.user_id,
        )
        return invitation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_invitations(
    org_id: int,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    from app.repositories.invitations import InvitationRepository

    invite_repo = InvitationRepository(db)
    invitations = invite_repo.list_all_for_org(org_id)
    return [
        {
            "id": inv.id,
            "email": inv.email,
            "role": inv.role,
            "status": inv.status,
            "invited_by": inv.invited_by,
            "expires_at": str(inv.expires_at),
            "created_at": str(inv.created_at),
        }
        for inv in invitations
    ]


@router.delete("/{invitation_id}")
def revoke_invitation_endpoint(
    org_id: int,
    invitation_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        revoke_invitation(
            db, invitation_id=invitation_id, org_id=org_id, revoked_by=org_ctx.user_id
        )
        return MessageResponse(detail="Invitation revoked")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Public endpoint (no auth required - for accepting invitations) ────


@router.post("/accept")
def accept_invitation_endpoint(
    org_id: int,
    data: InvitationAccept,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = accept_invitation(db, token=data.token, user_id=current_user.id)
        return {
            "message": "Invitation accepted",
            "organization_id": result["organization_id"],
            "role": result["role"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Admin: cleanup expired invitations ────────────────────────────────


@router.post("/cleanup")
def cleanup_expired(
    org_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    count = cleanup_expired_invitations(db)
    return {"expired_count": count}
