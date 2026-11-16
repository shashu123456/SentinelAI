"""Seed the read-only demo account.

Creates ``demo@sentinelai.dev`` (password from ``SENTINEL_DEMO_PASSWORD``) and
one completed scan of each kind (spec, deps, code) so the Reports page is not
empty for a stranger who clicks "Try the demo".

Idempotent: re-running only fills in whatever is missing and never duplicates a
kind that already has a completed scan. Refuses to run if the password is unset,
so the demo credential can never be committed or defaulted.

The password is never printed or logged.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database.database import SessionLocal, init_db  # noqa: E402
from app.models.models import AuthorizedUse, Scan, User  # noqa: E402
from app.repositories.users import UserRepository  # noqa: E402
from app.services.scan_service import execute_scan  # noqa: E402
from app.services.unified_scan import execute_unified_scan  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES = REPO_ROOT / "samples"


def _ensure_demo_user(db, settings) -> User:
    repo = UserRepository(db)
    user = repo.get_by_email(settings.SENTINEL_DEMO_EMAIL)
    if user is not None:
        return user
    user = repo.create(
        username="demo",
        email=settings.SENTINEL_DEMO_EMAIL,
        hashed_password=hash_password(settings.SENTINEL_DEMO_PASSWORD),
        role="user",
        is_active=True,
    )
    db.commit()
    db.refresh(user)
    print(f"Created demo user {user.username} <{user.email}>")
    return user


def _ensure_authorized(db, user: User) -> None:
    row = db.query(AuthorizedUse).filter(AuthorizedUse.user_id == user.id).one_or_none()
    if row is None:
        db.add(AuthorizedUse(user_id=user.id, version="1", ip_address="seed"))
        db.commit()


def _has_kind(db, user: User, kind: str) -> bool:
    return (
        db.query(Scan.id)
        .filter(Scan.user_id == user.id, Scan.kind == kind, Scan.status == "completed")
        .first()
        is not None
    )


def _seed_spec(db, user: User) -> None:
    if _has_kind(db, user, "spec"):
        print("spec scan already present; skipping")
        return
    spec = yaml.safe_load((SAMPLES / "demo-openapi.yaml").read_text(encoding="utf-8"))
    scan = execute_scan(db, user.id, "Demo Petstore API", spec)
    print(f"Seeded spec scan #{scan.id} ({scan.total_vulnerabilities} findings)")


def _seed_unified(db, user: User, kind: str, filename: str) -> None:
    if _has_kind(db, user, kind):
        print(f"{kind} scan already present; skipping")
        return
    data = (SAMPLES / filename).read_bytes()
    scan, partial = execute_unified_scan(db, user.id, kind, filename, data)
    print(
        f"Seeded {kind} scan #{scan.id} "
        f"({scan.total_vulnerabilities} findings, partial={partial})"
    )


def main() -> int:
    settings = get_settings()
    if not settings.SENTINEL_DEMO_PASSWORD:
        print(
            "ERROR: SENTINEL_DEMO_PASSWORD is not set. Refusing to seed the demo account.",
            file=sys.stderr,
        )
        return 1
    if not os.environ.get("SENTINEL_DEMO_PASSWORD"):
        print(
            "ERROR: SENTINEL_DEMO_PASSWORD must be provided as an environment variable.",
            file=sys.stderr,
        )
        return 1

    init_db()
    db = SessionLocal()
    try:
        user = _ensure_demo_user(db, settings)
        _ensure_authorized(db, user)
        _seed_spec(db, user)
        _seed_unified(db, user, "deps", "demo-requirements.txt")
        _seed_unified(db, user, "code", "demo-code.zip")

        total = (
            db.query(Scan.id).filter(Scan.user_id == user.id, Scan.status == "completed").count()
        )
        print(f"Demo account ready: {total} completed scan(s).")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
