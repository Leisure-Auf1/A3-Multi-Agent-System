"""
Phase 5.8 — Plugin Loader

Dynamic plugin loading via importlib. Supports loading from
module paths with optional auto-registration.

Usage:
    loader = PluginLoader(registry)
    plugin = loader.load("src.runtime.plugins.examples.my_plugin", "MyPlugin")
    plugins = loader.load_from_path("src.runtime.plugins.examples")
"""

from __future__ import annotations
import importlib
from typing import Any, Dict, List, Optional, Type

from .base import RuntimePlugin, PluginState
from .registry import PluginRegistry


class PluginLoader:
    """
    Dynamically loads RuntimePlugin classes from Python module paths.

    Uses importlib for clean dynamic imports. Supports loading individual
    plugins by class name or discovering all RuntimePlugin subclasses
    in a module.

    Usage:
        registry = PluginRegistry()
        loader = PluginLoader(registry)

        # Load by class name
        plugin = loader.load("my_package.my_module", "MyPlugin")

        # Auto-discover all plugins in a module
        plugins = loader.load_all("my_package.plugins")
    """

    def __init__(self, registry: Optional[PluginRegistry] = None):
        self._registry = registry or PluginRegistry()
        self._load_errors: List[Dict[str, Any]] = []

    # ── Load Single Plugin ────────────────────

    def load(
        self,
        module_path: str,
        class_name: str,
        register: bool = True,
        **init_kwargs: Any,
    ) -> Optional[RuntimePlugin]:
        """
        Load a single plugin class from a module.

        Args:
            module_path: Python module path (e.g. 'my_pkg.my_module').
            class_name: Name of the RuntimePlugin subclass.
            register: If True, auto-register in the registry.
            **init_kwargs: Passed to the plugin constructor.

        Returns:
            The loaded plugin, or None if loading failed.
        """
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)

            if not issubclass(cls, RuntimePlugin):
                raise TypeError(
                    f"{class_name} is not a RuntimePlugin subclass"
                )

            plugin = cls(**init_kwargs)

            if register:
                self._registry.register(plugin)

            return plugin

        except Exception as e:
            self._load_errors.append({
                "module": module_path,
                "class": class_name,
                "error": str(e),
            })
            return None

    # ── Load All ──────────────────────────────

    def load_all(
        self,
        module_path: str,
        register: bool = True,
    ) -> List[RuntimePlugin]:
        """
        Discover and load all RuntimePlugin subclasses in a module.

        Args:
            module_path: Python module path to scan.
            register: Auto-register loaded plugins.

        Returns:
            List of successfully loaded plugins.
        """
        loaded: List[RuntimePlugin] = []

        try:
            mod = importlib.import_module(module_path)
        except Exception as e:
            self._load_errors.append({
                "module": module_path,
                "error": f"Import failed: {e}",
            })
            return loaded

        for attr_name in dir(mod):
            try:
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, RuntimePlugin)
                    and attr is not RuntimePlugin
                ):
                    plugin = attr()
                    if register:
                        self._registry.register(plugin)
                    loaded.append(plugin)
            except Exception as e:
                self._load_errors.append({
                    "module": module_path,
                    "class": attr_name,
                    "error": str(e),
                })

        return loaded

    # ── Query ─────────────────────────────────

    @property
    def load_errors(self) -> List[Dict[str, Any]]:
        """Errors encountered during loading."""
        return list(self._load_errors)

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    def clear_errors(self) -> None:
        self._load_errors.clear()
