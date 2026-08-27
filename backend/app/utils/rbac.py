"""Enterprise Role-Based Access Control (RBAC) for SentinelAI.

Permission hierarchy:
  Global: super_admin > (no other global roles needed)
  Org:    owner > admin > security_engineer > developer > viewer
  Project: admin > security_engineer > developer > viewer
  Team:   admin > member

A super_admin can do anything anywhere.
An org owner has full control of their organization.
An org admin can manage members and settings but not billing/owner transfers.
A security_engineer can manage scans, findings, and security settings.
A developer can run scans and view results.
A viewer has read-only access.

Team roles are independent — they control team-level membership, not org/project access.
"""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import (
    Organization,
    OrganizationMember,
    Project,
    ProjectMember,
    TeamMember,
    User,
)
from app.utils.security import get_current_user

# ── Role levels (higher number = more permissions) ────────────────────
ORG_ROLE_LEVELS = {
    "viewer": 10,
    "developer": 20,
    "security_engineer": 30,
    "admin": 40,
    "owner": 50,
}

PROJECT_ROLE_LEVELS = {
    "viewer": 10,
    "developer": 20,
    "security_engineer": 30,
    "admin": 40,
}

TEAM_ROLE_LEVELS = {
    "member": 10,
    "admin": 20,
}


@dataclass
class OrgContext:
    """Resolved organization context for the current request."""

    organization: Organization
    org_role: str
    org_level: int
    user_id: int


@dataclass
class ProjectContext:
    """Resolved project context for the current request."""

    project: Project
    project_role: str
    project_level: int
    org_ctx: OrgContext


# ── Internal helpers ──────────────────────────────────────────────────


def _get_user_role_in_org(db: Session, org_id: int, user_id: int) -> str | None:
    """Return the user's role in the given organization, or None."""
    # Check if super_admin
    user = db.get(User, user_id)
    if user and user.role == "super_admin":
        return "owner"  # Super admins have owner-level access everywhere

    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
        .first()
    )
    return member.role if member else None


def _get_user_role_in_project(db: Session, project_id: int, user_id: int) -> str | None:
    """Return the user's role in the given project, or None.

    If the user has org-level admin or owner, they get admin project access.
    """
    # First check explicit project membership
    member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        .first()
    )
    if member:
        return member.role

    # Fall back to org-level: org owners and admins have admin project access
    project = db.get(Project, project_id)
    if project:
        org_role = _get_user_role_in_org(db, project.organization_id, user_id)
        if org_role in ("owner", "admin"):
            return "admin"
        if org_role == "security_engineer":
            return "security_engineer"
        if org_role == "developer":
            return "developer"
        if org_role == "viewer":
            return "viewer"

    return None


def _get_user_role_in_team(db: Session, team_id: int, user_id: int) -> str | None:
    member = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
        .first()
    )
    return member.role if member else None


# ── Dependency factories ──────────────────────────────────────────────


def require_org_role(min_role: str) -> Callable:
    """Dependency factory that checks the user has at least `min_role` in the organization.

    Usage:
        @router.get("/orgs/{org_id}/settings")
        def get_settings(
            org_ctx: OrgContext = Depends(require_org_role("admin")),
        ):
            ...
    """
    min_level = ORG_ROLE_LEVELS.get(min_role, 0)

    async def _dependency(
        org_id: int,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> OrgContext:
        role = _get_user_role_in_org(db, org_id, current_user.id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )
        level = ORG_ROLE_LEVELS.get(role, 0)
        if level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {min_role} role or higher",
            )
        org = db.get(Organization, org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        return OrgContext(organization=org, org_role=role, org_level=level, user_id=current_user.id)

    return _dependency


def require_project_role(min_role: str) -> Callable:
    """Dependency factory that checks the user has at least `min_role` in the project.

    Automatically checks org-level fallback.
    """
    min_level = PROJECT_ROLE_LEVELS.get(min_role, 0)

    async def _dependency(
        project_id: int,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> ProjectContext:
        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get org context
        org_role = _get_user_role_in_org(db, project.organization_id, current_user.id)
        if org_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this project's organization",
            )
        org_level = ORG_ROLE_LEVELS.get(org_role, 0)
        org = db.get(Organization, project.organization_id)
        org_ctx = OrgContext(
            organization=org, org_role=org_role, org_level=org_level, user_id=current_user.id
        )

        # Get project-level role
        proj_role = _get_user_role_in_project(db, project_id, current_user.id)
        if proj_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this project",
            )
        proj_level = PROJECT_ROLE_LEVELS.get(proj_role, 0)
        if proj_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires project {min_role} role or higher",
            )

        return ProjectContext(
            project=project,
            project_role=proj_role,
            project_level=proj_level,
            org_ctx=org_ctx,
        )

    return _dependency


def require_team_role(min_role: str) -> Callable:
    """Dependency factory for team-level role checks."""
    min_level = TEAM_ROLE_LEVELS.get(min_role, 0)

    async def _dependency(
        team_id: int,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        role = _get_user_role_in_team(db, team_id, current_user.id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this team",
            )
        level = TEAM_ROLE_LEVELS.get(role, 0)
        if level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires team {min_role} role or higher",
            )
        return {"role": role, "level": level}

    return _dependency


def require_super_admin() -> Callable:
    """Dependency factory that requires super_admin global role."""

    async def _dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin access required",
            )
        return current_user

    return _dependency
