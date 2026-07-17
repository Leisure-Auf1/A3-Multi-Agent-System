"""
Phase 4.9 — Runtime Event + EventBus

Lightweight pub/sub for runtime observability.
Emits events during state transitions for external observers.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid

from .state import AgentState


# ──────────────────────────────────────────────
# RuntimeEvent
# ──────────────────────────────────────────────

@dataclass
class RuntimeEvent:
    """
    An event emitted during runtime execution.

    Types:
      - "state_enter":      entering a new state
      - "state_exit":       leaving a state
      - "transition":       completing a state transition
      - "evaluation":       evaluation completed (with score)
      - "reflection":       reflection triggered
      - "meta_reflection":  meta-reflector triggered
      - "memory_update":    memory persisted
      - "error":            runtime error
      - "done":             pipeline complete
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: str = "transition"
    session_id: str = ""
    state: Optional[AgentState] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: float = 0.0
    status: str = "success"  # success | error | skipped
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "state": self.state.name if self.state else None,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "metadata": self.metadata,
        }


# ──────────────────────────────────────────────
# RuntimeEventBus
# ──────────────────────────────────────────────

Subscriber = Callable[[RuntimeEvent], None]


class RuntimeEventBus:
    """
    Lightweight pub/sub event bus for runtime observability.

    Usage:
        bus = RuntimeEventBus()
        bus.subscribe("state_enter", my_handler)
        bus.emit(RuntimeEvent(event_type="state_enter", state=AgentState.EVALUATE))
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Subscriber]] = {}
        self._all_subscribers: List[Subscriber] = []
        self._event_log: List[RuntimeEvent] = []

    def subscribe(self, event_type: str, handler: Subscriber) -> None:
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Subscriber) -> None:
        """Subscribe to ALL event types."""
        self._all_subscribers.append(handler)

    def emit(self, event: RuntimeEvent) -> None:
        """Emit an event to all matching subscribers."""
        self._event_log.append(event)

        # Specific subscribers
        handlers = self._subscribers.get(event.event_type, [])
        for h in handlers:
            try:
                h(event)
            except Exception:
                pass

        # Global subscribers
        for h in self._all_subscribers:
            try:
                h(event)
            except Exception:
                pass

    def event_log(self) -> List[RuntimeEvent]:
        """Return the full event log."""
        return list(self._event_log)

    def events_by_type(self, event_type: str) -> List[RuntimeEvent]:
        """Filter events by type."""
        return [e for e in self._event_log if e.event_type == event_type]

    def clear(self) -> None:
        """Clear the event log (does not unsubscribe)."""
        self._event_log = []

    def subscriber_count(self) -> int:
        """Total number of registered subscribers."""
        type_count = sum(len(v) for v in self._subscribers.values())
        return type_count + len(self._all_subscribers)
