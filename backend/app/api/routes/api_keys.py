"""Enterprise API Key management routes.

Features:
- Create API keys with scopes
- Revoke API keys
- List API keys
- Validate API keys (internal)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.schemas import MessageResponse
from app.services.api_key_service import create_api_key, list_api_keys, revoke_api_key
from app.utils.rbac import OrgContext, require_org_role

router = APIRouter(prefix="/api/organizations/{org_id}/api-keys", tags=["Enterprise API Keys"])


# ── Schemas ───────────────────────────────────────────────────────────


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] | None = None
    expires_days: int | None = Field(None, ge=1, le=365)


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
def create_api_key_endpoint(
    org_id: int,
    data: ApiKeyCreate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        result = create_api_key(
            db,
            organization_id=org_id,
            user_id=org_ctx.user_id,
            name=data.name,
            scopes=data.scopes,
            expires_days=data.expires_days,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_api_keys_endpoint(
    org_id: int,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    return list_api_keys(db, org_id)


@router.delete("/{api_key_id}")
def revoke_api_key_endpoint(
    org_id: int,
    api_key_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        revoke_api_key(
            db,
            api_key_id=api_key_id,
            organization_id=org_id,
            user_id=org_ctx.user_id,
        )
        return MessageResponse(detail="API key revoked")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
