from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.config import get_settings

_settings = get_settings()

SCAN_STATUSES = ("pending", "running", "completed", "failed")
RISK_LEVELS = ("Critical", "High", "Medium", "Low", "Info")
SEVERITIES = ("Critical", "High", "Medium", "Low", "Info")
SCAN_SORT_FIELDS = ("created_at", "risk_score", "api_name", "total_vulnerabilities", "status")
FINDING_SORT_FIELDS = (
    "severity",
    "vulnerability_name",
    "confidence",
    "cvss_score",
    "affected_endpoint",
)
SORT_DIRECTIONS = ("asc", "desc")


def parse_sort_fields(sort_by: str, default_desc: bool = False) -> list[tuple[str, bool]]:
    """Parse a comma-separated sort spec into ``(field, descending)`` pairs.

    A leading ``-`` on a field marks it as descending (overriding the caller's
    default direction); unprefixed fields use ``default_desc``.
    """
    result: list[tuple[str, bool]] = []
    for part in sort_by.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("-"):
            result.append((part[1:], True))
        else:
            result.append((part, default_desc))
    return result


class Role(StrEnum):
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
    reset_token: str | None = None


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
    revoked_at: datetime | None = None
    replaced_by: str | None = None
    ip_address: str | None = None

    class Config:
        from_attributes = True


class ScanCreate(BaseModel):
    api_name: str = Field(..., min_length=1, max_length=200)


class ScanResponse(BaseModel):
    id: int
    api_name: str
    api_title: str | None = None
    api_version: str | None = None
    total_endpoints: int
    total_vulnerabilities: int
    risk_score: int
    risk_level: str
    status: str
    organization_id: int | None = None
    project_id: int | None = None
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class FindingResponse(BaseModel):
    id: int
    vulnerability_name: str
    owasp_category: str
    cwe_id: str | None = None
    severity: str
    confidence: int | None = 85
    description: str
    evidence: str | None = None
    impact: str
    remediation: str
    technical_impact: str | None = None
    business_impact: str | None = None
    request_example: str | None = None
    response_example: str | None = None
    fix_recommendation: str | None = None
    references: list | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    affected_endpoint: str | None = None
    affected_method: str | None = None
    detection_reason: str | None = None
    false_positive_note: str | None = None

    class Config:
        from_attributes = True


class AIAnalysisResponse(BaseModel):
    executive_summary: str | None = None
    technical_explanation: str | None = None
    business_impact: str | None = None
    attack_scenario: str | None = None
    recommended_mitigation: str | None = None

    class Config:
        from_attributes = True


class ScanDetailResponse(ScanResponse):
    findings: list[FindingResponse] = []
    ai_analysis: AIAnalysisResponse | None = None


class VulnerabilityItem(BaseModel):
    vulnerability_name: str
    owasp_category: str
    cwe_id: str | None = None
    severity: str
    confidence: int | None = 85
    description: str
    evidence: str | None = None
    impact: str
    remediation: str
    technical_impact: str | None = None
    business_impact: str | None = None
    request_example: str | None = None
    response_example: str | None = None
    fix_recommendation: str | None = None
    references: list | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    affected_endpoint: str | None = None
    affected_method: str | None = None
    detection_reason: str | None = None
    false_positive_note: str | None = None


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


class ScanListParams(BaseModel):
    """Query parameters for paginated, filtered, sorted scan listing."""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    status: str | None = None
    risk_level: str | None = None
    severity: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    search: str | None = Field(None, max_length=100)
    sort_by: str = Field("created_at", max_length=100)
    order: Literal["asc", "desc"] = "desc"

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in SCAN_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(SCAN_STATUSES)}")
        return v

    @field_validator("risk_level")
    @classmethod
    def _validate_risk_level(cls, v: str | None) -> str | None:
        if v is not None and v not in RISK_LEVELS:
            raise ValueError(f"risk_level must be one of: {', '.join(RISK_LEVELS)}")
        return v

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, v: str | None) -> str | None:
        if v is not None and v not in SEVERITIES:
            raise ValueError(f"severity must be one of: {', '.join(SEVERITIES)}")
        return v

    @field_validator("sort_by")
    @classmethod
    def _validate_sort_by(cls, v: str) -> str:
        fields = [name for name, _ in parse_sort_fields(v)]
        if not fields:
            raise ValueError("sort_by must name at least one field")
        invalid = [f for f in fields if f not in SCAN_SORT_FIELDS]
        if invalid:
            raise ValueError(f"invalid sort field(s): {', '.join(invalid)}")
        return v

    @model_validator(mode="after")
    def _check_date_range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be earlier than or equal to date_to")
        return self

    def sort_columns(self) -> list[tuple[str, bool]]:
        return parse_sort_fields(self.sort_by, self.order == "desc")


class FindingListParams(BaseModel):
    """Query parameters for paginated, filtered, sorted finding listing."""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    severity: str | None = None
    search: str | None = Field(None, max_length=100)
    sort_by: str = Field("severity", max_length=100)
    order: Literal["asc", "desc"] = "asc"

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, v: str | None) -> str | None:
        if v is not None and v not in SEVERITIES:
            raise ValueError(f"severity must be one of: {', '.join(SEVERITIES)}")
        return v

    @field_validator("sort_by")
    @classmethod
    def _validate_sort_by(cls, v: str) -> str:
        fields = [name for name, _ in parse_sort_fields(v)]
        if not fields:
            raise ValueError("sort_by must name at least one field")
        invalid = [f for f in fields if f not in FINDING_SORT_FIELDS]
        if invalid:
            raise ValueError(f"invalid sort field(s): {', '.join(invalid)}")
        return v

    def sort_columns(self) -> list[tuple[str, bool]]:
        return parse_sort_fields(self.sort_by, self.order == "desc")
