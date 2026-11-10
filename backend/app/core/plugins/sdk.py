"""Plugin SDK for SentinelAI.

Defines the contracts that every plugin must implement. All plugin types
extend from a base PluginProtocol, with specialized interfaces for each
domain: scanner, report, AI provider, notification, and export.

Design Principles:
- Protocol-based: plugins are validated at load time via structural typing
- Minimal dependencies: plugins only need the SDK, not the full app
- Explicit permissions: plugins declare what they need
- Version-aware: plugins declare compatibility ranges

Usage::

    from app.core.plugins.sdk import (
        ScannerPlugin,
        PluginManifest,
        PluginContext,
        PluginPermission,
    )

    class MyScanner(ScannerPlugin):
        manifest = PluginManifest(
            id="my-scanner",
            name="My Custom Scanner",
            version="1.0.0",
            plugin_type="scanner",
            permissions=[PluginPermission.SCANNER_READ],
        )

        def scan(self, context: PluginContext) -> list[dict]:
            return [{"vulnerability_name": "Custom finding", "severity": "High"}]
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

# ═══════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════


class PluginType(str, Enum):
    SCANNER = "scanner"
    REPORT = "report"
    AI_PROVIDER = "ai_provider"
    NOTIFICATION = "notification"
    EXPORT = "export"
    AUTH_PROVIDER = "auth_provider"
    INTEGRATION = "integration"


class PluginPermission(str, Enum):
    """Granular permissions that plugins can request."""

    # Scanner permissions
    SCANNER_READ = "scanner:read"
    SCANNER_WRITE = "scanner:write"
    FINDINGS_READ = "findings:read"
    FINDINGS_WRITE = "findings:write"

    # Data permissions
    ORG_READ = "org:read"
    PROJECT_READ = "project:read"
    USER_READ = "user:read"
    SCAN_READ = "scan:read"

    # AI permissions
    AI_REQUEST = "ai:request"
    AI_CACHE = "ai:cache"

    # Notification permissions
    NOTIFICATION_SEND = "notification:send"

    # Export permissions
    EXPORT_READ = "export:read"
    EXPORT_WRITE = "export:write"

    # System permissions
    SETTINGS_READ = "settings:read"
    METRICS_READ = "metrics:read"
    WEBHOOK_SEND = "webhook:send"


class PluginStatus(str, Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UPDATING = "updating"


# ═══════════════════════════════════════════════════════════════════════
# Manifest
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class PluginManifest:
    """Plugin metadata and configuration.

    Every plugin MUST provide a manifest. The manifest is the source of truth
    for plugin identity, permissions, and compatibility.
    """

    id: str
    name: str
    version: str
    plugin_type: PluginType | str
    description: str = ""
    author: str = ""
    homepage: str = ""
    license: str = "MIT"

    # Compatibility
    min_platform_version: str = "1.0.0"
    max_platform_version: str = ""  # empty = no upper bound

    # Permissions required by this plugin
    permissions: list[PluginPermission | str] = field(default_factory=list)

    # Configuration schema (JSON Schema format)
    config_schema: dict[str, Any] = field(default_factory=dict)

    # Dependencies on other plugins
    dependencies: list[str] = field(default_factory=list)

    # Entry point module path
    entry_point: str = ""

    # Tags for marketplace search
    tags: list[str] = field(default_factory=list)

    # Icon URL for marketplace display
    icon_url: str = ""

    def is_compatible_with(self, platform_version: str) -> bool:
        """Check if this plugin is compatible with the given platform version."""
        from packaging.version import Version

        try:
            pv = Version(platform_version)
            min_v = (
                Version(self.min_platform_version)
                if self.min_platform_version
                else Version("0.0.0")
            )
            max_v = (
                Version(self.max_platform_version)
                if self.max_platform_version
                else Version("999.999.999")
            )
            return min_v <= pv <= max_v
        except Exception:
            return True  # If we can't parse, assume compatible

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "plugin_type": (
                self.plugin_type.value
                if isinstance(self.plugin_type, PluginType)
                else self.plugin_type
            ),
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "license": self.license,
            "min_platform_version": self.min_platform_version,
            "max_platform_version": self.max_platform_version,
            "permissions": [
                p.value if isinstance(p, PluginPermission) else p for p in self.permissions
            ],
            "config_schema": self.config_schema,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
            "tags": self.tags,
            "icon_url": self.icon_url,
        }


# ═══════════════════════════════════════════════════════════════════════
# Plugin Context
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class PluginContext:
    """Context passed to plugin execution.

    Provides read-only access to the application state that the plugin
    needs. Plugins never get direct DB access — they receive sanitized
    context objects.
    """

    # Organization context
    organization_id: int | None = None
    organization_name: str = ""

    # Project context
    project_id: int | None = None
    project_name: str = ""

    # User context
    user_id: int | None = None
    username: str = ""

    # Scan context (for scanner plugins)
    scan_id: int | None = None
    scan_type: str = ""

    # Plugin configuration
    config: dict[str, Any] = field(default_factory=dict)

    # Request correlation
    correlation_id: str = ""

    # Execution metadata
    started_at: float = field(default_factory=time.time)

    def elapsed_ms(self) -> float:
        """Milliseconds since context creation."""
        return round((time.time() - self.started_at) * 1000, 2)


# ═══════════════════════════════════════════════════════════════════════
# Base Plugin Protocol
# ═══════════════════════════════════════════════════════════════════════


@runtime_checkable
class PluginProtocol(Protocol):
    """Base protocol that all plugins must satisfy.

    Any class with a `manifest` attribute of type PluginManifest
    and an `initialize`/`shutdown` method satisfies this protocol.
    """

    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None:
        """Called when the plugin is loaded and enabled."""
        ...

    def shutdown(self) -> None:
        """Called when the plugin is disabled or unloaded."""
        ...

    def health_check(self) -> dict[str, Any]:
        """Return plugin health status."""
        ...


# ═══════════════════════════════════════════════════════════════════════
# Scanner Plugin Interface
# ═══════════════════════════════════════════════════════════════════════


class ScannerPlugin(ABC):
    """Base class for scanner plugins.

    Scanner plugins analyze API specifications, source code, or dependencies
    and return structured findings.

    The `scan` method receives a PluginContext with the scan configuration
    and returns a list of finding dictionaries matching the SentinelAI
    finding schema.
    """

    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None:
        """Called when the plugin is loaded. Override for setup logic."""
        return None

    def shutdown(self) -> None:
        """Called when the plugin is disabled. Override for cleanup logic."""
        return None

    def health_check(self) -> dict[str, Any]:
        """Return plugin health status."""
        return {"healthy": True}

    @abstractmethod
    def scan(self, context: PluginContext) -> list[dict[str, Any]]:
        """Execute a scan and return findings.

        Each finding dict must include:
            - vulnerability_name (str)
            - owasp_category (str)
            - severity (str): Critical, High, Medium, Low, Info
            - description (str)
            - evidence (str)
            - impact (str)
            - remediation (str)

        Optional fields:
            - cwe_id, affected_endpoint, affected_method, confidence,
              cvss_score, cvss_vector, detection_reason
        """
        ...

    def get_scan_types(self) -> list[str]:
        """Return the scan types this plugin supports."""
        return ["custom"]

    def get_supported_formats(self) -> list[str]:
        """Return supported input formats (openapi, swagger, yaml, json)."""
        return ["openapi"]


# ═══════════════════════════════════════════════════════════════════════
# Report Plugin Interface
# ═══════════════════════════════════════════════════════════════════════


class ReportPlugin(ABC):
    """Base class for report generation plugins.

    Report plugins transform scan findings into formatted reports.
    """

    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def health_check(self) -> dict[str, Any]:
        return {"healthy": True}

    @abstractmethod
    def generate(
        self,
        context: PluginContext,
        scan_data: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> bytes:
        """Generate a report and return as bytes.

        Args:
            context: Plugin execution context
            scan_data: Scan metadata (name, status, dates, etc.)
            findings: List of finding dictionaries

        Returns:
            Report content as bytes (PDF, HTML, JSON, etc.)
        """
        ...

    def get_format(self) -> str:
        """Return the output format of this report."""
        return "pdf"

    def get_mime_type(self) -> str:
        """Return the MIME type of generated reports."""
        return "application/pdf"


# ═══════════════════════════════════════════════════════════════════════
# AI Provider Interface
# ═══════════════════════════════════════════════════════════════════════


class AIProviderPlugin(ABC):
    """Base class for AI provider plugins.

    AI provider plugins wrap LLM services (OpenAI, Anthropic, local models)
    and provide a unified interface for the AI Copilot and analysis features.
    """

    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def health_check(self) -> dict[str, Any]:
        return {"healthy": True}

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        context: PluginContext | None = None,
    ) -> str:
        """Send a completion request to the AI provider.

        Returns the model's text response.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the AI provider is currently reachable."""
        ...

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return "unknown"

    def get_latency_ms(self) -> float:
        """Return the last request latency in milliseconds."""
        return 0.0


