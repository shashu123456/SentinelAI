"""API Key repository with secure key management."""

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.models import ApiKey
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    model = ApiKey

    def __init__(self, db: Session):
        super().__init__(db)

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """Generate an API key. Returns (full_key, key_prefix, key_hash)."""
        raw = f"sai_{secrets.token_urlsafe(32)}"
        prefix = raw[:12]
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        return raw, prefix, key_hash

    def create_key(
        self,
        *,
        organization_id: int,
        user_id: int,
        name: str,
        scopes: list[str] | None = None,
        expires_days: int | None = None,
    ) -> tuple[ApiKey, str]:
        """Create a new API key. Returns (ApiKey, raw_key)."""
        full_key, prefix, key_hash = self.generate_key()
        expires_at = None
        if expires_days:
            expires_at = datetime.now(UTC) + __import__("datetime").timedelta(days=expires_days)

        api_key = ApiKey(
            organization_id=organization_id,
            user_id=user_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes={"allowed": scopes} if scopes else None,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        self.db.flush()
        return api_key, full_key

    def get_by_prefix(self, key_prefix: str) -> ApiKey | None:
        return self.db.query(ApiKey).filter(ApiKey.key_prefix == key_prefix).first()

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        return self.db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()

    def validate_key(self, raw_key: str) -> ApiKey | None:
        """Validate a raw API key. Returns the ApiKey if valid, None otherwise."""
        prefix = raw_key[:12]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = (
            self.db.query(ApiKey)
            .filter(
                ApiKey.key_prefix == prefix,
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,  # noqa: E712
            )
            .first()
        )

        if api_key is None:
            return None

        # Check expiry
        if api_key.expires_at and api_key.expires_at < datetime.now(UTC):
            return None

        # Check revocation
        if api_key.revoked_at is not None:
            return None

        # Update last_used_at
        api_key.last_used_at = datetime.now(UTC)
        self.db.flush()

        return api_key

    def list_for_org(self, org_id: int) -> list[ApiKey]:
        return (
            self.db.query(ApiKey)
            .filter(ApiKey.organization_id == org_id)
            .order_by(ApiKey.created_at.desc())
            .all()
        )

    def list_for_user(self, user_id: int) -> list[ApiKey]:
        return (
            self.db.query(ApiKey)
            .filter(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
            .all()
        )

    def revoke(self, api_key: ApiKey) -> None:
        api_key.is_active = False
        api_key.revoked_at = datetime.now(UTC)
        self.db.flush()

    def deactivate(self, api_key: ApiKey) -> None:
        api_key.is_active = False
        self.db.flush()

    def activate(self, api_key: ApiKey) -> None:
        api_key.is_active = True
        api_key.revoked_at = None
        self.db.flush()

    def count_active_for_org(self, org_id: int) -> int:
        from sqlalchemy import func

        return (
            self.db.query(func.count(ApiKey.id))
            .filter(ApiKey.organization_id == org_id, ApiKey.is_active == True)  # noqa: E712
            .scalar()
            or 0
        )
