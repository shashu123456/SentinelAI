"""Kubernetes-compatible health endpoints under /api/v1.

Endpoints:
    GET /api/v1/health   — Full health check with all component details
    GET /api/v1/ready    — Readiness probe (can the service accept traffic?)
    GET /api/v1/live     — Liveness probe (is the process alive?)
    GET /api/v1/version  — Version info (commit SHA, env, build)

Design:
    - /live must NEVER fail (only fails if the process is truly dead)
    - /ready fails if critical dependencies are down (DB, etc.)
    - /health returns full diagnostic information
    - /version exposes deployment metadata for diagnostics and CI/CD
"""

import time
import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.database import get_db
from app.utils.logger import logger
from app.utils.system_metrics import (
    collect_all_health,
    get_uptime,
)

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
def full_health(db: Session = Depends(get_db)):
    """Full health check with all component details."""
    health = collect_all_health()
    status_code = (
        200 if health["status"] == "healthy" else (207 if health["status"] == "degraded" else 503)
    )
    return JSONResponse(content=health, status_code=status_code)


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe.

    Returns 200 only if critical dependencies (database) are operational.
    Used by load balancers to decide if this instance should receive traffic.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "timestamp": time.time()}
    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        return JSONResponse(
            content={"status": "not_ready", "error": str(e), "timestamp": time.time()},
            status_code=503,
        )


@router.get("/live")
def liveness_check():
    """Kubernetes liveness probe.

    This endpoint must always return 200 unless the process is truly dead.
    It does NOT check external dependencies — only that the app is running.
    """
    return {
        "status": "alive",
        "uptime_seconds": round(get_uptime(), 0),
        "timestamp": time.time(),
    }


@router.get("/version")
def version_info():
    """Deployment version and commit info.

    Returns environment, build commit SHA, and SENTINEL_ENV.
    Used by health checks and CI/CD to verify deploy drift.
    """
    # Providers expose the deployed revision under different names.
    commit = (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("VERCEL_GIT_COMMIT_SHA")
        or os.getenv("COMMIT_SHA")
        or "dev"
    )
    env = os.getenv("SENTINEL_ENV", "dev")
    build = commit if commit != "dev" else "dev"
    return {
        "commit": commit,
        "env": env,
        "build": build[:7] if len(build) >= 7 else build,
    }
