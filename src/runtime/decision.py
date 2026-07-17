"""
Phase 5.2 — Runtime Decision

Records decisions made by the RuntimePolicyEngine.
Immutable — each decision is a point-in-time record.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .state import AgentState


@dataclass
class RuntimeDecision:
    """
    A decision made by the policy engine during runtime.

    Fields:
      - from_state / to_state: state transition decided
      - reason: why this decision was made
      - confidence: 0.0–1.0
      - action: CONTINUE | RETRY | REFLECT | META_REFLECT | TERMINATE
      - metadata: additional context (failure, score, etc.)
    """

    from_state: Optional[AgentState] = None
    to_state: Optional[AgentState] = None
    action: str = "CONTINUE"  # CONTINUE | RETRY | REFLECT | META_REFLECT | TERMINATE
    reason: str = ""
    confidence: float = 1.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_state": self.from_state.name if self.from_state else None,
            "to_state": self.to_state.name if self.to_state else None,
            "action": self.action,
            "reason": self.reason,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"RuntimeDecision({self.action}: "
            f"{self.from_state.name if self.from_state else '?'} → "
            f"{self.to_state.name if self.to_state else '?'}, "
            f"conf={self.confidence:.0%})"
        )


@dataclass
class DecisionLog:
    """Accumulates decisions for post-run analysis."""

    decisions: List[RuntimeDecision] = field(default_factory=list)

    def record(self, decision: RuntimeDecision) -> None:
        self.decisions.append(decision)

    def by_action(self, action: str) -> List[RuntimeDecision]:
        return [d for d in self.decisions if d.action == action]

    def last(self) -> Optional[RuntimeDecision]:
        return self.decisions[-1] if self.decisions else None

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self.decisions]

    def summary(self) -> Dict[str, Any]:
        actions = {}
        for d in self.decisions:
            actions[d.action] = actions.get(d.action, 0) + 1
        return {
            "total": len(self.decisions),
            "actions": actions,
        }
