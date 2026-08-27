"""Audit log repository with enterprise-grade filtering and pagination."""

from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.models.models import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        action: str,
        *,
        user_id: int | None = None,
        username: str | None = None,
        module: str | None = None,
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
        risk_level: str = "info",
    ) -> AuditLog:
        entry = AuditLog(
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
        self.add(entry)
        return entry

    def paginate_filtered(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        user_id: int | None = None,
        action: str | None = None,
        action_prefix: str | None = None,
        module: str | None = None,
        entity_type: str | None = None,
        risk_level: str | None = None,
        status: str | None = None,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        order_by: Any = None,
    ) -> tuple[list[AuditLog], int]:
        """Paginated, filtered audit log query."""
        criteria = []

        if user_id is not None:
            criteria.append(AuditLog.user_id == user_id)
        if action:
            criteria.append(AuditLog.action == action)
        if action_prefix:
            criteria.append(AuditLog.action.startswith(action_prefix))
        if module:
            criteria.append(AuditLog.module == module)
        if entity_type:
            criteria.append(AuditLog.entity_type == entity_type)
        if risk_level:
            criteria.append(AuditLog.risk_level == risk_level)
        if status:
            criteria.append(AuditLog.status == status)
        if date_from:
            criteria.append(AuditLog.created_at >= date_from)
        if date_to:
            criteria.append(AuditLog.created_at <= date_to)
        if search:
            pattern = f"%{search}%"
            criteria.append(
                or_(
                    AuditLog.action.ilike(pattern),
                    AuditLog.username.ilike(pattern),
                    AuditLog.resource.ilike(pattern),
                    AuditLog.entity_type.ilike(pattern),
                )
            )

        order = order_by if order_by is not None else desc(AuditLog.created_at)
        return self.paginate(*criteria, page=page, page_size=page_size, order_by=order)

    def get_by_id(self, log_id: int) -> AuditLog | None:
        return self.get(log_id)

    def count_by_module(self, user_id: int | None = None) -> dict[str, int]:
        """Count audit events grouped by module."""
        criteria = []
        if user_id is not None:
            criteria.append(AuditLog.user_id == user_id)
        stmt = (
            self.db.query(AuditLog.module, func.count(AuditLog.id))
            .filter(*criteria)
            .group_by(AuditLog.module)
        )
        return {module: count for module, count in stmt.all() if module}

    def count_by_risk_level(self, user_id: int | None = None) -> dict[str, int]:
        """Count audit events grouped by risk level."""
        criteria = []
        if user_id is not None:
            criteria.append(AuditLog.user_id == user_id)
        stmt = (
            self.db.query(AuditLog.risk_level, func.count(AuditLog.id))
            .filter(*criteria)
            .group_by(AuditLog.risk_level)
        )
        return {level: count for level, count in stmt.all()}

    def count_by_action(self, user_id: int | None = None, limit: int = 10) -> list[dict]:
        """Top N most frequent actions."""
        criteria = []
        if user_id is not None:
            criteria.append(AuditLog.user_id == user_id)
        stmt = (
            self.db.query(AuditLog.action, func.count(AuditLog.id))
            .filter(*criteria)
            .group_by(AuditLog.action)
            .order_by(desc(func.count(AuditLog.id)))
            .limit(limit)
        )
        return [{"action": action, "count": count} for action, count in stmt.all()]

    def purge_old(self, before: datetime) -> int:
        """Delete audit logs older than the given date (admin only). Returns count."""
        count = self.db.query(AuditLog).filter(AuditLog.created_at < before).delete()
        return count
