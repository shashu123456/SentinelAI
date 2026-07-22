"""API routes for SAST scanning, dependency scanning, and security copilot."""

import os
import tempfile
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import User
from app.database.database import get_db
from app.utils.security import get_current_user
from app.utils.logger import logger
from app.core.sast_engine import run_sast_scan
from app.core.dep_scanner import run_dep_scan
from app.core.copilot import SecurityCopilot

router = APIRouter(prefix="/api/security", tags=["Security Intelligence"])


# =============================================================================
# SAST Schemas
# =============================================================================

class SASTFindingResponse(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    cwe_id: str
    owasp_category: Optional[str] = None
    language: str
    file_path: str
    line_number: int
    line_content: str
    description: str
    remediation: str
    confidence: float
    tags: list[str] = []


class SASTScanSummary(BaseModel):
    total_findings: int
    severity_counts: dict
    files_scanned: int
    lines_scanned: int
    files_with_findings: int
    languages_detected: list[str]


class SASTScanResponse(BaseModel):
    target_path: str
    summary: SASTScanSummary
    findings: list[SASTFindingResponse]
    errors: list[str] = []


# =============================================================================
# Dependency Scan Schemas
# =============================================================================

class DepFindingResponse(BaseModel):
    package: str
    installed_version: str
    severity: str
    cvss_score: float
    cve_id: str
    cwe_id: str
    description: str
    fixed_in: str
    ecosystem: str
    file_path: str
    url: str = ""
    confidence: float = 1.0


class DependencyInfoResponse(BaseModel):
    name: str
    version: str
    ecosystem: str
    file: str
    is_dev: bool = False


class DepScanSummary(BaseModel):
    total_dependencies: int
    total_vulnerabilities: int
    severity_counts: dict
    files_scanned: int
    ecosystems_detected: list[str]


class DepScanResponse(BaseModel):
    target_path: str
    summary: DepScanSummary
    findings: list[DepFindingResponse]
    dependencies: list[DependencyInfoResponse]
    errors: list[str] = []


# =============================================================================
# Copilot Schemas
# =============================================================================

class CopilotChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    scan_id: Optional[int] = None


class CopilotChatResponse(BaseModel):
    response: str
    intent: str
    tool_used: str
    has_context: bool


class CopilotSidebarResponse(BaseModel):
    risk_score: int
    risk_level: str
    total_scans: int
    total_findings: int
    severity_counts: dict
    latest_scan: Optional[dict] = None
    critical_count: int
    recent_findings: list[dict]
    scan_history: list[dict]


# =============================================================================
# SAST Endpoints
# =============================================================================

@router.post("/sast/scan", response_model=SASTScanResponse)
async def scan_source_code(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a source code file or zip for SAST analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    valid_extensions = (".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".zip", ".tar", ".gz")
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(valid_extensions)}"
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max: 10MB")

    tmp_dir = tempfile.mkdtemp(prefix="sentinelai_sast_")
    try:
        tmp_path = os.path.join(tmp_dir, file.filename)
        with open(tmp_path, "wb") as f:
            f.write(content)

        logger.info(f"SAST scan started by user {current_user.username}: {file.filename}")
        result = run_sast_scan(tmp_path)

        return SASTScanResponse(
            target_path=file.filename,
            summary=SASTScanSummary(
                total_findings=len(result.findings),
                severity_counts=result.summary.get("severity_counts", {}),
                files_scanned=result.total_files_scanned,
                lines_scanned=result.total_lines_scanned,
                files_with_findings=result.files_with_findings,
                languages_detected=result.languages_detected,
            ),
            findings=[SASTFindingResponse(**f.to_dict()) for f in result.findings],
            errors=result.errors,
        )
    except Exception as e:
        logger.error(f"SAST scan failed: {e}")
        raise HTTPException(status_code=500, detail="SAST scan failed")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/sast/scan/text", response_model=SASTScanResponse)
async def scan_source_text(
    code: str = Form(...),
    filename: str = Form("code.py"),
    current_user: User = Depends(get_current_user),
):
    """Scan source code provided as text."""
    if not code.strip():
        raise HTTPException(status_code=400, detail="No code provided")

    tmp_dir = tempfile.mkdtemp(prefix="sentinelai_sast_")
    try:
        tmp_path = os.path.join(tmp_dir, filename)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(code)

        result = run_sast_scan(tmp_path)

        return SASTScanResponse(
            target_path=filename,
            summary=SASTScanSummary(
                total_findings=len(result.findings),
                severity_counts=result.summary.get("severity_counts", {}),
                files_scanned=result.total_files_scanned,
                lines_scanned=result.total_lines_scanned,
                files_with_findings=result.files_with_findings,
                languages_detected=result.languages_detected,
            ),
            findings=[SASTFindingResponse(**f.to_dict()) for f in result.findings],
            errors=result.errors,
        )
    except Exception as e:
        logger.error(f"SAST text scan failed: {e}")
        raise HTTPException(status_code=500, detail="SAST scan failed")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# =============================================================================
# Dependency Scan Endpoints
# =============================================================================

@router.post("/deps/scan", response_model=DepScanResponse)
async def scan_dependencies(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a dependency manifest file for security analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    valid_filenames = ("requirements.txt", "package.json", "pom.xml",
                       "requirements.in", "Pipfile")
    if file.filename not in valid_filenames:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file. Allowed: {', '.join(valid_filenames)}"
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max: 5MB")

    tmp_dir = tempfile.mkdtemp(prefix="sentinelai_dep_")
    try:
        tmp_path = os.path.join(tmp_dir, file.filename)
        with open(tmp_path, "wb") as f:
            f.write(content)

        logger.info(f"Dependency scan started by user {current_user.username}: {file.filename}")
        result = run_dep_scan(tmp_path)

        return DepScanResponse(
            target_path=file.filename,
            summary=DepScanSummary(
                total_dependencies=result.total_dependencies,
                total_vulnerabilities=len(result.findings),
                severity_counts=result.summary.get("severity_counts", {}),
                files_scanned=result.total_files_scanned,
                ecosystems_detected=result.ecosystems_detected,
            ),
            findings=[DepFindingResponse(**f.to_dict()) for f in result.findings],
            dependencies=[
                DependencyInfoResponse(
                    name=d.name, version=d.version,
                    ecosystem=d.ecosystem, file=d.file_path, is_dev=d.is_dev,
                ) for d in result.dependencies
            ],
            errors=result.errors,
        )
    except Exception as e:
        logger.error(f"Dependency scan failed: {e}")
        raise HTTPException(status_code=500, detail="Dependency scan failed")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# =============================================================================
# Security Copilot Endpoints
# =============================================================================

_copilot_sessions: dict[int, SecurityCopilot] = {}


def _get_or_create_copilot(user_id: int, db: Session) -> SecurityCopilot:
    """Get or create a copilot instance for the user with database access."""
    if user_id not in _copilot_sessions:
        try:
            from app.config import get_settings
            settings = get_settings()
        except Exception:
            settings = None
        _copilot_sessions[user_id] = SecurityCopilot(settings=settings, db=db, user_id=user_id)
    else:
        _copilot_sessions[user_id].db = db
        _copilot_sessions[user_id].user_id = user_id
        _copilot_sessions[user_id].agent.db = db
        _copilot_sessions[user_id].agent.user_id = user_id
        _copilot_sessions[user_id].agent.state.db = db
    return _copilot_sessions[user_id]


@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    request: CopilotChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat with the AI Security Agent.

    The agent automatically loads your scan data from the database
    and provides contextual responses grounded in your actual findings.
    """
    copilot = _get_or_create_copilot(current_user.id, db)
    result = copilot.chat(request.message, scan_id=request.scan_id)

    return CopilotChatResponse(
        response=result["response"],
        intent=result["intent"],
        tool_used=result.get("tool_used", ""),
        has_context=result.get("has_context", False),
    )


@router.get("/copilot/sidebar", response_model=CopilotSidebarResponse)
async def get_copilot_sidebar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get sidebar data for the copilot UI.

    Returns current risk score, findings summary, and recent scan history
    for the sidebar panel.
    """
    copilot = _get_or_create_copilot(current_user.id, db)
    sidebar = copilot.get_sidebar()

    return CopilotSidebarResponse(
        risk_score=sidebar.get("risk_score", 0),
        risk_level=sidebar.get("risk_level", "Unknown"),
        total_scans=sidebar.get("total_scans", 0),
        total_findings=sidebar.get("total_findings", 0),
        severity_counts=sidebar.get("severity_counts", {}),
        latest_scan=sidebar.get("latest_scan"),
        critical_count=sidebar.get("critical_count", 0),
        recent_findings=sidebar.get("recent_findings", []),
        scan_history=sidebar.get("scan_history", []),
    )


@router.post("/copilot/context")
async def load_copilot_context(
    scan_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Load a specific scan's context into the copilot."""
    copilot = _get_or_create_copilot(current_user.id, db)
    return {"status": "loaded", "context": copilot.get_context_summary()}


@router.post("/copilot/clear")
async def clear_copilot_context(
    current_user: User = Depends(get_current_user),
):
    """Clear the copilot's conversation history."""
    if current_user.id in _copilot_sessions:
        _copilot_sessions[current_user.id].clear()
    return {"status": "cleared"}


@router.get("/copilot/commands")
async def get_copilot_commands():
    """List what the copilot can do."""
    return {
        "capabilities": [
            {
                "category": "Natural Conversation",
                "description": "I understand natural language. Just talk to me.",
                "examples": ["hello", "what's my security status", "how are we doing"],
            },
            {
                "category": "Vulnerability Analysis",
                "description": "Analyze and explain security findings.",
                "examples": ["What is my highest risk issue?", "Explain this vulnerability", "Why is this critical?"],
            },
            {
                "category": "Remediation",
                "description": "Get specific fix guidance.",
                "examples": ["How do I fix this?", "Generate remediation plan", "What should I fix first?"],
            },
            {
                "category": "Executive Reporting",
                "description": "Generate leadership-ready reports.",
                "examples": ["Write executive summary", "What's the bottom line?"],
            },
            {
                "category": "Attack Analysis",
                "description": "Understand attack vectors and paths.",
                "examples": ["How would an attacker exploit this?", "What data is at risk?"],
            },
            {
                "category": "Compliance",
                "description": "Map findings to standards.",
                "examples": ["Map to OWASP Top 10", "CWE analysis"],
            },
        ]
    }
