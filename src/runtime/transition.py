"""
Phase 4.8 — Transition Table + Handler Types

Defines:
  - StateTransition: record of a state change
  - TransitionTable: mapping of state → next state(s)
  - Handler protocol: callable that executes state logic
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .state import AgentState


# ──────────────────────────────────────────────
# State Transition Record
# ──────────────────────────────────────────────

@dataclass
class StateTransition:
    """Record of a single state transition."""
    from_state: AgentState
    to_state: AgentState
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: float = 0.0
    status: str = "success"  # success | error | skipped
    input_summary: str = ""
    output_summary: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_state.name,
            "to": self.to_state.name,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "input": self.input_summary[:120],
            "output": self.output_summary[:120],
            "error": self.error,
        }


# ──────────────────────────────────────────────
# Transition Table
# ──────────────────────────────────────────────

class TransitionTable:
    """
    Maps each state to its valid next state(s).

    Conditional transitions (like REFLECT → META_REFLECT vs REFLECT → MEMORY_UPDATE)
    are resolved at runtime by a guard function.
    """

    # Default linear path
    DEFAULT = {
        AgentState.INIT:          AgentState.PROFILE,
        AgentState.PROFILE:       AgentState.PLAN,
        AgentState.PLAN:          AgentState.EXECUTE,
        AgentState.EXECUTE:       AgentState.EVALUATE,
        AgentState.EVALUATE:      AgentState.REFLECT,
        AgentState.REFLECT:       AgentState.MEMORY_UPDATE,  # default (no meta)
        AgentState.META_REFLECT:  AgentState.MEMORY_UPDATE,
        AgentState.MEMORY_UPDATE: AgentState.DONE,
    }

    def __init__(self, custom: Optional[Dict[AgentState, AgentState]] = None):
        self._table: Dict[AgentState, Any] = {**self.DEFAULT, **(custom or {})}

    def next_state(self, current: AgentState) -> Optional[AgentState]:
        """Get the default next state."""
        return self._table.get(current)

    def set_conditional(
        self,
        from_state: AgentState,
        guard: Callable[[Any], bool],
        true_branch: AgentState,
        false_branch: Optional[AgentState] = None,
    ) -> None:
        """
        Register a conditional transition.

        Example:
            table.set_conditional(
                AgentState.REFLECT,
                guard=lambda ctx: ctx.meta_reflector is not None and ctx.should_meta_reflect(),
                true_branch=AgentState.META_REFLECT,
                false_branch=AgentState.MEMORY_UPDATE,
            )
        """
        if false_branch is None:
            false_branch = self._table.get(from_state)
        self._table[from_state] = (guard, true_branch, false_branch)

    def resolve(self, current: AgentState, context: Any) -> Optional[AgentState]:
        """Resolve the next state, evaluating guards if needed."""
        entry = self._table.get(current)
        if entry is None:
            return None
        if isinstance(entry, tuple):
            guard, true_branch, false_branch = entry
            return true_branch if guard(context) else false_branch
        return entry


# ──────────────────────────────────────────────
# Handler type
# ──────────────────────────────────────────────

#: A state handler receives the RuntimeContext and returns nothing.
#: Errors are caught by RuntimeEngine and recorded as failed transitions.
StateHandler = Callable[[Any], None]
