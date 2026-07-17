"""
Phase 5.2 — Failure Detector

Detects runtime failures from transitions and context.
Produces structured FailureEvent for the policy engine.

Failure types:
  - EXCEPTION: handler raised an exception
  - TIMEOUT: transition took too long
  - LOW_SCORE: evaluation score below threshold
  - REPEATED_TRANSITION: same state executed too many times
  - MEMORY_FAILURE: memory update failed
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .state import AgentState
from .transition import StateTransition


# ──────────────────────────────────────────────
# FailureEvent
# ──────────────────────────────────────────────

@dataclass
class FailureEvent:
    """A detected failure during runtime execution."""

    failure_type: str  # EXCEPTION | TIMEOUT | LOW_SCORE | REPEATED | MEMORY_FAILURE
    state: Optional[AgentState] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    detail: str = ""          # Human-readable description
    severity: str = "MEDIUM"  # LOW | MEDIUM | HIGH | CRITICAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_type": self.failure_type,
            "state": self.state.name if self.state else None,
            "timestamp": self.timestamp,
            "detail": self.detail,
            "severity": self.severity,
            "metadata": self.metadata,
        }


# ──────────────────────────────────────────────
# FailureDetector
# ──────────────────────────────────────────────

class FailureDetector:
    """
    Detects failures from transitions and runtime context.

    Usage:
        detector = FailureDetector()
        failure = detector.detect_from_transition(transition, ctx)
        if failure:
            print(failure.failure_type, failure.detail)
    """

    SCORE_THRESHOLD_LOW = 40    # Below this: CRITICAL
    SCORE_THRESHOLD_MED = 70    # Below this: LOW_SCORE failure
    TIMEOUT_THRESHOLD_MS = 30000  # 30 seconds
    REPEAT_THRESHOLD = 3        # Same state 3+ times

    def __init__(self, state_history: Optional[List[AgentState]] = None):
        self._state_history: List[AgentState] = list(state_history or [])

    def detect_from_transition(
        self,
        transition: StateTransition,
        context: Any,  # RuntimeContext
    ) -> Optional[FailureEvent]:
        """
        Detect failures from a completed state transition.

        Returns None if no failure detected.
        """
        self._state_history.append(transition.to_state)

        # 1. Exception failure
        if transition.status == "error":
            return FailureEvent(
                failure_type="EXCEPTION",
                state=transition.to_state,
                detail=transition.error or "Unknown handler exception",
                severity=self._severity_from_state(transition.to_state),
                metadata={
                    "from_state": transition.from_state.name,
                    "duration_ms": transition.duration_ms,
                },
            )

        # 2. Timeout failure
        if transition.duration_ms > self.TIMEOUT_THRESHOLD_MS:
            return FailureEvent(
                failure_type="TIMEOUT",
                state=transition.to_state,
                detail=f"Transition took {transition.duration_ms:.0f}ms (threshold: {self.TIMEOUT_THRESHOLD_MS}ms)",
                severity="HIGH",
                metadata={"duration_ms": transition.duration_ms},
            )

        # 3. Low score failure (after evaluation)
        if transition.to_state == AgentState.EVALUATE:
            score = self._get_evaluation_score(context)
            if score is not None and score < self.SCORE_THRESHOLD_MED:
                severity = "CRITICAL" if score < self.SCORE_THRESHOLD_LOW else "HIGH"
                return FailureEvent(
                    failure_type="LOW_SCORE",
                    state=AgentState.EVALUATE,
                    detail=f"Evaluation score {score} < {self.SCORE_THRESHOLD_MED}",
                    severity=severity,
                    metadata={"score": score},
                )

        # 4. Repeated transition
        repeats = self._count_repeats(transition.to_state)
        if repeats >= self.REPEAT_THRESHOLD:
            return FailureEvent(
                failure_type="REPEATED_TRANSITION",
                state=transition.to_state,
                detail=f"State {transition.to_state.name} repeated {repeats} times",
                severity="MEDIUM",
                metadata={"repeats": repeats},
            )

        # 5. Memory failure
        if transition.to_state == AgentState.MEMORY_UPDATE and transition.status != "success":
            return FailureEvent(
                failure_type="MEMORY_FAILURE",
                state=AgentState.MEMORY_UPDATE,
                detail=transition.error or "Memory update failed",
                severity="HIGH",
            )

        return None

    def detect_from_context(
        self,
        context: Any,  # RuntimeContext
    ) -> List[FailureEvent]:
        """Scan the whole context for accumulated failures."""
        failures: List[FailureEvent] = []

        errors = getattr(context, 'errors', []) or []
        for err in errors:
            state_name = self._extract_state_from_error(err)
            failures.append(FailureEvent(
                failure_type="EXCEPTION",
                state=self._state_by_name(state_name),
                detail=str(err)[:200],
                severity="HIGH",
            ))

        evaluation = getattr(context, 'evaluation', None) or {}
        if isinstance(evaluation, dict):
            score = evaluation.get("score", 100)
            if score < self.SCORE_THRESHOLD_MED:
                failures.append(FailureEvent(
                    failure_type="LOW_SCORE",
                    state=AgentState.EVALUATE,
                    detail=f"Context evaluation score: {score}",
                    severity="CRITICAL" if score < self.SCORE_THRESHOLD_LOW else "HIGH",
                    metadata={"score": score},
                ))

        return failures

    # ── Helpers ─────────────────────────────

    @staticmethod
    def _get_evaluation_score(ctx: Any) -> Optional[int]:
        ev = getattr(ctx, 'evaluation', None) or {}
        if isinstance(ev, dict):
            return ev.get("score")
        return None

    def _count_repeats(self, state: AgentState) -> int:
        return sum(1 for s in self._state_history if s == state)

    @staticmethod
    def _severity_from_state(state: AgentState) -> str:
        if state in (AgentState.EVALUATE, AgentState.META_REFLECT):
            return "CRITICAL"
        if state in (AgentState.REFLECT, AgentState.MEMORY_UPDATE):
            return "HIGH"
        return "MEDIUM"

    @staticmethod
    def _extract_state_from_error(error: str) -> str:
        for s in AgentState:
            if s.name in error:
                return s.name
        return "UNKNOWN"

    @staticmethod
    def _state_by_name(name: str) -> Optional[AgentState]:
        try:
            return AgentState[name] if name in AgentState.__members__ else None
        except (KeyError, AttributeError):
            return None
