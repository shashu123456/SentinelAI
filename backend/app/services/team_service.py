"""Enterprise Team management service."""

from sqlalchemy.orm import Session

from app.repositories.teams import TeamRepository
from app.services.audit_service import record_org_event
from app.utils.logger import logger


def create_team(
    db: Session,
    *,
    org_id: int,
    name: str,
    slug: str,
    description: str | None,
    creator_id: int,
) -> dict:
    """Create a team and add the creator as admin."""
    team_repo = TeamRepository(db)

    if team_repo.get_by_slug(org_id, slug):
        raise ValueError("Team slug already taken in this organization")

    team = team_repo.create(
        organization_id=org_id,
        name=name,
        slug=slug,
        description=description,
    )
    team_repo.add_member(team.id, creator_id, role="admin", added_by=creator_id)

    record_org_event(
        db,
        "team.created",
        user_id=creator_id,
        org_id=org_id,
        detail={"team_name": name, "team_slug": slug},
    )
    db.commit()
    db.refresh(team)

    logger.info(f"Team '{name}' created in org {org_id} by user {creator_id}")
    return {
        "id": team.id,
        "name": team.name,
        "slug": team.slug,
        "description": team.description,
        "organization_id": team.organization_id,
        "created_at": str(team.created_at),
    }


def add_team_member(
    db: Session,
    *,
    team_id: int,
    user_id: int,
    role: str,
    added_by: int,
    org_id: int,
) -> None:
    """Add a user to a team."""
    team_repo = TeamRepository(db)

    if team_repo.is_member(team_id, user_id):
        raise ValueError("User is already a member of this team")

    team_repo.add_member(team_id, user_id, role=role, added_by=added_by)

    record_org_event(
        db,
        "team.member_added",
        user_id=added_by,
        org_id=org_id,
        detail={"team_id": team_id, "added_user_id": user_id, "role": role},
    )
    db.commit()


def remove_team_member(
    db: Session,
    *,
    team_id: int,
    user_id: int,
    removed_by: int,
    org_id: int,
) -> None:
    """Remove a user from a team."""
    team_repo = TeamRepository(db)

    if not team_repo.is_member(team_id, user_id):
        raise ValueError("User is not a member of this team")

    team_repo.remove_member(team_id, user_id)

    record_org_event(
        db,
        "team.member_removed",
        user_id=removed_by,
        org_id=org_id,
        detail={"team_id": team_id, "removed_user_id": user_id},
    )
    db.commit()


def delete_team(
    db: Session,
    *,
    team_id: int,
    org_id: int,
    deleted_by: int,
) -> None:
    """Delete a team and all its memberships."""
    from app.models.models import Team

    team = db.get(Team, team_id)
    if team is None:
        raise ValueError("Team not found")

    team_repo = TeamRepository(db)
    record_org_event(
        db,
        "team.deleted",
        user_id=deleted_by,
        org_id=org_id,
        detail={"team_name": team.name, "team_slug": team.slug},
    )
    db.delete(team)
    db.commit()
    logger.info(f"Team {team_id} deleted from org {org_id}")
