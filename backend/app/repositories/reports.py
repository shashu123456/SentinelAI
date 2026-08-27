from sqlalchemy.orm import Session

from app.models.models import Report, Scan
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    model = Report

    def __init__(self, db: Session):
        super().__init__(db)

    def get_for_scan(self, scan_id: int, format: str) -> Report | None:
        return self.first(Report.scan_id == scan_id, Report.format == format)

    def create(self, scan: Scan, format: str, content: bytes) -> Report:
        record = Report(scan_id=scan.id, format=format, content=content)
        self.add(record)
        return record
