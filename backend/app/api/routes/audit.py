"""Enterprise Audit Center API.

Endpoints:
    GET  /api/audit/logs        — Paginated, filtered audit log list
    GET  /api/audit/logs/{id}   — Single audit event detail
    GET  /api/audit/stats       — Aggregate statistics (module/risk/action counts)
    GET  /api/audit/export      — CSV export of filtered logs
    GET  /api/audit/modules     — List distinct modules for filter dropdown
    GET  /api/audit/actions     — List distinct actions for filter dropdown

RBAC:
    viewer/admin → read access (any user can view their own org's logs)
    admin only   → stats, export, purge
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import AuditLog, User
from app.repositories.audit import AuditLogRepository
from app.schemas.schemas import Role
from app.utils.security import get_current_user, require_roles

router = APIRouter(prefix="/api/audit", tags=["Audit Center"])

admin_required = require_roles(Role.admin)


def _log_to_dict(log: AuditLog) -> dict:
    """Serialize an AuditLog to a JSON-safe dict."""
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "action": log.action,
        "module": log.module,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "resource": log.resource,
        "old_value": log.old_value,
        "new_value": log.new_value,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "request_id": log.request_id,
        "status": log.status,
        "risk_level": log.risk_level,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


# ── Paginated log list ────────────────────────────────────────────────


@router.get("/logs")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: int | None = Query(None),
    action: str | None = Query(None, description="Exact action match"),
    action_prefix: str | None = Query(None, description="Action prefix match"),
    module: str | None = Query(None),
    entity_type: str | None = Query(None),
    risk_level: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List audit logs with advanced filtering and pagination."""
    repo = AuditLogRepository(db)

    items, total = repo.paginate_filtered(
        page=page,
        page_size=page_size,
        user_id=user_id,
        action=action,
        action_prefix=action_prefix,
        module=module,
        entity_type=entity_type,
        risk_level=risk_level,
        status=status,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

    return {
        "items": [_log_to_dict(log) for log in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ── Single event detail ───────────────────────────────────────────────


@router.get("/logs/{log_id}")
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a single audit event."""
    repo = AuditLogRepository(db)
    log = repo.get_by_id(log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return _log_to_dict(log)


# ── Aggregate statistics ──────────────────────────────────────────────


@router.get("/stats")
def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    """Get aggregate audit statistics (admin only)."""
    repo = AuditLogRepository(db)
    total = repo.count()
    by_module = repo.count_by_module()
    by_risk = repo.count_by_risk_level()
    top_actions = repo.count_by_action(limit=10)

    return {
        "total_events": total,
        "by_module": by_module,
        "by_risk_level": by_risk,
        "top_actions": top_actions,
    }


# ── CSV export ────────────────────────────────────────────────────────


@router.get("/export")
def export_audit_logs(
    action_prefix: str | None = Query(None),
    module: str | None = Query(None),
    risk_level: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    """Export audit logs as CSV (admin only)."""
    import csv
    import io

    repo = AuditLogRepository(db)
    items, _ = repo.paginate_filtered(
        page=1,
        page_size=10000,
        action_prefix=action_prefix,
        module=module,
        risk_level=risk_level,
        date_from=date_from,
        date_to=date_to,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Timestamp",
            "User ID",
            "Username",
            "Action",
            "Module",
            "Entity Type",
            "Entity ID",
            "Resource",
            "Risk Level",
            "Status",
            "IP Address",
            "User Agent",
            "Request ID",
            "Detail",
        ]
    )
    for log in items:
        writer.writerow(
            [
                log.id,
                log.created_at.isoformat() if log.created_at else "",
                log.user_id or "",
                log.username or "",
                log.action,
                log.module or "",
                log.entity_type or "",
                log.entity_id or "",
                log.resource or "",
                log.risk_level,
                log.status,
                log.ip_address or "",
                log.user_agent or "",
                log.request_id or "",
                str(log.detail) if log.detail else "",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-logs.csv"},
    )


# ── Distinct values for filter dropdowns ──────────────────────────────


@router.get("/modules")
def list_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List distinct module values for filter dropdown."""
    from sqlalchemy import distinct

    rows = (
        db.query(distinct(AuditLog.module))
        .filter(AuditLog.module.isnot(None))
        .order_by(AuditLog.module)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/actions")
def list_actions(
    module: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List distinct action values, optionally filtered by module."""
    from sqlalchemy import distinct

    query = db.query(distinct(AuditLog.action))
    if module:
        query = query.filter(AuditLog.module == module)
    rows = query.order_by(AuditLog.action).all()
    return [r[0] for r in rows]
