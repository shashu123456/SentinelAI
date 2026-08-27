"""Team and TeamMember repositories."""

from sqlalchemy.orm import Session

from app.models.models import Team, TeamMember, User
from app.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    model = Team

    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, **kwargs) -> Team:
        team = Team(**kwargs)
        self.db.add(team)
        self.db.flush()
        return team

    def list_for_org(self, org_id: int) -> list[Team]:
        return self.db.query(Team).filter(Team.organization_id == org_id).all()

    def get_by_slug(self, org_id: int, slug: str) -> Team | None:
        return self.db.query(Team).filter(Team.organization_id == org_id, Team.slug == slug).first()

    def add_member(
        self, team_id: int, user_id: int, role: str = "member", added_by: int | None = None
    ) -> TeamMember:
        member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role=role,
            added_by=added_by,
        )
        self.db.add(member)
        self.db.flush()
        return member

    def remove_member(self, team_id: int, user_id: int) -> None:
        self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        ).delete()

    def is_member(self, team_id: int, user_id: int) -> bool:
        return (
            self.db.query(TeamMember)
            .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
            .first()
            is not None
        )

    def get_member_role(self, team_id: int, user_id: int) -> str | None:
        member = (
            self.db.query(TeamMember)
            .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
            .first()
        )
        return member.role if member else None

    def list_members(self, team_id: int) -> list[dict]:
        """Return team members with user info."""
        rows = (
            self.db.query(TeamMember, User)
            .join(User, TeamMember.user_id == User.id)
            .filter(TeamMember.team_id == team_id)
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

    def count_members(self, team_id: int) -> int:
        from sqlalchemy import func

        return (
            self.db.query(func.count(TeamMember.id)).filter(TeamMember.team_id == team_id).scalar()
            or 0
        )
