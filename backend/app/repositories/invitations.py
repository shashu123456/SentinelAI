"""Invitation repository."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.models import Invitation
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository[Invitation]):
    model = Invitation

    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, **kwargs) -> Invitation:
        invitation = Invitation(**kwargs)
        self.db.add(invitation)
        self.db.flush()
        return invitation

    def get_by_token(self, token: str) -> Invitation | None:
        return self.db.query(Invitation).filter(Invitation.token == token).first()

    def get_pending_by_email(self, org_id: int, email: str) -> Invitation | None:
        return (
            self.db.query(Invitation)
            .filter(
                Invitation.organization_id == org_id,
                Invitation.email == email,
                Invitation.status == "pending",
                Invitation.expires_at > datetime.now(UTC),
            )
            .first()
        )

    def list_pending_for_org(self, org_id: int) -> list[Invitation]:
        return (
            self.db.query(Invitation)
            .filter(
                Invitation.organization_id == org_id,
                Invitation.status == "pending",
                Invitation.expires_at > datetime.now(UTC),
            )
            .order_by(Invitation.created_at.desc())
            .all()
        )

    def list_all_for_org(self, org_id: int, limit: int = 50) -> list[Invitation]:
        return (
            self.db.query(Invitation)
            .filter(Invitation.organization_id == org_id)
            .order_by(Invitation.created_at.desc())
            .limit(limit)
            .all()
        )

    def accept(self, invitation: Invitation) -> None:
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(UTC)
        self.db.flush()

    def revoke(self, invitation: Invitation) -> None:
        invitation.status = "revoked"
        self.db.flush()

    def cleanup_expired(self) -> int:
        """Mark expired invitations. Returns count of expired."""
        result = (
            self.db.query(Invitation)
            .filter(
                Invitation.status == "pending",
                Invitation.expires_at <= datetime.now(UTC),
            )
            .update({Invitation.status: "expired"}, synchronize_session=False)
        )
        self.db.flush()
        return result
