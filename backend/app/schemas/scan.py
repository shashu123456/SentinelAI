"""Scan-related schemas."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.constants import (
    FINDING_SORT_FIELDS,
    RISK_LEVELS,
    SCAN_SORT_FIELDS,
    SCAN_STATUSES,
    SEVERITIES,
    parse_sort_fields,
)

if TYPE_CHECKING:
    from app.schemas.finding import AIAnalysisResponse, FindingResponse


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

    model_config = {"from_attributes": True}


class ScanDetailResponse(ScanResponse):
    findings: list[FindingResponse] = []
    ai_analysis: AIAnalysisResponse | None = None
    transition_history: list[dict] = []


# Resolve forward references after finding.py has been imported
def _rebuild_scan_detail():
    """Called from schemas/__init__.py to resolve circular forward refs."""
    ScanDetailResponse.model_rebuild()


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
