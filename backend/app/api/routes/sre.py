"""SRE & Observability API routes for SentinelAI.

Endpoints for:
- Circuit breaker status and control
- SLA dashboard and error budget
- Alert management
- Uptime monitoring
- Incident tracking
- Distributed tracing
- Resilience patterns

All routes require authentication.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import User
from app.api.routes.auth import get_current_user
from app.utils.resilience import get_resilience_status
from app.utils.sla import (
    alert_manager,
    incident_tracker,
    sla_tracker,
    uptime_monitor,
    AlertSeverity,
)
from app.utils.tracing import get_recent_spans, get_trace_spans, clear_spans
from app.utils.performance import get_performance_stats, get_cache_stats, get_cpu_stats

router = APIRouter(prefix="/api/sre", tags=["SRE & Observability"])


# ── Resilience ────────────────────────────────────────────────────────


@router.get("/resilience")
def resilience_status(
    current_user: User = Depends(get_current_user),
):
    """Get status of all circuit breakers and bulkheads."""
    return get_resilience_status()


# ── SLA Dashboard ────────────────────────────────────────────────────


@router.get("/sla")
def sla_dashboard(
    current_user: User = Depends(get_current_user),
):
    """Get SLA compliance dashboard with availability, latency, error rate, and error budget."""
    return sla_tracker.get_sla_summary()


@router.get("/sla/error-budget")
def error_budget(
    current_user: User = Depends(get_current_user),
):
    """Get error budget status and burn rate."""
    return sla_tracker.get_error_budget()


@router.get("/sla/availability")
def availability(
    current_user: User = Depends(get_current_user),
):
    """Get current availability metrics."""
    return sla_tracker.get_availability()


@router.get("/sla/latency")
def latency(
    current_user: User = Depends(get_current_user),
):
    """Get latency percentile metrics."""
    return sla_tracker.get_latency()


# ── Alerts ────────────────────────────────────────────────────────────


@router.get("/alerts")
def list_alerts(
    current_user: User = Depends(get_current_user),
):
    """Get all active alerts."""
    return {"alerts": alert_manager.get_active_alerts()}


@router.post("/alerts/{alert_name}/acknowledge")
def acknowledge_alert(
    alert_name: str,
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an active alert."""
    result = alert_manager.acknowledge_alert(alert_name)
    if not result:
        return {"error": "Alert not found or already resolved"}
    return {"message": f"Alert '{alert_name}' acknowledged"}


@router.get("/alerts/history")
def alert_history(
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
):
    """Get alert history."""
    return {"alerts": alert_manager.get_alert_history(limit=limit)}


@router.post("/alerts/check")
def check_alerts(
    current_user: User = Depends(get_current_user),
):
    """Manually trigger alert threshold check."""
    fired = alert_manager.check_thresholds(sla_tracker)
    return {
        "fired": len(fired),
        "alerts": [
            {"name": a.name, "severity": a.severity.value, "message": a.message}
            for a in fired
        ],
    }


# ── Uptime ────────────────────────────────────────────────────────────


@router.get("/uptime")
def uptime_status(
    current_user: User = Depends(get_current_user),
):
    """Get uptime status for all monitored services."""
    return uptime_monitor.get_uptime_summary()


# ── Incidents ─────────────────────────────────────────────────────────


@router.get("/incidents")
def list_incidents(
    current_user: User = Depends(get_current_user),
):
    """Get all active incidents."""
    return {"incidents": incident_tracker.get_active_incidents()}


@router.get("/incidents/history")
def incident_history(
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
):
    """Get incident history."""
    return {"incidents": incident_tracker.get_incident_history(limit=limit)}


@router.post("/incidents")
def create_incident(
    title: str = Query(...),
    severity: str = Query("warning"),
    current_user: User = Depends(get_current_user),
):
    """Create a new incident."""
    sev = AlertSeverity(severity) if severity in AlertSeverity.__members__.values() else AlertSeverity.WARNING
    incident = incident_tracker.create_incident(title=title, severity=sev)
    return {"incident_id": incident.id, "message": "Incident created"}


@router.post("/incidents/{incident_id}/update")
def update_incident(
    incident_id: str,
    status: str = Query(...),
    message: str = Query(""),
    root_cause: str | None = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Update an incident's status."""
    incident = incident_tracker.update_incident(
        incident_id, status=status, message=message, root_cause=root_cause
    )
    if not incident:
        return {"error": "Incident not found"}
    return {"message": f"Incident {incident_id} updated to {status}"}


# ── Tracing ──────────────────────────────────────────────────────────


@router.get("/traces")
def recent_traces(
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
):
    """Get recent trace spans."""
    return {"spans": get_recent_spans(limit=limit)}


@router.get("/traces/{trace_id}")
def trace_detail(
    trace_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get all spans for a specific trace."""
    return {"trace_id": trace_id, "spans": get_trace_spans(trace_id)}


@router.delete("/traces")
def clear_traces(
    current_user: User = Depends(get_current_user),
):
    """Clear trace storage."""
    clear_spans()
    return {"message": "Traces cleared"}


# ── Performance ──────────────────────────────────────────────────────


@router.get("/performance")
def performance_dashboard(
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive performance metrics."""
    return {
        "requests": get_performance_stats(),
        "cache": get_cache_stats(),
        "cpu": get_cpu_stats(),
    }
