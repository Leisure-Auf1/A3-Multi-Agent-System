"""
Phase 5.2 — Agent Runtime State Machine (Intelligence Layer)

State-machine + analyzer + failure detection + policy decisions + observability.

Usage:
    from src.runtime import AgentState, RuntimeEngine, RuntimePolicyEngine

    policy = RuntimePolicyEngine()
    engine = RuntimeEngine(session_id="demo", policy_engine=policy)
    engine.run()
    for d in policy.decision_log.decisions:
        print(d.action, d.reason)
"""

from .state import AgentState
from .transition import StateTransition, TransitionTable
from .checkpoint import RuntimeCheckpoint
from .events import RuntimeEvent, RuntimeEventBus
from .hooks import RuntimeHook, CompositeHook
from .observer import RuntimeObserver
from .metrics import RuntimeMetrics
from .snapshot import RuntimeSnapshot, RuntimeBus
from .store import RuntimeStore, SessionRecord
from .analyzer import RuntimeAnalyzer, HealthReport, StateAnalysis
from .failure_detector import FailureDetector, FailureEvent
from .policy import RuntimePolicyEngine
from .decision import RuntimeDecision, DecisionLog
from .runtime import RuntimeEngine, RuntimeContext, create_runtime_from_workflow

__all__ = [
    "AgentState",
    "StateTransition",
    "TransitionTable",
    "RuntimeCheckpoint",
    "RuntimeEvent",
    "RuntimeEventBus",
    "RuntimeHook",
    "CompositeHook",
    "RuntimeObserver",
    "RuntimeMetrics",
    "RuntimeSnapshot",
    "RuntimeBus",
    "RuntimeStore",
    "SessionRecord",
    "RuntimeAnalyzer",
    "HealthReport",
    "StateAnalysis",
    "FailureDetector",
    "FailureEvent",
    "RuntimePolicyEngine",
    "RuntimeDecision",
    "DecisionLog",
    "RuntimeEngine",
    "RuntimeContext",
    "create_runtime_from_workflow",
]
