from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_username(self, username: str) -> User | None:
        return self.first(User.username == username)

    def get_by_email(self, email: str) -> User | None:
        return self.first(User.email == email)

    def get_by_username_or_email(self, username: str, email: str) -> User | None:
        return self.first(or_(User.username == username, User.email == email))

    def create(
        self,
        username: str,
        email: str,
        hashed_password: str,
        role: str = "user",
        is_active: bool = True,
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=is_active,
        )
        self.add(user)
        return user

    def register_failed_attempt(self, user: User, lock_until) -> None:
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if lock_until is not None:
            user.locked_until = lock_until

    def reset_failed_attempts(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None

    def lock(self, user: User, lock_until) -> None:
        user.locked_until = lock_until

    def unlock(self, user: User) -> None:
        user.locked_until = None
        user.failed_login_attempts = 0
