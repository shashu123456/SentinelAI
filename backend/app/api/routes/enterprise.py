"""Enterprise API routes.

Scheduled scans, templates, policies, webhooks, compliance center,
export center, version comparison, historical analytics, executive reports.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import User
from app.services import enterprise_service as es
from app.utils.rbac import OrgContext, require_org_role
from app.utils.security import get_current_user

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────

class ScheduledScanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    frequency: str = "weekly"
    cron_expression: str | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    hour: int = 2
    minute: int = 0
    timezone: str = "UTC"
    scan_type: str = "api"
    scan_config: dict | None = None
    project_id: int | None = None
    template_id: int | None = None


class ScheduledScanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    frequency: str | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    hour: int | None = None
    minute: int | None = None
    scan_type: str | None = None
    scan_config: dict | None = None
    is_active: bool | None = None


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    scan_type: str
    config: dict = {}
    compliance_frameworks: list[str] | None = None
    is_default: bool = False
    is_shared: bool = False


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    policy_type: str = "finding_gate"
    rules: dict
    severity: str = "high"
    is_active: bool = True
    enforce_on_scans: bool = False
    notify_on_violation: bool = True


class WebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    webhook_type: str
    url: str | None = None
    config: dict | None = None
    events: list[str] = []
    secret: str | None = None


class ExportRequest(BaseModel):
    export_type: str
    format: str
    scope: dict = {}


class CompareRequest(BaseModel):
    scan_id_1: int
    scan_id_2: int


# ── Scheduled Scans ──────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/scheduled-scans")
def list_scheduled_scans(
    org_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    items, total = es.list_scheduled_scans(db, org_id, page, page_size)
    return {
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "frequency": s.frequency,
                "scan_type": s.scan_type,
                "is_active": s.is_active,
                "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
                "run_count": s.run_count,
                "failure_count": s.failure_count,
                "created_at": s.created_at.isoformat(),
            }
            for s in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/orgs/{org_id}/scheduled-scans", status_code=201)
def create_scheduled_scan(
    org_id: int,
    data: ScheduledScanCreate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    scan = es.create_scheduled_scan(db, org_id, org_ctx.user_id, data.model_dump())
    return {"id": scan.id, "name": scan.name, "next_run_at": scan.next_run_at.isoformat() if scan.next_run_at else None}


@router.put("/orgs/{org_id}/scheduled-scans/{scan_id}")
def update_scheduled_scan(
    org_id: int,
    scan_id: int,
    data: ScheduledScanUpdate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    scan = es.update_scheduled_scan(db, scan_id, org_id, data.model_dump(exclude_unset=True))
    if not scan:
        raise HTTPException(404, "Scheduled scan not found")
    return {"id": scan.id, "name": scan.name, "is_active": scan.is_active}


@router.delete("/orgs/{org_id}/scheduled-scans/{scan_id}")
def delete_scheduled_scan(
    org_id: int,
    scan_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    if not es.delete_scheduled_scan(db, scan_id, org_id):
        raise HTTPException(404, "Scheduled scan not found")
    return {"detail": "Scheduled scan deleted"}


# ── Scan Templates ───────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/templates")
def list_templates(
    org_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    items, total = es.list_templates(db, org_id, page, page_size)
    return {
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "scan_type": t.scan_type,
                "config": t.config,
                "compliance_frameworks": t.compliance_frameworks,
                "is_default": t.is_default,
                "use_count": t.use_count,
                "created_at": t.created_at.isoformat(),
            }
            for t in items
        ],
        "total": total,
    }


@router.post("/orgs/{org_id}/templates", status_code=201)
def create_template(
    org_id: int,
    data: TemplateCreate,
    org_ctx: OrgContext = Depends(require_org_role("security_engineer")),
    db: Session = Depends(get_db),
):
    t = es.create_template(db, org_id, org_ctx.user_id, data.model_dump())
    return {"id": t.id, "name": t.name, "scan_type": t.scan_type}


@router.put("/orgs/{org_id}/templates/{template_id}")
def update_template(
    org_id: int,
    template_id: int,
    data: TemplateCreate,
    org_ctx: OrgContext = Depends(require_org_role("security_engineer")),
    db: Session = Depends(get_db),
):
    t = es.update_template(db, template_id, org_id, data.model_dump(exclude_unset=True))
    if not t:
        raise HTTPException(404, "Template not found")
    return {"id": t.id, "name": t.name}


@router.delete("/orgs/{org_id}/templates/{template_id}")
def delete_template(
    org_id: int,
    template_id: int,
    org_ctx: OrgContext = Depends(require_org_role("security_engineer")),
    db: Session = Depends(get_db),
):
    if not es.delete_template(db, template_id, org_id):
        raise HTTPException(404, "Template not found")
    return {"detail": "Template deleted"}


# ── Policies ─────────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/policies")
def list_policies(
    org_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    items, total = es.list_policies(db, org_id, page, page_size)
    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "policy_type": p.policy_type,
                "rules": p.rules,
                "severity": p.severity,
                "is_active": p.is_active,
                "enforce_on_scans": p.enforce_on_scans,
                "evaluation_count": p.evaluation_count,
                "violation_count": p.violation_count,
                "last_evaluated_at": p.last_evaluated_at.isoformat() if p.last_evaluated_at else None,
                "created_at": p.created_at.isoformat(),
            }
            for p in items
        ],
        "total": total,
    }


@router.post("/orgs/{org_id}/policies", status_code=201)
def create_policy(
    org_id: int,
    data: PolicyCreate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    p = es.create_policy(db, org_id, org_ctx.user_id, data.model_dump())
    return {"id": p.id, "name": p.name, "policy_type": p.policy_type}


@router.put("/orgs/{org_id}/policies/{policy_id}")
def update_policy(
    org_id: int,
    policy_id: int,
    data: PolicyCreate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    p = es.update_policy(db, policy_id, org_id, data.model_dump(exclude_unset=True))
    if not p:
        raise HTTPException(404, "Policy not found")
    return {"id": p.id, "name": p.name}


@router.delete("/orgs/{org_id}/policies/{policy_id}")
def delete_policy(
    org_id: int,
    policy_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    if not es.delete_policy(db, policy_id, org_id):
        raise HTTPException(404, "Policy not found")
    return {"detail": "Policy deleted"}


# ── Webhooks ─────────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/webhooks")
def list_webhooks(
    org_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    items, total = es.list_webhooks(db, org_id, page, page_size)
    return {
        "items": [
            {
                "id": w.id,
                "name": w.name,
                "webhook_type": w.webhook_type,
                "url": w.url[:50] + "..." if w.url and len(w.url) > 50 else w.url,
                "events": w.events,
                "is_active": w.is_active,
                "delivery_count": w.delivery_count,
                "failure_count": w.failure_count,
                "last_triggered_at": w.last_triggered_at.isoformat() if w.last_triggered_at else None,
                "created_at": w.created_at.isoformat(),
            }
            for w in items
        ],
        "total": total,
    }


@router.post("/orgs/{org_id}/webhooks", status_code=201)
def create_webhook(
    org_id: int,
    data: WebhookCreate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    w = es.create_webhook(db, org_id, org_ctx.user_id, data.model_dump())
    return {"id": w.id, "name": w.name, "webhook_type": w.webhook_type}


@router.put("/orgs/{org_id}/webhooks/{webhook_id}")
def update_webhook(
    org_id: int,
    webhook_id: int,
    data: WebhookCreate,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    w = es.update_webhook(db, webhook_id, org_id, data.model_dump(exclude_unset=True))
    if not w:
        raise HTTPException(404, "Webhook not found")
    return {"id": w.id, "name": w.name}


@router.delete("/orgs/{org_id}/webhooks/{webhook_id}")
def delete_webhook(
    org_id: int,
    webhook_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    if not es.delete_webhook(db, webhook_id, org_id):
        raise HTTPException(404, "Webhook not found")
    return {"detail": "Webhook deleted"}


@router.post("/orgs/{org_id}/webhooks/{webhook_id}/test")
def test_webhook(
    org_id: int,
    webhook_id: int,
    org_ctx: OrgContext = Depends(require_org_role("admin")),
    db: Session = Depends(get_db),
):
    result = es.test_webhook(db, webhook_id, org_id)
    if not result["success"]:
        raise HTTPException(404, result.get("error", "Webhook not found"))
    return result


# ── Compliance Center ────────────────────────────────────────────────────

@router.get("/compliance/frameworks")
def list_compliance_frameworks(
    db: Session = Depends(get_db),
):
    """List all available compliance frameworks."""
    # Ensure frameworks are seeded
    es.seed_compliance_frameworks(db)
    frameworks = es.list_frameworks(db)
    return {
        "frameworks": [
            {
                "id": fw.id,
                "name": fw.name,
                "slug": fw.slug,
                "version": fw.version,
                "category": fw.category,
                "description": fw.description,
                "controls_count": len(fw.controls),
            }
            for fw in frameworks
        ]
    }


@router.get("/orgs/{org_id}/compliance")
def get_org_compliance(
    org_id: int,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    """Get compliance status across all frameworks."""
    es.seed_compliance_frameworks(db)
    return {"frameworks": es.get_org_compliance_status(db, org_id)}


@router.get("/orgs/{org_id}/compliance/{framework_slug}")
def get_framework_detail(
    org_id: int,
    framework_slug: str,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    result = es.get_framework_detail(db, framework_slug, org_id)
    if not result:
        raise HTTPException(404, "Framework not found")
    return result


# ── Export Center ────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/exports")
def list_exports(
    org_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    items, total = es.list_export_jobs(db, org_id, page, page_size)
    return {
        "items": [
            {
                "id": e.id,
                "export_type": e.export_type,
                "format": e.format,
                "scope": e.scope,
                "status": e.status,
                "progress": e.progress,
                "file_size": e.file_size,
                "created_at": e.created_at.isoformat(),
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            }
            for e in items
        ],
        "total": total,
    }


@router.post("/orgs/{org_id}/exports", status_code=201)
def create_export(
    org_id: int,
    data: ExportRequest,
    org_ctx: OrgContext = Depends(require_org_role("security_engineer")),
    db: Session = Depends(get_db),
):
    job = es.create_export_job(db, org_id, org_ctx.user_id, data.model_dump())
    return {"id": job.id, "status": job.status, "export_type": job.export_type, "format": job.format}


@router.get("/orgs/{org_id}/exports/{export_id}/sarif")
def download_sarif(
    org_id: int,
    export_id: int,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    """Generate SARIF format export for selected scans."""
    from app.models.enterprise import ExportJob
    job = db.query(ExportJob).filter(ExportJob.id == export_id, ExportJob.organization_id == org_id).first()
    if not job:
        raise HTTPException(404, "Export job not found")

    scan_ids = job.scope.get("scan_ids", [])
    sarif = es.generate_sarif_export(db, scan_ids)
    return sarif


# ── Version Comparison ───────────────────────────────────────────────────

@router.post("/scans/compare")
def compare_scans(
    data: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = es.compare_scans(db, data.scan_id_1, data.scan_id_2)
    if not result:
        raise HTTPException(404, "One or both scans not found")
    return result


# ── Historical Analytics ─────────────────────────────────────────────────

@router.get("/orgs/{org_id}/analytics/history")
def get_historical_analytics(
    org_id: int,
    months: int = Query(12, ge=1, le=60),
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    return es.get_historical_analytics(db, org_id, months)


# ── Executive Reports ────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/executive-report")
def get_executive_report(
    org_id: int,
    org_ctx: OrgContext = Depends(require_org_role("viewer")),
    db: Session = Depends(get_db),
):
    return es.generate_executive_summary(db, org_id)
