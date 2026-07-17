"""
Phase 5.7 — Explanation Recorder

Non-invasive RuntimeHook that captures and explains every policy decision.
Provides structured explanations for dashboard, audit, and benchmark analysis.

Usage:
    from src.runtime.explain import ExplanationRecorder

    recorder = ExplanationRecorder()
    engine = RuntimeEngine(session_id="demo", policy_engine=policy)
    engine.add_hook(recorder)
    engine.run()

    # Get all decision traces with explanations
    for trace in recorder.traces:
        print(trace.to_summary())

    # Dashboard export
    dashboard_data = recorder.to_dict()
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..hooks import RuntimeHook
from ..state import AgentState
from ..transition import StateTransition
from ..decision import RuntimeDecision
from .trace import (
    DecisionTrace,
    DecisionReason,
    DecisionCategory,
    DecisionChain,
)


# ══════════════════════════════════════════════
# ExplanationRecorder (RuntimeHook)
# ══════════════════════════════════════════════


class ExplanationRecorder(RuntimeHook):
    """
    Records and explains every policy decision during engine execution.

    Implements RuntimeHook for non-invasive integration. No engine
    modification required — just `engine.add_hook(recorder)`.

    Features:
      - Captures pre-decision context (errors, scores, health)
      - Records structured DecisionReason for each decision
      - Links related decisions into causal chains
      - Exports explainability data for dashboard / benchmark
    """

    def __init__(self, auto_chain: bool = True):
        super().__init__()
        self._traces: List[DecisionTrace] = []
        self._chains: List[DecisionChain] = []
        self._current_chain: Optional[DecisionChain] = None
        self._auto_chain = auto_chain
        self._decision_index: int = 0
        self._engine: Any = None

    # ── RuntimeHook Interface ────────────

    def on_run_start(self, engine: Any, ctx: Any) -> None:
        """Initialize a new explainability session."""
        self._engine = engine
        self._decision_index = 0

    def after_transition(
        self,
        engine: Any,
        from_state: AgentState,
        to_state: AgentState,
        ctx: Any,
        transition: StateTransition,
    ) -> None:
        """
        After a transition, capture the decision context.

        If the engine has a policy_engine, we read its last decision
        and build a DecisionTrace from it.
        """
        policy = getattr(engine, '_policy_engine', None)
        if policy is None:
            return

        # Get the last decision from the policy log
        log = getattr(policy, 'decision_log', None)
        if log is None:
            return

        last_decision = log.last()
        if last_decision is None:
            return

        # Check if we've already traced this decision
        decision_id = getattr(last_decision, 'timestamp', '') + str(self._decision_index)
        if any(t.trace_id == decision_id for t in self._traces):
            return

        # ── Build DecisionReason from decision metadata ──
        reason = self._build_reason(last_decision, transition, ctx)

        # ── Build context snapshot ──
        context = self._build_context(ctx, transition)

        # ── Recovery outcome ──
        recovery_mgr = getattr(engine, '_recovery_manager', None)
        recovery_attempted = recovery_mgr is not None and len(recovery_mgr.history) > 0
        recovery_success = None
        if recovery_attempted:
            recovery_success = any(r.success for r in recovery_mgr.history)

        # ── Create trace ──
        trace = DecisionTrace(
            action=last_decision.action,
            from_state=last_decision.from_state,
            to_state=last_decision.to_state,
            reason=reason,
            confidence=last_decision.confidence,
            context=context,
            recovery_attempted=recovery_attempted,
            recovery_success=recovery_success,
            trace_id=decision_id,
        )

        self._traces.append(trace)
        self._decision_index += 1

        # ── Chain management ──
        if self._auto_chain:
            if self._current_chain is None:
                self._current_chain = DecisionChain(
                    chain_id=f"chain_{len(self._chains)}"
                )
                self._chains.append(self._current_chain)

            self._current_chain.add(trace)

            # Close chain on terminal decisions
            if last_decision.action == "TERMINATE":
                self._current_chain = None

    def on_run_end(
        self,
        engine: Any,
        ctx: Any,
        total_duration_ms: float,
    ) -> None:
        """Finalize any open chains."""
        if self._current_chain and self._current_chain.length > 0:
            self._current_chain = None  # mark as complete

    # ── Decision Reason Builder ──────────

    def _build_reason(
        self,
        decision: RuntimeDecision,
        transition: StateTransition,
        ctx: Any,
    ) -> DecisionReason:
        """Build a structured DecisionReason from a RuntimeDecision's context."""
        metadata = decision.metadata or {}
        action = decision.action

        # Extract failure info if present
        failure = metadata.get("failure", {})
        failure_type = failure.get("failure_type", "") if isinstance(failure, dict) else ""

        if action == "CONTINUE":
            return DecisionReason(
                rule_id="normal_continue",
                category=DecisionCategory.NORMAL_FLOW,
                priority=0,
                evidence={"transition_status": transition.status},
                description="Normal flow — no failures detected",
            )

        elif action == "RETRY":
            if failure_type == "TIMEOUT":
                return DecisionReason(
                    rule_id="timeout_retry",
                    category=DecisionCategory.FAILURE_RECOVERY,
                    priority=1,
                    evidence=failure,
                    description=f"LLM timeout — retrying ({transition.to_state.label})",
                )
            elif failure_type == "EXCEPTION":
                retry_info = metadata.get("retry_count", "?")
                return DecisionReason(
                    rule_id="exception_retry",
                    category=DecisionCategory.FAILURE_RECOVERY,
                    priority=2,
                    evidence=failure,
                    description=f"Agent exception at {transition.to_state.label} — retry #{retry_info}",
                )
            else:
                return DecisionReason(
                    rule_id="generic_retry",
                    category=DecisionCategory.FAILURE_RECOVERY,
                    priority=1,
                    evidence={"decision": decision.to_dict()},
                    description=f"Retry triggered by {failure_type or 'unknown'}",
                )

        elif action == "REFLECT":
            return DecisionReason(
                rule_id="low_score_reflect",
                category=DecisionCategory.QUALITY_GATE,
                priority=3,
                evidence=failure,
                description=f"Quality below threshold — triggering reflection",
            )

        elif action == "META_REFLECT":
            return DecisionReason(
                rule_id="low_score_meta_reflect",
                category=DecisionCategory.QUALITY_GATE,
                priority=4,
                evidence=failure,
                description=f"Critical quality issue — triggering meta-reflection",
            )

        elif action == "TERMINATE":
            if failure_type == "REPEATED_TRANSITION":
                return DecisionReason(
                    rule_id="repeated_terminate",
                    category=DecisionCategory.LOOP_GUARD,
                    priority=5,
                    evidence=failure,
                    description=f"Infinite loop detected — terminating",
                )
            elif failure_type == "MEMORY_FAILURE":
                return DecisionReason(
                    rule_id="memory_terminate",
                    category=DecisionCategory.MEMORY_ISSUE,
                    priority=5,
                    evidence=failure,
                    description=f"Memory corruption — terminating",
                )
            else:
                return DecisionReason(
                    rule_id="escalation_terminate",
                    category=DecisionCategory.ESCALATION,
                    priority=5,
                    evidence=failure,
                    description=f"Unrecoverable {failure_type or 'error'} — terminating",
                )

        # Fallback
        return DecisionReason(
            rule_id="unknown_decision",
            category=DecisionCategory.NORMAL_FLOW,
            priority=0,
            evidence={"action": action},
            description=f"Decision: {action}",
        )

    def _build_context(
        self,
        ctx: Any,
        transition: StateTransition,
    ) -> Dict[str, Any]:
        """Build a context snapshot for the decision trace."""
        context = {
            "transition_status": transition.status,
            "transition_duration_ms": transition.duration_ms,
        }

        # Engine errors
        errors = getattr(ctx, 'errors', []) or []
        if errors:
            context["errors"] = list(errors[-3:])  # last 3

        # Evaluation score
        evaluation = getattr(ctx, 'evaluation', None)
        if evaluation and isinstance(evaluation, dict):
            score = evaluation.get("score")
            if score is not None:
                context["evaluation_score"] = score

        # Health check if available
        policy = getattr(self._engine, '_policy_engine', None)
        if policy:
            analyzer = getattr(policy, '_analyzer', None)
            if analyzer:
                metrics = getattr(self._engine, '_metrics', None)
                if metrics:
                    try:
                        health = analyzer.health_score(metrics, ctx)
                        context["health_status"] = health.status
                        context["health_score"] = health.score
                    except Exception:
                        pass

        return context

    # ── Query ─────────────────────────────

    @property
    def traces(self) -> List[DecisionTrace]:
        return list(self._traces)

    @property
    def chains(self) -> List[DecisionChain]:
        return list(self._chains)

    def last_trace(self) -> Optional[DecisionTrace]:
        return self._traces[-1] if self._traces else None

    def traces_by_action(self, action: str) -> List[DecisionTrace]:
        return [t for t in self._traces if t.action == action]

    def traces_by_category(self, category: DecisionCategory) -> List[DecisionTrace]:
        return [
            t for t in self._traces
            if t.reason and t.reason.category == category
        ]

    def recovery_traces(self) -> List[DecisionTrace]:
        return self.traces_by_category(DecisionCategory.FAILURE_RECOVERY)

    def recovery_success_rate(self) -> float:
        """Fraction of recovery decisions that succeeded."""
        rec_traces = self.recovery_traces()
        if not rec_traces:
            return 0.0
        resolved = [t for t in rec_traces if t.recovery_success is not None]
        if not resolved:
            return 0.0
        return sum(1 for t in resolved if t.recovery_success) / len(resolved)

    # ── Explainability Metrics ────────────

    def explainability_score(self) -> float:
        """
        Calculate an explainability score (0.0–1.0).

        Factors:
          - Decisions with structured reasons (weight: 0.5)
          - Decisions with context data (weight: 0.3)
          - Decisions in completed chains (weight: 0.2)
        """
        if not self._traces:
            return 1.0  # No decisions is perfectly explainable

        total = len(self._traces)

        # Structured reasons
        with_reason = sum(1 for t in self._traces if t.reason and t.reason.rule_id)
        reason_score = with_reason / total * 0.5

        # Context data
        with_context = sum(1 for t in self._traces if len(t.context) > 0)
        context_score = with_context / total * 0.3

        # Completed chains
        chains_complete = sum(1 for c in self._chains if c.length > 1)
        chain_score = (chains_complete / max(len(self._chains), 1)) * 0.2 if self._chains else 0.2

        return min(1.0, reason_score + context_score + chain_score)

    def decision_diversity(self) -> float:
        """Measure of how diverse the decision actions are (0.0–1.0)."""
        if not self._traces:
            return 0.0
        actions = {t.action for t in self._traces}
        return len(actions) / 5  # 5 possible actions

    # ── Serialization ────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Export all explainability data for dashboard."""
        return {
            "total_decisions": len(self._traces),
            "explainability_score": round(self.explainability_score(), 3),
            "decision_diversity": round(self.decision_diversity(), 3),
            "recovery_success_rate": round(self.recovery_success_rate(), 3),
            "chains": {
                "total": len(self._chains),
                "complete": sum(1 for c in self._chains if c.length > 1),
            },
            "by_action": {
                action: len(self.traces_by_action(action))
                for action in ["CONTINUE", "RETRY", "REFLECT", "META_REFLECT", "TERMINATE"]
            },
            "by_category": {
                cat.value: len(self.traces_by_category(cat))
                for cat in DecisionCategory
            },
            "traces": [t.to_dict() for t in self._traces],
            "chains_data": [c.to_dict() for c in self._chains],
        }

    def to_summary(self) -> Dict[str, Any]:
        """Lightweight summary for benchmark integration."""
        return {
            "total_decisions": len(self._traces),
            "explainability_score": round(self.explainability_score(), 3),
            "decision_diversity": round(self.decision_diversity(), 3),
            "recovery_success_rate": round(self.recovery_success_rate(), 3),
            "recovery_decisions": len(self.recovery_traces()),
            "chain_count": len(self._chains),
        }

    def reset(self) -> None:
        """Clear all recorded traces and chains."""
        self._traces.clear()
        self._chains.clear()
        self._current_chain = None
        self._decision_index = 0
