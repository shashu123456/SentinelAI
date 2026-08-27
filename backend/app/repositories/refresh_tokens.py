from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.first(RefreshToken.token_hash == token_hash)

    def create(
        self,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
    ) -> RefreshToken:
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
        )
        self.add(record)
        return record

    def revoke(self, record: RefreshToken, replaced_by: str | None = None) -> None:
        from app.utils.security import utcnow

        record.revoked_at = utcnow()
        if replaced_by:
            record.replaced_by = replaced_by

    def revoke_all_for_user(self, user_id: int) -> None:
        from app.utils.security import utcnow

        now = utcnow()
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({RefreshToken.revoked_at: now}, synchronize_session=False)

    def list_for_user(self, user_id: int) -> list[RefreshToken]:
        return self.list(
            RefreshToken.user_id == user_id,
            order_by=RefreshToken.created_at.desc(),
        )
