"""
Phase 5.8 — Runtime Plugin Base

Abstract base class for all Runtime plugins. Plugins extend RuntimeHook
for native engine integration and define their own lifecycle.

Usage:
    class MyPlugin(RuntimePlugin):
        name = "my_plugin"
        version = "1.0.0"

        def on_initialize(self, runtime):
            print("Plugin initialized")

        def on_start(self):
            print("Plugin started")
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..hooks import RuntimeHook


class PluginState(Enum):
    """Lifecycle states of a RuntimePlugin."""
    UNREGISTERED = "unregistered"
    INSTALLED = "installed"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    DISABLED = "disabled"
    ERROR = "error"

    @property
    def is_active(self) -> bool:
        return self == PluginState.STARTED

    @property
    def is_operational(self) -> bool:
        return self in (PluginState.INITIALIZED, PluginState.STARTED)


@dataclass
class PluginMetadata:
    """
    Metadata describing a RuntimePlugin.

    Used for registry discovery, compatibility checks, and dashboard display.
    """
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    priority: int = 0
    """Higher priority plugins are initialized first."""

    dependencies: List[str] = field(default_factory=list)
    """Names of plugins this one depends on."""

    tags: List[str] = field(default_factory=list)
    """Tags for categorization (e.g. ['security', 'observability'])."""

    min_runtime_version: str = ""
    """Minimum runtime version required (e.g. '5.0')."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "min_runtime_version": self.min_runtime_version,
        }


class RuntimePlugin(RuntimeHook, ABC):
    """
    Abstract base for all Runtime plugins.

    Extends RuntimeHook for native engine integration — plugins can
    override any hook method (on_run_start, before_transition, etc.).

    Lifecycle:
        UNREGISTERED → INSTALLED → INITIALIZED → STARTED → STOPPED → DISABLED
    """

    # ── Plugin identity (override in subclasses) ──

    @property
    def meta(self) -> PluginMetadata:
        """Plugin metadata. Override properties in subclasses."""
        return PluginMetadata(
            name=getattr(self, 'name', self.__class__.__name__),
            version=getattr(self, 'version', '1.0.0'),
            description=getattr(self.__class__, '__doc__', '') or '',
        )

    @property
    def state(self) -> PluginState:
        return getattr(self, '_state', PluginState.UNREGISTERED)

    # ── Lifecycle (override in subclasses) ──────

    def initialize(self, runtime: Any) -> None:
        """
        Called when the plugin is initialized with a RuntimeEngine.

        Override on_initialize() in subclasses.
        """
        self._runtime = runtime
        try:
            self.on_initialize(runtime)
            self._state = PluginState.INITIALIZED
        except Exception as e:
            self._state = PluginState.ERROR
            raise RuntimeError(f"Plugin '{self.meta.name}' init failed: {e}") from e

    def start(self) -> None:
        """Activate the plugin."""
        if self.state != PluginState.INITIALIZED:
            raise RuntimeError(
                f"Cannot start plugin '{self.meta.name}': "
                f"expected INITIALIZED, got {self.state.value}"
            )
        try:
            self.on_start()
            self._state = PluginState.STARTED
        except Exception as e:
            self._state = PluginState.ERROR
            raise

    def stop(self) -> None:
        """Deactivate the plugin (can be restarted)."""
        try:
            self.on_stop()
            self._state = PluginState.STOPPED
        except Exception:
            self._state = PluginState.ERROR

    def shutdown(self) -> None:
        """Permanently shut down the plugin."""
        try:
            self.on_shutdown()
            self._state = PluginState.DISABLED
        except Exception:
            self._state = PluginState.ERROR

    def enable(self) -> None:
        """Re-enable a disabled plugin."""
        if self.state == PluginState.DISABLED:
            self._state = PluginState.INSTALLED

    # ── Hook overrides (optional) ───────────────

    def on_initialize(self, runtime: Any) -> None:
        """Called during initialize(). Override in subclasses."""
        pass

    def on_start(self) -> None:
        """Called during start(). Override in subclasses."""
        pass

    def on_stop(self) -> None:
        """Called during stop(). Override in subclasses."""
        pass

    def on_shutdown(self) -> None:
        """Called during shutdown(). Override in subclasses."""
        pass

    # ── Internal ─────────────────────────────────

    _state: PluginState = PluginState.UNREGISTERED
    _runtime: Any = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.meta.name} v{self.meta.version}, {self.state.value})"
