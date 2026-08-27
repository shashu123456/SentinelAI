"""Enterprise API Key management service."""

from sqlalchemy.orm import Session

from app.repositories.api_keys import ApiKeyRepository
from app.services.audit_service import record_action
from app.utils.logger import logger


def create_api_key(
    db: Session,
    *,
    organization_id: int,
    user_id: int,
    name: str,
    scopes: list[str] | None = None,
    expires_days: int | None = None,
) -> dict:
    """Create a new API key. Returns the key data including the raw key (shown only once)."""
    api_key_repo = ApiKeyRepository(db)

    api_key, raw_key = api_key_repo.create_key(
        organization_id=organization_id,
        user_id=user_id,
        name=name,
        scopes=scopes,
        expires_days=expires_days,
    )

    record_action(
        db,
        "api_key.created",
        user_id=user_id,
        entity_type="api_key",
        entity_id=api_key.id,
        resource=f"api_key '{name}'",
        detail={"key_prefix": api_key.key_prefix, "scopes": scopes},
    )
    db.commit()

    logger.info(f"API key '{name}' created for org {organization_id}")
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "raw_key": raw_key,  # Only shown at creation time
        "scopes": api_key.scopes,
        "expires_at": str(api_key.expires_at) if api_key.expires_at else None,
        "created_at": str(api_key.created_at),
    }


def revoke_api_key(
    db: Session,
    *,
    api_key_id: int,
    organization_id: int,
    user_id: int,
) -> None:
    """Revoke an API key."""
    api_key_repo = ApiKeyRepository(db)

    api_key = api_key_repo.get(api_key_id)
    if api_key is None or api_key.organization_id != organization_id:
        raise ValueError("API key not found")

    api_key_repo.revoke(api_key)

    record_action(
        db,
        "api_key.deleted",
        user_id=user_id,
        entity_type="api_key",
        entity_id=api_key.id,
        resource=f"api_key '{api_key.name}'",
        risk_level="high",
    )
    db.commit()


def list_api_keys(db: Session, organization_id: int) -> list[dict]:
    """List all API keys for an organization (without raw keys)."""
    api_key_repo = ApiKeyRepository(db)
    keys = api_key_repo.list_for_org(organization_id)
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "is_active": k.is_active,
            "last_used_at": str(k.last_used_at) if k.last_used_at else None,
            "expires_at": str(k.expires_at) if k.expires_at else None,
            "created_at": str(k.created_at),
            "revoked_at": str(k.revoked_at) if k.revoked_at else None,
        }
        for k in keys
    ]


def validate_api_key(db: Session, raw_key: str) -> dict | None:
    """Validate an API key and return its metadata if valid."""
    api_key_repo = ApiKeyRepository(db)
    api_key = api_key_repo.validate_key(raw_key)
    if api_key is None:
        return None
    return {
        "id": api_key.id,
        "organization_id": api_key.organization_id,
        "user_id": api_key.user_id,
        "name": api_key.name,
        "scopes": api_key.scopes,
    }
