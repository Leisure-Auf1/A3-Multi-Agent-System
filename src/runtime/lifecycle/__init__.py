"""
Phase 5.5 — Agent Lifecycle & Session Management

Agent lifecycle states and session tracking for the RuntimeEngine.
LifecycleManager integrates as a RuntimeHook for non-invasive monitoring.

Usage:
    from src.runtime.lifecycle import AgentLifecycle, LifecycleManager, RuntimeSession

    lm = LifecycleManager()
    engine = RuntimeEngine(session_id="demo")
    engine.add_hook(lm)
    engine.run()

    # Per-agent lifecycle states
    print(lm.agent_states)  # {"profile": "terminated", "plan": "terminated", ...}

    # Full session export
    print(lm.session.to_dict())

    # Dashboard-ready summary
    print(lm.agent_summary())
"""

from .lifecycle import (
    AgentLifecycle,
    AgentLifecycleRecord,
    LifecycleManager,
    agent_name_for_state,
)
from .session import RuntimeSession

__all__ = [
    "AgentLifecycle",
    "AgentLifecycleRecord",
    "LifecycleManager",
    "RuntimeSession",
    "agent_name_for_state",
]
