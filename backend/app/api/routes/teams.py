"""Enterprise Team management routes.

Features:
- Team CRUD with org RBAC
- Team member management
- Team listing
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.repositories.teams import TeamRepository
from app.schemas.schemas import MessageResponse
from app.services.team_service import add_team_member, create_team, delete_team, remove_team_member
from app.utils.rbac import OrgContext, require_org_role

router = APIRouter(prefix="/api/organizations/{org_id}/teams", tags=["Enterprise Teams"])


# ── Schemas ───────────────────────────────────────────────────────────


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None


class TeamMemberAdd(BaseModel):
    user_id: int
    role: str = Field("member", pattern=r"^(admin|member)$")


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
def create_team_endpoint(
    org_id: int,
    data: TeamCreate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        team = create_team(
            db,
            org_id=org_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            creator_id=org_ctx.user_id,
        )
        return team
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_teams(
    org_id: int,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    team_repo = TeamRepository(db)
    teams = team_repo.list_for_org(org_id)
    result = []
    for team in teams:
        member_count = team_repo.count_members(team.id)
        result.append(
            {
                "id": team.id,
                "name": team.name,
                "slug": team.slug,
                "description": team.description,
                "organization_id": team.organization_id,
                "member_count": member_count,
                "created_at": str(team.created_at),
            }
        )
    return result


@router.get("/{team_id}")
def get_team(
    org_id: int,
    team_id: int,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    team_repo = TeamRepository(db)
    team = team_repo.get(team_id)
    if team is None or team.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Team not found")

    members = team_repo.list_members(team_id)
    return {
        "id": team.id,
        "name": team.name,
        "slug": team.slug,
        "description": team.description,
        "organization_id": team.organization_id,
        "created_at": str(team.created_at),
        "members": members,
    }


@router.post("/{team_id}/members")
def add_team_member_endpoint(
    org_id: int,
    team_id: int,
    data: TeamMemberAdd,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    team_repo = TeamRepository(db)
    team = team_repo.get(team_id)
    if team is None or team.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        add_team_member(
            db,
            team_id=team_id,
            user_id=data.user_id,
            role=data.role,
            added_by=org_ctx.user_id,
            org_id=org_id,
        )
        return MessageResponse(detail="Team member added")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}/members/{user_id}")
def remove_team_member_endpoint(
    org_id: int,
    team_id: int,
    user_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    team_repo = TeamRepository(db)
    team = team_repo.get(team_id)
    if team is None or team.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        remove_team_member(
            db,
            team_id=team_id,
            user_id=user_id,
            removed_by=org_ctx.user_id,
            org_id=org_id,
        )
        return MessageResponse(detail="Team member removed")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}")
def delete_team_endpoint(
    org_id: int,
    team_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    team_repo = TeamRepository(db)
    team = team_repo.get(team_id)
    if team is None or team.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        delete_team(db, team_id=team_id, org_id=org_id, deleted_by=org_ctx.user_id)
        return MessageResponse(detail="Team deleted")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
