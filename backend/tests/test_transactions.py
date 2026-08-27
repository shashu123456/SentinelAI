"""Transaction context manager tests."""

import pytest

from app.database.database import transaction
from app.models.models import User
from app.repositories.users import UserRepository
from app.utils.security import hash_password


class TestTransaction:
    def test_commits_on_success(self, db_session):
        with transaction(db_session) as db:
            UserRepository(db).create(
                username="tx_ok",
                email="tx_ok@example.com",
                hashed_password=hash_password("testpass123"),
            )
        users = db_session.query(User).filter(User.username == "tx_ok").all()
        assert len(users) == 1

    def test_rolls_back_on_error(self, db_session):
        with pytest.raises(RuntimeError, match="boom"), transaction(db_session) as db:
            UserRepository(db).create(
                username="tx_rollback",
                email="tx_rollback@example.com",
                hashed_password=hash_password("testpass123"),
            )
            raise RuntimeError("boom")

        users = db_session.query(User).filter(User.username == "tx_rollback").all()
        assert users == []

    def test_nested_commit_preserves_prior_work(self, db_session):
        with transaction(db_session):
            UserRepository(db_session).create(
                username="outer",
                email="outer@example.com",
                hashed_password=hash_password("testpass123"),
            )
        assert db_session.query(User).filter(User.username == "outer").count() == 1
