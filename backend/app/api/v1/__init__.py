"""Version 1 API surface.

Exposes enveloped, paginated, filtered read endpoints under ``/api/v1``.
Legacy ``/api/*`` routes keep their original shapes for backward compatibility.
"""

from fastapi import APIRouter

from app.api.v1.routers import dashboard, findings, health, scans

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health.router)
v1_router.include_router(scans.router)
v1_router.include_router(findings.router)
v1_router.include_router(dashboard.router)

__all__ = ["v1_router"]
