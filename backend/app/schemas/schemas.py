from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional
from enum import Enum

from app.config import get_settings

_settings = get_settings()


class Role(str, Enum):
    user = "user"
    analyst = "analyst"
    viewer = "viewer"
    admin = "admin"


def validate_password_strength(password: str) -> str:
    if len(password) < _settings.PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {_settings.PASSWORD_MIN_LENGTH} characters")
    if _settings.PASSWORD_REQUIRE_UPPER and not any(c.isupper() for c in password):
        raise ValueError("Password must contain an uppercase letter")
    if _settings.PASSWORD_REQUIRE_NUMBER and not any(c.isdigit() for c in password):
        raise ValueError("Password must contain a number")
    if _settings.PASSWORD_REQUIRE_SPECIAL and not any(not c.isalnum() for c in password):
        raise ValueError("Password must contain a special character")
    return password


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: Role = Role.user
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _new_password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class MessageResponse(BaseModel):
    detail: str


class RoleUpdateRequest(BaseModel):
    role: Role


class SessionInfo(BaseModel):
    id: int
    created_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[str] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True



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
