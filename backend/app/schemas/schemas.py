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
from app.schemas.constants import (  # noqa: F401
    FINDING_SORT_FIELDS,
    RISK_LEVELS,
    SCAN_SORT_FIELDS,
    SCAN_STATUSES,
    SEVERITIES,
    SORT_DIRECTIONS,
    parse_sort_fields,
)

# Auth schemas
from app.schemas.auth import (  # noqa: F401
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

# Scan schemas
from app.schemas.scan import (  # noqa: F401
    ScanCreate,
    ScanDetailResponse,
    ScanListParams,
    ScanResponse,
)

# Finding schemas
from app.schemas.finding import (  # noqa: F401
    AIAnalysisResponse,
    FindingListParams,
    FindingResponse,
    VulnerabilityItem,
)

# Analytics schemas
from app.schemas.analytics import (  # noqa: F401
    AnalyticsResponse,
    OwaspCategoryItem,
    RiskScoreResponse,
    RiskTrendItem,
    ScanActivityItem,
)

# Dashboard schemas
from app.schemas.dashboard import (  # noqa: F401
    DashboardOverviewResponse,
    DashboardStats,
    ReportResponse,
)

# Resolve circular forward references
ScanDetailResponse.model_rebuild()
