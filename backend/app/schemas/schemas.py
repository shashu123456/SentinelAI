from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ScanCreate(BaseModel):
    api_name: str = Field(..., min_length=1, max_length=200)


class ScanResponse(BaseModel):
    id: int
    api_name: str
    api_title: Optional[str] = None
    api_version: Optional[str] = None
    total_endpoints: int
    total_vulnerabilities: int
    risk_score: int
    risk_level: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FindingResponse(BaseModel):
    id: int
    vulnerability_name: str
    owasp_category: str
    cwe_id: Optional[str] = None
    severity: str
    confidence: Optional[int] = 85
    description: str
    evidence: Optional[str] = None
    impact: str
    remediation: str
    affected_endpoint: Optional[str] = None
    affected_method: Optional[str] = None
    detection_reason: Optional[str] = None
    false_positive_note: Optional[str] = None

    class Config:
        from_attributes = True


class AIAnalysisResponse(BaseModel):
    executive_summary: Optional[str] = None
    technical_explanation: Optional[str] = None
    business_impact: Optional[str] = None
    attack_scenario: Optional[str] = None
    recommended_mitigation: Optional[str] = None

    class Config:
        from_attributes = True


class ScanDetailResponse(ScanResponse):
    findings: list[FindingResponse] = []
    ai_analysis: Optional[AIAnalysisResponse] = None


class VulnerabilityItem(BaseModel):
    vulnerability_name: str
    owasp_category: str
    cwe_id: Optional[str] = None
    severity: str
    confidence: Optional[int] = 85
    description: str
    evidence: Optional[str] = None
    impact: str
    remediation: str
    affected_endpoint: Optional[str] = None
    affected_method: Optional[str] = None
    detection_reason: Optional[str] = None
    false_positive_note: Optional[str] = None


class RiskScoreResponse(BaseModel):
    score: int
    level: str
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int


class DashboardStats(BaseModel):
    total_scans: int
    total_vulnerabilities: int
    average_risk_score: float
    recent_scans: list[ScanResponse]
    severity_distribution: dict


class ReportResponse(BaseModel):
    scan_id: int
    format: str
    download_url: str
