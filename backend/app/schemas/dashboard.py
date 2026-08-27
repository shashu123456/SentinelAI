"""Dashboard and report schemas."""

from pydantic import BaseModel

from app.schemas.scan import ScanResponse


class DashboardStats(BaseModel):
    total_scans: int
    total_vulnerabilities: int
    average_risk_score: float
    recent_scans: list[ScanResponse]
    severity_distribution: dict


class DashboardOverviewResponse(BaseModel):
    total_scans: int
    completed_scans: int
    total_vulnerabilities: int
    average_risk_score: float
    severity_distribution: dict[str, int]
    recent_scans: list[ScanResponse]


class ReportResponse(BaseModel):
    scan_id: int
    format: str
    download_url: str
