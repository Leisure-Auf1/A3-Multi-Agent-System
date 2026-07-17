"""
Phase 5.8 — Plugin Registry

Central registry for RuntimePlugins. Supports register, unregister,
discovery, and query operations.

Usage:
    registry = PluginRegistry()
    registry.register(SecurityPlugin())
    plugin = registry.get("security_plugin")
    plugins = registry.list_by_tag("observability")
"""

from __future__ import annotations
from typing import Any, Dict, Iterator, List, Optional, Type

from .base import RuntimePlugin, PluginMetadata, PluginState


class PluginRegistry:
    """
    Central registry for all RuntimePlugins.

    Stores plugins by name with their metadata. Supports tag-based
    filtering and discovery.

    Usage:
        registry = PluginRegistry()
        registry.register(my_plugin, install=True)
        registry.discover()  # validates dependencies
    """

    def __init__(self):
        self._plugins: Dict[str, RuntimePlugin] = {}
        self._metadata: Dict[str, PluginMetadata] = {}
        self._disabled: Dict[str, RuntimePlugin] = {}

    # ── Registration ─────────────────────────

    def register(self, plugin: RuntimePlugin) -> None:
        """
        Register a plugin in the registry.

        Plugin must have a unique name. Sets state to INSTALLED.

        Raises ValueError if a plugin with the same name already exists.
        """
        name = plugin.meta.name
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' already registered")

        plugin._state = PluginState.INSTALLED
        self._plugins[name] = plugin
        self._metadata[name] = plugin.meta

    def unregister(self, name: str) -> Optional[RuntimePlugin]:
        """
        Remove a plugin from the registry.

        Returns the removed plugin, or None if not found.
        """
        self._metadata.pop(name, None)
        self._disabled.pop(name, None)
        plugin = self._plugins.pop(name, None)
        if plugin:
            plugin._state = PluginState.UNREGISTERED
        return plugin

    def disable(self, name: str) -> bool:
        """Move a plugin to the disabled list."""
        plugin = self._plugins.pop(name, None)
        if plugin is None:
            return False
        plugin._state = PluginState.DISABLED
        self._disabled[name] = plugin
        self._metadata.pop(name, None)
        return True

    def enable(self, name: str) -> bool:
        """Re-enable a disabled plugin."""
        plugin = self._disabled.pop(name, None)
        if plugin is None:
            return False
        plugin._state = PluginState.INSTALLED
        self._plugins[name] = plugin
        self._metadata[name] = plugin.meta
        return True

    # ── Query ────────────────────────────────

    def get(self, name: str) -> Optional[RuntimePlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name) or self._disabled.get(name)

    def get_metadata(self, name: str) -> Optional[PluginMetadata]:
        """Get a plugin's metadata."""
        return self._metadata.get(name)

    def list_all(self) -> List[RuntimePlugin]:
        """List all registered (non-disabled) plugins."""
        return list(self._plugins.values())

    def list_disabled(self) -> List[RuntimePlugin]:
        """List disabled plugins."""
        return list(self._disabled.values())

    def list_by_tag(self, tag: str) -> List[RuntimePlugin]:
        """List plugins with a specific tag."""
        return [
            p for p in self._plugins.values()
            if tag in p.meta.tags
        ]

    def list_by_state(self, state: PluginState) -> List[RuntimePlugin]:
        """List plugins in a specific lifecycle state."""
        return [
            p for p in self._plugins.values()
            if p.state == state
        ]

    def names(self) -> List[str]:
        """All registered plugin names."""
        return list(self._plugins.keys())

    # ── Discovery ─────────────────────────────

    def discover(self) -> Dict[str, Any]:
        """
        Validate dependencies and return a discovery report.

        Returns:
            Dict with 'valid', 'missing_deps', 'total', 'active' keys.
        """
        report = {
            "valid": True,
            "missing_deps": [],
            "total": len(self._plugins),
            "active": len([p for p in self._plugins.values() if p.state.is_operational]),
            "plugins": {name: p.meta.to_dict() for name, p in self._plugins.items()},
        }

        for name, plugin in self._plugins.items():
            for dep in plugin.meta.dependencies:
                if dep not in self._plugins:
                    report["valid"] = False
                    report["missing_deps"].append({
                        "plugin": name,
                        "missing_dependency": dep,
                    })

        return report

    # ── Bulk ──────────────────────────────────

    def clear(self) -> None:
        """Remove all plugins from the registry."""
        for p in self._plugins.values():
            p._state = PluginState.UNREGISTERED
        self._plugins.clear()
        self._metadata.clear()
        self._disabled.clear()

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        return name in self._plugins or name in self._disabled

    def __iter__(self) -> Iterator[RuntimePlugin]:
        return iter(self._plugins.values())
