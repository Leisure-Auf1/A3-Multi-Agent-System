"""
Phase 4.8 — Runtime Checkpoint / Trace Integration

Records each state transition as a structured event.
Integrated with AgentTraceCollector for full observability.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from .state import AgentState
from .transition import StateTransition


class RuntimeCheckpoint:
    """
    Records state transitions during a runtime execution.

    Usage:
        cp = RuntimeCheckpoint(session_id="abc")
        cp.record(transition)
        print(cp.timeline)  # [StateTransition, ...]
    """

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self._transitions: List[StateTransition] = []
        self._state_history: List[AgentState] = []

    def record(self, transition: StateTransition) -> None:
        """Record a state transition."""
        self._transitions.append(transition)
        self._state_history.append(transition.to_state)

    def timeline(self) -> List[StateTransition]:
        """Return the full transition timeline."""
        return list(self._transitions)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Serialize all transitions for trace output."""
        return [t.to_dict() for t in self._transitions]

    def state_count(self) -> int:
        """Number of states visited."""
        return len(self._state_history)

    def error_count(self) -> int:
        """Number of failed transitions."""
        return sum(1 for t in self._transitions if t.status == "error")

    @property
    def current_state(self) -> Optional[AgentState]:
        return self._state_history[-1] if self._state_history else None

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total_transitions": len(self._transitions),
            "states_visited": [s.name for s in self._state_history],
            "errors": self.error_count(),
        }
