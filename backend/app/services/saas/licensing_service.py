"""License management for enterprise and self-hosted deployments."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from sqlalchemy.orm import Session

from app.models.saas import License
from app.utils.logger import logger


def validate_license(db: Session, license_key: str) -> License | None:
    """Validate a license key. Returns None if invalid/expired."""
    lic = db.query(License).filter(License.license_key == license_key).first()
    if not lic:
        return None

    now = datetime.now(UTC)

    if lic.status != "active":
        return None

    if lic.expires_at:
        exp = lic.expires_at
        if exp.tzinfo is None and now.tzinfo is not None:
            exp = exp.replace(tzinfo=UTC)
        elif exp.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=None)
        if exp < now:
            lic.status = "expired"
            db.commit()
            return None

    if lic.max_uses and lic.current_uses >= lic.max_uses:
        lic.status = "expired"
        db.commit()
        return None

    return lic


def activate_license(db: Session, *, license_key: str, organization_id: int) -> License | None:
    """Activate a license key for an organization."""
    lic = validate_license(db, license_key)
    if not lic:
        return None
    lic.organization_id = organization_id
    lic.current_uses += 1
    lic.status = "active"
    db.commit()
    db.refresh(lic)
    logger.info("License activated: org=%s type=%s", organization_id, lic.license_type)
    return lic


def create_license(
    db: Session,
    *,
    license_type: str = "trial",
    organization_id: int | None = None,
    expires_in_days: int | None = None,
    max_uses: int | None = None,
    features: dict | None = None,
    max_seats: int | None = None,
    metadata: dict | None = None,
) -> License:
    """Create a new license key."""
    now = datetime.now(UTC)
    lic = License(
        license_key=f"sai-{token_urlsafe(32)}",
        organization_id=organization_id,
        license_type=license_type,
        status="active",
        issued_at=now,
        expires_at=now + timedelta(days=expires_in_days) if expires_in_days else None,
        max_uses=max_uses,
        features=features or {},
        max_seats=max_seats,
        license_metadata=metadata,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    logger.info("License created: type=%s", license_type)
    return lic
