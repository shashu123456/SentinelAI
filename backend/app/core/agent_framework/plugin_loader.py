from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from app.core.agent_framework.agent_registry import AgentRegistry, RegistryScope, get_registry
from app.core.agent_framework.base_agent import BaseAgent
from app.core.agent_framework.shared_models import (
    AgentHealthInfo,
    AgentMetadata,
)


class PluginDiscoveryError(Exception):
    """Raised when plugin discovery fails."""

    pass


class PluginValidationError(Exception):
    """Raised when plugin validation fails."""

    pass


class PluginDependencyError(Exception):
    """Raised when plugin dependencies are not met."""

    pass


class PluginLoader:
    """Discovers, loads, and validates agent plugins.

    The Plugin Loader supports:
        - Automatic discovery of plugins in specified packages/directories
        - Registration of discovered agents with the AgentRegistry
        - Version checking against required versions
        - Dependency checking for plugin requirements
        - Plugin lifecycle management
        - Support for third-party plugins without code changes

    Plugins are expected to be Python packages with a standard structure:
        - A top-level package directory
        - A module containing a create_agent() or register() function
        - A metadata.json or similar configuration file
    """

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        """Initialize the Plugin Loader.

        Args:
            registry: Optional AgentRegistry instance. If None, uses the global registry.
        """
        self._registry: AgentRegistry = registry if registry is not None else get_registry()
        self._plugin_packages: list[str] = []
        self._loaded_plugins: dict[str, BaseAgent] = {}

    def discover_plugins(
        self,
        package_names: list[str] | None = None,
        search_dirs: list[str] | None = None,
    ) -> list[tuple[str, str, str]]:
        """Discover plugin packages in the given directories or packages.

        Args:
            package_names: List of Python package names to search within.
                If None, searches default packages.
            search_dirs: List of directory paths to scan for plugins.
                If None, uses default search paths.

        Returns:
            List of tuples (package_name, module_name, file_path) for discovered plugins.

        Raises:
            PluginDiscoveryError: If plugin discovery fails.
        """
        packages: list[str] = package_names or self._get_default_packages()
        discovered: list[tuple[str, str, str]] = []

        for package_name in packages:
            try:
                package = importlib.import_module(package_name)
                # Safely get package path; may be None for namespace packages
                if package.__file__ is not None:
                    package_path = Path(package.__file__).parent
                else:
                    # Fallback: use the package's __path__ if available
                    package_path = Path(getattr(package, "__path__", [None])[0] or "")

                # Walk the package directory for plugin submodules
                if package_path.exists():
                    for importer, modname, ispkg in pkgutil.iter_modules(
                        [package_path], prefix=f"{package_name}."
                    ):
                        discovered.append(
                            (package_name, modname, str(package_path / modname.replace(".", "/")))
                        )

            except ImportError:
                # Package not installed; try searching directories
                if search_dirs:
                    for search_dir in search_dirs:
                        try:
                            package_path = Path(search_dir) / package_name
                            if package_path.is_dir():
                                for importer, modname, ispkg in pkgutil.iter_modules(
                                    [package_path], prefix=f"{package_name}."
                                ):
                                    discovered.append(
                                        (
                                            package_name,
                                            modname,
                                            str(package_path / modname.replace(".", "/")),
                                        )
                                    )
                        except Exception:
                            continue

        return discovered

    def load_plugin(
        self,
        package_name: str,
        module_name: str,
        required_version: str | None = None,
        required_capabilities: list[str] | None = None,
    ) -> BaseAgent:
        """Load a plugin from a package and module.

        Args:
            package_name: The Python package name.
            module_name: The module name within the package.
            required_version: Optional required version string.
            required_capabilities: Optional list of required capabilities.

        Returns:
            A BaseAgent instance from the plugin.

        Raises:
            PluginDiscoveryError: If the plugin cannot be found or loaded.
            PluginValidationError: If the plugin validation fails.
            PluginDependencyError: If dependency checks fail.
        """
        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Look for plugin registration functions
            agent = None

            # Try common plugin entry points
            for attr_name in ["create_agent", "register_agent", "get_agent", "agent"]:
                if hasattr(module, attr_name):
                    attr = getattr(module, attr_name)
                    if callable(attr):
                        if (
                            attr_name == "create_agent"
                            or attr_name == "register_agent"
                            or attr_name == "get_agent"
                        ):
                            agent = attr()
                        break

            if agent is None:
                raise PluginValidationError(
                    f"No plugin entry point found in {module_name}.{package_name}"
                )

            # Validate the agent
            if not isinstance(agent, BaseAgent):
                raise PluginValidationError(
                    f"Plugin agent is not a BaseAgent subclass: {type(agent)}"
                )

            # Version checking
            if required_version:
                agent_version = getattr(agent, "metadata", None)
                if agent_version and agent_version.version:
                    if not self._version_meets_requirement(agent_version.version, required_version):
                        raise PluginDependencyError(
                            f"Agent version {agent_version.version} does not meet "
                            f"requirement {required_version}"
                        )

            # Capability checking
            if required_capabilities:
                agent_capabilities = getattr(agent, "capabilities", []) or []
                missing = [c for c in required_capabilities if c not in agent_capabilities]
                if missing:
                    raise PluginDependencyError(f"Agent missing required capabilities: {missing}")

            # Register with registry
            self._registry.register(agent, scope=RegistryScope.PLUGIN)

            # Track loaded plugin
            plugin_id = agent.metadata.id
            self._loaded_plugins[plugin_id] = agent

            return agent

        except Exception as exc:
            # Re-raise specific exceptions, wrap others
            if isinstance(
                exc, (PluginDiscoveryError, PluginValidationError, PluginDependencyError)
            ):
                raise
            raise PluginValidationError(
                f"Failed to load plugin {module_name} from {package_name}: {exc}"
            )

    def _version_meets_requirement(self, version: str, requirement: str) -> bool:
        """Check if a version meets a requirement.

        Simple version comparison - can be replaced with packaging.version
        for more sophisticated semantic versioning.

        Args:
            version: The agent's version string.
            requirement: The required version string.

        Returns:
            True if the version meets the requirement.
        """
        # Simple comparison: exact match or >=
        try:
            from packaging import version as pkg_version

            return pkg_version.parse(version) >= pkg_version.parse(requirement)
        except ImportError:
            # Fallback to simple string comparison
            return version >= requirement

    def unload_plugin(self, agent_id: str) -> BaseAgent | None:
        """Unload a previously loaded plugin.

        Args:
            agent_id: The agent's unique ID.

        Returns:
            The unloaded agent instance, or None if not found.
        """
        agent = self._registry.unregister(agent_id)
        if agent:
            self._loaded_plugins.pop(agent_id, None)
        return agent

    def list_loaded_plugins(self) -> list[BaseAgent]:
        """List all currently loaded plugins.

        Returns:
            List of loaded BaseAgent instances.
        """
        return list(self._loaded_plugins.values())

    def list_plugin_metadata(self) -> list[AgentMetadata]:
        """Get metadata for all loaded plugins.

        Returns:
            List of AgentMetadata instances.
        """
        return [agent.metadata for agent in self._loaded_plugins.values()]

    def check_plugin_health(self, agent_id: str) -> AgentHealthInfo:
        """Check the health of a loaded plugin.

        Args:
            agent_id: The agent's unique ID.

        Returns:
            AgentHealthInfo for the plugin.

        Raises:
            PluginDependencyError: If the plugin is not loaded.
        """
        agent = self._loaded_plugins.get(agent_id)
        if agent is None:
            raise PluginDependencyError(f"Plugin not loaded: {agent_id}")

        return agent.health_check()

    def validate_all_loaded_plugins(self) -> list[tuple[str, bool, str | None]]:
        """Validate all currently loaded plugins.

        Returns:
            List of tuples (agent_id, is_healthy, error_message).
        """
        results: list[tuple[str, bool, str | None]] = []
        for agent_id in self._loaded_plugins:
            try:
                health = self.check_plugin_health(agent_id)
                results.append((agent_id, health.healthy, health.error))
            except Exception as exc:
                results.append((agent_id, False, str(exc)))
        return results

    def _get_default_packages(self) -> list[str]:
        """Get the default package names to search for plugins.

        Returns:
            List of package names.
        """
        # Default to looking in the agent_framework package and common plugin locations
        return [
            "app.core.agent_framework",
            "sentinelai",
            "sentinelai.plugins",
        ]


