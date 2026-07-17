"""
Phase 4.10 — Runtime Observer (Native Hook)

Observes RuntimeEngine state changes via RuntimeHook interface.
No monkey-patching. Uses `engine.add_hook(observer)`.

Usage:
    observer = RuntimeObserver(bus=event_bus)
    engine = RuntimeEngine(session_id="s1")
    engine.add_hook(observer)  # Phase 4.10 — native hook
    engine.run()
    for event in observer.events():
        print(event.event_type)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from .state import AgentState
from .events import RuntimeEvent, RuntimeEventBus
from .hooks import RuntimeHook


class RuntimeObserver(RuntimeHook):
    """
    Observes RuntimeEngine execution and emits events.

    Registered as a native RuntimeHook on the engine.
    Events are published to the event bus.
    """

    def __init__(
        self,
        bus: Optional[RuntimeEventBus] = None,
        session_id: str = "",
        collect_events: bool = True,
    ):
        super().__init__()
        self._bus = bus or RuntimeEventBus()
        self.session_id = session_id
        self.collect_events = collect_events

        # Internal state
        self._current_state: Optional[AgentState] = None
        self._events: List[RuntimeEvent] = []

    # ── RuntimeHook interface ────────────────

    def on_run_start(self, engine: Any, ctx: Any) -> None:
        """Called when engine.run() starts."""
        self.session_id = getattr(engine, 'session_id', self.session_id)

    def before_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
    ) -> None:
        """Called before a state handler executes."""
        self._current_state = to_state
        self._emit("state_enter", to_state)

    def after_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
        transition: Any,
    ) -> None:
        """Called after a state handler completes."""
        # Build metadata from context
        metadata: Dict[str, Any] = {}
        if to_state == AgentState.EVALUATE:
            metadata["score"] = getattr(ctx, 'evaluation_score', lambda: 0)()
        elif to_state == AgentState.REFLECT:
            r = getattr(ctx, 'reflection', None) or {}
            metadata["success"] = r.get("success", False)
            metadata["score"] = r.get("score", 0)
        elif to_state == AgentState.META_REFLECT:
            mr = getattr(ctx, 'meta_reflection', None) or {}
            metadata["severity"] = mr.get("severity", "")

        dur = getattr(transition, 'duration_ms', 0.0)
        status = getattr(transition, 'status', 'success')

        event = RuntimeEvent(
            event_type="transition",
            session_id=self.session_id,
            state=to_state,
            duration_ms=dur,
            status=status,
            metadata=metadata,
        )
        self._publish(event)

        # Specialized events
        if to_state == AgentState.EVALUATE:
            self._emit("evaluation", to_state, metadata)
        elif to_state == AgentState.REFLECT:
            self._emit("reflection", to_state, metadata)
        elif to_state == AgentState.META_REFLECT:
            self._emit("meta_reflection", to_state, metadata)
        elif to_state == AgentState.MEMORY_UPDATE:
            self._emit("memory_update", to_state, metadata)

        # State exit
        self._emit("state_exit", to_state)

    def on_error(
        self,
        engine: Any,
        state: AgentState,
        ctx: Any,
        error: str,
    ) -> None:
        """Called when a handler raises an exception."""
        self._emit("error", state, {"error": error})

    def on_run_end(
        self,
        engine: Any,
        ctx: Any,
        total_duration_ms: float,
    ) -> None:
        """Called when engine.run() completes."""
        self._emit("done", AgentState.DONE, {
            "total_duration_ms": total_duration_ms,
        })

    # ── Legacy compatibility ────────────────

    def attach_to_engine(self, engine: Any) -> None:
        """
        Phase 4.10 — Uses native hook registration.
        Kept for backward compat with Phase 4.9 API.
        """
        engine.add_hook(self)

    # ── Query ──────────────────────────────

    def events(self) -> List[RuntimeEvent]:
        """Return collected events."""
        return list(self._events)

    def events_by_type(self, event_type: str) -> List[RuntimeEvent]:
        return [e for e in self._events if e.event_type == event_type]

    # ── Internal ───────────────────────────

    def _emit(
        self,
        event_type: str,
        state: AgentState,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RuntimeEvent:
        event = RuntimeEvent(
            event_type=event_type,
            session_id=self.session_id,
            state=state,
            metadata=metadata or {},
        )
        self._publish(event)
        return event

    def _publish(self, event: RuntimeEvent) -> None:
        if self.collect_events:
            self._events.append(event)
        self._bus.emit(event)
