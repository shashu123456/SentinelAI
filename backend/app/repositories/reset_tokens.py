from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self.first(PasswordResetToken.token_hash == token_hash)

    def create(self, user_id: int, token_hash: str, expires_at: datetime) -> PasswordResetToken:
        record = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.add(record)
        return record

    def mark_used(self, record: PasswordResetToken) -> None:
        from app.utils.security import utcnow

        record.used_at = utcnow()
