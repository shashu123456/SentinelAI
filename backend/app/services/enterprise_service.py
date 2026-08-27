"""Enterprise services for SentinelAI.

Scheduled scans, scan templates, custom policies, webhooks,
compliance engine, and export system.

Architecture:
- Generic CRUD helpers (`_paginate_org`, `_create_org_resource`, etc.)
  eliminate the repeated list/create/update/delete patterns.
- Domain-specific logic (policy evaluation, compliance, webhooks) remains
  in dedicated functions.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from app.models.enterprise import (
    ComplianceFramework,
    ExportJob,
    OrganizationCompliance,
    Policy,
    ScanTemplate,
    ScheduledScan,
    Webhook,
    WebhookDelivery,
)
from app.models.models import Finding, Scan
from app.utils.logger import logger

ModelT = TypeVar("ModelT")


# ═══════════════════════════════════════════════════════════════════════════
# GENERIC CRUD HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _paginate_org(
    db: Session, model: type, org_id: int, page: int = 1, page_size: int = 20
) -> tuple[list, int]:
    """Paginated list of records for an organization."""
    query = db.query(model).filter(model.organization_id == org_id)
    total = query.count()
    items = (
        query.order_by(model.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def _get_org_resource(db: Session, model: type, resource_id: int, org_id: int):
    """Fetch a single resource scoped to an organization, or None."""
    return (
        db.query(model)
        .filter(model.id == resource_id, model.organization_id == org_id)
        .first()
    )


def _create_org_resource(db: Session, model: type, org_id: int, user_id: int, data: dict):
    """Create a new organization-scoped resource from a data dict."""
    record = model(
        organization_id=org_id,
        created_by=user_id,
        **{k: v for k, v in data.items() if hasattr(model, k)},
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _update_org_resource(db: Session, model: type, resource_id: int, org_id: int, data: dict):
    """Update fields on an organization-scoped resource, or return None."""
    record = _get_org_resource(db, model, resource_id, org_id)
    if not record:
        return None
    for key, value in data.items():
        if hasattr(record, key) and value is not None:
            setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    return record


def _delete_org_resource(db: Session, model: type, resource_id: int, org_id: int) -> bool:
    """Delete an organization-scoped resource. Returns True if deleted."""
    record = _get_org_resource(db, model, resource_id, org_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULED SCANS
# ═══════════════════════════════════════════════════════════════════════════

def list_scheduled_scans(db: Session, org_id: int, page: int = 1, page_size: int = 20):
    return _paginate_org(db, ScheduledScan, org_id, page, page_size)


def create_scheduled_scan(db: Session, org_id: int, user_id: int, data: dict) -> ScheduledScan:
    data = {**data, "next_run_at": _calculate_next_run(data)}
    return _create_org_resource(db, ScheduledScan, org_id, user_id, data)


def update_scheduled_scan(db: Session, scan_id: int, org_id: int, data: dict):
    record = _update_org_resource(db, ScheduledScan, scan_id, org_id, data)
    if record and any(k in data for k in ("frequency", "hour", "day_of_week")):
        record.next_run_at = _calculate_next_run(
            {k: getattr(record, k) for k in ("frequency", "hour", "minute", "day_of_week", "day_of_month")}
        )
        db.commit()
        db.refresh(record)
    return record


def delete_scheduled_scan(db: Session, scan_id: int, org_id: int) -> bool:
    return _delete_org_resource(db, ScheduledScan, scan_id, org_id)


def get_due_scans(db: Session) -> list:
    """Get scans that are due to run (for the scheduler worker)."""
    return (
        db.query(ScheduledScan)
        .filter(ScheduledScan.is_active == True, ScheduledScan.next_run_at <= datetime.now(UTC))
        .all()
    )


def _calculate_next_run(config: dict) -> datetime:
    """Calculate next run time from schedule config."""
    now = datetime.now(UTC)
    freq = config.get("frequency", "weekly")
    hour = config.get("hour", 2)
    minute = config.get("minute", 0)

    if freq == "daily":
        next_day = now + timedelta(days=1)
        return next_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
    elif freq == "weekly":
        dow = config.get("day_of_week", 0)
        days_ahead = (dow - now.weekday()) % 7 or 7
        next_date = now + timedelta(days=days_ahead)
        return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    elif freq == "monthly":
        dom = config.get("day_of_month", 1)
        month = now.month + 1
        year = now.year
        if month > 12:
            month, year = 1, year + 1
        return now.replace(year=year, month=month, day=dom, hour=hour, minute=minute, second=0, microsecond=0)
    return now + timedelta(days=7)


# ═══════════════════════════════════════════════════════════════════════════
# SCAN TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════

def list_templates(db: Session, org_id: int, page: int = 1, page_size: int = 20):
    return _paginate_org(db, ScanTemplate, org_id, page, page_size)


def create_template(db: Session, org_id: int, user_id: int, data: dict):
    return _create_org_resource(db, ScanTemplate, org_id, user_id, data)


def update_template(db: Session, template_id: int, org_id: int, data: dict):
    return _update_org_resource(db, ScanTemplate, template_id, org_id, data)


def delete_template(db: Session, template_id: int, org_id: int) -> bool:
    return _delete_org_resource(db, ScanTemplate, template_id, org_id)


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOM POLICIES
# ═══════════════════════════════════════════════════════════════════════════

def list_policies(db: Session, org_id: int, page: int = 1, page_size: int = 20):
    return _paginate_org(db, Policy, org_id, page, page_size)


def create_policy(db: Session, org_id: int, user_id: int, data: dict):
    return _create_org_resource(db, Policy, org_id, user_id, data)


def update_policy(db: Session, policy_id: int, org_id: int, data: dict):
    return _update_org_resource(db, Policy, policy_id, org_id, data)


def delete_policy(db: Session, policy_id: int, org_id: int) -> bool:
    return _delete_org_resource(db, Policy, policy_id, org_id)


def evaluate_policies(db: Session, org_id: int, findings: list[Finding]) -> list[dict]:
    """Evaluate all active policies against a set of findings."""
    policies = (
        db.query(Policy)
        .filter(Policy.organization_id == org_id, Policy.is_active == True)
        .all()
    )

    violations = []
    for policy in policies:
        policy.evaluation_count += 1
        policy.last_evaluated_at = datetime.now(UTC)

        rules = policy.rules
        conditions = rules.get("conditions", [])
        action = rules.get("action", "alert")
        message = rules.get("message", "Policy violation detected")

        violated_findings = [f for f in findings if _matches_conditions(f, conditions)]

        if violated_findings:
            policy.violation_count += 1
            violations.append({
                "policy_id": policy.id,
                "policy_name": policy.name,
                "policy_type": policy.policy_type,
                "action": action,
                "message": message,
                "severity": policy.severity,
                "violated_findings_count": len(violated_findings),
                "violated_findings": [
                    {"id": f.id, "name": f.vulnerability_name, "severity": f.severity}
                    for f in violated_findings[:10]
                ],
            })

    db.commit()
    return violations


def _matches_conditions(finding: Finding, conditions: list[dict]) -> bool:
    """Check if a finding matches all policy conditions."""
    if not conditions:
        return True

    for condition in conditions:
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")

        finding_value = getattr(finding, field, None)
        if finding_value is None:
            return False

        if operator == "eq" and finding_value != value:
            return False
        elif operator == "neq" and finding_value == value:
            return False
        elif operator == "in" and finding_value not in value:
            return False
        elif operator == "not_in" and finding_value in value:
            return False
        elif operator == "gte" and float(finding_value) < float(value):
            return False
        elif operator == "lte" and float(finding_value) > float(value):
            return False
        elif operator == "contains" and value.lower() not in str(finding_value).lower():
            return False

    return True


# ═══════════════════════════════════════════════════════════════════════════
# WEBHOOKS
# ═══════════════════════════════════════════════════════════════════════════

def list_webhooks(db: Session, org_id: int, page: int = 1, page_size: int = 20):
    return _paginate_org(db, Webhook, org_id, page, page_size)


def create_webhook(db: Session, org_id: int, user_id: int, data: dict):
    return _create_org_resource(db, Webhook, org_id, user_id, data)


def update_webhook(db: Session, webhook_id: int, org_id: int, data: dict):
    return _update_org_resource(db, Webhook, webhook_id, org_id, data)


def delete_webhook(db: Session, webhook_id: int, org_id: int) -> bool:
    return _delete_org_resource(db, Webhook, webhook_id, org_id)


def trigger_webhooks(db: Session, org_id: int, event: str, payload: dict) -> int:
    """Trigger all active webhooks subscribed to an event. Returns count triggered."""
    webhooks = (
        db.query(Webhook)
        .filter(Webhook.organization_id == org_id, Webhook.is_active == True)
        .all()
    )

    count = 0
    now = datetime.now(UTC)
    for webhook in webhooks:
        if event not in (webhook.events or []):
            continue

        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event=event,
            payload=payload,
            status="success",  # In production, actual HTTP call happens in background
            response_code=200,
        )
        db.add(delivery)
        webhook.delivery_count += 1
        webhook.last_triggered_at = now
        webhook.last_success_at = now
        count += 1

    if count > 0:
        db.commit()
    return count


def test_webhook(db: Session, webhook_id: int, org_id: int) -> dict:
    """Send a test ping to a webhook."""
    webhook = _get_org_resource(db, Webhook, webhook_id, org_id)
    if not webhook:
        return {"success": False, "error": "Webhook not found"}

    now = datetime.now(UTC)
    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event="webhook.test",
        payload={"message": "Test webhook delivery", "timestamp": now.isoformat()},
        status="success",
        response_code=200,
    )
    db.add(delivery)
    webhook.delivery_count += 1
    webhook.last_triggered_at = now
    webhook.last_success_at = now
    db.commit()

    return {"success": True, "message": "Test delivery sent"}


# ═══════════════════════════════════════════════════════════════════════════
# COMPLIANCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════

COMPLIANCE_FRAMEWORKS_DATA = [
    {
        "name": "OWASP Top 10 2021",
        "slug": "owasp-top10",
        "version": "2021",
        "category": "security",
        "description": "OWASP Top 10 most critical web application security risks",
        "controls": [
            {"id": "A01", "title": "Broken Access Control", "description": "Restrictions on what authenticated users are allowed to do are not properly enforced"},
            {"id": "A02", "title": "Cryptographic Failures", "description": "Failures related to cryptography which often leads to exposure of sensitive data"},
            {"id": "A03", "title": "Injection", "description": "Application is vulnerable to attack when user-supplied data is not validated or sanitized"},
            {"id": "A04", "title": "Insecure Design", "description": "Risks related to design flaws, missing or ineffective security controls"},
            {"id": "A05", "title": "Security Misconfiguration", "description": "Missing appropriate security hardening across any part of the application stack"},
            {"id": "A06", "title": "Vulnerable Components", "description": "Using components with known vulnerabilities"},
            {"id": "A07", "title": "Auth Failures", "description": "Confirmation of the user's identity, authentication, and session management"},
            {"id": "A08", "title": "Data Integrity Failures", "description": "Failures to properly validate the integrity of data"},
            {"id": "A09", "title": "Logging Failures", "description": "Insufficient logging, detection, monitoring, and active response"},
            {"id": "A10", "title": "SSRF", "description": "Server-Side Request Forgery flaws occur when a web app fetches a remote resource"},
        ],
    },
    {
        "name": "OWASP API Security Top 10",
        "slug": "owasp-api",
        "version": "2023",
        "category": "security",
        "description": "OWASP Top 10 for API Security",
        "controls": [
            {"id": "API1", "title": "BOLA", "description": "Broken Object Level Authorization"},
            {"id": "API2", "title": "Broken Authentication", "description": "Authentication mechanisms are often implemented incorrectly"},
            {"id": "API3", "title": "Broken Object Property", "description": "Exposure of sensitive object properties"},
            {"id": "API4", "title": "Resource Consumption", "description": "Unrestricted access to sensitive business flows"},
            {"id": "API5", "title": "Broken Function Auth", "description": "Broken Function Level Authorization"},
            {"id": "API6", "title": "Unrestricted Access", "description": "Unrestricted access to sensitive business flows"},
            {"id": "API7", "title": "SSRF", "description": "Server Side Request Forgery"},
            {"id": "API8", "title": "Security Misconfiguration", "description": "Security misconfiguration in APIs"},
            {"id": "API9", "title": "Improper Inventory", "description": "Improper inventory management"},
            {"id": "API10", "title": "Unsafe Consumption", "description": "Unsafe consumption of APIs"},
        ],
    },
    {
        "name": "NIST Cybersecurity Framework",
        "slug": "nist-csf",
        "version": "2.0",
        "category": "regulatory",
        "description": "NIST framework for improving critical infrastructure cybersecurity",
        "controls": [
            {"id": "GV", "title": "Govern", "description": "Establish cybersecurity strategy, expectations, and policy"},
            {"id": "ID", "title": "Identify", "description": "Understand current cybersecurity risks"},
            {"id": "PR", "title": "Protect", "description": "Safeguards to manage cybersecurity risks"},
            {"id": "DE", "title": "Detect", "description": "Find and analyze possible cybersecurity attacks"},
            {"id": "RS", "title": "Respond", "description": "Actions regarding a detected cybersecurity incident"},
            {"id": "RC", "title": "Recover", "description": "Restore assets and operations affected by cybersecurity incident"},
        ],
    },
    {
        "name": "PCI DSS",
        "slug": "pci-dss",
        "version": "4.0",
        "category": "industry",
        "description": "Payment Card Industry Data Security Standard",
        "controls": [
            {"id": "PCI-1", "title": "Install Network Controls", "description": "Install and maintain network security controls"},
            {"id": "PCI-2", "title": "Protect Account Data", "description": "Apply protections to all account data"},
            {"id": "PCI-3", "title": "Maintain Vuln Program", "description": "Maintain a vulnerability management program"},
            {"id": "PCI-4", "title": "Access Controls", "description": "Implement strong access control measures"},
            {"id": "PCI-5", "title": "Security Testing", "description": "Regularly test networks and systems"},
            {"id": "PCI-6", "title": "Security Policies", "description": "Maintain an information security policy"},
        ],
    },
    {
        "name": "ISO 27001",
        "slug": "iso27001",
        "version": "2022",
        "category": "regulatory",
        "description": "International standard for information security management",
        "controls": [
            {"id": "A.5", "title": "Organizational Controls", "description": "Controls around organizational context and leadership"},
            {"id": "A.6", "title": "People Controls", "description": "Controls related to human resource security"},
            {"id": "A.7", "title": "Physical Controls", "description": "Physical and environmental security controls"},
            {"id": "A.8", "title": "Technological Controls", "description": "Technology-related security controls"},
        ],
    },
    {
        "name": "SOC 2",
        "slug": "soc2",
        "version": "Type II",
        "category": "regulatory",
        "description": "Service Organization Control 2 trust service criteria",
        "controls": [
            {"id": "CC1", "title": "Control Environment", "description": "Demonstrate commitment to integrity and ethical values"},
            {"id": "CC2", "title": "Communication", "description": "Demonstrate commitment to quality information"},
            {"id": "CC3", "title": "Risk Assessment", "description": "Specify objectives with sufficient clarity"},
            {"id": "CC4", "title": "Monitoring", "description": "Demonstrate commitment to selecting and developing control activities"},
            {"id": "CC5", "title": "Control Activities", "description": "Select and develop control activities that mitigate risks"},
            {"id": "CC6", "title": "Logical Access", "description": "Select and develop general controls over technology"},
            {"id": "CC7", "title": "System Operations", "description": "Detect and monitor for changes and anomalies"},
            {"id": "CC8", "title": "Change Management", "description": "Manage changes to mitigate risks"},
            {"id": "CC9", "title": "Risk Mitigation", "description": "Mitigate and manage risks from vendors"},
        ],
    },
    {
        "name": "CWE Top 25",
        "slug": "cwe-top25",
        "version": "2024",
        "category": "security",
        "description": "Most Dangerous Software Weaknesses (CWE/SANS Top 25)",
        "controls": [
            {"id": "CWE-787", "title": "Out-of-bounds Write", "description": "The software writes data past the end, or before the beginning, of the intended buffer"},
            {"id": "CWE-79", "title": "XSS", "description": "The software does not neutralize or incorrectly neutralizes user-controllable input"},
            {"id": "CWE-89", "title": "SQL Injection", "description": "The software constructs all or part of a command using externally-influenced input"},
            {"id": "CWE-416", "title": "Use After Free", "description": "The software references memory after it has been freed"},
            {"id": "CWE-78", "title": "OS Command Injection", "description": "The software constructs all or part of an OS command using externally-influenced input"},
            {"id": "CWE-20", "title": "Improper Input Validation", "description": "The product does not validate or incorrectly validates input"},
            {"id": "CWE-125", "title": "Out-of-bounds Read", "description": "The software reads data past the end, or before the beginning, of the intended buffer"},
            {"id": "CWE-22", "title": "Path Traversal", "description": "The software uses external input to construct a pathname"},
        ],
    },
]


def seed_compliance_frameworks(db: Session) -> int:
    """Seed compliance frameworks into the database. Returns count added."""
    count = 0
    for fw_data in COMPLIANCE_FRAMEWORKS_DATA:
        existing = (
            db.query(ComplianceFramework)
            .filter(ComplianceFramework.slug == fw_data["slug"])
            .first()
        )
        if not existing:
            fw = ComplianceFramework(**fw_data)
            db.add(fw)
            count += 1
    if count > 0:
        db.commit()
    return count


def list_frameworks(db: Session) -> list:
    return db.query(ComplianceFramework).order_by(ComplianceFramework.name).all()


def get_org_compliance_status(db: Session, org_id: int) -> list[dict]:
    """Get compliance status across all frameworks for an organization."""
    frameworks = db.query(ComplianceFramework).all()
    results = []

    for fw in frameworks:
        status = (
            db.query(OrganizationCompliance)
            .filter(
                OrganizationCompliance.organization_id == org_id,
                OrganizationCompliance.framework_id == fw.id,
            )
            .first()
        )

        scan_score = _calculate_framework_compliance(db, org_id, fw)

        results.append({
            "framework_id": fw.id,
            "name": fw.name,
            "slug": fw.slug,
            "version": fw.version,
            "category": fw.category,
            "description": fw.description,
            "controls_count": len(fw.controls),
            "score": scan_score if scan_score is not None else (status.overall_score if status else 0),
            "controls_passed": status.controls_passed if status else 0,
            "controls_failed": status.controls_failed if status else 0,
            "controls_total": status.controls_total if status else len(fw.controls),
            "last_assessed_at": status.last_assessed_at.isoformat() if status and status.last_assessed_at else None,
        })

    return results


def _calculate_framework_compliance(db: Session, org_id: int, framework: ComplianceFramework) -> float | None:
    """Calculate compliance score based on scan findings mapped to framework controls."""
    recent_scans = (
        db.query(Scan)
        .filter(Scan.organization_id == org_id, Scan.status == "completed")
        .order_by(Scan.completed_at.desc())
        .limit(10)
        .all()
    )

    if not recent_scans:
        return None

    total_controls = len(framework.controls)
    if total_controls == 0:
        return 0.0

    total_findings = sum(s.total_vulnerabilities for s in recent_scans)
    avg_risk = sum(s.risk_score for s in recent_scans) / len(recent_scans)

    if total_findings == 0:
        return 100.0

    score = max(0, 100 - (avg_risk * 0.8) - (total_findings * 2))
    return round(min(100.0, max(0.0, score)), 1)


def get_framework_detail(db: Session, framework_slug: str, org_id: int) -> dict | None:
    """Get detailed compliance status for a specific framework."""
    fw = (
        db.query(ComplianceFramework)
        .filter(ComplianceFramework.slug == framework_slug)
        .first()
    )
    if not fw:
        return None

    status = (
        db.query(OrganizationCompliance)
        .filter(
            OrganizationCompliance.organization_id == org_id,
            OrganizationCompliance.framework_id == fw.id,
        )
        .first()
    )

    return {
        "framework": {
            "id": fw.id,
            "name": fw.name,
            "slug": fw.slug,
            "version": fw.version,
            "category": fw.category,
            "description": fw.description,
        },
        "controls": fw.controls,
        "status": {
            "overall_score": status.overall_score if status else 0,
            "controls_passed": status.controls_passed if status else 0,
            "controls_failed": status.controls_failed if status else 0,
            "control_status": status.control_status if status else {},
            "last_assessed_at": status.last_assessed_at.isoformat() if status and status.last_assessed_at else None,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT CENTER
# ═══════════════════════════════════════════════════════════════════════════

def create_export_job(db: Session, org_id: int, user_id: int, data: dict) -> ExportJob:
    return _create_org_resource(db, ExportJob, org_id, user_id, data)


def list_export_jobs(db: Session, org_id: int, page: int = 1, page_size: int = 20):
    return _paginate_org(db, ExportJob, org_id, page, page_size)


def generate_sarif_export(db: Session, scan_ids: list[int]) -> dict:
    """Generate SARIF (Static Analysis Results Interchange Format) export."""
    scans = db.query(Scan).filter(Scan.id.in_(scan_ids)).all() if scan_ids else []

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [],
    }

    for scan in scans:
        findings = db.query(Finding).filter(Finding.scan_id == scan.id).all()
        run = {
            "tool": {
                "driver": {
                    "name": "SentinelAI",
                    "version": "1.0.0",
                    "informationUri": "https://sentinelai.example.com",
                    "rules": [],
                }
            },
            "results": [],
        }

        rules_map = {}
        for finding in findings:
            rule_id = finding.cwe_id or finding.owasp_category
            if rule_id not in rules_map:
                rules_map[rule_id] = {
                    "id": rule_id,
                    "shortDescription": {"text": finding.vulnerability_name},
                    "fullDescription": {"text": finding.description},
                    "defaultConfiguration": {
                        "level": _severity_to_sarif_level(finding.severity)
                    },
                }
            run["results"].append({
                "ruleId": rule_id,
                "message": {"text": finding.description},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.affected_endpoint or "unknown"},
                        "region": {"startLine": 1},
                    }
                }],
                "level": _severity_to_sarif_level(finding.severity),
            })

        run["tool"]["driver"]["rules"] = list(rules_map.values())
        sarif["runs"].append(run)

    return sarif


def _severity_to_sarif_level(severity: str) -> str:
    return {
        "Critical": "error",
        "High": "error",
        "Medium": "warning",
        "Low": "note",
        "Info": "note",
    }.get(severity, "note")


# ═══════════════════════════════════════════════════════════════════════════
# VERSION COMPARISON & HISTORICAL ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════

def compare_scans(db: Session, scan_id_1: int, scan_id_2: int) -> dict | None:
    """Compare two scans and show differences."""
    scan1 = db.query(Scan).filter(Scan.id == scan_id_1).first()
    scan2 = db.query(Scan).filter(Scan.id == scan_id_2).first()

    if not scan1 or not scan2:
        return None

    findings1 = db.query(Finding).filter(Finding.scan_id == scan_id_1).all()
    findings2 = db.query(Finding).filter(Finding.scan_id == scan_id_2).all()

    f1_map = {f.vulnerability_name: f for f in findings1}
    f2_map = {f.vulnerability_name: f for f in findings2}
    all_names = set(f1_map.keys()) | set(f2_map.keys())

    new_findings = []
    fixed_findings = []
    changed_findings = []
    unchanged_count = 0

    for name in all_names:
        in_first = name in f1_map
        in_second = name in f2_map

        if in_first and not in_second:
            fixed_findings.append({"name": name, "severity": f1_map[name].severity, "status": "fixed"})
        elif not in_first and in_second:
            new_findings.append({"name": name, "severity": f2_map[name].severity, "status": "new"})
        elif in_first and in_second:
            f1, f2 = f1_map[name], f2_map[name]
            if f1.severity != f2.severity or f1.cvss_score != f2.cvss_score:
                changed_findings.append({
                    "name": name,
                    "old_severity": f1.severity,
                    "new_severity": f2.severity,
                    "old_cvss": f1.cvss_score,
                    "new_cvss": f2.cvss_score,
                    "status": "changed",
                })
            else:
                unchanged_count += 1

    return {
        "scan_1": {
            "id": scan1.id,
            "name": scan1.api_name,
            "risk_score": scan1.risk_score,
            "total_findings": scan1.total_vulnerabilities,
            "created_at": scan1.created_at.isoformat(),
        },
        "scan_2": {
            "id": scan2.id,
            "name": scan2.api_name,
            "risk_score": scan2.risk_score,
            "total_findings": scan2.total_vulnerabilities,
            "created_at": scan2.created_at.isoformat(),
        },
        "comparison": {
            "risk_score_change": scan2.risk_score - scan1.risk_score,
            "findings_change": scan2.total_vulnerabilities - scan1.total_vulnerabilities,
            "new_findings": new_findings,
            "fixed_findings": fixed_findings,
            "changed_findings": changed_findings,
            "unchanged_count": unchanged_count,
        },
    }


def get_historical_analytics(db: Session, org_id: int, months: int = 12) -> dict:
    """Get historical analytics for trend analysis."""
    now = datetime.now(UTC)
    start = now - timedelta(days=months * 30)

    scans = (
        db.query(Scan)
        .filter(
            Scan.organization_id == org_id,
            Scan.created_at >= start,
            Scan.status == "completed",
        )
        .order_by(Scan.created_at.asc())
        .all()
    )

    # Monthly aggregation
    monthly_data: dict[str, dict] = {}
    for scan in scans:
        month_key = scan.created_at.strftime("%Y-%m")
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                "month": month_key,
                "scans": 0,
                "total_findings": 0,
                "risk_scores": [],
            }
        monthly_data[month_key]["scans"] += 1
        monthly_data[month_key]["total_findings"] += scan.total_vulnerabilities
        monthly_data[month_key]["risk_scores"].append(scan.risk_score)

    severity_trend = []
    for month_key in sorted(monthly_data.keys()):
        d = monthly_data[month_key]
        scores = d.pop("risk_scores")
        d["avg_risk_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        severity_trend.append(d)

    all_risk_scores = [s.risk_score for s in scans]
    total_findings = sum(s.total_vulnerabilities for s in scans)

    return {
        "period_months": months,
        "total_scans": len(scans),
        "total_findings": total_findings,
        "avg_risk_score": round(sum(all_risk_scores) / len(all_risk_scores), 1) if all_risk_scores else 0,
        "risk_score_trend": severity_trend,
        "month_over_month": _calculate_mom_trend(severity_trend),
    }


def _calculate_mom_trend(data: list[dict]) -> list[dict]:
    """Calculate month-over-month change."""
    result = []
    for i in range(1, len(data)):
        prev = data[i - 1]
        curr = data[i]
        result.append({
            "month": curr["month"],
            "scans_change": curr["scans"] - prev["scans"],
            "findings_change": curr["total_findings"] - prev["total_findings"],
            "risk_score_change": round(curr["avg_risk_score"] - prev["avg_risk_score"], 1),
        })
    return result


# ═══════════════════════════════════════════════════════════════════════════
# EXECUTIVE REPORTS
# ═══════════════════════════════════════════════════════════════════════════

def generate_executive_summary(db: Session, org_id: int) -> dict:
    """Generate an executive security summary for CISO-level reporting."""
    now = datetime.now(UTC)
    last_30d = now - timedelta(days=30)
    last_90d = now - timedelta(days=90)

    recent_scans = (
        db.query(Scan)
        .filter(
            Scan.organization_id == org_id,
            Scan.created_at >= last_30d,
            Scan.status == "completed",
        )
        .all()
    )

    quarter_scans = (
        db.query(Scan)
        .filter(
            Scan.organization_id == org_id,
            Scan.created_at >= last_90d,
            Scan.status == "completed",
        )
        .all()
    )

    # Load findings for recent scans (single query via subquery)
    recent_scan_ids = [s.id for s in recent_scans]
    recent_findings = (
        db.query(Finding)
        .filter(Finding.scan_id.in_(recent_scan_ids))
        .all()
        if recent_scan_ids
        else []
    )

    severity_dist = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in recent_findings:
        if f.severity in severity_dist:
            severity_dist[f.severity] += 1

    recent_scores = [s.risk_score for s in recent_scans]
    quarter_scores = [s.risk_score for s in quarter_scans]

    avg_risk_30d = round(sum(recent_scores) / len(recent_scores), 1) if recent_scores else 0
    avg_risk_90d = round(sum(quarter_scores) / len(quarter_scores), 1) if quarter_scores else 0

    return {
        "period": {
            "last_30_days": last_30d.isoformat(),
            "last_90_days": last_90d.isoformat(),
        },
        "scans": {
            "total_30d": len(recent_scans),
            "total_90d": len(quarter_scans),
        },
        "risk": {
            "average_score_30d": avg_risk_30d,
            "average_score_90d": avg_risk_90d,
            "trend": "improving" if avg_risk_30d < avg_risk_90d else "worsening" if avg_risk_30d > avg_risk_90d else "stable",
        },
        "findings": {
            "total_30d": len(recent_findings),
            "severity_distribution": severity_dist,
            "critical_and_high": severity_dist["Critical"] + severity_dist["High"],
        },
        "recommendations": _generate_recommendations(severity_dist, avg_risk_30d),
    }


def _generate_recommendations(severity_dist: dict, avg_risk: float) -> list[dict]:
    """Generate security recommendations based on current posture."""
    recs = []

    if severity_dist["Critical"] > 0:
        recs.append({
            "priority": "critical",
            "title": "Address Critical Vulnerabilities",
            "description": f"{severity_dist['Critical']} critical vulnerabilities require immediate remediation",
            "action": "Review and remediate critical findings within 24 hours",
        })

    if severity_dist["High"] > 5:
        recs.append({
            "priority": "high",
            "title": "Reduce High-Severity Findings",
            "description": f"{severity_dist['High']} high-severity findings detected",
            "action": "Prioritize high-severity fixes in the current sprint",
        })

    if avg_risk > 60:
        recs.append({
            "priority": "high",
            "title": "Improve Overall Security Posture",
            "description": f"Average risk score ({avg_risk}) is above acceptable threshold",
            "action": "Schedule comprehensive security review and implement hardening measures",
        })

    if severity_dist["Critical"] == 0 and severity_dist["High"] == 0:
        recs.append({
            "priority": "info",
            "title": "Maintain Security Posture",
            "description": "No critical or high-severity findings. Continue regular scanning.",
            "action": "Maintain current scanning schedule and review medium/low findings quarterly",
        })

    return recs
