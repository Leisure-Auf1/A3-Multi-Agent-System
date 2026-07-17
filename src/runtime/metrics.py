"""
Phase 4.9 — Runtime Metrics

Accumulates statistics across runtime executions.
Non-intrusive: subscribes to RuntimeEventBus.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .events import RuntimeEvent, RuntimeEventBus


@dataclass
class RuntimeMetrics:
    """
    Accumulated metrics from runtime executions.

    Usage:
        metrics = RuntimeMetrics()
        bus = RuntimeEventBus()
        metrics.attach(bus)  # auto-subscribe
        # ... run engine ...
        print(metrics.summary())
    """

    total_runs: int = 0
    total_transitions: int = 0
    success_count: int = 0
    error_count: int = 0
    reflection_count: int = 0
    meta_reflection_count: int = 0
    scores: List[int] = field(default_factory=list)
    durations_ms: List[float] = field(default_factory=list)
    _bus: Optional[RuntimeEventBus] = None

    # ── Attach / Detach ───────────────────

    def attach(self, bus: RuntimeEventBus) -> None:
        """Subscribe to all events on the given bus."""
        self._bus = bus
        bus.subscribe_all(self._on_event)

    def detach(self) -> None:
        """Unused: subscriber ref stays but bus can be cleared."""
        self._bus = None

    def reset(self) -> None:
        """Reset all counters."""
        self.total_runs = 0
        self.total_transitions = 0
        self.success_count = 0
        self.error_count = 0
        self.reflection_count = 0
        self.meta_reflection_count = 0
        self.scores = []
        self.durations_ms = []

    # ── Internal handler ──────────────────

    def _on_event(self, event: RuntimeEvent) -> None:
        """Process a runtime event and update counters."""
        if event.event_type == "transition":
            self.total_transitions += 1
            if event.status == "success":
                self.success_count += 1
            elif event.status == "error":
                self.error_count += 1

        elif event.event_type == "evaluation":
            score = event.metadata.get("score")
            if isinstance(score, (int, float)):
                self.scores.append(int(score))

        elif event.event_type == "reflection":
            self.reflection_count += 1

        elif event.event_type == "meta_reflection":
            self.meta_reflection_count += 1

        elif event.event_type == "done":
            self.total_runs += 1
            dur = event.metadata.get("total_duration_ms")
            if isinstance(dur, (int, float)):
                self.durations_ms.append(float(dur))

        if event.duration_ms > 0:
            self.durations_ms.append(event.duration_ms)

    # ── Derived stats ─────────────────────

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        return self.success_count / max(total, 1)

    @property
    def avg_score(self) -> float:
        return sum(self.scores) / max(len(self.scores), 1)

    @property
    def avg_duration_ms(self) -> float:
        return sum(self.durations_ms) / max(len(self.durations_ms), 1)

    # ── Summary ───────────────────────────

    def summary(self) -> Dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "total_transitions": self.total_transitions,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": round(self.success_rate, 3),
            "avg_score": round(self.avg_score, 1),
            "reflection_count": self.reflection_count,
            "meta_reflection_count": self.meta_reflection_count,
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "scores": self.scores[-10:],  # last 10 scores
        }
