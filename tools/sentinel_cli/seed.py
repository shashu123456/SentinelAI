"""Seed a realistic demo workspace without touching the network.

Creates (idempotently):

* user ``demo`` / ``demo1234``
* organization ``Demo Security`` (owner: demo)
* project ``Core Payments API``
* one scan per YAML file in ``samples/``

Run via ``make seed`` or ``sentinel demo``.
"""

from __future__ import annotations

from pathlib import Path

from .local import BACKEND_DIR, REPO_ROOT, load_spec

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@sentinelai.dev"
DEMO_PASSWORD = "demo1234"
ORG_NAME = "Demo Security"
ORG_SLUG = "demo-security"
PROJECT_NAME = "Core Payments API"
PROJECT_SLUG = "core-payments-api"


def _attach(db, obj) -> None:
    db.add(obj)
    db.commit()
    db.refresh(obj)


def seed_demo(spec_paths: list[Path] | None = None, quiet: bool = False) -> dict:
    """Create the demo workspace and return a summary of what exists."""
    # Keep seeding offline and fast: point the AI analyzer at a closed port so
    # the best-effort analysis step fails immediately instead of hanging on a
    # missing Ollama install.
    import os

    os.environ.setdefault("OLLAMA_URL", "http://127.0.0.1:9/api/generate")
    os.environ.setdefault("SENTINEL_ENV", "development")

    import sys

    backend = str(BACKEND_DIR)
    if backend not in sys.path:
        sys.path.insert(0, backend)

    # SQLite's default URL is relative (``sqlite:///./sentinelai.db``), and the
    # engine resolves it against the process cwd. The API runs from backend/,
    # so seed from there too — otherwise the demo login silently targets a
    # different database file than the server reads.
    os.chdir(BACKEND_DIR)

    from app.database.database import SessionLocal, init_db
    from app.models.models import Organization, OrganizationMember, Project
    from app.repositories.organizations import OrganizationRepository, ProjectRepository
    from app.repositories.users import UserRepository
    from app.services.scan_service import execute_scan
    from app.utils.security import hash_password

    init_db()
    db = SessionLocal()
    summary = {
        "created_user": False,
        "created_org": False,
        "created_project": False,
        "scans": [],
        "organization_id": None,
        "project_id": None,
    }
    org = None
    project = None

    try:
        users = UserRepository(db)
        user = users.get_by_username(DEMO_USERNAME)
        if user is None:
            user = users.create(
                username=DEMO_USERNAME,
                email=DEMO_EMAIL,
                hashed_password=hash_password(DEMO_PASSWORD),
                role="user",
            )
            db.commit()
            db.refresh(user)
            summary["created_user"] = True

        org = db.query(Organization).filter(Organization.slug == ORG_SLUG).one_or_none()
        if org is None:
            org = OrganizationRepository(db).create(
                name=ORG_NAME,
                slug=ORG_SLUG,
                description="Sandbox organization created by `sentinel demo`.",
                owner_id=user.id,
                subscription_tier="pro",
                max_members=25,
                max_projects=10,
                max_scans_per_month=500,
            )
            db.flush()
            db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
            db.commit()
            db.refresh(org)
            summary["created_org"] = True

        project = (
            db.query(Project)
            .filter(Project.organization_id == org.id, Project.slug == PROJECT_SLUG)
            .one_or_none()
        )
        if project is None:
            project = ProjectRepository(db).create(
                organization_id=org.id,
                name=PROJECT_NAME,
                slug=PROJECT_SLUG,
                description="Demo project for local development.",
                owner_id=user.id,
            )
            db.flush()
            db.commit()
            db.refresh(project)
            summary["created_project"] = True

        paths = spec_paths or sorted((REPO_ROOT / "samples").glob("*.yaml"))
        from app.models.models import Scan

        already = {row[0] for row in db.query(Scan.api_name).filter(Scan.user_id == user.id).all()}

        for path in paths:
            name = path.stem.replace("_", " ").title()
            if name in already:
                continue
            spec = load_spec(path)
            scan = execute_scan(db, user.id, name, spec)
            scan.organization_id = org.id
            scan.project_id = project.id
            db.commit()
            # Read scalars while the instance is still bound to the session;
            # the final commit below expires every loaded attribute.
            summary["scans"].append(
                {
                    "id": scan.id,
                    "api_name": scan.api_name,
                    "risk_score": scan.risk_score,
                    "risk_level": scan.risk_level,
                    "vulnerabilities": scan.total_vulnerabilities,
                }
            )

        summary["organization_id"] = org.id if org is not None else None
        summary["project_id"] = project.id if project is not None else None
    finally:
        db.close()

    summary.update(
        {
            "username": DEMO_USERNAME,
            "password": DEMO_PASSWORD,
            "email": DEMO_EMAIL,
        }
    )
    return summary
