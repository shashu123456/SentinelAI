"""Backward-compatible re-exports from domain-specific schema modules.

All schemas have been split into:
- app.schemas.constants  – Shared sort/validation constants
- app.schemas.auth       – Authentication & user schemas
- app.schemas.scan       – Scan schemas and sort helpers
- app.schemas.finding    – Finding, AIAnalysis, VulnerabilityItem schemas
- app.schemas.analytics  – Analytics schemas
- app.schemas.dashboard  – Dashboard & report schemas

This file re-exports everything so existing ``from app.schemas.schemas import ...``
continues to work.  Prefer importing from the specific sub-module in new code.
"""

# Constants
from app.schemas.analytics import (
    AnalyticsResponse,
    OwaspCategoryItem,
    RiskScoreResponse,
    RiskTrendItem,
    ScanActivityItem,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    MessageResponse,
    ResetPasswordRequest,
    Role,
    RoleUpdateRequest,
    SessionInfo,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
    validate_password_strength,
)
from app.schemas.constants import (
    FINDING_SORT_FIELDS,
    RISK_LEVELS,
    SCAN_SORT_FIELDS,
    SCAN_STATUSES,
    SEVERITIES,
    SORT_DIRECTIONS,
    parse_sort_fields,
)
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    DashboardStats,
    ReportResponse,
)
from app.schemas.finding import (
    AIAnalysisResponse,
    FindingListParams,
    FindingResponse,
    VulnerabilityItem,
)

# Scan schemas
from app.schemas.scan import (
    ScanCreate,
    ScanDetailResponse,
    ScanListParams,
    ScanResponse,
    UnifiedScanResponse,
)

# The names above exist for backward compatibility, so they are part of this
# module's public API even though nothing inside it references them.
__all__ = [
    "FINDING_SORT_FIELDS",
    "RISK_LEVELS",
    "SCAN_SORT_FIELDS",
    "SCAN_STATUSES",
    "SEVERITIES",
    "SORT_DIRECTIONS",
    "parse_sort_fields",
    "AnalyticsResponse",
    "OwaspCategoryItem",
    "RiskScoreResponse",
    "RiskTrendItem",
    "ScanActivityItem",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "MessageResponse",
    "ResetPasswordRequest",
    "Role",
    "RoleUpdateRequest",
    "SessionInfo",
    "Token",
    "UserLogin",
    "UserRegister",
    "UserResponse",
    "validate_password_strength",
    "DashboardOverviewResponse",
    "DashboardStats",
    "ReportResponse",
    "AIAnalysisResponse",
    "FindingListParams",
    "FindingResponse",
    "VulnerabilityItem",
    "ScanCreate",
    "ScanDetailResponse",
    "ScanListParams",
    "ScanResponse",
    "UnifiedScanResponse",
]

# Resolve circular forward references
ScanDetailResponse.model_rebuild()
