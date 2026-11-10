"""Enterprise Organization analytics service.

Provides org-level aggregate metrics across all projects and scans.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import Finding, OrganizationMember, Project, Scan, Team


def get_organization_dashboard(db: Session, org_id: int) -> dict:
    """Compute organization-level dashboard stats across all projects."""
    datetime.now(UTC)

    # Total scans in this org
    total_scans = (
        db.scalar(
            select(func.count(Scan.id)).where(
                Scan.organization_id == org_id, Scan.deleted_at.is_(None)
            )
        )
        or 0
    )

    # Completed scans
    completed_scans = (
        db.scalar(
            select(func.count(Scan.id)).where(
                Scan.organization_id == org_id,
                Scan.status == "completed",
                Scan.deleted_at.is_(None),
            )
        )
        or 0
    )

    # Total vulnerabilities
    total_vulns = (
        db.scalar(
            select(func.coalesce(func.sum(Scan.total_vulnerabilities), 0)).where(
                Scan.organization_id == org_id, Scan.deleted_at.is_(None)
            )
        )
        or 0
    )

    # Average risk score
    avg_risk = (
        db.scalar(
            select(func.coalesce(func.avg(Scan.risk_score), 0)).where(
                Scan.organization_id == org_id,
                Scan.status == "completed",
                Scan.deleted_at.is_(None),
            )
        )
        or 0
    )

    # Total projects
    total_projects = (
        db.scalar(
            select(func.count(Project.id)).filter(
                Project.organization_id == org_id, Project.is_active is True
            )  # noqa: E712
        )
        or 0
    )

    # Total members
    total_members = (
        db.scalar(
            select(func.count(OrganizationMember.id)).filter(
                OrganizationMember.organization_id == org_id
            )
        )
        or 0
    )

    # Total teams
    total_teams = db.scalar(select(func.count(Team.id)).filter(Team.organization_id == org_id)) or 0

    # Severity distribution across all org scans
    severity_dist = {}
    from app.repositories.scans import SEVERITY_ORDER

    rows = db.execute(
        select(Finding.severity, func.count(Finding.id))
        .join(Scan, Finding.scan_id == Scan.id)
        .where(Scan.organization_id == org_id, Scan.deleted_at.is_(None))
        .group_by(Finding.severity)
    ).all()
    for sev, count in rows:
        severity_dist[sev] = count
    for sev in SEVERITY_ORDER:
        severity_dist.setdefault(sev, 0)

    # Scans per project
    scans_per_project = db.execute(
        select(Project.name, func.count(Scan.id))
        .join(Scan, Scan.project_id == Project.id)
        .where(
            Project.organization_id == org_id,
            Scan.deleted_at.is_(None),
        )
        .group_by(Project.name)
        .order_by(func.count(Scan.id).desc())
        .limit(10)
    ).all()

    # Recent scans (across all org projects)
    recent_scans = (
        db.execute(
            select(Scan)
            .where(Scan.organization_id == org_id, Scan.deleted_at.is_(None))
            .order_by(Scan.created_at.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )

    return {
        "total_scans": total_scans,
        "completed_scans": completed_scans,
        "total_vulnerabilities": total_vulns,
        "average_risk_score": round(float(avg_risk), 1),
        "total_projects": total_projects,
        "total_members": total_members,
        "total_teams": total_teams,
        "severity_distribution": severity_dist,
        "scans_per_project": [
            {"project": name, "scans": count} for name, count in scans_per_project
        ],
        "recent_scans": [
            {
                "id": s.id,
                "api_name": s.api_name,
                "status": s.status,
                "risk_score": s.risk_score,
                "risk_level": s.risk_level,
                "total_vulnerabilities": s.total_vulnerabilities,
                "created_at": str(s.created_at),
            }
            for s in recent_scans
        ],
    }


def get_organization_analytics(db: Session, org_id: int) -> dict:
    """Compute time-series analytics for the organization."""
    now = datetime.now(UTC)

    # Scan activity over last 30 days
    scan_activity = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).date()
        day_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=UTC)
        day_end = datetime.combine(day, datetime.max.time()).replace(tzinfo=UTC)
        count = (
            db.scalar(
                select(func.count(Scan.id)).where(
                    Scan.organization_id == org_id,
                    Scan.created_at >= day_start,
                    Scan.created_at <= day_end,
                    Scan.deleted_at.is_(None),
                )
            )
            or 0
        )
        scan_activity.append({"date": day.isoformat(), "scans": count})

    # Risk trend over time
    risk_trend = []
    rows = db.execute(
        select(Scan.created_at, Scan.risk_score)
        .where(
            Scan.organization_id == org_id,
            Scan.status == "completed",
            Scan.deleted_at.is_(None),
        )
        .order_by(Scan.created_at.asc())
    ).all()
    for created_at, risk_score in rows:
        risk_trend.append(
            {
                "date": (
                    created_at.date().isoformat()
                    if hasattr(created_at, "date")
                    else str(created_at)
                ),
                "score": risk_score,
            }
        )

    # OWASP distribution
    owasp_stmt = (
        select(Finding.owasp_category, func.count(Finding.id))
        .join(Scan, Finding.scan_id == Scan.id)
        .where(Scan.organization_id == org_id, Scan.deleted_at.is_(None))
        .group_by(Finding.owasp_category)
        .order_by(func.count(Finding.id).desc())
    )
    owasp_dist = [{"category": cat, "count": cnt} for cat, cnt in db.execute(owasp_stmt).all()]

    return {
        "scan_activity": scan_activity,
        "risk_trend": risk_trend,
        "owasp_distribution": owasp_dist,
    }