# ------------------------------------------------------------------ #
# Convenience Functions
# ------------------------------------------------------------------ #


def load_plugins_from_dir(
    directory: str,
    registry: AgentRegistry | None = None,
    recursive: bool = True,
) -> list[BaseAgent]:
    """Load all plugins from a directory.

    Args:
        directory: The directory path to search for plugins.
        registry: Optional AgentRegistry instance.
        recursive: Whether to search recursively subdirectories.

    Returns:
        List of loaded BaseAgent instances.
    """
    loader = PluginLoader(registry=registry)
    discovered = loader.discover_plugins(search_dirs=[directory])

    loaded: list[BaseAgent] = []
    for package_name, module_name, file_path in discovered:
        try:
            agent = loader.load_plugin(package_name, module_name)
            loaded.append(agent)
        except Exception:
            # Continue loading other plugins even if one fails
            pass

    return loaded


def auto_discover_plugins(
    registry: AgentRegistry | None = None,
    package_names: list[str] | None = None,
    search_dirs: list[str] | None = None,
) -> list[BaseAgent]:
    """Automatically discover and load all available plugins.

    Args:
        registry: Optional AgentRegistry instance.
        package_names: List of Python package names to search.
        search_dirs: List of directory paths to scan.

    Returns:
        List of loaded BaseAgent instances from discovered plugins.
    """
    loader = PluginLoader(registry=registry)
    discovered = loader.discover_plugins(package_names, search_dirs)

    loaded: list[BaseAgent] = []
    for package_name, module_name, file_path in discovered:
        try:
            agent = loader.load_plugin(package_name, module_name)
            loaded.append(agent)
        except Exception:
            # Continue loading other plugins even if one fails
            pass

    return loaded
