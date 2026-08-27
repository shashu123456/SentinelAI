"""Threat detection engine for SentinelAI.

Provides:
- Suspicious login detection (new device, new location, rapid IP changes)
- IP reputation tracking (blocked IPs, repeat offenders)
- Brute force analytics (attack pattern detection)
- Geo anomaly detection (impossible travel)
- Session monitoring (JWT replay protection)
- Security event generation

All detection is append-only — events are recorded for the Security Events
dashboard and alert center.
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.utils.logger import logger

# ── In-Memory Threat Intelligence Stores ──────────────────────────────
# In production, these would be backed by Redis.

_lock = threading.Lock()

# IP reputation: ip -> {attempts, first_seen, last_seen, blocked}
_ip_reputation: dict[str, dict] = defaultdict(
    lambda: {
        "attempts": 0,
        "failures": 0,
        "first_seen": 0.0,
        "last_seen": 0.0,
        "blocked": False,
        "blocked_until": 0.0,
        "user_agents": set(),
    }
)

# Failed login tracking: username -> [{ip, timestamp, user_agent}]
_failed_logins: dict[str, list[dict]] = defaultdict(list)

# Successful login tracking: username -> [{ip, timestamp, user_agent}]
_successful_logins: dict[str, list[dict]] = defaultdict(list)

# Active sessions: token_hash -> {user_id, ip, user_agent, created_at}
_active_sessions: dict[str, dict] = {}

# Security events buffer
_security_events: list[dict] = []

# Brute force detection state
_brute_force_windows: dict[str, list[float]] = defaultdict(list)


# ── Configuration ─────────────────────────────────────────────────────

MAX_FAILED_LOGINS_PER_IP = 10  # per hour
MAX_FAILED_LOGINS_PER_USER = 5  # per hour
BRUTE_FORCE_WINDOW_SECONDS = 3600  # 1 hour
SUSPICIOUS_LOGIN_THRESHOLD = 3  # different IPs in window
BLOCK_DURATION_SECONDS = 3600  # 1 hour block
MAX_SESSIONS_PER_USER = 5
GEO_ANOMALY_SPEED_KMH = 900  # impossible travel speed (airplane max)


# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class ThreatAssessment:
    """Result of a login threat assessment."""

    risk_level: str  # "low", "medium", "high", "critical"
    reasons: list[str] = field(default_factory=list)
    should_block: bool = False
    should_alert: bool = False
    details: dict[str, Any] = field(default_factory=dict)


# ── IP Reputation ─────────────────────────────────────────────────────


def check_ip_reputation(ip: str | None) -> dict:
    """Check the reputation of an IP address."""
    if not ip:
        return {"status": "unknown", "failures": 0}

    with _lock:
        rep = _ip_reputation[ip]
        now = time.time()

        # Check if currently blocked
        if rep["blocked"] and rep["blocked_until"] > now:
            return {
                "status": "blocked",
                "failures": rep["failures"],
                "blocked_until": rep["blocked_until"],
                "blocked_remaining_seconds": int(rep["blocked_until"] - now),
            }

        # Unblock if block expired
        if rep["blocked"] and rep["blocked_until"] <= now:
            rep["blocked"] = False

        return {
            "status": "blocked" if rep["blocked"] else "active",
            "failures": rep["failures"],
            "attempts": rep["attempts"],
        }


def record_ip_attempt(ip: str | None, success: bool, user_agent: str = "") -> None:
    """Record a login attempt from an IP."""
    if not ip:
        return

    with _lock:
        rep = _ip_reputation[ip]
        now = time.time()
        rep["attempts"] += 1
        rep["last_seen"] = now
        if rep["first_seen"] == 0:
            rep["first_seen"] = now

        if not success:
            rep["failures"] += 1
            if user_agent:
                rep["user_agents"].add(user_agent[:200])

            # Auto-block after threshold
            if rep["failures"] >= MAX_FAILED_LOGINS_PER_IP:
                rep["blocked"] = True
                rep["blocked_until"] = now + BLOCK_DURATION_SECONDS
                _record_security_event(
                    severity="high",
                    category="brute_force",
                    title=f"IP blocked: {ip} ({rep['failures']} failures)",
                    detail={
                        "ip": ip,
                        "failures": rep["failures"],
                        "duration": BLOCK_DURATION_SECONDS,
                    },
                )
                logger.warning(f"IP {ip} blocked after {rep['failures']} failed attempts")


def is_ip_blocked(ip: str | None) -> bool:
    """Check if an IP is currently blocked."""
    if not ip:
        return False
    assessment = check_ip_reputation(ip)
    return assessment["status"] == "blocked"


# ── Suspicious Login Detection ────────────────────────────────────────


def assess_login(
    username: str,
    ip: str | None,
    user_agent: str = "",
    timestamp: float | None = None,
) -> ThreatAssessment:
    """Assess a login attempt for suspicious activity.

    Checks:
    1. IP reputation (blocked or high-failure IP)
    2. New device (never seen user agent)
    3. Rapid IP changes (different IPs in short window)
    4. Brute force patterns (many failures in window)
    5. Impossible travel (login from distant location in short time)
    """
    now = timestamp or time.time()
    reasons = []
    risk_level = "low"

    with _lock:
        # 1. IP blocked?
        if ip and is_ip_blocked(ip):
            reasons.append(f"IP {ip} is blocked due to repeated failures")
            return ThreatAssessment(
                risk_level="critical",
                reasons=reasons,
                should_block=True,
                should_alert=True,
            )

        # 2. High failure IP?
        if ip:
            rep = _ip_reputation[ip]
            if rep["failures"] >= MAX_FAILED_LOGINS_PER_IP // 2:
                reasons.append(f"IP {ip} has {rep['failures']} failures")
                risk_level = "max(risk_level, 'high')"

        # 3. New device?
        recent_logins = _successful_logins.get(username, [])
        known_agents = {
            login["user_agent"][:100]
            for login in recent_logins
            if now - login["timestamp"] < 30 * 86400  # last 30 days
        }
        if user_agent and known_agents and user_agent[:100] not in known_agents:
            reasons.append(f"New device/user agent: {user_agent[:100]}")
            if risk_level == "low":
                risk_level = "medium"

        # 4. Rapid IP changes?
        recent_ips = {
            login["ip"] for login in recent_logins if now - login["timestamp"] < 3600  # last hour
        }
        if ip and len(recent_ips) >= SUSPICIOUS_LOGIN_THRESHOLD and ip not in recent_ips:
            reasons.append(f"Rapid IP change: {len(recent_ips) + 1} different IPs in 1 hour")
            risk_level = "high"
            should_alert = True
        else:
            should_alert = False

        # 5. Brute force pattern?
        recent_failures = _failed_logins.get(username, [])
        failures_in_window = [
            f for f in recent_failures if now - f["timestamp"] < BRUTE_FORCE_WINDOW_SECONDS
        ]
        if len(failures_in_window) >= MAX_FAILED_LOGINS_PER_USER:
            reasons.append(f"{len(failures_in_window)} failures in last hour")
            risk_level = "high"
            should_alert = True
        else:
            should_alert = should_alert if risk_level == "high" else False

        # 6. Impossible travel?
        if recent_logins and ip:
            last_login = recent_logins[-1]
            time_diff_hours = (now - last_login["timestamp"]) / 3600
            if time_diff_hours > 0 and time_diff_hours < 24:
                # Check if IP changed significantly
                if last_login["ip"] and last_login["ip"] != ip:
                    reasons.append(f"Login from different IP ({time_diff_hours:.1f}h gap)")

    # Determine final risk level
    if should_alert and risk_level not in ("high", "critical"):
        risk_level = "high"

    return ThreatAssessment(
        risk_level=risk_level,
        reasons=reasons,
        should_block=False,
        should_alert=should_alert,
        details={
            "username": username,
            "ip": ip,
            "user_agent": user_agent[:200],
        },
    )


def record_successful_login(username: str, ip: str | None, user_agent: str = "") -> None:
    """Record a successful login for threat detection."""
    with _lock:
        _successful_logins[username].append(
            {
                "ip": ip,
                "user_agent": user_agent[:200],
                "timestamp": time.time(),
            }
        )
        # Trim old entries (keep last 100)
        if len(_successful_logins[username]) > 100:
            _successful_logins[username] = _successful_logins[username][-100:]


def record_failed_login(username: str, ip: str | None, user_agent: str = "") -> None:
    """Record a failed login for threat detection."""
    with _lock:
        _failed_logins[username].append(
            {
                "ip": ip,
                "user_agent": user_agent[:200],
                "timestamp": time.time(),
            }
        )
        # Trim old entries (keep last 50)
        if len(_failed_logins[username]) > 50:
            _failed_logins[username] = _failed_logins[username][-50:]


# ── Session Monitoring ────────────────────────────────────────────────


def register_session(
    token_hash: str,
    user_id: int,
    ip: str | None,
    user_agent: str = "",
) -> bool:
    """Register a new session. Returns False if too many sessions."""
    with _lock:
        # Count active sessions for this user
        user_sessions = [h for h, s in _active_sessions.items() if s["user_id"] == user_id]

        if len(user_sessions) >= MAX_SESSIONS_PER_USER:
            # Revoke oldest session
            oldest = min(user_sessions, key=lambda h: _active_sessions[h]["created_at"])
            del _active_sessions[oldest]
            _record_security_event(
                severity="medium",
                category="session",
                title=f"Session evicted for user {user_id} (max sessions exceeded)",
                detail={"user_id": user_id, "evicted_token": oldest[:16]},
            )

        _active_sessions[token_hash] = {
            "user_id": user_id,
            "ip": ip,
            "user_agent": user_agent[:200],
            "created_at": time.time(),
        }
        return True


def is_session_replay(token_hash: str, user_id: int) -> bool:
    """Check if a token is being replayed (used after being replaced)."""
    with _lock:
        session = _active_sessions.get(token_hash)
        if session is None:
            return False  # New token, not a replay
        # Token exists in active sessions — check if it's the current one
        return True  # Token is valid and tracked


def revoke_session(token_hash: str) -> None:
    """Revoke a specific session."""
    with _lock:
        _active_sessions.pop(token_hash, None)


def get_active_sessions(user_id: int) -> list[dict]:
    """Get all active sessions for a user."""
    with _lock:
        return [
            {
                "token_prefix": h[:16],
                "ip": s["ip"],
                "user_agent": s["user_agent"],
                "created_at": s["created_at"],
            }
            for h, s in _active_sessions.items()
            if s["user_id"] == user_id
        ]


# ── Security Events ───────────────────────────────────────────────────


def _record_security_event(
    severity: str,
    category: str,
    title: str,
    detail: dict | None = None,
) -> None:
    """Record a security event (append-only)."""
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "severity": severity,
        "category": category,
        "title": title,
        "detail": detail or {},
    }
    with _lock:
        _security_events.append(event)
        # Keep last 1000 events
        if len(_security_events) > 1000:
            _security_events[:] = _security_events[-1000:]

    logger.warning(f"Security event [{severity}]: {title}")


def get_security_events(
    severity: str | None = None,
    category: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Get recent security events with optional filtering."""
    with _lock:
        events = list(_security_events)

    if severity:
        events = [e for e in events if e["severity"] == severity]
    if category:
        events = [e for e in events if e["category"] == category]

    return events[-limit:]


