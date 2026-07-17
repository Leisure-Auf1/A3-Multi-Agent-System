"""
Phase 5.0 — Runtime Snapshot

Captures a point-in-time view of the runtime system:
state, metrics, recent events, timeline.
Designed as a read-only data layer for dashboards and APIs.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .events import RuntimeEvent, RuntimeEventBus
from .metrics import RuntimeMetrics
from .state import AgentState


@dataclass
class RuntimeSnapshot:
    """
    Immutable snapshot of runtime state at a point in time.

    Usage:
        bus = RuntimeBus.get_bus()
        metrics = RuntimeBus.get_metrics()
        snapshot = RuntimeSnapshot.capture(bus, metrics)
        print(snapshot.to_dict())
    """

    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # ── Events ──
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)

    # ── Metrics ──
    metrics: Dict[str, Any] = field(default_factory=dict)

    # ── State ──
    current_state: Optional[str] = None
    last_state: Optional[str] = None
    evaluation_score: Optional[int] = None

    # ── Derived ──
    has_errors: bool = False
    last_error: Optional[str] = None

    @classmethod
    def capture(
        cls,
        bus: RuntimeEventBus,
        metrics: Optional[RuntimeMetrics] = None,
        max_recent: int = 20,
    ) -> "RuntimeSnapshot":
        """
        Capture a snapshot from an EventBus and optional Metrics.

        Args:
            bus: RuntimeEventBus with accumulated events.
            metrics: Optional RuntimeMetrics for stats.
            max_recent: Max number of recent events to include.

        Returns:
            RuntimeSnapshot
        """
        all_events = bus.event_log()
        recent = all_events[-max_recent:] if all_events else []

        # Derive state from last event
        current_state = None
        last_state = None
        evaluation_score = None
        last_error = None
        has_errors = False

        for ev in all_events:
            if ev.status == "error":
                has_errors = True
                last_error = ev.metadata.get("error", ev.metadata.get("error_message", ""))
            if ev.event_type == "evaluation":
                score = ev.metadata.get("score")
                if isinstance(score, (int, float)):
                    evaluation_score = int(score)
            if ev.state is not None:
                last_state = current_state
                current_state = ev.state.name

        return cls(
            recent_events=[e.to_dict() for e in recent],
            timeline=[e.to_dict() for e in all_events],
            metrics=metrics.summary() if metrics else {},
            current_state=current_state,
            last_state=last_state,
            evaluation_score=evaluation_score,
            has_errors=has_errors,
            last_error=last_error,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "captured_at": self.captured_at,
            "current_state": self.current_state,
            "last_state": self.last_state,
            "evaluation_score": self.evaluation_score,
            "has_errors": self.has_errors,
            "last_error": self.last_error,
            "metrics": self.metrics,
            "recent_events": self.recent_events,
            "timeline": self.timeline,
        }


# ──────────────────────────────────────────────
# Singleton RuntimeBus holder
# ──────────────────────────────────────────────

class RuntimeBus:
    """
    Singleton holder for the global RuntimeEventBus and RuntimeMetrics.

    Allows the dashboard/API to access runtime data without
    coupling to engine instances.

    Usage:
        RuntimeBus.init()              # Initialize once
        bus = RuntimeBus.get_bus()     # Shared EventBus
        RuntimeBus.get_metrics()       # Shared Metrics
        snapshot = RuntimeBus.snapshot()  # Convenience
    """

    _bus: Optional[RuntimeEventBus] = None
    _metrics: Optional[RuntimeMetrics] = None

    @classmethod
    def init(cls) -> None:
        """Initialize the global bus and metrics. Idempotent."""
        if cls._bus is None:
            cls._bus = RuntimeEventBus()
        if cls._metrics is None:
            cls._metrics = RuntimeMetrics()
            cls._metrics.attach(cls._bus)

    @classmethod
    def get_bus(cls) -> RuntimeEventBus:
        """Get the shared event bus. Auto-inits if needed."""
        if cls._bus is None:
            cls.init()
        return cls._bus  # type: ignore[return-value]

    @classmethod
    def get_metrics(cls) -> RuntimeMetrics:
        """Get the shared metrics. Auto-inits if needed."""
        if cls._metrics is None:
            cls.init()
        return cls._metrics  # type: ignore[return-value]

    @classmethod
    def snapshot(cls) -> RuntimeSnapshot:
        """Capture a snapshot of the current runtime state."""
        return RuntimeSnapshot.capture(cls.get_bus(), cls.get_metrics())

    @classmethod
    def reset(cls) -> None:
        """Reset the global bus and metrics."""
        if cls._bus:
            cls._bus.clear()
        if cls._metrics:
            cls._metrics.reset()