# ═══════════════════════════════════════════════════════════════════════
# Notification Provider Interface
# ═══════════════════════════════════════════════════════════════════════


class NotificationPlugin(ABC):
    """Base class for notification provider plugins.

    Notification plugins send alerts through various channels (Slack, Email,
    PagerDuty, Microsoft Teams, Discord, etc.)
    """

    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def health_check(self) -> dict[str, Any]:
        return {"healthy": True}

    @abstractmethod
    def send(
        self,
        *,
        title: str,
        message: str,
        severity: str = "info",
        recipients: list[str] | None = None,
        context: PluginContext | None = None,
    ) -> bool:
        """Send a notification.

        Returns True if the notification was sent successfully.
        """
        ...

    def send_batch(
        self,
        notifications: list[dict[str, Any]],
        context: PluginContext | None = None,
    ) -> list[bool]:
        """Send multiple notifications. Default: send one by one."""
        results = []
        for notif in notifications:
            results.append(self.send(**notif, context=context))
        return results

    def get_channel_type(self) -> str:
        """Return the channel type (slack, email, webhook, etc.)."""
        return "unknown"


# ═══════════════════════════════════════════════════════════════════════
# Export Provider Interface
# ═══════════════════════════════════════════════════════════════════════


class ExportPlugin(ABC):
    """Base class for data export plugins.

    Export plugins transform findings and scan data into various formats
    for integration with external systems (SIEM, ticketing, etc.)
    """

    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def health_check(self) -> dict[str, Any]:
        return {"healthy": True}

    @abstractmethod
    def export(
        self,
        context: PluginContext,
        scan_data: dict[str, Any],
        findings: list[dict[str, Any]],
        *,
        format: str = "json",
    ) -> bytes:
        """Export findings in the specified format.

        Returns the exported data as bytes.
        """
        ...

    def get_supported_formats(self) -> list[str]:
        """Return the export formats this plugin supports."""
        return ["json"]

    def get_content_type(self, format: str) -> str:
        """Return the MIME type for a given format."""
        content_types = {
            "json": "application/json",
            "csv": "text/csv",
            "sarif": "application/sarif+json",
            "xml": "application/xml",
            "pdf": "application/pdf",
        }
        return content_types.get(format, "application/octet-stream")


