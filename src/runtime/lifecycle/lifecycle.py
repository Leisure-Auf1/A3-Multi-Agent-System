"""
Phase 5.5 — Agent Lifecycle Management

Defines the lifecycle of individual agents within the RuntimeEngine.
Managed by LifecycleManager which acts as a RuntimeHook for
non-invasive integration.

States:
    CREATED    → agent object created
    READY      → registered, waiting for execution
    RUNNING    → executing its state handler
    WAITING    → paused (e.g. waiting for user input)
    FAILED     → handler raised exception
    RECOVERING → recovery in progress
    TERMINATED → finished (success or final failure)

Usage:
    from src.runtime.lifecycle import AgentLifecycle, LifecycleManager

    lm = LifecycleManager()
    engine = RuntimeEngine(session_id="demo")
    engine.add_hook(lm)  # non-invasive hook integration
    engine.run()

    print(lm.session.to_dict())  # full execution record
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..hooks import RuntimeHook
from ..state import AgentState
from ..transition import StateTransition
from .session import RuntimeSession


# ══════════════════════════════════════════════
# AgentLifecycle
# ══════════════════════════════════════════════


class AgentLifecycle(Enum):
    """
    Lifecycle states of an individual agent during runtime execution.

    Flow:
        CREATED → READY → RUNNING → (READY | FAILED → RECOVERING → READY | TERMINATED)
                                          ↑_____________________________↓
    """
    CREATED = "created"        # Agent object instantiated
    READY = "ready"            # Registered in engine, waiting for its turn
    RUNNING = "running"        # Currently executing its handler
    WAITING = "waiting"        # Paused (e.g. external dependency)
    FAILED = "failed"          # Handler raised an exception
    RECOVERING = "recovering"  # Recovery in progress (retry/rollback/repair)
    TERMINATED = "terminated"  # Finished execution (success or final failure)

    @property
    def is_active(self) -> bool:
        """True if the agent is still in a non-terminal state."""
        return self not in (AgentLifecycle.TERMINATED,)

    @property
    def is_healthy(self) -> bool:
        """True if the agent is in a normal operating state."""
        return self in (AgentLifecycle.READY, AgentLifecycle.RUNNING, AgentLifecycle.WAITING)

    @property
    def label(self) -> str:
        return _LIFECYCLE_LABELS.get(self, self.name)


_LIFECYCLE_LABELS = {
    AgentLifecycle.CREATED: "已创建",
    AgentLifecycle.READY: "就绪",
    AgentLifecycle.RUNNING: "运行中",
    AgentLifecycle.WAITING: "等待中",
    AgentLifecycle.FAILED: "失败",
    AgentLifecycle.RECOVERING: "恢复中",
    AgentLifecycle.TERMINATED: "已终止",
}


# ══════════════════════════════════════════════
# AgentLifecycleRecord
# ══════════════════════════════════════════════


@dataclass
class AgentLifecycleRecord:
    """
    Tracks the lifecycle of a single agent during one runtime session.

    Records state transitions, errors, and recovery attempts.
    """
    agent_name: str  # Maps to AgentState name (e.g. "PROFILE", "PLAN")
    lifecycle: AgentLifecycle = AgentLifecycle.CREATED
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_count: int = 0
    last_error: Optional[str] = None
    recovery_count: int = 0
    duration_ms: float = 0.0
    history: List[Dict[str, Any]] = field(default_factory=list)

    def transition(self, to_lifecycle: AgentLifecycle, detail: str = "") -> None:
        """Record a lifecycle state change."""
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "from": self.lifecycle.value,
            "to": to_lifecycle.value,
            "timestamp": now,
            "detail": detail,
        }
        self.history.append(entry)
        self.lifecycle = to_lifecycle

        if to_lifecycle == AgentLifecycle.RUNNING and self.started_at is None:
            self.started_at = now
        if to_lifecycle == AgentLifecycle.TERMINATED:
            self.finished_at = now

    def record_error(self, error: str) -> None:
        """Record an error that occurred for this agent."""
        self.error_count += 1
        self.last_error = error

    def record_recovery(self) -> None:
        """Record a recovery attempt."""
        self.recovery_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "lifecycle": self.lifecycle.value,
            "label": self.lifecycle.label,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "recovery_count": self.recovery_count,
            "duration_ms": self.duration_ms,
            "history": self.history,
        }


# ══════════════════════════════════════════════
# LifecycleManager (RuntimeHook)
# ══════════════════════════════════════════════


class LifecycleManager(RuntimeHook):
    """
    Manages agent lifecycles as a RuntimeHook for non-invasive integration.

    Tracks per-agent lifecycle state, errors, and recoveries.
    Maintains a RuntimeSession for the full execution record.

    Integration:
        lm = LifecycleManager()
        engine.add_hook(lm)           # registers as native hook
        engine.run()
        print(lm.agent_states)        # per-agent lifecycle summary
        print(lm.session.to_dict())   # full session export for dashboard

    Backward compat: when not registered, engine behaves identically.
    """

    _STATE_MAP: Dict[str, str] = {
        # Maps AgentState name to "agent_name" for lifecycle tracking
    }

    def __init__(
        self,
        session: Optional[RuntimeSession] = None,
        auto_register: bool = True,
    ):
        super().__init__()
        self._session = session or RuntimeSession()
        self._agents: Dict[str, AgentLifecycleRecord] = {}
        self._auto_register = auto_register

    # ── Agent Registration ───────────────

    def register_agent(self, agent_name: str) -> AgentLifecycleRecord:
        """
        Register an agent for lifecycle tracking.

        Args:
            agent_name: Name matching an AgentState (e.g. "PROFILE", "PLAN").

        Returns:
            The lifecycle record for this agent.
        """
        if agent_name not in self._agents:
            record = AgentLifecycleRecord(agent_name=agent_name)
            record.transition(AgentLifecycle.READY, "Registered")
            self._agents[agent_name] = record
        return self._agents[agent_name]

    def get_agent(self, agent_name: str) -> Optional[AgentLifecycleRecord]:
        """Get lifecycle record for an agent."""
        return self._agents.get(agent_name)

    def transition_agent(
        self,
        agent_name: str,
        to_lifecycle: AgentLifecycle,
        detail: str = "",
    ) -> Optional[AgentLifecycleRecord]:
        """
        Transition an agent to a new lifecycle state.

        Auto-registers the agent if not yet tracked and auto_register is True.
        """
        record = self._agents.get(agent_name)
        if record is None:
            if self._auto_register:
                record = self.register_agent(agent_name)
            else:
                return None
        record.transition(to_lifecycle, detail)
        return record

    def mark_error(self, agent_name: str, error: str) -> None:
        """Mark an agent as having encountered an error."""
        record = self._agents.get(agent_name)
        if record is None and self._auto_register:
            record = self.register_agent(agent_name)
        if record:
            record.record_error(error)
            record.transition(AgentLifecycle.FAILED, f"Error: {error[:120]}")

    def mark_recovery(self, agent_name: str) -> None:
        """Mark an agent as being recovered."""
        record = self._agents.get(agent_name)
        if record:
            record.record_recovery()
            record.transition(AgentLifecycle.RECOVERING, "Recovery in progress")

    def mark_recovered(self, agent_name: str) -> None:
        """Mark an agent as recovered and ready again."""
        record = self._agents.get(agent_name)
        if record:
            record.transition(AgentLifecycle.READY, "Recovered successfully")

    # ── RuntimeHook Interface ────────────

    def on_run_start(self, engine: Any, ctx: Any) -> None:
        """Initialize session and set all registered agents to READY."""
        self._session.start(ctx.session_id if hasattr(ctx, 'session_id') else "")
        # Pre-register all known states as agents
        for state in AgentState:
            if state.is_terminal:
                continue
            name = _simplify_state_name(state.name)
            record = self._agents.get(name)
            if record is None:
                self.register_agent(name)

    def before_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
    ) -> None:
        """Mark target agent as RUNNING before handler executes."""
        if to_state.is_terminal:
            return
        name = _simplify_state_name(to_state.name)
        self.transition_agent(name, AgentLifecycle.RUNNING, f"→ {to_state.label}")

    def after_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
        transition: StateTransition,
    ) -> None:
        """Update lifecycle based on transition result."""
        if to_state.is_terminal:
            return
        name = _simplify_state_name(to_state.name)

        # Record the transition in session
        self._session.record_state(to_state, transition)

        if transition.status == "error":
            self.mark_error(name, transition.error or "Unknown error")
        elif transition.status == "success":
            record = self._agents.get(name)
            if record and record.lifecycle == AgentLifecycle.RUNNING:
                record.transition(AgentLifecycle.READY, "Completed successfully")
        # skipped: no-op

    def on_error(
        self,
        engine: Any,
        state: AgentState,
        ctx: Any,
        error: str,
    ) -> None:
        """Mark agent as FAILED on handler exception."""
        if state.is_terminal:
            return
        name = _simplify_state_name(state.name)
        self.mark_error(name, error)

    def on_run_end(
        self,
        engine: Any,
        ctx: Any,
        total_duration_ms: float,
    ) -> None:
        """Finalize session and mark all active agents as TERMINATED."""
        self._session.end(total_duration_ms)

        # Determine final status from session data
        error_count = sum(a.error_count for a in self._agents.values())
        self._session.final_status = "error" if error_count > 0 else "completed"

        # Terminate all active agents
        for record in self._agents.values():
            if record.lifecycle.is_active:
                record.transition(AgentLifecycle.TERMINATED, "Run ended")

        # Record agent summaries in session
        self._session.agent_summaries = {
            name: rec.to_dict() for name, rec in self._agents.items()
        }

    # ── Query ─────────────────────────────

    @property
    def session(self) -> RuntimeSession:
        return self._session

    @property
    def agent_states(self) -> Dict[str, str]:
        """Get current lifecycle state for all tracked agents."""
        return {name: rec.lifecycle.value for name, rec in self._agents.items()}

    def agent_summary(self) -> Dict[str, Any]:
        """Get a summary of all agent lifecycles."""
        return {
            "total_agents": len(self._agents),
            "states": self.agent_states,
            "errors": {
                name: rec.error_count
                for name, rec in self._agents.items()
                if rec.error_count > 0
            },
            "recoveries": {
                name: rec.recovery_count
                for name, rec in self._agents.items()
                if rec.recovery_count > 0
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full export: session + per-agent details."""
        return {
            "session": self._session.to_dict(),
            "agents": {name: rec.to_dict() for name, rec in self._agents.items()},
            "summary": self.agent_summary(),
        }

    def reset(self) -> None:
        """Clear all state for reuse."""
        self._session = RuntimeSession()
        self._agents.clear()


# ══════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════


def _simplify_state_name(name: str) -> str:
    """
    Convert AgentState names to friendly agent names.

    Examples:
        PROFILE → profile
        META_REFLECT → meta_reflect
        MEMORY_UPDATE → memory_update
    """
    # Handle compound names
    if name.startswith("META_"):
        return name.lower()
    if name.startswith("MEMORY_"):
        return name.lower()
    return name.lower()


def agent_name_for_state(state: AgentState) -> str:
    """Map AgentState to agent lifecycle name."""
    return _simplify_state_name(state.name)
