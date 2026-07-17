"""
Phase 4.10 — Runtime Hook (Native)

Base class for RuntimeEngine lifecycle hooks.
Replaces monkey-patching with a clean callback interface.

Usage:
    class MyHook(RuntimeHook):
        def after_transition(self, engine, from_state, to_state, ctx, transition):
            print(f"{from_state.name} → {to_state.name}")

    engine = RuntimeEngine()
    engine.add_hook(MyHook())
    engine.run()
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

from .state import AgentState
from .transition import StateTransition


class RuntimeHook:
    """
    Base class for runtime lifecycle hooks.

    Override any method. All have no-op defaults so you
    only implement what you need.

    Methods are called in registration order.
    """

    # ── Run lifecycle ────────────────────────

    def on_run_start(self, engine: Any, ctx: Any) -> None:
        """Called at the beginning of engine.run()."""
        pass

    def on_run_end(self, engine: Any, ctx: Any, total_duration_ms: float) -> None:
        """Called at the end of engine.run()."""
        pass

    # ── Transition lifecycle ─────────────────

    def before_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
    ) -> None:
        """Called BEFORE a state handler executes."""
        pass

    def after_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
        transition: StateTransition,
    ) -> None:
        """Called AFTER a state handler completes (success, error, or skipped)."""
        pass

    def on_error(
        self,
        engine: Any,
        state: AgentState,
        ctx: Any,
        error: str,
    ) -> None:
        """Called when a state handler raises an exception."""
        pass


# ──────────────────────────────────────────────
# Composite Hook (for registering multiple at once)
# ──────────────────────────────────────────────

class CompositeHook(RuntimeHook):
    """Groups multiple hooks into one registration."""

    def __init__(self, hooks: Optional[List[RuntimeHook]] = None):
        self._hooks: List[RuntimeHook] = list(hooks or [])

    def add(self, hook: RuntimeHook) -> None:
        self._hooks.append(hook)

    # ── Delegation ───────────────────────────

    def on_run_start(self, engine, ctx):
        for h in self._hooks:
            self._safe_call(h.on_run_start, engine, ctx)

    def on_run_end(self, engine, ctx, total_duration_ms):
        for h in self._hooks:
            self._safe_call(h.on_run_end, engine, ctx, total_duration_ms)

    def before_transition(self, engine, from_state, to_state, ctx):
        for h in self._hooks:
            self._safe_call(h.before_transition, engine, from_state, to_state, ctx)

    def after_transition(self, engine, from_state, to_state, ctx, transition):
        for h in self._hooks:
            self._safe_call(h.after_transition, engine, from_state, to_state, ctx, transition)

    def on_error(self, engine, state, ctx, error):
        for h in self._hooks:
            self._safe_call(h.on_error, engine, state, ctx, error)

    @staticmethod
    def _safe_call(fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except Exception:
            pass  # Hook failures MUST NOT break the engine
