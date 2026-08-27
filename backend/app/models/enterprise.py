"""Enterprise models for SentinelAI.

Scheduled scans, scan templates, compliance mappings, webhooks,
custom policies, and export jobs.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


# ── Scheduled Scans ──────────────────────────────────────────────────────
class ScheduledScan(Base):
    """Recurring scan schedule with CRON-like configuration."""

    __tablename__ = "scheduled_scans"
    __table_args__ = (
        Index("ix_scheduled_scans_org_id", "organization_id"),
        Index("ix_scheduled_scans_next_run", "next_run_at"),
        Index("ix_scheduled_scans_active", "is_active", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("scan_templates.id"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Schedule configuration (CRON-like)
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="weekly"
    )  # daily, weekly, monthly, custom
    cron_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=Mon
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hour: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Scan configuration
    scan_type: Mapped[str] = mapped_column(
        String(30), default="api", nullable=False
    )  # api, sast, dependency
    scan_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_scan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization")
    project = relationship("Project")
    creator = relationship("User", foreign_keys=[created_by])
    template = relationship("ScanTemplate")


# ── Scan Templates ───────────────────────────────────────────────────────
class ScanTemplate(Base):
    """Reusable scan configuration templates."""

    __tablename__ = "scan_templates"
    __table_args__ = (
        Index("ix_scan_templates_org_id", "organization_id"),
        UniqueConstraint(
            "organization_id", "name", name="uq_scan_template_name_org"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scan_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Configuration stored as JSON
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Example: {"severity_threshold": "medium", "ignore_rules": ["SA-19"], "custom_headers": {}}

    # Compliance targets for auto-mapping
    compliance_frameworks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Example: ["pci_dss", "soc2", "iso27001"]

    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])


# ── Custom Policies ──────────────────────────────────────────────────────
class Policy(Base):
    """Custom security policies with rule definitions."""

    __tablename__ = "policies"
    __table_args__ = (
        Index("ix_policies_org_id", "organization_id"),
        Index("ix_policies_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="finding_gate"
    )  # finding_gate, compliance_check, risk_threshold

    # Rule definition
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example rules format:
    # {
    #   "conditions": [
    #     {"field": "severity", "operator": "in", "value": ["Critical", "High"]},
    #     {"field": "cvss_score", "operator": "gte", "value": 7.0}
    #   ],
    #   "action": "block",
    #   "message": "Critical/High findings with CVSS >= 7.0 block the pipeline"
    # }

    severity: Mapped[str] = mapped_column(
        String(20), default="high", nullable=False
    )  # critical, high, medium, low
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enforce_on_scans: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notify_on_violation: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Statistics
    evaluation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])


# ── Webhooks ─────────────────────────────────────────────────────────────
class Webhook(Base):
    """Webhook integrations for notifications."""

    __tablename__ = "webhooks"
    __table_args__ = (
        Index("ix_webhooks_org_id", "organization_id"),
        Index("ix_webhooks_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    webhook_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # slack, teams, discord, email, custom
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # For email type, store addresses as JSON
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Slack: {"channel": "#security"}, Teams: {"channel_id": "..."}
    # Email: {"addresses": ["sec@co.com"]}, Discord: {"webhook_id": "..."}

    # Event subscriptions
    events: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # ["scan.completed", "scan.failed", "policy.violation", "high_risk_found"]

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    secret: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Statistics
    delivery_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])


# ── Compliance Mappings ──────────────────────────────────────────────────
class ComplianceFramework(Base):
    """Pre-defined compliance frameworks (OWASP, PCI-DSS, SOC2, etc.)."""

    __tablename__ = "compliance_frameworks"
    __table_args__ = (
        Index("ix_compliance_frameworks_slug", "slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # security, privacy, industry, regulatory
    controls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # [{"id": "PCI-DSS-1.2.1", "title": "...", "description": "...", "severity": "high"}]
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )


class OrganizationCompliance(Base):
    """Organization compliance status against frameworks."""

    __tablename__ = "org_compliance"
    __table_args__ = (
        Index("ix_org_compliance_org_framework", "organization_id", "framework_id"),
        UniqueConstraint(
            "organization_id", "framework_id", name="uq_org_framework"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    framework_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compliance_frameworks.id"), nullable=False
    )

    # Status tracking
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    controls_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    controls_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    controls_na: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    controls_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Per-control status
    control_status: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # {"PCI-DSS-1.2.1": {"status": "pass", "evidence": "...", "last_checked": "..."}}

    last_assessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_assessment_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization")
    framework = relationship("ComplianceFramework")


# ── Export Jobs ──────────────────────────────────────────────────────────
class ExportJob(Base):
    """Async export job tracking."""

    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_org_id", "organization_id"),
        Index("ix_export_jobs_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    export_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # scan_report, compliance_report, executive_report, findings_export
    format: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # pdf, csv, json, sarif
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)
    # {"scan_ids": [1,2,3], "framework": "pci_dss", "date_from": "...", "date_to": "..."}

    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, processing, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Results
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization = relationship("Organization")
    user = relationship("User")


# ── Webhook Delivery Log ────────────────────────────────────────────────
class WebhookDelivery(Base):
    """Webhook delivery attempts log."""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_webhook_id", "webhook_id"),
        Index("ix_webhook_deliveries_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    webhook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("webhooks.id"), nullable=False
    )
    event: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # success, failed, pending
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    webhook = relationship("Webhook")
