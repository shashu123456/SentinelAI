"""Finding-related schemas."""

from pydantic import BaseModel, Field, field_validator

from app.schemas.constants import FINDING_SORT_FIELDS, SEVERITIES, parse_sort_fields


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

    model_config = {"from_attributes": True}


class AIAnalysisResponse(BaseModel):
    executive_summary: str | None = None
    technical_explanation: str | None = None
    business_impact: str | None = None
    attack_scenario: str | None = None
    recommended_mitigation: str | None = None

    model_config = {"from_attributes": True}


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


class FindingListParams(BaseModel):
    """Query parameters for paginated, filtered, sorted finding listing."""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    severity: str | None = None
    search: str | None = Field(None, max_length=100)
    sort_by: str = Field("severity", max_length=100)
    order: str = "asc"

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
