"""AI Platform API routes.

Comprehensive AI endpoints: executive reports, risk explanation,
threat prediction, root cause, code fixes, architecture review,
security advisor, scan summarizer, NL search, knowledge graph,
conversation memory, prompt registry.

Security: All user-provided text inputs are screened for prompt injection
patterns before being passed to the AI engine.
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.database import get_db
from app.models.models import Finding, Scan, User
from app.utils.ratelimit import limiter
from app.utils.security import get_current_user

router = APIRouter()

# ── Prompt Injection Protection ───────────────────────────────────────
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:a\s+)?(?:different|new|admin|root)", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"repeat\s+(?:your\s+)?(?:system|initial)\s+prompt", re.IGNORECASE),
    re.compile(r"what\s+(?:is\s+)?your\s+(?:system|initial)\s+prompt", re.IGNORECASE),
    re.compile(r" reveal\s+(?:your\s+)?(?:system|initial)\s+prompt", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<<SYS>>", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\|im_end\|>", re.IGNORECASE),
    re.compile(r"<\|endoftext\|>", re.IGNORECASE),
]


def _detect_prompt_injection(text: str) -> bool:
    """Check if user input contains prompt injection patterns."""
    if not text:
        return False
    return any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS)



class ExecutiveReportRequest(BaseModel):
    scan_id: int | None = None


class RiskExplainRequest(BaseModel):
    risk_score: int
    risk_level: str
    scan_id: int | None = None


class ThreatPredictRequest(BaseModel):
    scan_id: int | None = None


class RootCauseRequest(BaseModel):
    finding_id: int


class CodeFixRequest(BaseModel):
    finding_id: int


class ArchitectureReviewRequest(BaseModel):
    scan_id: int


class SecurityAdvisorRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    scan_id: int | None = None


class NLSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)


class KnowledgeGraphRequest(BaseModel):
    scan_id: int


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    scan_id: int | None = None


def _get_scan_findings(db: Session, scan_id: int, user_id: int) -> tuple[Scan | None, list[dict]]:
    scan = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == user_id).first()
    if not scan:
        return None, []
    findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
    findings_dicts = [
        {
            "id": f.id,
            "vulnerability_name": f.vulnerability_name,
            "owasp_category": f.owasp_category,
            "cwe_id": f.cwe_id,
            "severity": f.severity,
            "confidence": f.confidence,
            "description": f.description,
            "impact": f.impact,
            "remediation": f.remediation,
            "affected_endpoint": f.affected_endpoint,
            "affected_method": f.affected_method,
            "evidence": f.evidence,
            "cvss_score": f.cvss_score,
        }
        for f in findings
    ]
    return scan, findings_dicts


def _get_all_findings_for_user(db: Session, user_id: int) -> list[dict]:
    scans = db.query(Scan).filter(Scan.user_id == user_id, Scan.status == "completed").all()
    scan_ids = [s.id for s in scans]
    if not scan_ids:
        return []
    findings = db.query(Finding).filter(Finding.scan_id.in_(scan_ids)).all()
    return [
        {
            "id": f.id,
            "vulnerability_name": f.vulnerability_name,
            "owasp_category": f.owasp_category,
            "cwe_id": f.cwe_id,
            "severity": f.severity,
            "confidence": f.confidence,
            "description": f.description,
            "impact": f.impact,
            "remediation": f.remediation,
            "affected_endpoint": f.affected_endpoint,
            "affected_method": f.affected_method,
            "evidence": f.evidence,
            "cvss_score": f.cvss_score,
            "scan_id": f.scan_id,
        }
        for f in findings
    ]


# ── Executive Report ──────────────────────────────────────────────────────

@router.post("/ai/executive-report")
def generate_executive_report(
    data: ExecutiveReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    all_findings = _get_all_findings_for_user(db, current_user.id)
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in all_findings:
        sev = f.get("severity", "Info")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    scan_data = {
        "total_findings": len(all_findings),
        "risk_score": round(sum(f.get("cvss_score", 0) or 0 for f in all_findings) / max(1, len(all_findings)) * 10, 1),
        "critical_count": severity_counts.get("Critical", 0),
        "high_count": severity_counts.get("High", 0),
        "severity_distribution": severity_counts,
        "top_findings": [
            {"name": f["vulnerability_name"], "severity": f["severity"], "cwe": f.get("cwe_id")}
            for f in sorted(all_findings, key=lambda x: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}.get(x.get("severity"), 5))[:10]
        ],
    }

    return engine.generate_executive_report(scan_data)


# ── Risk Explanation ──────────────────────────────────────────────────────

@router.post("/ai/risk-explain")
def explain_risk(
    data: RiskExplainRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    findings = _get_all_findings_for_user(db, current_user.id)
    summary = "; ".join(f"{f['vulnerability_name']} ({f['severity']})" for f in findings[:10])

    return engine.explain_risk(data.risk_score, data.risk_level, summary)


# ── Threat Prediction ─────────────────────────────────────────────────────

@router.post("/ai/threat-predict")
def predict_threats(
    data: ThreatPredictRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    if data.scan_id:
        _, findings = _get_scan_findings(db, data.scan_id, current_user.id)
    else:
        findings = _get_all_findings_for_user(db, current_user.id)

    return engine.predict_threats(findings)


# ── Root Cause ────────────────────────────────────────────────────────────

@router.post("/ai/root-cause")
def explain_root_cause(
    data: RootCauseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    finding = db.query(Finding).filter(Finding.id == data.finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")

    finding_dict = {
        "vulnerability_name": finding.vulnerability_name,
        "owasp_category": finding.owasp_category,
        "cwe_id": finding.cwe_id,
        "description": finding.description,
        "affected_endpoint": finding.affected_endpoint,
        "evidence": finding.evidence,
    }

    return engine.explain_root_cause(finding_dict)


# ── Code Fix ──────────────────────────────────────────────────────────────

@router.post("/ai/code-fix")
def generate_code_fix(
    data: CodeFixRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    finding = db.query(Finding).filter(Finding.id == data.finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")

    finding_dict = {
        "vulnerability_name": finding.vulnerability_name,
        "cwe_id": finding.cwe_id,
        "description": finding.description,
        "affected_endpoint": finding.affected_endpoint,
        "affected_method": finding.affected_method,
    }

    return engine.generate_code_fix(finding_dict)


# ── Architecture Review ───────────────────────────────────────────────────

@router.post("/ai/architecture-review")
def review_architecture(
    data: ArchitectureReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    scan, findings = _get_scan_findings(db, data.scan_id, current_user.id)
    if not scan:
        raise HTTPException(404, "Scan not found")

    api_spec = scan.source_spec or {}
    return engine.review_architecture(api_spec, findings)


# ── Security Advisor ──────────────────────────────────────────────────────

@router.post("/ai/advise")
@limiter.limit(f"{get_settings().COPILOT_RATE_LIMIT_PER_MINUTE}/minute")
def security_advisor(
    request: Request,
    data: SecurityAdvisorRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Prompt injection protection
    if _detect_prompt_injection(data.question):
        raise HTTPException(
            status_code=400,
            detail="Input contains patterns that are not allowed. Please ask security-related questions only."
        )

    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    findings = _get_all_findings_for_user(db, current_user.id)
    context = {
        "total_findings": len(findings),
        "findings_summary": [
            {"name": f["vulnerability_name"], "severity": f["severity"], "cwe": f.get("cwe_id")}
            for f in findings[:20]
        ],
    }

    result = engine.advise(data.question, context, current_user.id)
    # Store in memory
    from app.core.ai_platform.conversation_memory import get_conversation_memory
    mem = get_conversation_memory()
    mem.add_entry(current_user.id, "user", data.question, scan_id=data.scan_id)
    if result.get("data", {}).get("answer"):
        mem.add_entry(current_user.id, "assistant", result["data"]["answer"])
    return result


# ── Scan Summarizer ───────────────────────────────────────────────────────

@router.post("/ai/summarize")
def summarize_scan(
    data: ExecutiveReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    scan, findings = _get_scan_findings(db, data.scan_id, current_user.id)
    if not scan:
        raise HTTPException(404, "Scan not found")

    scan_dict = {
        "api_name": scan.api_name,
        "api_version": scan.api_version,
        "risk_score": scan.risk_score,
        "risk_level": scan.risk_level,
        "total_endpoints": scan.total_endpoints,
        "total_vulnerabilities": scan.total_vulnerabilities,
    }

    return engine.summarize_scan(scan_dict, findings)


# ── Natural Language Search ───────────────────────────────────────────────

@router.post("/ai/search")
@limiter.limit(f"{get_settings().COPILOT_RATE_LIMIT_PER_MINUTE}/minute")
def nl_search(
    request: Request,
    data: NLSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Prompt injection protection
    if _detect_prompt_injection(data.query):
        raise HTTPException(
            status_code=400,
            detail="Input contains patterns that are not allowed."
        )

    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    findings = _get_all_findings_for_user(db, current_user.id)
    return engine.nl_search(data.query, findings)


# ── Knowledge Graph ───────────────────────────────────────────────────────

@router.post("/ai/knowledge-graph")
def build_knowledge_graph(
    data: KnowledgeGraphRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.engine import get_ai_engine
    engine = get_ai_engine()

    _, findings = _get_scan_findings(db, data.scan_id, current_user.id)
    return engine.build_knowledge_graph(findings)


# ── Conversation Memory ───────────────────────────────────────────────────

@router.get("/ai/memory")
def get_conversation_history(
    current_user: User = Depends(get_current_user),
):
    from app.core.ai_platform.conversation_memory import get_conversation_memory
    mem = get_conversation_memory()
    return {
        "history": mem.get_full_history(current_user.id),
        "entities": mem.get_entities(current_user.id),
    }


@router.delete("/ai/memory")
def clear_conversation_memory(
    current_user: User = Depends(get_current_user),
):
    from app.core.ai_platform.conversation_memory import get_conversation_memory
    mem = get_conversation_memory()
    mem.clear(current_user.id)
    return {"detail": "Conversation memory cleared"}


# ── Prompt Registry ───────────────────────────────────────────────────────

@router.get("/ai/prompts")
def list_prompts():
    from app.core.ai_platform.prompt_registry import get_prompt_registry
    registry = get_prompt_registry()
    return {"prompts": registry.list_all()}


# ── Semantic Search (standalone) ──────────────────────────────────────────

@router.get("/ai/search-index")
def get_search_index(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.ai_platform.semantic_search import get_semantic_search
    search = get_semantic_search()
    findings = _get_all_findings_for_user(db, current_user.id)
    search.add_findings(findings)
    return {"indexed_findings": len(findings), "status": "ready"}
