"""Framework-agnostic repository base class.

Repositories centralize all data access for a model so services and API routes
never reach into SQLAlchemy directly. They use the SQLAlchemy 2.x `select()`
style, which behaves identically on SQLite and PostgreSQL.
"""

import builtins
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar, cast

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """CRUD + query helpers for a single ORM model."""

    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ read

    def get(self, obj_id: int) -> ModelT | None:
        return self.db.get(self.model, obj_id)

    def get_or_404(self, obj_id: int, detail: str = "Resource not found") -> ModelT:
        obj = self.get(obj_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        return obj

    def first(self, *criteria, order_by=None) -> ModelT | None:
        stmt = select(self.model)
        if criteria:
            stmt = stmt.where(*criteria)
        if order_by is not None:
            stmt = (
                stmt.order_by(*order_by)
                if isinstance(order_by, list | tuple)
                else stmt.order_by(order_by)
            )
        return self.db.scalars(stmt).first()

    def list(
        self,
        *criteria,
        order_by=None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ModelT]:
        stmt = select(self.model)
        if criteria:
            stmt = stmt.where(*criteria)
        if order_by is not None:
            stmt = (
                stmt.order_by(*order_by)
                if isinstance(order_by, list | tuple)
                else stmt.order_by(order_by)
            )
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        return list(self.db.scalars(stmt).all())

    def count(self, *criteria) -> int:
        stmt = select(func.count()).select_from(self.model)
        if criteria:
            stmt = stmt.where(*criteria)
        return self.db.scalar(stmt) or 0

    def paginate(
        self,
        *criteria,
        page: int = 1,
        page_size: int = 20,
        order_by=None,
    ) -> tuple[builtins.list[ModelT], int]:
        """Return `(items, total)` for a page of results.

        A deterministic order is always applied: without an `ORDER BY` the
        database is free to return rows in any order, so `LIMIT/OFFSET`
        pages could repeat or skip records. Callers that care about a
        specific order (e.g. newest first) pass `order_by` explicitly.
        """
        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)
        if order_by is None:
            # `model` is declared as `type[ModelT]`, so the mapped table is only
            # visible on the concrete model; `cast` states that for the checker.
            table = cast(Any, self.model).__table__
            order_by = desc(table.primary_key.columns[0])
        total = self.count(*criteria)
        items = self.list(
            *criteria,
            order_by=order_by,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return items, total

    # ------------------------------------------------------------------ write

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        return obj

    def add_all(self, objs: builtins.list[ModelT]) -> None:
        self.db.add_all(objs)

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)

    def soft_delete(self, obj: ModelT) -> None:
        """Mark `deleted_at` when the model supports it, else hard delete."""
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = datetime.now(UTC)
        else:
            self.delete(obj)

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, obj: ModelT) -> ModelT:
        self.db.refresh(obj)
        return obj
