"""SLA tracking, error budget, and alerting for SentinelAI.

Provides:

- SLA definition and tracking (availability, latency, error rate)
- Error budget calculation and burn rate monitoring
- Uptime monitoring with check history
- Alert threshold definitions and notification
- Incident lifecycle tracking

Usage::

    from app.utils.sla import sla_tracker, alert_manager

    # Record a successful request
    sla_tracker.record_request(success=True, latency_ms=45.2)

    # Check error budget
    budget = sla_tracker.get_error_budget()
    print(f"Error budget remaining: {budget['remaining_percent']}%")

    # Check alerts
    alerts = alert_manager.check_all()
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ═══════════════════════════════════════════════════════════════════════
# SLA Definitions
# ═══════════════════════════════════════════════════════════════════════


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class SLADefinition:
    """Define an SLA target."""

    name: str
    description: str

    # Availability target (0-100%)
    availability_target: float = 99.9  # 99.9% uptime

    # Latency targets (ms)
    latency_p95_target: float = 500.0  # 95th percentile < 500ms
    latency_p99_target: float = 1000.0  # 99th percentile < 1000ms

    # Error rate target (0-100%)
    error_rate_target: float = 1.0  # <1% error rate

    # Time window (seconds) for measurement
    window_seconds: int = 86400  # 24 hours

    # Error budget
    error_budget_percent: float = 0.1  # 0.1% downtime allowed


# Default SLA for SentinelAI
DEFAULT_SLA = SLADefinition(
    name="sentinelai-sla",
    description="SentinelAI Platform SLA",
    availability_target=99.9,
    latency_p95_target=500.0,
    latency_p99_target=1000.0,
    error_rate_target=1.0,
    error_budget_percent=0.1,
)


# ═══════════════════════════════════════════════════════════════════════
# SLA Tracker
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class RequestRecord:
    success: bool
    latency_ms: float
    timestamp: float
    status_code: int = 200
    path: str = ""


class SLATracker:
    """Track SLA compliance in real-time."""

    def __init__(self, sla: SLADefinition | None = None):
        self.sla = sla or DEFAULT_SLA
        self._records: deque[RequestRecord] = deque(maxlen=100000)
        self._lock = threading.Lock()
        self._incident_start: float | None = None
        self._total_downtime_seconds: float = 0.0
        self._last_check: float = time.time()

    def record_request(
        self,
        *,
        success: bool,
        latency_ms: float,
        status_code: int = 200,
        path: str = "",
    ) -> None:
        """Record a request for SLA tracking."""
        record = RequestRecord(
            success=success,
            latency_ms=latency_ms,
            timestamp=time.time(),
            status_code=status_code,
            path=path,
        )
        with self._lock:
            self._records.append(record)

    def record_downtime(self, seconds: float) -> None:
        """Record explicit downtime (e.g., maintenance window)."""
        with self._lock:
            self._total_downtime_seconds += seconds

    def _get_window_records(self) -> list[RequestRecord]:
        """Get records within the SLA window."""
        cutoff = time.time() - self.sla.window_seconds
        with self._lock:
            return [r for r in self._records if r.timestamp >= cutoff]

    def get_availability(self) -> dict[str, Any]:
        """Calculate current availability within the SLA window."""
        records = self._get_window_records()
        if not records:
            return {
                "availability_percent": 100.0,
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "target": self.sla.availability_target,
                "met": True,
            }

        total = len(records)
        successful = sum(1 for r in records if r.success)
        failed = total - successful
        availability = (successful / total) * 100 if total > 0 else 100.0

        return {
            "availability_percent": round(availability, 3),
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": failed,
            "target": self.sla.availability_target,
            "met": availability >= self.sla.availability_target,
            "window_seconds": self.sla.window_seconds,
        }

    def get_latency(self) -> dict[str, Any]:
        """Calculate latency statistics within the SLA window."""
        records = self._get_window_records()
        if not records:
            return {
                "p50_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "avg_ms": 0,
                "max_ms": 0,
                "p95_target": self.sla.latency_p95_target,
                "p99_target": self.sla.latency_p99_target,
                "p95_met": True,
                "p99_met": True,
            }

        latencies = sorted(r.latency_ms for r in records)
        n = len(latencies)

        p50 = latencies[int(n * 0.5)] if n > 0 else 0
        p95 = latencies[int(n * 0.95)] if n > 0 else 0
        p99 = latencies[int(n * 0.99)] if n > 0 else 0
        avg = sum(latencies) / n if n > 0 else 0
        max_lat = max(latencies) if latencies else 0

        return {
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "avg_ms": round(avg, 2),
            "max_ms": round(max_lat, 2),
            "p95_target": self.sla.latency_p95_target,
            "p99_target": self.sla.latency_p99_target,
            "p95_met": p95 <= self.sla.latency_p95_target,
            "p99_met": p99 <= self.sla.latency_p99_target,
        }

    def get_error_rate(self) -> dict[str, Any]:
        """Calculate error rate within the SLA window."""
        records = self._get_window_records()
        if not records:
            return {
                "error_rate_percent": 0.0,
                "total": 0,
                "errors": 0,
                "target": self.sla.error_rate_target,
                "met": True,
            }

        total = len(records)
        errors = sum(1 for r in records if not r.success)
        error_rate = (errors / total) * 100 if total > 0 else 0

        return {
            "error_rate_percent": round(error_rate, 3),
            "total": total,
            "errors": errors,
            "target": self.sla.error_rate_target,
            "met": error_rate <= self.sla.error_rate_target,
        }

    def get_error_budget(self) -> dict[str, Any]:
        """Calculate error budget status.

        Error budget = allowed downtime - actual downtime.
        Burn rate = how fast the budget is being consumed.
        """
        availability = self.get_availability()
        total_requests = availability["total_requests"]
        failed_requests = availability["failed_requests"]

        # Error budget in requests
        budget_percent = self.sla.error_budget_percent
        allowed_failures = int(total_requests * budget_percent / 100)
        remaining_failures = max(0, allowed_failures - failed_requests)
        remaining_percent = (
            (remaining_failures / allowed_failures * 100) if allowed_failures > 0 else 100
        )

        # Burn rate (how fast we're consuming the budget)
        # 1.0 = consuming at expected rate, >1.0 = consuming faster
        window = self.sla.window_seconds
        time.time() - (self._records[0].timestamp if self._records else time.time())
        expected_failure_rate = budget_percent / 100
        actual_failure_rate = failed_requests / total_requests if total_requests > 0 else 0
        burn_rate = actual_failure_rate / expected_failure_rate if expected_failure_rate > 0 else 0

        # Time to exhaustion
        if burn_rate > 0 and remaining_failures > 0:
            # How much budget remains vs burn rate
            time_remaining_hours = (
                (remaining_percent / 100) * (window / 3600) / max(burn_rate, 0.01)
            )
        else:
            time_remaining_hours = float("inf")

        return {
            "budget_percent": budget_percent,
            "allowed_failures": allowed_failures,
            "actual_failures": failed_requests,
            "remaining_failures": remaining_failures,
            "remaining_percent": round(remaining_percent, 1),
            "burn_rate": round(burn_rate, 2),
            "time_to_exhaustion_hours": (
                round(time_remaining_hours, 1) if time_remaining_hours != float("inf") else None
            ),
            "status": (
                "healthy"
                if remaining_percent > 50
                else "warning" if remaining_percent > 20 else "critical"
            ),
        }

    def get_sla_summary(self) -> dict[str, Any]:
        """Get complete SLA compliance summary."""
        availability = self.get_availability()
        latency = self.get_latency()
        error_rate = self.get_error_rate()
        error_budget = self.get_error_budget()

        # Overall SLA status
        all_met = (
            availability["met"] and latency["p95_met"] and latency["p99_met"] and error_rate["met"]
        )

        return {
            "sla_name": self.sla.name,
            "description": self.sla.description,
            "overall_status": "met" if all_met else "breached",
            "availability": availability,
            "latency": latency,
            "error_rate": error_rate,
            "error_budget": error_budget,
            "window_seconds": self.sla.window_seconds,
            "targets": {
                "availability": self.sla.availability_target,
                "latency_p95": self.sla.latency_p95_target,
                "latency_p99": self.sla.latency_p99_target,
                "error_rate": self.sla.error_rate_target,
            },
        }


# ═══════════════════════════════════════════════════════════════════════
# Alert Manager
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Alert:
    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    source: str
    created_at: float
    acknowledged_at: float | None = None
    resolved_at: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertThreshold:
    name: str
    metric: str  # "availability", "latency_p95", "latency_p99", "error_rate", "burn_rate"
    severity: AlertSeverity
    threshold: float
    comparison: str = "lt"  # "lt" (less than), "gt" (greater than)
    description: str = ""


class AlertManager:
    """Manage alerts based on SLA metrics and thresholds."""

    def __init__(self):
        self._thresholds: list[AlertThreshold] = []
        self._active_alerts: dict[str, Alert] = {}
        self._alert_history: deque[Alert] = deque(maxlen=1000)
        self._lock = threading.Lock()

        # Default thresholds
        self.add_threshold(
            AlertThreshold(
                name="availability_critical",
                metric="availability",
                severity=AlertSeverity.CRITICAL,
                threshold=99.0,
                comparison="lt",
                description="Availability dropped below 99%",
            )
        )
        self.add_threshold(
            AlertThreshold(
                name="availability_warning",
                metric="availability",
                severity=AlertSeverity.WARNING,
                threshold=99.5,
                comparison="lt",
                description="Availability dropped below 99.5%",
            )
        )
        self.add_threshold(
            AlertThreshold(
                name="latency_p95_warning",
                metric="latency_p95",
                severity=AlertSeverity.WARNING,
                threshold=500.0,
                comparison="gt",
                description="P95 latency exceeded 500ms",
            )
        )
        self.add_threshold(
            AlertThreshold(
                name="latency_p99_critical",
                metric="latency_p99",
                severity=AlertSeverity.CRITICAL,
                threshold=1000.0,
                comparison="gt",
                description="P99 latency exceeded 1000ms",
            )
        )
        self.add_threshold(
            AlertThreshold(
                name="error_rate_critical",
                metric="error_rate",
                severity=AlertSeverity.CRITICAL,
                threshold=5.0,
                comparison="gt",
                description="Error rate exceeded 5%",
            )
        )
        self.add_threshold(
            AlertThreshold(
                name="error_budget_critical",
                metric="burn_rate",
                severity=AlertSeverity.CRITICAL,
                threshold=10.0,
                comparison="gt",
                description="Error budget burning >10x expected rate",
            )
        )

    def add_threshold(self, threshold: AlertThreshold) -> None:
        """Add an alert threshold."""
        with self._lock:
            self._thresholds.append(threshold)

    def check_thresholds(self, sla_tracker: SLATracker) -> list[Alert]:
        """Check all thresholds against current SLA metrics and fire alerts."""
        sla = sla_tracker.get_sla_summary()
        fired = []

        metric_values = {
            "availability": sla["availability"]["availability_percent"],
            "latency_p95": sla["latency"]["p95_ms"],
            "latency_p99": sla["latency"]["p99_ms"],
            "error_rate": sla["error_rate"]["error_rate_percent"],
            "burn_rate": sla["error_budget"]["burn_rate"],
        }

        with self._lock:
            for threshold in self._thresholds:
                value = metric_values.get(threshold.metric)
                if value is None:
                    continue

                triggered = False
                if (
                    threshold.comparison == "gt"
                    and value > threshold.threshold
                    or threshold.comparison == "lt"
                    and value < threshold.threshold
                ):
                    triggered = True

                if triggered and threshold.name not in self._active_alerts:
                    alert = Alert(
                        id=f"alert-{threshold.name}-{int(time.time())}",
                        name=threshold.name,
                        severity=threshold.severity,
                        status=AlertStatus.ACTIVE,
                        message=f"{threshold.description} (current: {value}, threshold: {threshold.threshold})",
                        source="sla_monitor",
                        created_at=time.time(),
                        details={
                            "metric": threshold.metric,
                            "value": value,
                            "threshold": threshold.threshold,
                        },
                    )
                    self._active_alerts[threshold.name] = alert
                    self._alert_history.append(alert)
                    fired.append(alert)
                elif not triggered and threshold.name in self._active_alerts:
                    # Auto-resolve
                    old = self._active_alerts.pop(threshold.name)
                    old.status = AlertStatus.RESOLVED
                    old.resolved_at = time.time()
                    self._alert_history.append(old)

        return fired

    def get_active_alerts(self) -> list[dict]:
        """Get all active alerts."""
        with self._lock:
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "severity": a.severity.value,
                    "status": a.status.value,
                    "message": a.message,
                    "source": a.source,
                    "created_at": a.created_at,
                    "age_seconds": round(time.time() - a.created_at),
                }
                for a in self._active_alerts.values()
            ]

    def acknowledge_alert(self, alert_name: str) -> bool:
        """Acknowledge an active alert."""
        with self._lock:
            alert = self._active_alerts.get(alert_name)
            if alert:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = time.time()
                return True
            return False

    def get_alert_history(self, limit: int = 50) -> list[dict]:
        """Get recent alert history."""
        with self._lock:
            recent = list(self._alert_history)[-limit:]
        return [
            {
                "id": a.id,
                "name": a.name,
                "severity": a.severity.value,
                "status": a.status.value,
                "message": a.message,
                "created_at": a.created_at,
                "resolved_at": a.resolved_at,
            }
            for a in recent
        ]


# ═══════════════════════════════════════════════════════════════════════
# Uptime Monitor
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class UptimeCheck:
    name: str
    url: str | None = None
    last_check: float = 0.0
    last_status: str = "unknown"
    last_latency_ms: float = 0.0
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0


class UptimeMonitor:
    """Track uptime for services and endpoints."""

    def __init__(self):
        self._checks: dict[str, UptimeCheck] = {}
        self._lock = threading.Lock()

        # Register default checks
        self.register_check("api", "Health endpoint")
        self.register_check("database", "Database connection")
        self.register_check("redis", "Redis connection")
        self.register_check("ai_engine", "AI engine (Ollama)")

    def register_check(self, name: str, description: str = "", url: str | None = None) -> None:
        """Register a new uptime check."""
        with self._lock:
            self._checks[name] = UptimeCheck(name=name, url=url, last_check=time.time())

    def record_check(self, name: str, success: bool, latency_ms: float = 0.0) -> None:
        """Record the result of an uptime check."""
        with self._lock:
            check = self._checks.get(name)
            if not check:
                check = UptimeCheck(name=name)
                self._checks[name] = check

            check.last_check = time.time()
            check.last_status = "healthy" if success else "unhealthy"
            check.last_latency_ms = latency_ms
            check.total_checks += 1

            if success:
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
                check.total_failures += 1

    def get_uptime_summary(self) -> dict[str, Any]:
        """Get uptime summary for all checks."""
        with self._lock:
            checks = dict(self._checks)

        results = {}
        for name, check in checks.items():
            uptime_pct = (
                ((check.total_checks - check.total_failures) / check.total_checks * 100)
                if check.total_checks > 0
                else 100.0
            )
            results[name] = {
                "status": check.last_status,
                "uptime_percent": round(uptime_pct, 3),
                "last_check": check.last_check,
                "last_latency_ms": check.last_latency_ms,
                "consecutive_failures": check.consecutive_failures,
                "total_checks": check.total_checks,
                "total_failures": check.total_failures,
            }

        return results


# ═══════════════════════════════════════════════════════════════════════
# Global Instances
# ═══════════════════════════════════════════════════════════════════════

sla_tracker = SLATracker()
alert_manager = AlertManager()
uptime_monitor = UptimeMonitor()


# ═══════════════════════════════════════════════════════════════════════
# Incident Tracking
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Incident:
    id: str
    title: str
    severity: AlertSeverity
    status: str  # investigating, identified, monitoring, resolved
    created_at: float
    acknowledged_at: float | None = None
    identified_at: float | None = None
    resolved_at: float | None = None
    timeline: list[dict[str, Any]] = field(default_factory=list)
    affected_services: list[str] = field(default_factory=list)
    root_cause: str | None = None


class IncidentTracker:
    """Track incidents through their lifecycle."""

    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._incident_history: deque[Incident] = deque(maxlen=200)
        self._lock = threading.Lock()
        self._counter = 0

    def create_incident(
        self,
        title: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        affected_services: list[str] | None = None,
    ) -> Incident:
        """Create a new incident."""
        with self._lock:
            self._counter += 1
            now = time.time()
            incident = Incident(
                id=f"INC-{self._counter:04d}",
                title=title,
                severity=severity,
                status="investigating",
                created_at=now,
                affected_services=affected_services or [],
                timeline=[
                    {"time": now, "status": "created", "message": f"Incident created: {title}"}
                ],
            )
            self._incidents[incident.id] = incident
            self._incident_history.append(incident)
        return incident

    def update_incident(
        self,
        incident_id: str,
        status: str,
        message: str,
        root_cause: str | None = None,
    ) -> Incident | None:
        """Update an incident's status."""
        with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                return None

            now = time.time()
            incident.status = status
            incident.timeline.append({"time": now, "status": status, "message": message})

            if status == "acknowledged":
                incident.acknowledged_at = now
            elif status == "identified":
                incident.identified_at = now
            elif status == "resolved":
                incident.resolved_at = now
            if root_cause:
                incident.root_cause = root_cause

        return incident

    def get_active_incidents(self) -> list[dict]:
        """Get all unresolved incidents."""
        with self._lock:
            active = [i for i in self._incidents.values() if i.status != "resolved"]
        return [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status,
                "age_seconds": round(time.time() - i.created_at),
                "affected_services": i.affected_services,
                "timeline": i.timeline[-5:],
            }
            for i in active
        ]

    def get_incident_history(self, limit: int = 20) -> list[dict]:
        """Get recent incident history."""
        with self._lock:
            recent = list(self._incident_history)[-limit:]
        return [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status,
                "created_at": i.created_at,
                "resolved_at": i.resolved_at,
                "duration_seconds": round(i.resolved_at - i.created_at) if i.resolved_at else None,
                "root_cause": i.root_cause,
            }
            for i in reversed(recent)
        ]


incident_tracker = IncidentTracker()
