"""Enterprise Invitation management service."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import User
from app.utils.security import utcnow
from app.repositories.invitations import InvitationRepository
from app.repositories.organizations import OrganizationRepository
from app.services.audit_service import record_org_event
from app.utils.logger import logger

INVITATION_EXPIRY_DAYS = 7


def create_invitation(
    db: Session,
    *,
    org_id: int,
    email: str,
    role: str,
    invited_by: int,
) -> dict:
    """Create an organization invitation."""
    invite_repo = InvitationRepository(db)
    org_repo = OrganizationRepository(db)

    # Check if user is already a member
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        if org_repo.is_member(org_id, existing_user.id):
            raise ValueError("User is already a member of this organization")

    # Check if there's already a pending invitation
    existing_invite = invite_repo.get_pending_by_email(org_id, email)
    if existing_invite:
        raise ValueError("A pending invitation already exists for this email")

    # Check capacity
    if not org_repo.can_add_member(org_id):
        org = org_repo.get(org_id)
        raise ValueError(f"Organization has reached the maximum of {org.max_members} members")

    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)

    invitation = invite_repo.create(
        organization_id=org_id,
        email=email,
        role=role,
        token=token,
        invited_by=invited_by,
        status="pending",
        expires_at=now + timedelta(days=INVITATION_EXPIRY_DAYS),
    )

    record_org_event(
        db,
        "org.invitation_sent",
        user_id=invited_by,
        org_id=org_id,
        detail={"email": email, "role": role},
    )
    db.commit()
    db.refresh(invitation)

    logger.info(f"Invitation sent to {email} for org {org_id} by user {invited_by}")
    return {
        "id": invitation.id,
        "email": invitation.email,
        "role": invitation.role,
        "status": invitation.status,
        "token": token,
        "expires_at": str(invitation.expires_at),
        "created_at": str(invitation.created_at),
    }


def accept_invitation(
    db: Session,
    *,
    token: str,
    user_id: int,
) -> dict:
    """Accept an invitation and add the user to the organization."""
    invite_repo = InvitationRepository(db)
    org_repo = OrganizationRepository(db)

    invitation = invite_repo.get_by_token(token)
    if invitation is None:
        raise ValueError("Invalid invitation token")

    if invitation.status != "pending":
        raise ValueError(f"Invitation is already {invitation.status}")

    if invitation.expires_at < utcnow():
        invite_repo.revoke(invitation)
        db.commit()
        raise ValueError("Invitation has expired")

    # Accept the invitation
    invite_repo.accept(invitation)

    # Add user to organization
    if not org_repo.is_member(invitation.organization_id, user_id):
        org_repo.add_member(
            invitation.organization_id,
            user_id,
            role=invitation.role,
        )

    # Check email match
    user = db.get(User, user_id)
    if user and user.email != invitation.email:
        raise ValueError("Invitation email does not match your account email")

    record_org_event(
        db,
        "org.invitation_accepted",
        user_id=user_id,
        org_id=invitation.organization_id,
        detail={"invitation_email": invitation.email, "role": invitation.role},
    )
    db.commit()

    logger.info(f"Invitation accepted: user {user_id} joined org {invitation.organization_id}")
    return {
        "organization_id": invitation.organization_id,
        "role": invitation.role,
    }


def revoke_invitation(
    db: Session,
    *,
    invitation_id: int,
    org_id: int,
    revoked_by: int,
) -> None:
    """Revoke a pending invitation."""
    invite_repo = InvitationRepository(db)

    invitation = invite_repo.get(invitation_id)
    if invitation is None or invitation.organization_id != org_id:
        raise ValueError("Invitation not found")

    invite_repo.revoke(invitation)

    record_org_event(
        db,
        "org.invitation_revoked",
        user_id=revoked_by,
        org_id=org_id,
        detail={"email": invitation.email, "role": invitation.role},
    )
    db.commit()


def cleanup_expired_invitations(db: Session) -> int:
    """Mark expired invitations as expired."""
    invite_repo = InvitationRepository(db)
    count = invite_repo.cleanup_expired()
    if count > 0:
        db.commit()
        logger.info(f"Cleaned up {count} expired invitations")
    return count
