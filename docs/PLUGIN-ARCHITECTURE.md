# SentinelAI — Plugin Architecture

> Extensible plugin system for scanners, reports, AI providers, notifications, exports, and authentication providers.

---

## Overview

SentinelAI's plugin system enables third-party developers and security teams to extend the platform without modifying core code. Every capability — scanning, reporting, AI analysis, notifications, exports, and authentication — is available as a pluggable interface.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Plugin System                              │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│ Scanner  │ Report   │ AI       │ Notif    │ Export   │ Auth     │
│ Plugin   │ Plugin   │ Provider │ Plugin   │ Plugin   │ Provider │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────────┤
│                    Plugin Registry                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Discovery│ │ Loading  │ │ Sandbox  │ │ Health Monitor   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Plugin Types

| Type | Interface | Purpose |
|------|-----------|---------|
| `scanner` | `ScannerPlugin` | Analyze APIs, code, dependencies for vulnerabilities |
| `report` | `ReportPlugin` | Generate formatted reports (PDF, HTML, etc.) |
| `ai_provider` | `AIProviderPlugin` | Wrap LLM services for AI Copilot |
| `notification` | `NotificationPlugin` | Send alerts via Slack, Email, PagerDuty, etc. |
| `export` | `ExportPlugin` | Export findings to SIEM, ticketing, etc. |
| `auth_provider` | `AuthProviderPlugin` | SSO, SAML, LDAP, OAuth integration |
| `integration` | Custom | Any other platform extension |

---

## Creating a Plugin

### 1. Define the Manifest

```python
from app.core.plugins.sdk import PluginManifest, PluginPermission

manifest = PluginManifest(
    id="my-custom-scanner",
    name="My Custom Scanner",
    version="1.0.0",
    plugin_type="scanner",
    description="Scans for custom security patterns",
    author="Your Name",
    min_platform_version="1.0.0",
    permissions=[
        PluginPermission.SCANNER_READ,
        PluginPermission.FINDINGS_WRITE,
    ],
    tags=["security", "custom"],
)
```

### 2. Implement the Interface

```python
from app.core.plugins.sdk import ScannerPlugin, PluginContext

class MyScannerPlugin(ScannerPlugin):
    manifest = PluginManifest(...)

    def scan(self, context: PluginContext) -> list[dict]:
        # Your scanning logic here
        return [
            {
                "vulnerability_name": "Custom Finding",
                "owasp_category": "API1",
                "severity": "High",
                "description": "...",
                "evidence": "...",
                "impact": "...",
                "remediation": "...",
            }
        ]
```

### 3. Register the Plugin

```python
from app.core.plugins.registry import plugin_registry

# In-memory registration
plugin_registry.install(MyScannerPlugin)

# Or load from file
plugin_registry.install_from_path("/path/to/my_plugin.py")
```

---

## Plugin Interface Contracts

### ScannerPlugin

```python
class ScannerPlugin(ABC):
    manifest: PluginManifest

    def initialize(self, context: PluginContext) -> None: ...
    def shutdown(self) -> None: ...
    def health_check(self) -> dict: ...

    @abstractmethod
    def scan(self, context: PluginContext) -> list[dict]: ...

    def get_scan_types(self) -> list[str]: ...
    def get_supported_formats(self) -> list[str]: ...
```

**Finding Schema:**
```python
{
    "vulnerability_name": str,       # Required
    "owasp_category": str,           # Required (API1-API10)
    "severity": str,                 # Required (Critical/High/Medium/Low/Info)
    "description": str,              # Required
    "evidence": str,                 # Required
    "impact": str,                   # Required
    "remediation": str,              # Required
    "cwe_id": str,                   # Optional
    "confidence": int,               # Optional (0-100)
    "cvss_score": float,             # Optional
    "cvss_vector": str,              # Optional
    "affected_endpoint": str,        # Optional
    "affected_method": str,          # Optional
}
```

### ReportPlugin

```python
class ReportPlugin(ABC):
    @abstractmethod
    def generate(self, context, scan_data, findings) -> bytes: ...
    def get_format(self) -> str: ...
    def get_mime_type(self) -> str: ...
```

### AIProviderPlugin

```python
class AIProviderPlugin(ABC):
    @abstractmethod
    def complete(self, prompt, *, system_prompt="", temperature=0.3, ...) -> str: ...
    @abstractmethod
    def is_available(self) -> bool: ...
    def get_model_name(self) -> str: ...
```

### NotificationPlugin

```python
class NotificationPlugin(ABC):
    @abstractmethod
    def send(self, *, title, message, severity="info", recipients=None) -> bool: ...
    def get_channel_type(self) -> str: ...
```

### ExportPlugin

```python
class ExportPlugin(ABC):
    @abstractmethod
    def export(self, context, scan_data, findings, *, format="json") -> bytes: ...
    def get_supported_formats(self) -> list[str]: ...
    def get_content_type(self, format: str) -> str: ...
```

### AuthProviderPlugin

```python
class AuthProviderPlugin(ABC):
    @abstractmethod
    def authenticate(self, credentials, context=None) -> dict: ...
    @abstractmethod
    def get_login_url(self, callback_url: str) -> str: ...
    def supports_sso(self) -> bool: ...
```

