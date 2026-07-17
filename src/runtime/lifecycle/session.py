"""
Phase 5.5 — Runtime Session

Records the full execution of one engine.run() call.
Captures: session_id, timing, state timeline, decisions, recoveries, per-agent lifecycle.

Usage:
    session = RuntimeSession()
    session.start("run_001")
    session.record_state(AgentState.PROFILE, transition)
    session.end(total_duration_ms=1500)
    print(session.timeline())  # ["INIT", "PROFILE", "PLAN", "DONE"]
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..state import AgentState
from ..transition import StateTransition


@dataclass
class RuntimeSession:
    """
    Complete execution record for one runtime session.

    Tracks timing, state transitions, decisions, recoveries,
    and per-agent lifecycle summaries.

    Designed for dashboard display and API export.
    """

    session_id: str = ""
    task_id: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_duration_ms: float = 0.0

    # State timeline
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    current_state: Optional[str] = None

    # Policy decisions (from PolicyEngine)
    decisions: List[Dict[str, Any]] = field(default_factory=list)

    # Recovery results (from RecoveryManager)
    recoveries: List[Dict[str, Any]] = field(default_factory=list)

    # Final outcome
    final_status: str = "unknown"  # completed | error | terminated

    # Per-agent summaries (filled by LifecycleManager)
    agent_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── Start / End ──────────────────────────

    def start(self, session_id: str, task_id: str = "") -> None:
        """Initialize the session with a unique ID."""
        now = datetime.now(timezone.utc).isoformat()
        self.session_id = session_id
        self.task_id = task_id or f"task_{session_id}"
        self.start_time = now
        self.current_state = "INIT"

    def end(self, total_duration_ms: float) -> None:
        """Finalize the session."""
        self.end_time = datetime.now(timezone.utc).isoformat()
        self.total_duration_ms = total_duration_ms

    # ── State Tracking ───────────────────────

    def record_state(
        self,
        state: AgentState,
        transition: Optional[StateTransition] = None,
    ) -> None:
        """
        Record a state visit in the timeline.

        Args:
            state: The state reached.
            transition: Optional transition record for detail.
        """
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "state": state.name,
            "timestamp": now,
            "status": transition.status if transition else "unknown",
            "duration_ms": transition.duration_ms if transition else 0.0,
            "error": transition.error if transition and transition.error else None,
        }
        self.state_history.append(entry)
        self.current_state = state.name

    # ── Decisions / Recoveries ───────────────

    def record_decision(self, decision: Dict[str, Any]) -> None:
        """Record a policy decision."""
        self.decisions.append(decision)

    def record_recovery(self, recovery: Dict[str, Any]) -> None:
        """Record a recovery result."""
        self.recoveries.append(recovery)

    # ── Query ────────────────────────────────

    def timeline(self) -> List[str]:
        """Return ordered list of state names visited."""
        return [h["state"] for h in self.state_history]

    def state_count(self) -> int:
        return len(self.state_history)

    def error_count(self) -> int:
        return sum(1 for h in self.state_history if h["status"] == "error")

    def decision_count(self) -> int:
        return len(self.decisions)

    def recovery_count(self) -> int:
        return len(self.recoveries)

    # ── Serialization ────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """
        Export full session data for dashboard / API.

        Returns a dict suitable for JSON serialization.
        """
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "current_state": self.current_state,
            "final_status": self.final_status,
            "timeline": self.timeline(),
            "state_count": self.state_count(),
            "error_count": self.error_count(),
            "decision_count": self.decision_count(),
            "recovery_count": self.recovery_count(),
            "state_history": self.state_history,
            "decisions": self.decisions,
            "recoveries": self.recoveries,
            "agent_summaries": self.agent_summaries,
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Lightweight summary for list views."""
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "start_time": self.start_time,
            "total_duration_ms": self.total_duration_ms,
            "final_status": self.final_status,
            "state_count": self.state_count(),
            "error_count": self.error_count(),
            "timeline": self.timeline(),
        }
