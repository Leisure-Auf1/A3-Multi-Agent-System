"""
Phase 5.7 — Runtime Decision Explainability Layer

Captures, structures, and explains every policy decision made during
runtime execution. Provides explainability metrics for benchmarking.

Modules:
    trace    — DecisionTrace + DecisionReason + DecisionChain
    recorder — ExplanationRecorder (RuntimeHook)

Usage:
    from src.runtime.explain import ExplanationRecorder, DecisionTrace

    recorder = ExplanationRecorder()
    engine = RuntimeEngine(session_id="demo", policy_engine=policy)
    engine.add_hook(recorder)
    engine.run()

    # Dashboard-ready explainability data
    print(recorder.to_dict())
    print(f"Explainability: {recorder.explainability_score():.0%}")
"""

from .trace import DecisionTrace, DecisionReason, DecisionCategory, DecisionChain
from .recorder import ExplanationRecorder

__all__ = [
    "DecisionTrace",
    "DecisionReason",
    "DecisionCategory",
    "DecisionChain",
    "ExplanationRecorder",
]
