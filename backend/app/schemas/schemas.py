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
from app.schemas.constants import (
    FINDING_SORT_FIELDS,
    RISK_LEVELS,
    SCAN_SORT_FIELDS,
    SCAN_STATUSES,
    SEVERITIES,
    SORT_DIRECTIONS,
    parse_sort_fields,
)

# Analytics schemas
from app.schemas.analytics import (
    AnalyticsResponse,
    OwaspCategoryItem,
    RiskScoreResponse,
    RiskTrendItem,
    ScanActivityItem,
)

# Auth schemas
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

# Dashboard schemas
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    DashboardStats,
    ReportResponse,
)

# Finding schemas
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

# Resolve circular forward references
ScanDetailResponse.model_rebuild()