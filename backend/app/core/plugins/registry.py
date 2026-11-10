"""Plugin Registry — the central engine for plugin lifecycle management.

Handles:
- Plugin discovery and loading from filesystem
- Plugin validation (manifest, permissions, compatibility)
- Plugin installation, enabling, disabling, removal
- Plugin execution with sandboxing and error isolation
- Plugin health monitoring
- Plugin execution logging

Usage::

    from app.core.plugins.registry import plugin_registry

    # Install a plugin
    plugin_registry.install(plugin_class)

    # Execute a plugin
    result = plugin_registry.execute("my-scanner", context)

    # Get all installed plugins
    plugins = plugin_registry.list_plugins()
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.plugins.sdk import (
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginStatus,
    PluginType,
)
from app.utils.logger import logger

# ═══════════════════════════════════════════════════════════════════════
# Plugin Registry
# ═══════════════════════════════════════════════════════════════════════


class PluginRegistry:
    """Central plugin registry managing the full plugin lifecycle.

    Plugins are loaded into memory and tracked by their unique ID.
    The registry provides execution sandboxing, health monitoring,
    and execution logging.
    """

    def __init__(self):
        self._plugins: dict[str, Any] = {}  # plugin_id -> plugin instance
        self._manifests: dict[str, PluginManifest] = {}  # plugin_id -> manifest
        self._status: dict[str, PluginStatus] = {}  # plugin_id -> status
        self._config: dict[str, dict] = {}  # plugin_id -> config
        self._execution_stats: dict[str, dict] = {}  # plugin_id -> stats
        self._health_cache: dict[str, dict] = {}  # plugin_id -> health
        self._execution_log: list[dict] = []

    # ── Plugin Installation ──────────────────────────────────────────

    def install(self, plugin_class: type, config: dict | None = None) -> PluginManifest:
        """Install a plugin from a class.

        The class must have a `manifest` attribute of type PluginManifest
        and implement the appropriate plugin interface.

        Returns the plugin manifest.
        """
        # Instantiate the plugin
        try:
            plugin_instance = plugin_class()
        except Exception as e:
            raise PluginInstallError(f"Failed to instantiate plugin: {e}") from e

        # Validate manifest
        manifest = getattr(plugin_instance, "manifest", None)
        if not manifest or not isinstance(manifest, PluginManifest):
            raise PluginInstallError(
                "Plugin must have a 'manifest' attribute of type PluginManifest"
            )

        # Validate required fields
        if not manifest.id:
            raise PluginInstallError("Plugin manifest must have an 'id'")
        if not manifest.name:
            raise PluginInstallError("Plugin manifest must have a 'name'")
        if not manifest.version:
            raise PluginInstallError("Plugin manifest must have a 'version'")

        # Check for duplicate
        if manifest.id in self._plugins:
            raise PluginInstallError(f"Plugin '{manifest.id}' is already installed")

        # Validate compatibility
        from app.config import get_settings

        settings = get_settings()
        if not manifest.is_compatible_with(settings.VERSION):
            raise PluginInstallError(
                f"Plugin '{manifest.id}' v{manifest.version} is not compatible "
                f"with platform v{settings.VERSION} "
                f"(requires >= {manifest.min_platform_version})"
            )

        # Validate dependencies
        for dep_id in manifest.dependencies:
            if dep_id not in self._plugins:
                raise PluginInstallError(
                    f"Plugin '{manifest.id}' depends on '{dep_id}' which is not installed"
                )

        # Initialize the plugin
        try:
            context = PluginContext(config=config or {})
            plugin_instance.initialize(context)
        except Exception as e:
            raise PluginInstallError(f"Plugin initialization failed: {e}") from e

        # Register
        self._plugins[manifest.id] = plugin_instance
        self._manifests[manifest.id] = manifest
        self._status[manifest.id] = PluginStatus.ENABLED
        self._config[manifest.id] = config or {}
        self._execution_stats[manifest.id] = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "avg_latency_ms": 0,
        }

        logger.info(
            f"Plugin installed: {manifest.name} v{manifest.version} "
            f"(type={manifest.plugin_type})"
        )
        return manifest

    def install_from_path(self, module_path: str) -> PluginManifest:
        """Install a plugin by loading a Python module from a file path.

        The module must define a top-level `plugin_class` variable
        or a class ending in `Plugin` that implements a plugin interface.
        """
        path = Path(module_path)
        if not path.exists():
            raise PluginInstallError(f"Plugin path not found: {module_path}")

        # Load the module
        module_name = f"sentinelai_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if not spec or not spec.loader:
            raise PluginInstallError(f"Cannot load module from: {module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise PluginInstallError(f"Failed to load plugin module: {e}") from e

        # Find the plugin class
        plugin_class = getattr(module, "plugin_class", None)
        if not plugin_class:
            # Try to find any class ending in Plugin
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and attr_name.endswith("Plugin")
                    and attr_name != "Plugin"
                ):
                    plugin_class = attr
                    break

        if not plugin_class:
            raise PluginInstallError(
                f"No plugin class found in {module_path}. "
                "Define 'plugin_class' or a class ending in 'Plugin'."
            )

        return self.install(plugin_class)

    # ── Plugin Lifecycle ─────────────────────────────────────────────

    def enable(self, plugin_id: str) -> bool:
        """Enable an installed plugin."""
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]
        try:
            context = PluginContext(config=self._config.get(plugin_id, {}))
            plugin.initialize(context)
        except Exception as e:
            self._status[plugin_id] = PluginStatus.ERROR
            logger.error(f"Failed to enable plugin '{plugin_id}': {e}")
            return False

        self._status[plugin_id] = PluginStatus.ENABLED
        logger.info(f"Plugin enabled: {plugin_id}")
        return True

    def disable(self, plugin_id: str) -> bool:
        """Disable a plugin without removing it."""
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]
        try:
            plugin.shutdown()
        except Exception as e:
            logger.warning(f"Error during plugin shutdown '{plugin_id}': {e}")

        self._status[plugin_id] = PluginStatus.DISABLED
        logger.info(f"Plugin disabled: {plugin_id}")
        return True

    def uninstall(self, plugin_id: str) -> bool:
        """Remove a plugin completely."""
        if plugin_id not in self._plugins:
            return False

        # Shutdown first
        self.disable(plugin_id)

        # Remove
        del self._plugins[plugin_id]
        del self._manifests[plugin_id]
        del self._status[plugin_id]
        self._config.pop(plugin_id, None)
        self._execution_stats.pop(plugin_id, None)
        self._health_cache.pop(plugin_id, None)

        logger.info(f"Plugin uninstalled: {plugin_id}")
        return True

    # ── Plugin Execution ─────────────────────────────────────────────

    def execute(
        self,
        plugin_id: str,
        method: str,
        context: PluginContext,
        **kwargs: Any,
    ) -> PluginResult:
        """Execute a plugin method with sandboxing.

        Wraps the execution in a try/except to isolate plugin failures
        from the main application. Records execution stats and logs.
        """
        if plugin_id not in self._plugins:
            return PluginResult.fail(plugin_id, f"Plugin '{plugin_id}' not found")

        if self._status.get(plugin_id) != PluginStatus.ENABLED:
            return PluginResult.fail(plugin_id, f"Plugin '{plugin_id}' is not enabled")

        plugin = self._plugins[plugin_id]
        target_method = getattr(plugin, method, None)
        if not target_method or not callable(target_method):
            return PluginResult.fail(plugin_id, f"Method '{method}' not found on plugin")

        # Check permissions
        self._manifests[plugin_id]
        # (Permission checking is done at a higher level via the API layer)

        # Execute with timing and error isolation
        start_time = time.time()
        try:
            result_data = target_method(context, **kwargs) if kwargs else target_method(context)
            duration_ms = (time.time() - start_time) * 1000

            # Update stats
            stats = self._execution_stats[plugin_id]
            stats["total"] += 1
            stats["success"] += 1
            n = stats["total"]
            stats["avg_latency_ms"] = (stats["avg_latency_ms"] * (n - 1) + duration_ms) / n

            # Log execution
            self._log_execution(plugin_id, context, "success", duration_ms)

            return PluginResult.ok(
                plugin_id,
                data=result_data,
                duration_ms=round(duration_ms, 2),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Update stats
            stats = self._execution_stats[plugin_id]
            stats["total"] += 1
            stats["failed"] += 1

            # Track consecutive failures
            if plugin_id in self._execution_stats:
                self._execution_stats[plugin_id]["consecutive_failures"] = (
                    self._execution_stats[plugin_id].get("consecutive_failures", 0) + 1
                )

            # Log execution
            self._log_execution(plugin_id, context, "error", duration_ms, str(e))

            logger.error(f"Plugin execution failed: {plugin_id}.{method} — {type(e).__name__}: {e}")

            return PluginResult.fail(
                plugin_id,
                error=f"{type(e).__name__}: {e}",
                duration_ms=round(duration_ms, 2),
            )

    # ── Plugin Queries ───────────────────────────────────────────────

    def get_plugin(self, plugin_id: str) -> Any | None:
        """Get a plugin instance by ID."""
        return self._plugins.get(plugin_id)

    def get_manifest(self, plugin_id: str) -> PluginManifest | None:
        """Get a plugin's manifest."""
        return self._manifests.get(plugin_id)

    def get_status(self, plugin_id: str) -> PluginStatus | None:
        """Get a plugin's current status."""
        return self._status.get(plugin_id)

    def get_config(self, plugin_id: str) -> dict:
        """Get a plugin's configuration."""
        return self._config.get(plugin_id, {})

    def is_installed(self, plugin_id: str) -> bool:
        """Check if a plugin is installed."""
        return plugin_id in self._plugins

    def is_enabled(self, plugin_id: str) -> bool:
        """Check if a plugin is enabled."""
        return self._status.get(plugin_id) == PluginStatus.ENABLED

    def list_plugins(
        self,
        plugin_type: PluginType | str | None = None,
        status: PluginStatus | None = None,
    ) -> list[dict]:
        """List all installed plugins with their status."""
        results = []
        for pid in self._plugins:
            manifest = self._manifests[pid]
            plugin_type_val = manifest.plugin_type
            if isinstance(plugin_type_val, PluginType):
                plugin_type_val = plugin_type_val.value

            if plugin_type and plugin_type_val != (
                plugin_type.value if isinstance(plugin_type, PluginType) else plugin_type
            ):
                continue

            plugin_status = self._status.get(pid)
            if status and plugin_status != status:
                continue

            stats = self._execution_stats.get(pid, {})
            results.append(
                {
                    "id": pid,
                    "name": manifest.name,
                    "version": manifest.version,
                    "plugin_type": plugin_type_val,
                    "description": manifest.description,
                    "author": manifest.author,
                    "status": plugin_status.value if plugin_status else "unknown",
                    "permissions": [
                        p.value if hasattr(p, "value") else p for p in manifest.permissions
                    ],
                    "tags": manifest.tags,
                    "executions": stats.get("total", 0),
                    "success_rate": round(
                        (stats.get("success", 0) / max(stats.get("total", 1), 1)) * 100, 1
                    ),
                    "avg_latency_ms": round(stats.get("avg_latency_ms", 0), 1),
                }
            )

        return sorted(results, key=lambda x: x["name"])

    def list_by_type(self, plugin_type: PluginType | str) -> list[str]:
        """List plugin IDs of a specific type."""
        type_val = plugin_type.value if isinstance(plugin_type, PluginType) else plugin_type
        return [
            pid
            for pid, manifest in self._manifests.items()
            if (
                manifest.plugin_type.value
                if isinstance(manifest.plugin_type, PluginType)
                else manifest.plugin_type
            )
            == type_val
            and self._status.get(pid) == PluginStatus.ENABLED
        ]

    # ── Health Monitoring ────────────────────────────────────────────

    def health_check(self, plugin_id: str) -> dict:
        """Run health check on a specific plugin."""
        if plugin_id not in self._plugins:
            return {"plugin_id": plugin_id, "healthy": False, "error": "Not found"}

        plugin = self._plugins[plugin_id]
        start = time.time()
        try:
            health = plugin.health_check()
            latency = (time.time() - start) * 1000
            result = {
                "plugin_id": plugin_id,
                "healthy": True,
                "latency_ms": round(latency, 2),
                **health,
            }
        except Exception as e:
            result = {
                "plugin_id": plugin_id,
                "healthy": False,
                "error": str(e),
            }

        self._health_cache[plugin_id] = result
        return result

    def health_check_all(self) -> list[dict]:
        """Run health check on all enabled plugins."""
        results = []
        for pid in self._plugins:
            if self._status.get(pid) == PluginStatus.ENABLED:
                results.append(self.health_check(pid))
        return results

    # ── Execution Log ────────────────────────────────────────────────

    def _log_execution(
        self,
        plugin_id: str,
        context: PluginContext,
        status: str,
        duration_ms: float,
        error: str | None = None,
    ) -> None:
        """Record a plugin execution."""
        log_entry = {
            "plugin_id": plugin_id,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "error": error,
            "organization_id": context.organization_id,
            "user_id": context.user_id,
            "correlation_id": context.correlation_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._execution_log.append(log_entry)
        # Keep last 1000 entries
        if len(self._execution_log) > 1000:
            self._execution_log = self._execution_log[-500:]

    def get_execution_log(
        self,
        plugin_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get recent plugin execution logs."""
        logs = self._execution_log
        if plugin_id:
            logs = [l for l in logs if l["plugin_id"] == plugin_id]
        return logs[-limit:]

    def get_execution_stats(self) -> dict:
        """Get aggregate execution statistics."""
        total = sum(s.get("total", 0) for s in self._execution_stats.values())
        success = sum(s.get("success", 0) for s in self._execution_stats.values())
        failed = sum(s.get("failed", 0) for s in self._execution_stats.values())
        return {
            "total_executions": total,
            "successful": success,
            "failed": failed,
            "success_rate": round((success / max(total, 1)) * 100, 1),
            "plugins_installed": len(self._plugins),
            "plugins_enabled": sum(1 for s in self._status.values() if s == PluginStatus.ENABLED),
        }


# ═══════════════════════════════════════════════════════════════════════
# Errors
# ═══════════════════════════════════════════════════════════════════════


class PluginInstallError(Exception):
    """Raised when a plugin fails to install."""

    pass


class PluginExecutionError(Exception):
    """Raised when a plugin execution fails critically."""

    pass


class PluginPermissionError(Exception):
    """Raised when a plugin lacks required permissions."""

    pass


# ═══════════════════════════════════════════════════════════════════════
# Global Registry Instance
# ═══════════════════════════════════════════════════════════════════════

plugin_registry = PluginRegistry()
