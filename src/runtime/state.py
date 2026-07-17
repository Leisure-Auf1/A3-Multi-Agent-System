"""
Phase 4.8 — AgentState Enumeration

All states in the Agent Runtime State Machine.
"""

from __future__ import annotations
from enum import Enum, auto


class AgentState(Enum):
    """
    Runtime state machine states.

    Flow:
        INIT → PROFILE → PLAN → EXECUTE → EVALUATE → REFLECT
          ┌───────────────────────────────────────────────┘
          ▼
        (if meta_reflector triggers)
        META_REFLECT → MEMORY_UPDATE → DONE

        (otherwise)
        MEMORY_UPDATE → DONE
    """

    INIT = auto()           # Start: session init + EventBus reset
    PROFILE = auto()        # ProfileAgent: extract user profile
    PLAN = auto()           # PlannerAgent: generate learning plan
    EXECUTE = auto()        # ResourceAgent: recommend resources
    EVALUATE = auto()       # EvaluationManager: score + issues
    REFLECT = auto()        # ReflectionAgent: post-execution reflection
    META_REFLECT = auto()   # MetaReflector: system-level reflection (conditional)
    MEMORY_UPDATE = auto()  # MemoryManager: persist session + experience
    DONE = auto()           # Terminal: finalize result, collect trace

    # ── Convenience ────────────────────

    @property
    def is_terminal(self) -> bool:
        return self is AgentState.DONE

    @property
    def label(self) -> str:
        """Human-readable label for traces."""
        return _STATE_LABELS.get(self, self.name)


_STATE_LABELS = {
    AgentState.INIT: "初始化",
    AgentState.PROFILE: "画像提取",
    AgentState.PLAN: "路径规划",
    AgentState.EXECUTE: "资源推荐",
    AgentState.EVALUATE: "质量评估",
    AgentState.REFLECT: "执行反思",
    AgentState.META_REFLECT: "系统反思",
    AgentState.MEMORY_UPDATE: "记忆更新",
    AgentState.DONE: "完成",
}
