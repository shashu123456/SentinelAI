"""Enterprise Organization management routes.

Features:
- Organization CRUD with RBAC
- Member management with roles
- Project management with RBAC
- Organization settings
- Organization analytics
- Organization dashboard
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import User
from app.repositories.organizations import OrganizationRepository, ProjectRepository
from app.schemas.schemas import MessageResponse
from app.services.audit_service import record_action, record_org_event
from app.services.org_analytics_service import (
    get_organization_analytics,
    get_organization_dashboard,
)
from app.utils.rbac import OrgContext, require_org_role
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/organizations", tags=["Enterprise Organizations"])


# ── Schemas ───────────────────────────────────────────────────────────


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class OrganizationSettingsUpdate(BaseModel):
    default_project_visibility: str | None = Field(None, pattern=r"^(public|private)$")
    enforce_sso: bool | None = None
    allowed_email_domains: list[str] | None = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    owner_id: int
    subscription_tier: str = "free"
    max_members: int = 10
    max_projects: int = 5
    max_scans_per_month: int = 50
    scans_used_this_month: int = 0
    default_project_visibility: str = "private"
    enforce_sso: bool = False
    allowed_email_domains: list | None = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None


class ProjectMemberAdd(BaseModel):
    user_id: int
    role: str = Field("developer", pattern=r"^(admin|security_engineer|developer|viewer)$")


class MemberInvite(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    role: str = Field("developer", pattern=r"^(admin|security_engineer|developer|viewer)$")


class MemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern=r"^(admin|security_engineer|developer|viewer)$")


# ── Organization Endpoints ────────────────────────────────────────────


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_repo = OrganizationRepository(db)

    if org_repo.get_by_slug(data.slug):
        raise HTTPException(status_code=409, detail="Organization slug already taken")

    org = org_repo.create(
        name=data.name,
        slug=data.slug,
        description=data.description,
        owner_id=current_user.id,
    )
    # Owner gets the "owner" role
    org_repo.add_member(org.id, current_user.id, role="owner")
    db.commit()
    db.refresh(org)

    record_action(
        db,
        "org.created",
        user_id=current_user.id,
        entity_type="organization",
        entity_id=org.id,
        resource=f"org {org.name}",
    )
    db.commit()

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        owner_id=org.owner_id,
        subscription_tier=org.subscription_tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        max_scans_per_month=org.max_scans_per_month,
        scans_used_this_month=org.scans_used_this_month,
        default_project_visibility=org.default_project_visibility,
        enforce_sso=org.enforce_sso,
        allowed_email_domains=org.allowed_email_domains,
        created_at=str(org.created_at),
        updated_at=str(org.updated_at),
    )


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_repo = OrganizationRepository(db)
    orgs = org_repo.list_for_user(current_user.id)
    return [
        OrganizationResponse(
            id=o.id,
            name=o.name,
            slug=o.slug,
            description=o.description,
            owner_id=o.owner_id,
            subscription_tier=o.subscription_tier,
            max_members=o.max_members,
            max_projects=o.max_projects,
            max_scans_per_month=o.max_scans_per_month,
            scans_used_this_month=o.scans_used_this_month,
            default_project_visibility=o.default_project_visibility,
            enforce_sso=o.enforce_sso,
            allowed_email_domains=o.allowed_email_domains,
            created_at=str(o.created_at),
            updated_at=str(o.updated_at),
        )
        for o in orgs
    ]


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
):
    o = org_ctx.organization
    return OrganizationResponse(
        id=o.id,
        name=o.name,
        slug=o.slug,
        description=o.description,
        owner_id=o.owner_id,
        subscription_tier=o.subscription_tier,
        max_members=o.max_members,
        max_projects=o.max_projects,
        max_scans_per_month=o.max_scans_per_month,
        scans_used_this_month=o.scans_used_this_month,
        default_project_visibility=o.default_project_visibility,
        enforce_sso=o.enforce_sso,
        allowed_email_domains=o.allowed_email_domains,
        created_at=str(o.created_at),
        updated_at=str(o.updated_at),
    )


@router.patch("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    org = org_ctx.organization

    if data.name is not None:
        org.name = data.name
    if data.description is not None:
        org.description = data.description
    org.updated_at = datetime.now(UTC)

    record_org_event(
        db,
        "org.updated",
        user_id=org_ctx.user_id,
        org_id=org_id,
        org_name=org.name,
    )
    db.commit()
    db.refresh(org)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        owner_id=org.owner_id,
        subscription_tier=org.subscription_tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        max_scans_per_month=org.max_scans_per_month,
        scans_used_this_month=org.scans_used_this_month,
        default_project_visibility=org.default_project_visibility,
        enforce_sso=org.enforce_sso,
        allowed_email_domains=org.allowed_email_domains,
        created_at=str(org.created_at),
        updated_at=str(org.updated_at),
    )


# ── Settings ──────────────────────────────────────────────────────────


@router.get("/{org_id}/settings")
def get_org_settings(
    org_ctx: OrgContext = Depends(require_org_role("admin")),
):
    o = org_ctx.organization
    return {
        "default_project_visibility": o.default_project_visibility,
        "enforce_sso": o.enforce_sso,
        "allowed_email_domains": o.allowed_email_domains,
        "subscription_tier": o.subscription_tier,
        "max_members": o.max_members,
        "max_projects": o.max_projects,
        "max_scans_per_month": o.max_scans_per_month,
        "scans_used_this_month": o.scans_used_this_month,
    }


@router.patch("/{org_id}/settings")
def update_org_settings(
    org_id: int,
    data: OrganizationSettingsUpdate,
    org_ctx: OrgContext = Depends(require_org_role("owner")),
    db: Session = Depends(get_db),
):
    org = org_ctx.organization

    if data.default_project_visibility is not None:
        org.default_project_visibility = data.default_project_visibility
    if data.enforce_sso is not None:
        org.enforce_sso = data.enforce_sso
    if data.allowed_email_domains is not None:
        org.allowed_email_domains = data.allowed_email_domains

    org.updated_at = datetime.now(UTC)

    record_org_event(
        db,
        "org.settings_changed",
        user_id=org_ctx.user_id,
        org_id=org_id,
        org_name=org.name,
    )
    db.commit()

    return MessageResponse(detail="Settings updated")


# ── Dashboard & Analytics ─────────────────────────────────────────────


@router.get("/{org_id}/dashboard")
def get_org_dashboard(
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    return get_organization_dashboard(db, org_ctx.organization.id)


@router.get("/{org_id}/analytics")
def get_org_analytics(
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    return get_organization_analytics(db, org_ctx.organization.id)


# ── Members ───────────────────────────────────────────────────────────


@router.get("/{org_id}/members")
def list_members(
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    org_repo = OrganizationRepository(db)
    return org_repo.list_members(org_ctx.organization.id)


@router.post("/{org_id}/members")
def add_member(
    org_id: int,
    data: MemberInvite,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    from app.models.models import User as UserModel

    org_repo = OrganizationRepository(db)

    # Check capacity
    if not org_repo.can_add_member(org_id):
        org = org_repo.get(org_id)
        raise HTTPException(
            status_code=400,
            detail=f"Organization has reached the maximum of {org.max_members} members",
        )

    # Find the user by email
    target_user = db.query(UserModel).filter(UserModel.email == data.email).first()
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found. They must register first.")

    if org_repo.is_member(org_id, target_user.id):
        raise HTTPException(status_code=409, detail="User is already a member")

    org_repo.add_member(org_id, target_user.id, data.role)
    record_org_event(
        db,
        "org.member_added",
        user_id=org_ctx.user_id,
        org_id=org_id,
        org_name=org_ctx.organization.name,
        detail={"email": data.email, "role": data.role},
    )
    db.commit()

    return MessageResponse(detail="Member added")


@router.patch("/{org_id}/members/{user_id}/role")
def update_member_role(
    org_id: int,
    user_id: int,
    data: MemberRoleUpdate,
    org_ctx: OrgContext = Depends(require_org_role("owner")),
    db: Session = Depends(get_db),
):
    org_repo = OrganizationRepository(db)
    org = org_repo.get_or_404(org_id)

    if user_id == org.owner_id:
        raise HTTPException(status_code=400, detail="Cannot change the owner's role")

    success = org_repo.update_member_role(org_id, user_id, data.role)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")

    record_org_event(
        db,
        "org.member_role_changed",
        user_id=org_ctx.user_id,
        org_id=org_id,
        org_name=org.name,
        detail={"target_user_id": user_id, "new_role": data.role},
    )
    db.commit()

    return MessageResponse(detail="Role updated")


@router.delete("/{org_id}/members/{user_id}", response_model=MessageResponse)
def remove_member(
    org_id: int,
    user_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    org_repo = OrganizationRepository(db)
    org = org_repo.get_or_404(org_id)

    if user_id == org.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove the organization owner")

    org_repo.remove_member(org_id, user_id)
    record_org_event(
        db,
        "org.member_removed",
        user_id=org_ctx.user_id,
        org_id=org_id,
        org_name=org.name,
        detail={"removed_user_id": user_id},
    )
    db.commit()

    return MessageResponse(detail="Member removed")


# ── Project Endpoints ─────────────────────────────────────────────────


@router.post("/{org_id}/projects", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_project(
    org_id: int,
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    org_ctx: OrgContext = Depends(require_org_role("developer")),
    db: Session = Depends(get_db),
):
    org_repo = OrganizationRepository(db)

    if not org_repo.can_create_project(org_id):
        org = org_repo.get(org_id)
        raise HTTPException(
            status_code=400,
            detail=f"Organization has reached the maximum of {org.max_projects} projects",
        )

    project_repo = ProjectRepository(db)
    if project_repo.get_by_slug(org_id, data.slug):
        raise HTTPException(
            status_code=409, detail="Project slug already taken in this organization"
        )

    project = project_repo.create(
        organization_id=org_id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        owner_id=current_user.id,
    )

    db.commit()
    db.refresh(project)

    record_action(
        db,
        "project.created",
        user_id=project.owner_id,
        entity_type="project",
        entity_id=project.id,
        resource=f"project {project.name}",
    )
    db.commit()

    return {
        "id": project.id,
        "organization_id": project.organization_id,
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "owner_id": project.owner_id,
        "is_active": project.is_active,
        "created_at": str(project.created_at),
    }


@router.get("/{org_id}/projects")
def list_projects(
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    project_repo = ProjectRepository(db)
    projects = project_repo.list_for_org(org_ctx.organization.id)
    return [
        {
            "id": p.id,
            "organization_id": p.organization_id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "owner_id": p.owner_id,
            "is_active": p.is_active,
            "created_at": str(p.created_at),
        }
        for p in projects
    ]


@router.get("/{org_id}/projects/{project_id}")
def get_project(
    org_id: int,
    project_id: int,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    project_repo = ProjectRepository(db)
    project = project_repo.get(project_id)
    if project is None or project.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Project not found")

    project_repo_members = ProjectRepository(db)
    members = project_repo_members.list_members(project_id)

    return {
        "id": project.id,
        "organization_id": project.organization_id,
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "owner_id": project.owner_id,
        "is_active": project.is_active,
        "created_at": str(project.created_at),
        "members": members,
    }


@router.post("/{org_id}/projects/{project_id}/members")
def add_project_member(
    org_id: int,
    project_id: int,
    data: ProjectMemberAdd,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    project_repo = ProjectRepository(db)
    project = project_repo.get(project_id)
    if project is None or project.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models.models import User as UserModel

    target_user = db.get(UserModel, data.user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    project_repo.add_member(project_id, data.user_id, data.role, added_by=org_ctx.user_id)
    db.commit()

    return MessageResponse(detail="Project member added")


@router.delete("/{org_id}/projects/{project_id}/members/{user_id}")
def remove_project_member(
    org_id: int,
    project_id: int,
    user_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    project_repo = ProjectRepository(db)
    project = project_repo.get(project_id)
    if project is None or project.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Project not found")

    project_repo.remove_member(project_id, user_id)
    db.commit()

    return MessageResponse(detail="Project member removed")
