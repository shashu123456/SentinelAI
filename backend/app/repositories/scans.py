from sqlalchemy import UnaryExpression, func, select
from sqlalchemy.orm import Session

from app.models.models import Finding, Scan
from app.repositories.base import BaseRepository
from app.schemas.schemas import SCAN_SORT_FIELDS, ScanListParams

SEVERITY_ORDER = ("Critical", "High", "Medium", "Low", "Info")

SCAN_SORT_COLUMNS = {name: getattr(Scan, name) for name in SCAN_SORT_FIELDS}


class ScanRepository(BaseRepository[Scan]):
    model = Scan

    def __init__(self, db: Session):
        super().__init__(db)

    @staticmethod
    def active_criteria():
        return Scan.deleted_at.is_(None)

    def get_owned(self, scan_id: int, user_id: int) -> Scan | None:
        """Fetch a scan that belongs to `user_id` and is not soft-deleted."""
        return self.first(
            Scan.id == scan_id,
            Scan.user_id == user_id,
            Scan.deleted_at.is_(None),
        )

    def get_owned_or_404(self, scan_id: int, user_id: int) -> Scan:
        scan = self.get_owned(scan_id, user_id)
        if scan is None:
            raise self.not_found(scan_id)
        return scan

    @staticmethod
    def not_found(scan_id: int):
        from fastapi import HTTPException, status

        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    def list_by_user(self, user_id: int, limit: int = 50) -> list[Scan]:
        return self.list(
            Scan.user_id == user_id,
            Scan.deleted_at.is_(None),
            order_by=Scan.created_at.desc(),
            limit=limit,
        )

    def _build_sort(self, params: ScanListParams) -> list[UnaryExpression]:
        clauses: list[UnaryExpression] = []
        for name, descending in params.sort_columns():
            column = SCAN_SORT_COLUMNS.get(name)
            if column is None:
                continue
            clauses.append(column.desc() if descending else column.asc())
        if not clauses:
            clauses.append(Scan.created_at.desc())
        return clauses

    def list_for_user_filtered(
        self, user_id: int, params: ScanListParams
    ) -> tuple[list[Scan], int]:
        """Return ``(items, total)`` for a paginated, filtered, sorted scan list.

        Supports status / risk_level / severity (via a scan with findings of
        that severity) / date-range / api_name search filters plus a whitelisted
        multi-column sort. Only the user's own non-deleted scans are returned.
        """
        criteria = [Scan.user_id == user_id, Scan.deleted_at.is_(None)]
        if params.status:
            criteria.append(Scan.status == params.status)
        if params.risk_level:
            criteria.append(Scan.risk_level == params.risk_level)
        if params.severity:
            criteria.append(
                select(Finding.id)
                .where(Finding.scan_id == Scan.id, Finding.severity == params.severity)
                .exists()
            )
        if params.date_from:
            criteria.append(Scan.created_at >= params.date_from)
        if params.date_to:
            criteria.append(Scan.created_at <= params.date_to)
        if params.search:
            criteria.append(Scan.api_name.ilike(f"%{params.search}%"))

        return self.paginate(
            *criteria,
            page=params.page,
            page_size=params.page_size,
            order_by=self._build_sort(params),
        )

    def recent_for_user(self, user_id: int, limit: int = 10) -> list[Scan]:
        return self.list_by_user(user_id, limit=limit)

    def count_for_user(self, user_id: int) -> int:
        return self.count(Scan.user_id == user_id, Scan.deleted_at.is_(None))

    def count_completed_for_user(self, user_id: int) -> int:
        return self.count(
            Scan.user_id == user_id,
            Scan.deleted_at.is_(None),
            Scan.status == "completed",
        )

    def total_vulnerabilities_for_user(self, user_id: int) -> int:
        stmt = select(func.coalesce(func.sum(Scan.total_vulnerabilities), 0)).where(
            Scan.user_id == user_id,
            Scan.deleted_at.is_(None),
        )
        return self.db.scalar(stmt) or 0

    def average_risk_for_user(self, user_id: int) -> float:
        stmt = select(func.coalesce(func.avg(Scan.risk_score), 0)).where(
            Scan.user_id == user_id,
            Scan.status == "completed",
            Scan.deleted_at.is_(None),
        )
        return float(self.db.scalar(stmt) or 0)

    def severity_distribution_for_user(self, user_id: int) -> dict:
        stmt = (
            select(Finding.severity, func.count(Finding.id))
            .join(Scan, Finding.scan_id == Scan.id)
            .where(Scan.user_id == user_id, Scan.deleted_at.is_(None))
            .group_by(Finding.severity)
        )
        dist: dict[str, int] = {sev: count for sev, count in self.db.execute(stmt).all()}
        for sev in SEVERITY_ORDER:
            dist.setdefault(sev, 0)
        return dist

    def create_scan(
        self,
        user_id: int,
        api_name: str,
        source_spec: dict | None = None,
        status: str = "running",
    ) -> Scan:
        scan = Scan(
            user_id=user_id,
            api_name=api_name,
            status=status,
            source_spec=source_spec,
        )
        self.add(scan)
        return scan

    def complete(self, scan: Scan, risk: dict, transition_history: list | None = None) -> None:
        scan.total_vulnerabilities = risk["total_vulnerabilities"]
        scan.risk_score = risk["score"]
        scan.risk_level = risk["level"]
        if transition_history is not None:
            scan.transition_history = transition_history

    def fail(self, scan: Scan) -> None:
        scan.status = "failed"
