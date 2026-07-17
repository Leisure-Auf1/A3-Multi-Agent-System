"""
Phase 5.8 — Agent Runtime (Plugin System)

State-machine + analyzer + failure detection + policy + recovery + lifecycle + explainability + plugins + observability.

Usage:
    from src.runtime import RuntimeEngine, PluginManager, RuntimePlugin

    class MyPlugin(RuntimePlugin):
        name = "my_plugin"
        def on_start(self): print("started!")

    mgr = PluginManager()
    mgr.install(MyPlugin())
    mgr.initialize_all(engine)
    mgr.start_all()
    engine.add_hook(mgr.bridge)
    engine.run()
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
from .plugins import RuntimePlugin, PluginState, PluginMetadata, PluginRegistry, PluginLoader, PluginHookBridge, PluginManager  # Phase 5.8
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
    "RuntimePlugin",           # Phase 5.8
    "PluginState",             # Phase 5.8
    "PluginMetadata",          # Phase 5.8
    "PluginRegistry",          # Phase 5.8
    "PluginLoader",            # Phase 5.8
    "PluginHookBridge",        # Phase 5.8
    "PluginManager",           # Phase 5.8
    "RuntimeEngine",
    "RuntimeContext",
    "create_runtime_from_workflow",
]
