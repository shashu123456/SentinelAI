"""Organization and Project repositories."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import (
    Organization,
    OrganizationMember,
    Project,
    ProjectMember,
)
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, **kwargs) -> Organization:
        org = Organization(**kwargs)
        self.db.add(org)
        self.db.flush()
        return org

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.db.query(Organization).filter(Organization.slug == slug).first()

    def list_for_user(self, user_id: int) -> list[Organization]:
        return (
            self.db.query(Organization)
            .join(OrganizationMember)
            .filter(OrganizationMember.user_id == user_id)
            .all()
        )

    def count_members(self, org_id: int) -> int:
        return (
            self.db.query(func.count(OrganizationMember.id))
            .filter(OrganizationMember.organization_id == org_id)
            .scalar()
            or 0
        )

    def list_members(self, org_id: int) -> list[dict]:
        from app.models.models import User

        rows = (
            self.db.query(OrganizationMember, User)
            .join(User, OrganizationMember.user_id == User.id)
            .filter(OrganizationMember.organization_id == org_id)
            .all()
        )
        return [
            {
                "id": m.id,
                "user_id": u.id,
                "username": u.username,
                "email": u.email,
                "role": m.role,
                "joined_at": str(m.joined_at),
            }
            for m, u in rows
        ]

    def update_member_role(self, org_id: int, user_id: int, new_role: str) -> bool:
        member = (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
        )
        if member is None:
            return False
        member.role = new_role
        self.db.flush()
        return True

    def can_add_member(self, org_id: int) -> bool:
        org = self.get(org_id)
        if org is None:
            return False
        return self.count_members(org_id) < org.max_members

    def can_create_project(self, org_id: int) -> bool:
        org = self.get(org_id)
        if org is None:
            return False
        count = (
            self.db.query(func.count(Project.id)).filter(Project.organization_id == org_id).scalar()
            or 0
        )
        return count < org.max_projects

    def add_member(self, org_id: int, user_id: int, role: str = "member") -> OrganizationMember:
        member = OrganizationMember(
            organization_id=org_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        self.db.flush()
        return member

    def remove_member(self, org_id: int, user_id: int) -> None:
        self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        ).delete()

    def is_member(self, org_id: int, user_id: int) -> bool:
        return (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
            is not None
        )

    def get_member_role(self, org_id: int, user_id: int) -> str | None:
        member = (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
        )
        return member.role if member else None


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, **kwargs) -> Project:
        project = Project(**kwargs)
        self.db.add(project)
        self.db.flush()
        return project

    def get_by_slug(self, org_id: int, slug: str) -> Project | None:
        return (
            self.db.query(Project)
            .filter(Project.organization_id == org_id, Project.slug == slug)
            .first()
        )

    def list_for_org(self, org_id: int) -> list[Project]:
        return self.db.query(Project).filter(Project.organization_id == org_id).all()

    def list_for_user(self, user_id: int) -> list[Project]:
        return self.db.query(Project).filter(Project.owner_id == user_id).all()

    def add_member(
        self, project_id: int, user_id: int, role: str = "developer", added_by: int | None = None
    ) -> ProjectMember:
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role,
            added_by=added_by,
        )
        self.db.add(member)
        self.db.flush()
        return member

    def remove_member(self, project_id: int, user_id: int) -> None:
        self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        ).delete()

    def list_members(self, project_id: int) -> list[dict]:
        from app.models.models import User

        rows = (
            self.db.query(ProjectMember, User)
            .join(User, ProjectMember.user_id == User.id)
            .filter(ProjectMember.project_id == project_id)
            .all()
        )
        return [
            {
                "id": m.id,
                "user_id": u.id,
                "username": u.username,
                "email": u.email,
                "role": m.role,
                "added_at": str(m.added_at),
            }
            for m, u in rows
        ]

    def count_members(self, project_id: int) -> int:
        return (
            self.db.query(func.count(ProjectMember.id))
            .filter(ProjectMember.project_id == project_id)
            .scalar()
            or 0
        )
