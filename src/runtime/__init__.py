"""
Phase 5.5 — Agent Runtime State Machine (Intelligence + Recovery + Lifecycle)

State-machine + analyzer + failure detection + policy decisions + recovery + lifecycle + observability.

Usage:
    from src.runtime import AgentState, RuntimeEngine, LifecycleManager

    lm = LifecycleManager()
    recovery = RecoveryManager()
    policy = RuntimePolicyEngine()
    engine = RuntimeEngine(session_id="demo", policy_engine=policy, recovery_manager=recovery)
    engine.add_hook(lm)
    engine.run()
    for name, state in lm.agent_states.items():
        print(name, state)
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
from .recovery import RecoveryManager, RecoveryResult, CheckpointManager, RecoveryStrategy, RecoveryConfig, ProviderFallback  # Phase 5.4
from .lifecycle import AgentLifecycle, LifecycleManager, RuntimeSession, AgentLifecycleRecord  # Phase 5.5
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
    "RecoveryManager",       # Phase 5.4
    "RecoveryResult",        # Phase 5.4
    "CheckpointManager",     # Phase 5.4
    "RecoveryStrategy",      # Phase 5.4
    "RecoveryConfig",        # Phase 5.4
    "ProviderFallback",      # Phase 5.4
    "AgentLifecycle",         # Phase 5.5
    "LifecycleManager",       # Phase 5.5
    "RuntimeSession",         # Phase 5.5
    "AgentLifecycleRecord",   # Phase 5.5
    "RuntimeEngine",
    "RuntimeContext",
    "create_runtime_from_workflow",
]
