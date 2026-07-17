"""
Phase 5.8 — Plugin Manager

Orchestrates the full plugin lifecycle: install → initialize → start →
stop → disable → remove. Manages the registry, loader, and hook bridge.

Usage:
    manager = PluginManager(registry)
    manager.install(my_plugin)
    manager.initialize_all(runtime_engine)
    manager.start_all()
    engine.add_hook(manager.bridge)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from .base import RuntimePlugin, PluginState, PluginMetadata
from .registry import PluginRegistry
from .loader import PluginLoader
from .bridge import PluginHookBridge


class PluginManager:
    """
    Manages the full lifecycle of RuntimePlugins.

    Coordinates registry, loader, and hook bridge. Plugins flow
    through: install → initialize → start → (stop) → disable → remove.

    Usage:
        registry = PluginRegistry()
        manager = PluginManager(registry)

        manager.install(SecurityPlugin())
        manager.initialize_all(engine)
        manager.start_all()

        engine.add_hook(manager.bridge)  # plugins receive events
        engine.run()

        manager.stop_all()
        manager.shutdown_all()
    """

    def __init__(
        self,
        registry: Optional[PluginRegistry] = None,
        loader: Optional[PluginLoader] = None,
        bridge: Optional[PluginHookBridge] = None,
    ):
        self._registry = registry or PluginRegistry()
        self._loader = loader or PluginLoader(self._registry)
        self._bridge = bridge or PluginHookBridge()
        self._runtime: Any = None

    # ── Install / Remove ──────────────────────

    def install(self, plugin: RuntimePlugin) -> RuntimePlugin:
        """
        Install a plugin into the registry.

        Returns the plugin (for chaining).
        """
        self._registry.register(plugin)
        return plugin

    def install_from_path(
        self,
        module_path: str,
        class_name: str,
    ) -> Optional[RuntimePlugin]:
        """Load and install a plugin from a module path."""
        plugin = self._loader.load(module_path, class_name, register=True)
        return plugin

    def remove(self, name: str) -> bool:
        """
        Remove a plugin from the registry.

        Automatically stops and shuts down the plugin first.
        Returns False if the plugin doesn't exist.
        """
        plugin = self._registry.get(name)
        if plugin is None:
            return False

        # Graceful shutdown
        if plugin.state == PluginState.STARTED:
            try:
                plugin.stop()
            except Exception:
                pass
        if plugin.state in (PluginState.INITIALIZED, PluginState.STOPPED):
            try:
                plugin.shutdown()
            except Exception:
                pass

        self._bridge.remove_plugin(plugin)
        self._registry.unregister(name)
        return True

    # ── Lifecycle ─────────────────────────────

    def initialize_all(self, runtime: Any) -> List[str]:
        """
        Initialize all installed plugins with the RuntimeEngine.

        Plugins are initialized in priority order (higher priority first).
        Returns list of plugin names that successfully initialized.
        """
        self._runtime = runtime
        initialized = []

        # Sort by priority (descending)
        plugins = sorted(
            self._registry.list_all(),
            key=lambda p: p.meta.priority,
            reverse=True,
        )

        for plugin in plugins:
            try:
                plugin.initialize(runtime)
                initialized.append(plugin.meta.name)
            except Exception:
                pass  # skip failed initializations

        return initialized

    def start_all(self) -> List[str]:
        """
        Start all initialized plugins.

        Returns list of plugin names that started successfully.
        """
        started = []
        for plugin in self._registry.list_all():
            if plugin.state == PluginState.INITIALIZED:
                try:
                    plugin.start()
                    self._bridge.add_plugin(plugin)
                    started.append(plugin.meta.name)
                except Exception:
                    pass
        return started

    def stop_all(self) -> List[str]:
        """Stop all started plugins."""
        stopped = []
        for plugin in self._registry.list_all():
            if plugin.state == PluginState.STARTED:
                try:
                    plugin.stop()
                    self._bridge.remove_plugin(plugin)
                    stopped.append(plugin.meta.name)
                except Exception:
                    pass
        return stopped

    def shutdown_all(self) -> List[str]:
        """Shut down all initialized/started/stopped plugins."""
        shutdown = []
        for plugin in self._registry.list_all():
            if plugin.state.is_operational or plugin.state == PluginState.STOPPED:
                try:
                    plugin.shutdown()
                    shutdown.append(plugin.meta.name)
                except Exception:
                    pass
        return shutdown

    def disable(self, name: str) -> bool:
        """
        Disable a plugin (stop + move to disabled list).

        Returns False if the plugin doesn't exist.
        """
        plugin = self._registry.get(name)
        if plugin is None:
            return False

        if plugin.state == PluginState.STARTED:
            try:
                plugin.stop()
            except Exception:
                pass
        self._bridge.remove_plugin(plugin)
        return self._registry.disable(name)

    def enable(self, name: str) -> bool:
        """
        Re-enable a disabled plugin.

        Returns False if the plugin doesn't exist or is already enabled.
        """
        if not self._registry.enable(name):
            return False

        plugin = self._registry.get(name)
        if plugin and self._runtime:
            try:
                plugin.initialize(self._runtime)
            except Exception:
                pass

        return True

    # ── Query ─────────────────────────────────

    @property
    def bridge(self) -> PluginHookBridge:
        return self._bridge

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    @property
    def loader(self) -> PluginLoader:
        return self._loader

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins with their state and metadata."""
        return [
            {
                "name": p.meta.name,
                "version": p.meta.version,
                "state": p.state.value,
                "priority": p.meta.priority,
                "tags": p.meta.tags,
            }
            for p in self._registry.list_all()
        ]

    def discovery_report(self) -> Dict[str, Any]:
        """Run discovery and return a report."""
        return self._registry.discover()

    def summary(self) -> Dict[str, Any]:
        """Get a summary of the plugin system state."""
        all_plugins = self._registry.list_all()
        return {
            "total_installed": len(all_plugins),
            "disabled": len(self._registry.list_disabled()),
            "started": len([p for p in all_plugins if p.state == PluginState.STARTED]),
            "initialized": len([p for p in all_plugins if p.state == PluginState.INITIALIZED]),
            "stopped": len([p for p in all_plugins if p.state == PluginState.STOPPED]),
            "error": len([p for p in all_plugins if p.state == PluginState.ERROR]),
            "plugins": self.list_plugins(),
        }
