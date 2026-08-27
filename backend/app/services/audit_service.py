"""Enterprise audit logging service.

Records security- and compliance-relevant events into the `audit_logs` table.
Every record captures: timestamp, user, action, module, resource, IP, user agent,
request ID, old/new values, status, and risk level.

Design principles:
- Append-only: no function in this module deletes or modifies existing logs.
- Every caller commits the transaction; this service only adds rows.
- Risk levels are auto-classified based on the action pattern.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.audit import AuditLogRepository

# ── Risk level classification ──────────────────────────────────────────
# High-risk actions are security-sensitive and should trigger alerts.
HIGH_RISK_ACTIONS = frozenset(
    {
        "auth.login_failed",
        "auth.password_reset",
        "auth.password_change",
        "auth.logout_all",
        "auth.account_locked",
        "auth.account_unlocked",
        "user.role_changed",
        "user.deactivated",
        "user.deleted",
        "org.created",
        "org.member_removed",
        "org.settings_changed",
        "api_key.created",
        "api_key.deleted",
        "settings.security_changed",
        "scan.deleted",
    }
)

MEDIUM_RISK_ACTIONS = frozenset(
    {
        "auth.register",
        "auth.login",
        "user.created",
        "org.member_added",
        "scan.completed",
        "scan.failed",
        "report.exported",
        "copilot.chat",
    }
)

# Module extraction from action prefix
_MODULE_MAP = {
    "auth": "authentication",
    "user": "user_management",
    "scan": "scanning",
    "report": "reporting",
    "org": "organization",
    "project": "project",
    "settings": "settings",
    "api_key": "api_keys",
    "copilot": "ai_copilot",
    "audit": "audit",
}


def _classify_risk(action: str) -> str:
    """Auto-classify risk level based on the action string."""
    if action in HIGH_RISK_ACTIONS:
        return "high"
    if action in MEDIUM_RISK_ACTIONS:
        return "medium"
    # Heuristic: any action with 'delete', 'remove', 'lock', 'revoke' is high
    lower = action.lower()
    for keyword in ("delete", "remove", "lock", "revoke", "reset", "failed"):
        if keyword in lower:
            return "high"
    for keyword in ("create", "add", "login", "export", "update"):
        if keyword in lower:
            return "medium"
    return "info"


def _extract_module(action: str) -> str:
    """Extract the module name from an action string like 'auth.login'."""
    prefix = action.split(".")[0] if "." in action else action
    return _MODULE_MAP.get(prefix, prefix)


def record_action(
    db: Session,
    action: str,
    *,
    user_id: int | None = None,
    username: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    resource: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    status: str = "success",
    risk_level: str | None = None,
) -> None:
    """Persist a single audit entry (does not commit).

    If risk_level is not provided, it is auto-classified from the action.
    """
    if risk_level is None:
        risk_level = _classify_risk(action)

    module = _extract_module(action)

    AuditLogRepository(db).create(
        action=action,
        user_id=user_id,
        username=username,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        resource=resource,
        old_value=old_value,
        new_value=new_value,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        status=status,
        risk_level=risk_level,
    )


def record_scan_event(
    db: Session,
    action: str,
    *,
    user_id: int,
    username: str | None = None,
    scan_id: int,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    """Record a scan lifecycle event."""
    record_action(
        db,
        action,
        user_id=user_id,
        username=username,
        entity_type="scan",
        entity_id=scan_id,
        resource=f"scan #{scan_id}",
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


def record_report_export(
    db: Session,
    *,
    user_id: int,
    username: str | None = None,
    scan_id: int,
    format: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    """Record a report export."""
    record_action(
        db,
        f"report.exported.{format}",
        user_id=user_id,
        username=username,
        entity_type="report",
        entity_id=scan_id,
        resource=f"scan #{scan_id} report ({format})",
        detail={"format": format},
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


def record_user_change(
    db: Session,
    action: str,
    *,
    actor_id: int,
    actor_username: str | None = None,
    target_user_id: int,
    target_username: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    """Record a user management event (role change, lock, etc.)."""
    record_action(
        db,
        action,
        user_id=actor_id,
        username=actor_username,
        entity_type="user",
        entity_id=target_user_id,
        resource=f"user {target_username or target_user_id}",
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


def record_org_event(
    db: Session,
    action: str,
    *,
    user_id: int,
    username: str | None = None,
    org_id: int,
    org_name: str | None = None,
    detail: dict[str, Any] | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    """Record an organization event."""
    record_action(
        db,
        action,
        user_id=user_id,
        username=username,
        entity_type="organization",
        entity_id=org_id,
        resource=f"org {org_name or org_id}",
        detail=detail,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