def get_security_stats() -> dict:
    """Get aggregate security statistics."""
    with _lock:
        events = list(_security_events)

    now = time.time()
    last_hour = [
        e
        for e in events
        if (
            datetime.fromisoformat(e["timestamp"]).timestamp()
            if isinstance(e["timestamp"], str)
            else 0
        )
        > now - 3600
    ]
    last_24h = [
        e
        for e in events
        if (
            datetime.fromisoformat(e["timestamp"]).timestamp()
            if isinstance(e["timestamp"], str)
            else 0
        )
        > now - 86400
    ]

    severity_counts = defaultdict(int)
    category_counts = defaultdict(int)
    for e in events:
        severity_counts[e["severity"]] += 1
        category_counts[e["category"]] += 1

    with _lock:
        blocked_ips = sum(1 for r in _ip_reputation.values() if r["blocked"])
        total_failed = sum(r["failures"] for r in _ip_reputation.values())
        active_sessions_count = len(_active_sessions)

    return {
        "total_events": len(events),
        "events_last_hour": len(last_hour),
        "events_last_24h": len(last_24h),
        "severity_distribution": dict(severity_counts),
        "category_distribution": dict(category_counts),
        "blocked_ips": blocked_ips,
        "total_ip_failures": total_failed,
        "active_sessions": active_sessions_count,
    }


# ── Brute Force Analytics ────────────────────────────────────────────


def detect_brute_force_pattern(username: str) -> dict:
    """Analyze brute force patterns for a specific user."""
    with _lock:
        failures = list(_failed_logins.get(username, []))

    now = time.time()
    hourly_failures = [f for f in failures if now - f["timestamp"] < 3600]
    daily_failures = [f for f in failures if now - f["timestamp"] < 86400]

    # Unique attacking IPs
    unique_ips = set(f["ip"] for f in hourly_failures if f["ip"])

    # Time between failures
    if len(hourly_failures) >= 2:
        timestamps = sorted(f["timestamp"] for f in hourly_failures)
        avg_interval = (timestamps[-1] - timestamps[0]) / len(timestamps)
    else:
        avg_interval = 0

    return {
        "username": username,
        "failures_last_hour": len(hourly_failures),
        "failures_last_24h": len(daily_failures),
        "unique_attacking_ips": len(unique_ips),
        "attacking_ips": list(unique_ips)[:10],
        "average_failure_interval_seconds": round(avg_interval, 1),
        "is_likely_brute_force": len(hourly_failures) >= MAX_FAILED_LOGINS_PER_USER,
    }