# ═══════════════════════════════════════════════════════════════════════
# Auth Provider Interface
# ═══════════════════════════════════════════════════════════════════════


class AuthProviderPlugin(ABC):
    """Base class for authentication provider plugins.

    Auth provider plugins enable SSO, SAML, LDAP, OAuth, and other
    enterprise authentication mechanisms.
    """

    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def health_check(self) -> dict[str, Any]:
        return {"healthy": True}

    @abstractmethod
    def authenticate(
        self,
        credentials: dict[str, Any],
        context: PluginContext | None = None,
    ) -> dict[str, Any]:
        """Authenticate a user with the given credentials.

        Returns a dict with:
            - success (bool)
            - user_info (dict): email, name, groups, etc.
            - error (str | None): error message if failed
        """
        ...

    @abstractmethod
    def get_login_url(self, callback_url: str) -> str:
        """Return the URL to redirect users for login."""
        ...

    def get_provider_name(self) -> str:
        """Return the name of this auth provider."""
        return "unknown"

    def supports_sso(self) -> bool:
        """Whether this provider supports Single Sign-On."""
        return False


# ═══════════════════════════════════════════════════════════════════════
# Plugin Result Types
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class PluginResult:
    """Standardized result from plugin execution."""

    success: bool
    plugin_id: str
    data: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, plugin_id: str, data: Any = None, **meta: Any) -> PluginResult:
        return cls(success=True, plugin_id=plugin_id, data=data, metadata=meta)

    @classmethod
    def fail(cls, plugin_id: str, error: str, **meta: Any) -> PluginResult:
        return cls(success=False, plugin_id=plugin_id, error=error, metadata=meta)


@dataclass
class PluginHealthStatus:
    """Plugin health report."""

    plugin_id: str
    healthy: bool
    message: str = ""
    latency_ms: float = 0.0
    last_check: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)
