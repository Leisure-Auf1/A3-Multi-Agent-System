"""
Phase 5.7 — Decision Trace

Captures the full decision-making context at each policy decision point.
Each DecisionTrace records: what the engine knew, what the policy decided,
and what evidence supported that decision.

Usage:
    trace = DecisionTrace(
        action="RETRY",
        from_state=AgentState.PROFILE,
        to_state=AgentState.PROFILE,
        reason=DecisionReason(
            rule_id="exception_retry",
            category="failure_recovery",
            priority=2,
            evidence={"failure_type": "EXCEPTION", "attempt": 1},
        ),
        context={"errors": ["timeout"], "health_score": 75},
    )
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..state import AgentState


# ══════════════════════════════════════════════
# DecisionReason — structured why
# ══════════════════════════════════════════════


class DecisionCategory(Enum):
    """Categories of policy decisions for explainability grouping."""
    NORMAL_FLOW = "normal_flow"
    FAILURE_RECOVERY = "failure_recovery"
    QUALITY_GATE = "quality_gate"
    HEALTH_CHECK = "health_check"
    LOOP_GUARD = "loop_guard"
    MEMORY_ISSUE = "memory_issue"
    ESCALATION = "escalation"


@dataclass
class DecisionReason:
    """
    Structured explanation of why a decision was made.

    Captures the rule that fired, its category, priority, and evidence.
    Designed for dashboard display and benchmark analysis.
    """
    rule_id: str = ""
    """Unique identifier for the decision rule (e.g. 'exception_retry', 'low_score_reflect')."""

    category: DecisionCategory = DecisionCategory.NORMAL_FLOW
    """High-level category for grouping decisions."""

    priority: int = 0
    """Rule priority (higher = more critical)."""

    evidence: Dict[str, Any] = field(default_factory=dict)
    """Concrete data that triggered this decision (failure, score, metrics)."""

    description: str = ""
    """Human-readable description of the reasoning."""

    @property
    def is_recovery(self) -> bool:
        return self.category == DecisionCategory.FAILURE_RECOVERY

    @property
    def is_termination(self) -> bool:
        return self.category in (DecisionCategory.LOOP_GUARD, DecisionCategory.ESCALATION)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category.value,
            "priority": self.priority,
            "evidence": self.evidence,
            "description": self.description or self._auto_description(),
        }

    def _auto_description(self) -> str:
        """Generate a description if none provided."""
        parts = []
        if self.rule_id:
            parts.append(f"Rule: {self.rule_id}")
        if self.category != DecisionCategory.NORMAL_FLOW:
            parts.append(f"Category: {self.category.value}")
        if self.evidence:
            parts.append(f"Evidence: {list(self.evidence.keys())}")
        return "; ".join(parts) if parts else "No details available"


# ══════════════════════════════════════════════
# DecisionTrace — full decision context
# ══════════════════════════════════════════════


@dataclass
class DecisionTrace:
    """
    Complete record of a policy decision and its context.

    Captures:
      - What transition triggered the decision
      - Why the decision was made (structured reason)
      - What context was available (errors, scores, health)
      - What happened as a result (recovery outcome)

    Immutable once created — each trace is a point-in-time snapshot.
    """

    # ── Decision identity ─────────────────────
    action: str = ""
    """The action decided: CONTINUE | RETRY | REFLECT | META_REFLECT | TERMINATE."""

    from_state: Optional[AgentState] = None
    to_state: Optional[AgentState] = None

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    """When the decision was made (UTC ISO)."""

    # ── Why ───────────────────────────────────
    reason: Optional[DecisionReason] = None
    """Structured reason for the decision."""

    confidence: float = 1.0
    """Policy confidence in this decision (0.0–1.0)."""

    # ── Context ───────────────────────────────
    context: Dict[str, Any] = field(default_factory=dict)
    """Snapshot of relevant context at decision time."""

    # ── Outcome ───────────────────────────────
    recovery_attempted: bool = False
    """Whether recovery was attempted after this decision."""

    recovery_success: Optional[bool] = None
    """Whether recovery succeeded (None if no recovery attempted)."""

    trace_id: str = ""
    """Unique trace identifier for linking decisions in a chain."""

    # ── Serialization ─────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "from_state": self.from_state.name if self.from_state else None,
            "to_state": self.to_state.name if self.to_state else None,
            "timestamp": self.timestamp,
            "reason": self.reason.to_dict() if self.reason else None,
            "confidence": self.confidence,
            "context": self.context,
            "recovery_attempted": self.recovery_attempted,
            "recovery_success": self.recovery_success,
            "trace_id": self.trace_id,
        }

    def to_summary(self) -> str:
        """One-line human-readable summary."""
        fs = self.from_state.name if self.from_state else "?"
        ts = self.to_state.name if self.to_state else "?"
        rule = f" [{self.reason.rule_id}]" if self.reason and self.reason.rule_id else ""
        recovery = ""
        if self.recovery_attempted:
            recovery = " → recovered" if self.recovery_success else " → recovery failed"
        return f"{self.action}: {fs}→{ts}{rule} (conf={self.confidence:.0%}){recovery}"


# ══════════════════════════════════════════════
# DecisionChain — linked sequence of decisions
# ══════════════════════════════════════════════


@dataclass
class DecisionChain:
    """
    A linked sequence of related decisions forming a causal chain.

    Example: EXCEPTION → RETRY → success
    Example: LOW_SCORE → REFLECT → META_REFLECT → TERMINATE
    """
    traces: List[DecisionTrace] = field(default_factory=list)
    chain_id: str = ""

    def add(self, trace: DecisionTrace) -> None:
        self.traces.append(trace)

    @property
    def length(self) -> int:
        return len(self.traces)

    @property
    def final_action(self) -> Optional[str]:
        return self.traces[-1].action if self.traces else None

    @property
    def all_recovered(self) -> bool:
        """True if all recovery decisions in this chain succeeded."""
        recovery_traces = [t for t in self.traces if t.recovery_attempted]
        if not recovery_traces:
            return True
        return all(t.recovery_success for t in recovery_traces)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "length": self.length,
            "traces": [t.to_dict() for t in self.traces],
            "final_action": self.final_action,
            "all_recovered": self.all_recovered,
        }

    def _build_rule_map() -> Dict[str, Dict[str, Any]]:
        """Build a mapping of known decision rules for explainability."""
        return {
            "exception_retry": {
                "category": "failure_recovery",
                "description": "Agent handler raised exception → retry up to 2 times",
                "priority": 2,
            },
            "timeout_retry": {
                "category": "failure_recovery",
                "description": "LLM request timed out → retry once",
                "priority": 1,
            },
            "low_score_reflect": {
                "category": "quality_gate",
                "description": "Evaluation score below threshold → trigger reflection",
                "priority": 3,
            },
            "low_score_meta_reflect": {
                "category": "quality_gate",
                "description": "Critical low score → trigger meta-reflection",
                "priority": 4,
            },
            "repeated_terminate": {
                "category": "loop_guard",
                "description": "Same state repeated 3+ times → terminate to prevent loop",
                "priority": 5,
            },
            "health_terminate": {
                "category": "health_check",
                "description": "System health failing → terminate for safety",
                "priority": 5,
            },
            "memory_terminate": {
                "category": "memory_issue",
                "description": "Memory failure detected → terminate",
                "priority": 5,
            },
            "normal_continue": {
                "category": "normal_flow",
                "description": "No failures detected → continue normal flow",
                "priority": 0,
            },
        }
