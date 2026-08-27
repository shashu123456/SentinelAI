"""Schema packages — import all sub-modules and resolve circular forward refs."""

from app.schemas.constants import *  # noqa: F401,F403
from app.schemas.auth import *  # noqa: F401,F403
from app.schemas.finding import *  # noqa: F401,F403
from app.schemas.scan import *  # noqa: F401,F403
from app.schemas.analytics import *  # noqa: F401,F403
from app.schemas.dashboard import *  # noqa: F401,F403

# Resolve circular forward references between scan.py and finding.py.
# scan.py uses TYPE_CHECKING for FindingResponse/AIAnalysisResponse;
# model_rebuild() forces Pydantic to evaluate the forward annotations now
# that all types are loaded.
from app.schemas.scan import ScanDetailResponse  # noqa: E402
ScanDetailResponse.model_rebuild()
