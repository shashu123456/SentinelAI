"""Plugin System API routes.

Endpoints for plugin management: install, enable, disable, uninstall,
execute, health check, and listing.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import User
from app.api.routes.auth import get_current_user
from app.core.plugins.registry import plugin_registry, PluginInstallError
from app.core.plugins.sdk import PluginContext, PluginType, PluginStatus

router = APIRouter(prefix="/api/plugins", tags=["Plugin System"])


# ── Plugin Listing ────────────────────────────────────────────────────


@router.get("/")
def list_plugins(
    plugin_type: str | None = Query(None),
    current_user: User = Depends(get_current_user),
):
    """List all installed plugins."""
    plugins = plugin_registry.list_plugins(plugin_type=plugin_type)
    return {"plugins": plugins, "count": len(plugins)}


@router.get("/stats")
def plugin_stats(
    current_user: User = Depends(get_current_user),
):
    """Get plugin system statistics."""
    return plugin_registry.get_execution_stats()


@router.get("/types")
def plugin_types(
    current_user: User = Depends(get_current_user),
):
    """List available plugin types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in PluginType
        ]
    }


# ── Plugin Details ────────────────────────────────────────────────────


@router.get("/{plugin_id}")
def get_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific plugin."""
    manifest = plugin_registry.get_manifest(plugin_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    stats = plugin_registry._execution_stats.get(plugin_id, {})
    return {
        "manifest": manifest.to_dict(),
        "status": plugin_registry.get_status(plugin_id).value
        if plugin_registry.get_status(plugin_id)
        else "unknown",
        "config": plugin_registry.get_config(plugin_id),
        "stats": stats,
    }


# ── Plugin Lifecycle ──────────────────────────────────────────────────


@router.post("/{plugin_id}/enable")
def enable_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
):
    """Enable an installed plugin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if not plugin_registry.is_installed(plugin_id):
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    result = plugin_registry.enable(plugin_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to enable plugin")

    return {"message": f"Plugin '{plugin_id}' enabled", "status": "enabled"}


@router.post("/{plugin_id}/disable")
def disable_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
):
    """Disable an installed plugin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if not plugin_registry.is_installed(plugin_id):
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    result = plugin_registry.disable(plugin_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to disable plugin")

    return {"message": f"Plugin '{plugin_id}' disabled", "status": "disabled"}


@router.delete("/{plugin_id}")
def uninstall_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
):
    """Uninstall a plugin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if not plugin_registry.is_installed(plugin_id):
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    result = plugin_registry.uninstall(plugin_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to uninstall plugin")

    return {"message": f"Plugin '{plugin_id}' uninstalled"}


# ── Plugin Execution ──────────────────────────────────────────────────


@router.post("/{plugin_id}/execute/{method}")
def execute_plugin(
    plugin_id: str,
    method: str,
    current_user: User = Depends(get_current_user),
):
    """Execute a plugin method."""
    if not plugin_registry.is_installed(plugin_id):
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    if not plugin_registry.is_enabled(plugin_id):
        raise HTTPException(status_code=400, detail=f"Plugin '{plugin_id}' is not enabled")

    context = PluginContext(
        user_id=current_user.id,
        username=current_user.username,
    )

    result = plugin_registry.execute(plugin_id, method, context)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "data": result.data,
        "duration_ms": result.duration_ms,
    }


# ── Plugin Health ────────────────────────────────────────────────────


@router.get("/{plugin_id}/health")
def plugin_health(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
):
    """Run health check on a specific plugin."""
    return plugin_registry.health_check(plugin_id)


@router.get("/health/all")
def all_plugins_health(
    current_user: User = Depends(get_current_user),
):
    """Run health check on all enabled plugins."""
    return {"results": plugin_registry.health_check_all()}


# ── Execution Logs ────────────────────────────────────────────────────


@router.get("/{plugin_id}/logs")
def plugin_logs(
    plugin_id: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    """Get execution logs for a plugin."""
    logs = plugin_registry.get_execution_log(plugin_id=plugin_id, limit=limit)
    return {"logs": logs, "count": len(logs)}
