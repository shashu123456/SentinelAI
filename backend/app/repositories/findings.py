from collections.abc import Iterable

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.models import Finding, Scan
from app.repositories.base import BaseRepository
from app.schemas.schemas import FINDING_SORT_FIELDS, FindingListParams

SEVERITY_ORDER = ("Critical", "High", "Medium", "Low", "Info")
SEVERITY_RANK = case(
    *[(Finding.severity == sev, rank) for rank, sev in enumerate(SEVERITY_ORDER)],
    else_=len(SEVERITY_ORDER),
)

FINDING_SORT_COLUMNS = {
    "severity": SEVERITY_RANK,
    **{name: getattr(Finding, name) for name in FINDING_SORT_FIELDS if name != "severity"},
}


class FindingRepository(BaseRepository[Finding]):
    model = Finding

    def __init__(self, db: Session):
        super().__init__(db)

    @staticmethod
    def from_scan_data(scan_id: int, data: dict) -> Finding:
        """Build a Finding ORM instance from a scanner finding dict."""
        return Finding(
            scan_id=scan_id,
            vulnerability_name=data["vulnerability_name"],
            owasp_category=data["owasp_category"],
            cwe_id=data.get("cwe_id"),
            severity=data["severity"],
            confidence=data.get("confidence", 85),
            description=data["description"],
            evidence=data.get("evidence", ""),
            impact=data["impact"],
            remediation=data["remediation"],
            technical_impact=data.get("technical_impact"),
            business_impact=data.get("business_impact"),
            request_example=data.get("request_example"),
            response_example=data.get("response_example"),
            fix_recommendation=data.get("fix_recommendation"),
            references=data.get("references"),
            cvss_score=data.get("cvss_score"),
            cvss_vector=data.get("cvss_vector"),
            affected_endpoint=data.get("affected_endpoint"),
            affected_method=data.get("affected_method"),
            detection_reason=data.get("detection_reason", ""),
            false_positive_note=data.get("false_positive_note", ""),
        )

    def bulk_add_from_scan(self, scan_id: int, findings: Iterable[dict]) -> list[Finding]:
        objects = [self.from_scan_data(scan_id, f) for f in findings]
        self.add_all(objects)
        return objects

    def severity_counts_for_user(self, user_id: int) -> dict:
        stmt = (
            select(Finding.severity, func.count(Finding.id))
            .join(Scan, Finding.scan_id == Scan.id)
            .where(Scan.user_id == user_id, Scan.deleted_at.is_(None))
            .group_by(Finding.severity)
        )
        dist: dict[str, int] = {sev: count for sev, count in self.db.execute(stmt).all()}
        for sev in ("Critical", "High", "Medium", "Low", "Info"):
            dist.setdefault(sev, 0)
        return dist

    def _build_sort(self, params: FindingListParams) -> list:
        clauses = []
        for name, descending in params.sort_columns():
            column = FINDING_SORT_COLUMNS.get(name)
            if column is None:
                continue
            clauses.append(column.desc() if descending else column.asc())
        if not clauses:
            clauses.append(SEVERITY_RANK.asc())
        return clauses

    def paginate_for_scan(
        self, scan_id: int, params: FindingListParams
    ) -> tuple[list[Finding], int]:
        """Return ``(items, total)`` findings for a scan with optional severity
        filter, endpoint/vulnerability search, and whitelisted multi-column sort.

        Severity sorting uses the canonical ``Critical > High > Medium > Low > Info``
        order rather than alphabetical.
        """
        criteria = [Finding.scan_id == scan_id]
        if params.severity:
            criteria.append(Finding.severity == params.severity)
        if params.search:
            pattern = f"%{params.search}%"
            criteria.append(
                (Finding.vulnerability_name.ilike(pattern))
                | (Finding.affected_endpoint.ilike(pattern))
            )
        return self.paginate(
            *criteria,
            page=params.page,
            page_size=params.page_size,
            order_by=self._build_sort(params),
        )
