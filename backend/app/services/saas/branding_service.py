"""White-label branding management."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.saas import CustomBranding
from app.utils.logger import logger


def get_branding(db: Session, org_id: int) -> CustomBranding | None:
    """Get branding configuration for an organization."""
    return db.query(CustomBranding).filter(CustomBranding.organization_id == org_id).first()


def upsert_branding(db: Session, *, organization_id: int, **fields: Any) -> CustomBranding:
    """Create or update branding for an organization."""
    branding = get_branding(db, organization_id)
    if not branding:
        branding = CustomBranding(organization_id=organization_id)
        db.add(branding)
    for key, value in fields.items():
        if hasattr(branding, key):
            setattr(branding, key, value)
    branding.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(branding)
    logger.info("Branding updated: org=%s", organization_id)
    return branding


def verify_custom_domain(db: Session, org_id: int, verification_token: str) -> bool:
    """Verify ownership of a custom domain."""
    branding = get_branding(db, org_id)
    if not branding:
        return False
    if branding.domain_verification_token == verification_token:
        branding.domain_verified = True
        db.commit()
        return True
    return False
