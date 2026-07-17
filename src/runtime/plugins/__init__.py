"""
Phase 5.8 — Runtime Plugin System

Pluggable extension system for the RuntimeEngine. Plugins extend
RuntimeHook for native integration and follow a managed lifecycle.

Modules:
    base     — RuntimePlugin ABC + PluginState + PluginMetadata
    registry — PluginRegistry (register/unregister/discover/query)
    loader   — PluginLoader (dynamic import via importlib)
    bridge   — PluginHookBridge (plugin → RuntimeHook adapter)
    manager  — PluginManager (full lifecycle orchestration)

Usage:
    from src.runtime.plugins import PluginManager, RuntimePlugin

    class MyPlugin(RuntimePlugin):
        name = "my_plugin"

        def on_start(self):
            print("Plugin started!")

    manager = PluginManager()
    manager.install(MyPlugin())
    manager.initialize_all(engine)
    manager.start_all()

    engine.add_hook(manager.bridge)
    engine.run()
"""

from .base import RuntimePlugin, PluginState, PluginMetadata
from .registry import PluginRegistry
from .loader import PluginLoader
from .bridge import PluginHookBridge, bridge_from_registry
from .manager import PluginManager

__all__ = [
    "RuntimePlugin",
    "PluginState",
    "PluginMetadata",
    "PluginRegistry",
    "PluginLoader",
    "PluginHookBridge",
    "bridge_from_registry",
    "PluginManager",
]
