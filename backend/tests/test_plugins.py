"""Plugin system tests.

Tests cover:
- Plugin SDK (manifest, context, protocol)
- Plugin installation, enabling, disabling, uninstalling
- Plugin execution with sandboxing
- Plugin health checks
- Plugin listing and filtering
- Plugin execution logs and stats
- Example plugin: Security Headers Scanner
- Error handling and edge cases
"""

import pytest

from app.core.plugins.sdk import (
    PluginContext,
    PluginManifest,
    PluginPermission,
    PluginResult,
    PluginStatus,
    PluginType,
    ScannerPlugin,
)
from app.core.plugins.registry import (
    PluginRegistry,
    PluginInstallError,
    plugin_registry,
)
from app.core.plugins.examples.security_headers_scanner import (
    SecurityHeadersScannerPlugin,
)


# ═══════════════════════════════════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def fresh_registry():
    """Create a fresh plugin registry for each test."""
    return PluginRegistry()


class MockScannerPlugin(ScannerPlugin):
    """Simple mock scanner for testing."""

    manifest = PluginManifest(
        id="mock-scanner",
        name="Mock Scanner",
        version="1.0.0",
        plugin_type="scanner",
        description="A mock scanner for testing",
        author="Test",
        permissions=[PluginPermission.SCANNER_READ],
        tags=["test", "mock"],
    )

    def scan(self, context: PluginContext) -> list[dict]:
        return [
            {
                "vulnerability_name": "Mock Finding",
                "owasp_category": "API1",
                "severity": "High",
                "description": "A mock vulnerability for testing",
                "evidence": "Mock evidence",
                "impact": "Mock impact",
                "remediation": "Mock remediation",
            }
        ]


class FailingPlugin(ScannerPlugin):
    """Plugin that fails during execution."""

    manifest = PluginManifest(
        id="failing-plugin",
        name="Failing Plugin",
        version="1.0.0",
        plugin_type="scanner",
        description="A plugin that always fails",
    )

    def scan(self, context: PluginContext) -> list[dict]:
        raise RuntimeError("Intentional failure for testing")

    def health_check(self) -> dict:
        return {"healthy": False, "error": "Always failing"}


class HealthCheckPlugin(ScannerPlugin):
    """Plugin with a custom health check."""

    manifest = PluginManifest(
        id="health-plugin",
        name="Health Check Plugin",
        version="1.0.0",
        plugin_type="scanner",
        description="Plugin with custom health check",
    )

    def scan(self, context: PluginContext) -> list[dict]:
        return []

    def health_check(self) -> dict:
        return {"healthy": True, "message": "All good", "custom": "data"}


# ═══════════════════════════════════════════════════════════════════════
# Manifest Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPluginManifest:
    """Test plugin manifest creation and serialization."""

    def test_manifest_creation(self):
        manifest = PluginManifest(
            id="test",
            name="Test Plugin",
            version="1.0.0",
            plugin_type="scanner",
        )
        assert manifest.id == "test"
        assert manifest.name == "Test Plugin"
        assert manifest.version == "1.0.0"

    def test_manifest_to_dict(self):
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            plugin_type="scanner",
            permissions=[PluginPermission.SCANNER_READ],
            tags=["test"],
        )
        d = manifest.to_dict()
        assert d["id"] == "test"
        assert d["permissions"] == ["scanner:read"]
        assert d["tags"] == ["test"]

    def test_compatibility_check(self):
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            plugin_type="scanner",
            min_platform_version="1.0.0",
            max_platform_version="2.0.0",
        )
        assert manifest.is_compatible_with("1.5.0") is True
        assert manifest.is_compatible_with("0.9.0") is False
        assert manifest.is_compatible_with("2.1.0") is False

    def test_compatibility_no_upper_bound(self):
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            plugin_type="scanner",
            min_platform_version="1.0.0",
        )
        assert manifest.is_compatible_with("99.0.0") is True


# ═══════════════════════════════════════════════════════════════════════
# Plugin Context Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPluginContext:
    """Test plugin context creation and usage."""

    def test_context_creation(self):
        ctx = PluginContext(
            organization_id=1,
            organization_name="Test Org",
            user_id=42,
            username="testuser",
        )
        assert ctx.organization_id == 1
        assert ctx.user_id == 42
        assert ctx.elapsed_ms() >= 0

    def test_context_with_config(self):
        ctx = PluginContext(config={"api_key": "secret", "timeout": 30})
        assert ctx.config["api_key"] == "secret"


# ═══════════════════════════════════════════════════════════════════════
# Plugin Result Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPluginResult:
    """Test plugin result creation."""

    def test_ok_result(self):
        result = PluginResult.ok("test", data={"count": 5})
        assert result.success is True
        assert result.data["count"] == 5

    def test_fail_result(self):
        result = PluginResult.fail("test", error="Something broke")
        assert result.success is False
        assert result.error == "Something broke"


