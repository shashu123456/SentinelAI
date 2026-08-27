"""Analytics schemas."""

from pydantic import BaseModel


class RiskScoreResponse(BaseModel):
    score: int
    level: str
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int


class ScanActivityItem(BaseModel):
    date: str
    scans: int


class RiskTrendItem(BaseModel):
    date: str
    score: int


class OwaspCategoryItem(BaseModel):
    category: str
    count: int


class AnalyticsResponse(BaseModel):
    scan_activity: list[ScanActivityItem]
    risk_trend: list[RiskTrendItem]
    owasp_distribution: list[OwaspCategoryItem]
