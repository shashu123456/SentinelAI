"""SentinelAI Plugin System.

Provides a modular, extensible plugin architecture for scanners, reports,
AI providers, notifications, exports, and authentication providers.
"""

from app.core.plugins.registry import (
    PluginInstallError,
    PluginRegistry,
    plugin_registry,
)
from app.core.plugins.sdk import (
    AIProviderPlugin,
    AuthProviderPlugin,
    ExportPlugin,
    NotificationPlugin,
    PluginContext,
    PluginManifest,
    PluginPermission,
    PluginProtocol,
    PluginResult,
    PluginStatus,
    PluginType,
    ReportPlugin,
    ScannerPlugin,
)

__all__ = [
    "PluginContext",
    "PluginManifest",
    "PluginPermission",
    "PluginProtocol",
    "PluginResult",
    "PluginStatus",
    "PluginType",
    "ScannerPlugin",
    "ReportPlugin",
    "AIProviderPlugin",
    "NotificationPlugin",
    "ExportPlugin",
    "AuthProviderPlugin",
    "PluginRegistry",
    "PluginInstallError",
    "plugin_registry",
]