# ═══════════════════════════════════════════════════════════════════════
# Plugin Registry Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPluginRegistry:
    """Test plugin registry operations."""

    def test_install_plugin(self, fresh_registry):
        manifest = fresh_registry.install(MockScannerPlugin)
        assert manifest.id == "mock-scanner"
        assert fresh_registry.is_installed("mock-scanner")

    def test_install_duplicate_raises(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        with pytest.raises(PluginInstallError, match="already installed"):
            fresh_registry.install(MockScannerPlugin)

    def test_install_invalid_manifest(self, fresh_registry):
        class BadPlugin:
            manifest = "not a manifest"

        with pytest.raises(PluginInstallError, match="PluginManifest"):
            fresh_registry.install(BadPlugin)

    def test_enable_disable(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        assert fresh_registry.is_enabled("mock-scanner")

        fresh_registry.disable("mock-scanner")
        assert not fresh_registry.is_enabled("mock-scanner")

        fresh_registry.enable("mock-scanner")
        assert fresh_registry.is_enabled("mock-scanner")

    def test_uninstall(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        result = fresh_registry.uninstall("mock-scanner")
        assert result is True
        assert not fresh_registry.is_installed("mock-scanner")

    def test_uninstall_nonexistent(self, fresh_registry):
        result = fresh_registry.uninstall("nonexistent")
        assert result is False

    def test_list_plugins(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        plugins = fresh_registry.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["id"] == "mock-scanner"

    def test_list_plugins_by_type(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        scanners = fresh_registry.list_plugins(plugin_type="scanner")
        assert len(scanners) == 1
        reports = fresh_registry.list_plugins(plugin_type="report")
        assert len(reports) == 0


# ═══════════════════════════════════════════════════════════════════════
# Plugin Execution Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPluginExecution:
    """Test plugin execution with sandboxing."""

    def test_successful_execution(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        context = PluginContext(user_id=1)
        result = fresh_registry.execute("mock-scanner", "scan", context)
        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.data) == 1

    def test_execution_not_found(self, fresh_registry):
        context = PluginContext()
        result = fresh_registry.execute("nonexistent", "scan", context)
        assert result.success is False
        assert "not found" in result.error

    def test_execution_disabled_plugin(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        fresh_registry.disable("mock-scanner")
        context = PluginContext()
        result = fresh_registry.execute("mock-scanner", "scan", context)
        assert result.success is False
        assert "not enabled" in result.error

    def test_execution_invalid_method(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        context = PluginContext()
        result = fresh_registry.execute("mock-scanner", "nonexistent_method", context)
        assert result.success is False
        assert "not found" in result.error

    def test_execution_error_isolation(self, fresh_registry):
        fresh_registry.install(FailingPlugin)
        context = PluginContext()
        result = fresh_registry.execute("failing-plugin", "scan", context)
        assert result.success is False
        assert "Intentional failure" in result.error
        # Registry should still be functional
        assert fresh_registry.is_installed("failing-plugin")

    def test_execution_records_stats(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        context = PluginContext()
        fresh_registry.execute("mock-scanner", "scan", context)
        stats = fresh_registry._execution_stats["mock-scanner"]
        assert stats["total"] == 1
        assert stats["success"] == 1

    def test_execution_logs(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        context = PluginContext(user_id=42)
        fresh_registry.execute("mock-scanner", "scan", context)
        logs = fresh_registry.get_execution_log(plugin_id="mock-scanner")
        assert len(logs) == 1
        assert logs[0]["plugin_id"] == "mock-scanner"
        assert logs[0]["status"] == "success"


# ═══════════════════════════════════════════════════════════════════════
# Plugin Health Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPluginHealth:
    """Test plugin health monitoring."""

    def test_health_check(self, fresh_registry):
        fresh_registry.install(HealthCheckPlugin)
        health = fresh_registry.health_check("health-plugin")
        assert health["healthy"] is True
        assert health["message"] == "All good"

    def test_health_check_failing(self, fresh_registry):
        fresh_registry.install(FailingPlugin)
        health = fresh_registry.health_check("failing-plugin")
        assert health["healthy"] is False

    def test_health_check_all(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        fresh_registry.install(HealthCheckPlugin)
        results = fresh_registry.health_check_all()
        assert len(results) == 2


# ═══════════════════════════════════════════════════════════════════════
# Example Plugin Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSecurityHeadersScanner:
    """Test the Security Headers Scanner example plugin."""

    def test_install_example_plugin(self, fresh_registry):
        manifest = fresh_registry.install(SecurityHeadersScannerPlugin)
        assert manifest.id == "security-headers-scanner"
        assert manifest.plugin_type == "scanner"

    def test_scan_finds_missing_headers(self, fresh_registry):
        fresh_registry.install(SecurityHeadersScannerPlugin)
        context = PluginContext(
            config={
                "parsed_api": {
                    "servers": [{"url": "http://example.com"}],
                    "endpoints": [],
                }
            }
        )
        result = fresh_registry.execute(
            "security-headers-scanner", "scan", context
        )
        assert result.success is True
        assert len(result.data) > 0
        # Should find HTTPS not enforced
        assert any("HTTPS" in f["vulnerability_name"] for f in result.data)

    def test_scan_types(self):
        plugin = SecurityHeadersScannerPlugin()
        assert "security_headers" in plugin.get_scan_types()


# ═══════════════════════════════════════════════════════════════════════
# Aggregate Stats Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAggregateStats:
    """Test aggregate execution statistics."""

    def test_stats_empty(self, fresh_registry):
        stats = fresh_registry.get_execution_stats()
        assert stats["total_executions"] == 0
        assert stats["plugins_installed"] == 0

    def test_stats_after_execution(self, fresh_registry):
        fresh_registry.install(MockScannerPlugin)
        context = PluginContext()
        fresh_registry.execute("mock-scanner", "scan", context)
        stats = fresh_registry.get_execution_stats()
        assert stats["total_executions"] == 1
        assert stats["successful"] == 1
        assert stats["plugins_installed"] == 1
        assert stats["plugins_enabled"] == 1
