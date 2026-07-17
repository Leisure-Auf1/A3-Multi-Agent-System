"""
Phase 5.2 — Runtime Policy Engine

Decides runtime actions based on state, analysis, and failures.

Decision rules:
  - EXCEPTION at non-critical state → RETRY (up to 2)
  - LOW_SCORE → REFLECT → retry EVALUATE
  - REPEATED_TRANSITION → TERMINATE (infinite loop guard)
  - CRITICAL failure → META_REFLECT → TERMINATE
  - Normal flow → CONTINUE (use TransitionTable default)

Usage:
    policy = RuntimePolicyEngine()
    decision = policy.decide(from_state, to_state, ctx, transition, failures)
    # decision.action: CONTINUE | RETRY | REFLECT | META_REFLECT | TERMINATE
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from .state import AgentState
from .transition import StateTransition
from .failure_detector import FailureDetector, FailureEvent
from .analyzer import RuntimeAnalyzer
from .decision import RuntimeDecision, DecisionLog


class RuntimePolicyEngine:
    """
    Makes runtime decisions based on state analysis and failure detection.

    Injected into RuntimeEngine as an optional intelligence layer.
    When not injected, the engine uses its default linear state machine.
    """

    MAX_RETRIES_PER_STATE = 2

    def __init__(
        self,
        analyzer: Optional[RuntimeAnalyzer] = None,
        detector: Optional[FailureDetector] = None,
        log: Optional[DecisionLog] = None,
    ):
        self._analyzer = analyzer or RuntimeAnalyzer()
        self._detector = detector or FailureDetector()
        self._log = log or DecisionLog()
        self._retry_counts: Dict[str, int] = {}

    # ── Main API ──────────────────────────────

    def decide(
        self,
        from_state: AgentState,
        to_state: AgentState,
        context: Any,  # RuntimeContext
        transition: Optional[StateTransition] = None,
    ) -> RuntimeDecision:
        """
        Decide what action to take after a transition completes.

        Args:
            from_state: The state we came from.
            to_state: The state we just executed.
            context: RuntimeContext with agent outputs.
            transition: The completed StateTransition (None before execution).

        Returns:
            RuntimeDecision with action + target state.
        """
        # Detect failures from this transition
        failures: List[FailureEvent] = []
        if transition is not None:
            failure = self._detector.detect_from_transition(transition, context)
            if failure:
                failures = [failure]

        # Also scan context for accumulated failures
        if transition is None or transition.status != "error":
            ctx_failures = self._detector.detect_from_context(context)
            for cf in ctx_failures:
                if cf not in failures:
                    failures.append(cf)

        if not failures:
            return self._continue(from_state, to_state)

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        failures.sort(key=lambda f: severity_order.get(f.severity, 99))

        primary = failures[0]

        # ── Decision rules ──────────────────────

        # Rule 1: CRITICAL → META_REFLECT → TERMINATE
        if primary.failure_type in ("LOW_SCORE",) and primary.severity == "CRITICAL":
            return self._meta_reflect(from_state, to_state, primary)

        # Rule 2: Exception → RETRY (limited)
        if primary.failure_type == "EXCEPTION":
            state_key = primary.state.name if primary.state else to_state.name
            self._retry_counts[state_key] = self._retry_counts.get(state_key, 0) + 1
            if self._retry_counts[state_key] <= self.MAX_RETRIES_PER_STATE:
                return self._retry(from_state, to_state, primary)
            return self._terminate(from_state, to_state, primary)

        # Rule 3: Low score → REFLECT
        if primary.failure_type == "LOW_SCORE":
            return self._reflect(from_state, to_state, primary)

        # Rule 4: Timeout → RETRY once
        if primary.failure_type == "TIMEOUT":
            return self._retry(from_state, to_state, primary)

        # Rule 5: Repeated → TERMINATE
        if primary.failure_type == "REPEATED_TRANSITION":
            return self._terminate(from_state, to_state, primary)

        # Rule 6: Memory failure → TERMINATE
        if primary.failure_type == "MEMORY_FAILURE":
            return self._terminate(from_state, to_state, primary)

        return self._continue(from_state, to_state)

    def decide_pre_transition(
        self,
        from_state: AgentState,
        to_state: AgentState,
        context: Any,
    ) -> RuntimeDecision:
        """
        Called BEFORE a transition executes.
        Used to override the next state based on context analysis.
        Returns CONTINUE by default (no override).
        """
        # Health check before critical states
        if to_state in (AgentState.REFLECT, AgentState.META_REFLECT):
            health = self._analyzer.health_score(
                metrics=getattr(context, '_metrics', None),
                context=context,
            )
            if health.status == "failing":
                decision = RuntimeDecision(
                    from_state=from_state,
                    to_state=AgentState.DONE,
                    action="TERMINATE",
                    reason=f"Health check: {health.status} (score={health.score})",
                    confidence=0.85,
                    metadata={"health": {"score": health.score, "status": health.status}},
                )
                self._log.record(decision)
                return decision

        return self._continue(from_state, to_state)

    # ── Decision builders ─────────────────────

    def _continue(
        self, from_state: AgentState, to_state: AgentState
    ) -> RuntimeDecision:
        d = RuntimeDecision(
            from_state=from_state,
            to_state=to_state,
            action="CONTINUE",
            reason="Normal flow — no failures detected",
            confidence=1.0,
        )
        self._log.record(d)
        return d

    def _retry(
        self, from_state: AgentState, to_state: AgentState, failure: FailureEvent
    ) -> RuntimeDecision:
        retry_state = failure.state or to_state
        d = RuntimeDecision(
            from_state=from_state,
            to_state=retry_state,
            action="RETRY",
            reason=f"Retry after {failure.failure_type}: {failure.detail[:80]}",
            confidence=0.7,
            metadata={"failure": failure.to_dict()},
        )
        self._log.record(d)
        return d

    def _reflect(
        self, from_state: AgentState, to_state: AgentState, failure: FailureEvent
    ) -> RuntimeDecision:
        d = RuntimeDecision(
            from_state=from_state,
            to_state=AgentState.REFLECT,
            action="REFLECT",
            reason=f"Trigger reflection after {failure.failure_type}: {failure.detail[:80]}",
            confidence=0.8,
            metadata={"failure": failure.to_dict()},
        )
        self._log.record(d)
        return d

    def _meta_reflect(
        self, from_state: AgentState, to_state: AgentState, failure: FailureEvent
    ) -> RuntimeDecision:
        d = RuntimeDecision(
            from_state=from_state,
            to_state=AgentState.META_REFLECT,
            action="META_REFLECT",
            reason=f"Critical failure requires meta-reflection: {failure.detail[:80]}",
            confidence=0.9,
            metadata={"failure": failure.to_dict()},
        )
        self._log.record(d)
        return d

    def _terminate(
        self, from_state: AgentState, to_state: AgentState, failure: FailureEvent
    ) -> RuntimeDecision:
        d = RuntimeDecision(
            from_state=from_state,
            to_state=AgentState.DONE,
            action="TERMINATE",
            reason=f"Terminate after unrecoverable {failure.failure_type}: {failure.detail[:80]}",
            confidence=0.95,
            metadata={"failure": failure.to_dict()},
        )
        self._log.record(d)
        return d

    # ── Query ─────────────────────────────────

    @property
    def decision_log(self) -> DecisionLog:
        return self._log

    def reset(self) -> None:
        self._retry_counts.clear()
        self._log = DecisionLog()
