"""
Phase 5.8 — Plugin Hook Bridge

Bridges the Plugin System to the RuntimeHook interface.
Enables plugins to receive RuntimeEvents as structured callbacks
without directly implementing RuntimeHook methods.

Usage:
    bridge = PluginHookBridge()
    bridge.add_plugin(my_plugin)

    # Plugin receives RuntimeEvents:
    engine = RuntimeEngine()
    engine.add_hook(bridge)  # bridge forwards events to all plugins
    engine.run()
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional

from ..hooks import RuntimeHook
from ..state import AgentState
from ..transition import StateTransition
from ..events import RuntimeEvent
from .base import RuntimePlugin, PluginState


class PluginHookBridge(RuntimeHook):
    """
    Bridges RuntimeHook events to registered RuntimePlugins.

    Acts as a single RuntimeHook that distributes engine events
    to all registered plugins. Plugins can implement on_event()
    or any RuntimeHook method to receive callbacks.

    Usage:
        bridge = PluginHookBridge()
        bridge.add_plugin(security_plugin)
        bridge.add_plugin(explain_plugin)

        engine = RuntimeEngine()
        engine.add_hook(bridge)
        # All engine events now flow to both plugins
    """

    def __init__(self, bus: Any = None):
        super().__init__()
        self._plugins: List[RuntimePlugin] = []
        self._event_bus = bus

    # ── Plugin Management ────────────────────

    def add_plugin(self, plugin: RuntimePlugin) -> None:
        """
        Add a plugin to receive hook events.

        Only adds if not already registered.
        """
        if plugin not in self._plugins:
            self._plugins.append(plugin)

    def remove_plugin(self, plugin: RuntimePlugin) -> None:
        """Remove a plugin from the bridge."""
        if plugin in self._plugins:
            self._plugins.remove(plugin)

    def list_plugins(self) -> List[RuntimePlugin]:
        return list(self._plugins)

    def get_plugin(self, name: str) -> Optional[RuntimePlugin]:
        for p in self._plugins:
            if p.meta.name == name:
                return p
        return None

    # ── RuntimeHook Interface ────────────────

    def on_run_start(self, engine: Any, ctx: Any) -> None:
        self._broadcast("on_run_start", engine, ctx)

    def on_run_end(self, engine: Any, ctx: Any, total_duration_ms: float) -> None:
        self._broadcast("on_run_end", engine, ctx, total_duration_ms)

    def before_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
    ) -> None:
        self._broadcast("before_transition", engine, from_state, to_state, ctx)

    def after_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
        transition: StateTransition,
    ) -> None:
        self._broadcast("after_transition", engine, from_state, to_state, ctx, transition)

    def on_error(
        self,
        engine: Any,
        state: AgentState,
        ctx: Any,
        error: str,
    ) -> None:
        self._broadcast("on_error", engine, state, ctx, error)

    # ── Event-based Interface ────────────────

    def relay_event(self, event: RuntimeEvent) -> None:
        """
        Relay a RuntimeEvent to all active plugins.

        Each plugin's on_event() is called with the event.
        """
        for plugin in self._plugins:
            if plugin.state.is_operational:
                try:
                    on_event = getattr(plugin, 'on_event', None)
                    if on_event:
                        on_event(event)
                except Exception:
                    pass  # isolated — plugin failure doesn't break others

    # ── Internal ─────────────────────────────

    def _broadcast(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """
        Call `method_name` on all active plugins.

        Plugin errors are isolated — one failing plugin does not
        prevent others from receiving the event.
        """
        for plugin in self._plugins:
            if not plugin.state.is_operational:
                continue
            try:
                fn = getattr(plugin, method_name, None)
                if fn:
                    fn(*args, **kwargs)
            except Exception:
                pass  # isolation


# ──────────────────────────────────────────────
# Convenience: create from registry
# ──────────────────────────────────────────────


def bridge_from_registry(registry: Any) -> PluginHookBridge:
    """
    Create a PluginHookBridge pre-populated from a PluginRegistry.

    All registered, operational plugins are added to the bridge.

    Args:
        registry: PluginRegistry instance.

    Returns:
        PluginHookBridge with all active plugins added.
    """
    bridge = PluginHookBridge()
    for plugin in registry.list_all():
        if plugin.state.is_operational:
            bridge.add_plugin(plugin)
    return bridge
