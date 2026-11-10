"""Security Events and Alert Center routes.

Provides:
- Security events listing with filtering
- Security statistics dashboard
- Threat intelligence overview
- Brute force analytics
- Session monitoring
- IP reputation lookup
"""

from fastapi import APIRouter, Depends, Query

from app.models.models import User
from app.utils.security import get_current_user
from app.utils.threat_detection import (
    check_ip_reputation,
    detect_brute_force_pattern,
    get_active_sessions,
    get_security_events,
    get_security_stats,
)

router = APIRouter(prefix="/api/security-events", tags=["Security Events"])


@router.get("/events")
def list_events(
    severity: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
):
    """List security events. Requires authentication."""
    events = get_security_events(severity=severity, category=category, limit=limit)
    return {"events": events, "count": len(events)}


@router.get("/stats")
def security_stats(
    current_user: User = Depends(get_current_user),
):
    """Get security statistics dashboard."""
    return get_security_stats()


@router.get("/ip/{ip_address}")
def ip_lookup(
    ip_address: str,
    current_user: User = Depends(get_current_user),
):
    """Look up IP reputation."""
    return check_ip_reputation(ip_address)


@router.get("/brute-force/{username}")
def brute_force_analysis(
    username: str,
    current_user: User = Depends(get_current_user),
):
    """Analyze brute force patterns for a user."""
    return detect_brute_force_pattern(username)


@router.get("/sessions")
def list_sessions(
    current_user: User = Depends(get_current_user),
):
    """List active sessions for the current user."""
    sessions = get_active_sessions(current_user.id)
    return {"sessions": sessions, "count": len(sessions)}


@router.get("/dashboard")
def security_dashboard(
    current_user: User = Depends(get_current_user),
):
    """Combined security dashboard data."""
    stats = get_security_stats()
    recent_events = get_security_events(limit=50)
    sessions = get_active_sessions(current_user.id)

    return {
        "stats": stats,
        "recent_events": recent_events,
        "active_sessions": sessions,
        "session_count": len(sessions),
    }
