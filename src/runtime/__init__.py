"""
Phase 5.7 — Agent Runtime (Intelligence + Recovery + Lifecycle + Explainability)

State-machine + analyzer + failure detection + policy decisions + recovery + lifecycle + explainability + observability.

Usage:
    from src.runtime import AgentState, RuntimeEngine, ExplanationRecorder

    recorder = ExplanationRecorder()
    recovery = RecoveryManager()
    policy = RuntimePolicyEngine()
    engine = RuntimeEngine(session_id="demo", policy_engine=policy, recovery_manager=recovery)
    engine.add_hook(recorder)
    engine.run()
    print(recorder.to_dict())
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
from .explain import DecisionTrace, DecisionReason, DecisionCategory, DecisionChain, ExplanationRecorder  # Phase 5.7
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
    "DecisionTrace",          # Phase 5.7
    "DecisionReason",         # Phase 5.7
    "DecisionCategory",       # Phase 5.7
    "DecisionChain",          # Phase 5.7
    "ExplanationRecorder",    # Phase 5.7
    "RuntimeEngine",
    "RuntimeContext",
    "create_runtime_from_workflow",
]