---

## Plugin Lifecycle

```
install() → initialize() → ENABLED → execute() → disable() → shutdown() → REMOVED
                                    ↕
                              health_check()
```

### States

| State | Description |
|-------|-------------|
| `installed` | Plugin loaded but not yet enabled |
| `enabled` | Active and ready for execution |
| `disabled` | Temporarily inactive |
| `error` | Plugin encountered a critical error |
| `updating` | Plugin is being updated |

---

## Permissions

Plugins declare required permissions in their manifest. The registry validates permissions at install time.

| Permission | Description |
|------------|-------------|
| `scanner:read` | Read scanner configuration |
| `scanner:write` | Write scanner results |
| `findings:read` | Read finding data |
| `findings:write` | Create/update findings |
| `org:read` | Read organization data |
| `project:read` | Read project data |
| `user:read` | Read user data |
| `scan:read` | Read scan data |
| `ai:request` | Make AI provider requests |
| `notification:send` | Send notifications |
| `export:read` | Read export data |
| `export:write` | Create exports |
| `webhook:send` | Send webhooks |

---

## Execution Sandboxing

Plugin execution is isolated from the main application:

1. **Error Isolation**: Plugin failures are caught and logged, never crash the host
2. **Timeout Protection**: Plugins can be executed with timeout limits
3. **Resource Monitoring**: Execution stats track latency, success rate, and failures
4. **Consecutive Failure Detection**: Plugins that fail repeatedly are flagged
5. **Execution Logging**: Every execution is logged with correlation IDs

---

## Version Compatibility

```python
manifest = PluginManifest(
    id="my-plugin",
    name="My Plugin",
    version="2.0.0",
    min_platform_version="1.5.0",  # Minimum SentinelAI version
    max_platform_version="2.0.0",  # Maximum SentinelAI version (optional)
    ...
)
```

The registry validates compatibility before installation.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/plugins/` | List all plugins |
| GET | `/api/plugins/stats` | Plugin system statistics |
| GET | `/api/plugins/types` | Available plugin types |
| GET | `/api/plugins/{id}` | Plugin details |
| POST | `/api/plugins/{id}/enable` | Enable a plugin |
| POST | `/api/plugins/{id}/disable` | Disable a plugin |
| DELETE | `/api/plugins/{id}` | Uninstall a plugin |
| POST | `/api/plugins/{id}/execute/{method}` | Execute a plugin method |
| GET | `/api/plugins/{id}/health` | Plugin health check |
| GET | `/api/plugins/health/all` | All plugins health |
| GET | `/api/plugins/{id}/logs` | Plugin execution logs |

---

## Example: Security Headers Scanner

The included example plugin demonstrates:

- Manifest with permissions and tags
- Scanner interface implementation
- Finding generation with CVSS scoring
- Integration with existing SentinelAI utilities

```bash
# Install the example plugin
curl -X POST http://localhost:8000/api/plugins/install \
  -H "Content-Type: application/json" \
  -d '{"module_path": "app/core/plugins/examples/security_headers_scanner.py"}'

# Execute a scan
curl -X POST http://localhost:8000/api/plugins/security-headers-scanner/execute/scan
```

---

## Writing a New Plugin

### Step 1: Choose the interface

Pick the plugin type that matches your use case:
- Scanning APIs or code → `ScannerPlugin`
- Generating reports → `ReportPlugin`
- Wrapping an LLM → `AIProviderPlugin`
- Sending notifications → `NotificationPlugin`
- Exporting data → `ExportPlugin`
- Adding SSO → `AuthProviderPlugin`

### Step 2: Define the manifest

Set `id`, `name`, `version`, `plugin_type`, and `permissions`.

### Step 3: Implement the abstract methods

At minimum, implement the core method for your plugin type (e.g., `scan` for scanners).

### Step 4: Add optional methods

Override `initialize()`, `shutdown()`, `health_check()` for lifecycle management.

### Step 5: Test

Use `PluginRegistry` directly in tests:

```python
from app.core.plugins.registry import PluginRegistry

def test_my_plugin():
    registry = PluginRegistry()
    registry.install(MyPlugin)
    result = registry.execute("my-plugin", "scan", PluginContext())
    assert result.success
```

### Step 6: Distribute

Save as a `.py` file. Users install via:
```python
plugin_registry.install_from_path("path/to/my_plugin.py")
```

---

## Architecture Decisions

### Why Protocol-based interfaces?
- Structural typing allows plugins without inheriting from base classes
- Easier to implement in different Python styles (classes, functions)
- Better IDE support with type checking

### Why in-memory registry?
- Plugins are loaded at startup, not from a database
- Fast execution without DB overhead
- Easy to test and reason about
- Persistence handled separately via database models

### Why error isolation?
- Third-party plugins should never crash the host application
- Execution stats track failure rates for health monitoring
- Consecutive failure detection enables automatic degradation

### Why permission-based?
- Plugins declare what they need, not what they take
- Granular permissions enable least-privilege access
- Enterprise customers can audit plugin access patterns
