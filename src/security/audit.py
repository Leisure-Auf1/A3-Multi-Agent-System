"""
Phase 5.3 — Audit Logger

Records security-relevant events for traceability.
All agent actions, tool calls, and security decisions are logged.

Usage:
    logger = AuditLogger()
    logger.record(
        agent="ProfileAgent",
        action="call_llm",
        result="allowed",
        risk="LOW",
    )
    logger.query(agent="ProfileAgent")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


# ──────────────────────────────────────────────
# AuditRecord
# ──────────────────────────────────────────────

@dataclass
class AuditRecord:
    """One auditable event."""

    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    agent: str = ""               # Which agent performed the action
    action: str = ""              # What was attempted
    result: str = "allowed"       # allowed | denied | error
    risk: str = "LOW"             # LOW | MEDIUM | HIGH
    detail: str = ""              # Additional context
    session_id: str = ""          # Runtime session
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "agent": self.agent,
            "action": self.action,
            "result": self.result,
            "risk": self.risk,
            "detail": self.detail,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


# ──────────────────────────────────────────────
# AuditLogger
# ──────────────────────────────────────────────

class AuditLogger:
    """
    Records auditable security events.

    Usage:
        logger = AuditLogger()
        logger.record(agent="ProfileAgent", action="read_memory", result="allowed")
        denied = logger.query(result="denied")
    """

    MAX_RECORDS = 5000  # Safety limit

    def __init__(self):
        self._records: List[AuditRecord] = []
        self._denied_count: int = 0
        self._allowed_count: int = 0

    def record(
        self,
        agent: str = "",
        action: str = "",
        result: str = "allowed",
        risk: str = "LOW",
        detail: str = "",
        session_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        """Log an auditable event."""
        rec = AuditRecord(
            agent=agent,
            action=action,
            result=result,
            risk=risk,
            detail=detail,
            session_id=session_id,
            metadata=metadata or {},
        )

        # Evict oldest if at capacity
        if len(self._records) >= self.MAX_RECORDS:
            self._records.pop(0)

        self._records.append(rec)

        if result == "denied":
            self._denied_count += 1
        elif result == "allowed":
            self._allowed_count += 1

        return rec

    def record_denied(
        self,
        agent: str,
        action: str,
        reason: str = "",
        risk: str = "MEDIUM",
    ) -> AuditRecord:
        """Convenience: log a denied action."""
        return self.record(
            agent=agent,
            action=action,
            result="denied",
            risk=risk,
            detail=reason,
        )

    def record_allowed(
        self,
        agent: str,
        action: str,
        detail: str = "",
        risk: str = "LOW",
    ) -> AuditRecord:
        """Convenience: log an allowed action."""
        return self.record(
            agent=agent,
            action=action,
            result="allowed",
            risk=risk,
            detail=detail,
        )

    # ── Query ─────────────────────────────────

    def query(
        self,
        agent: str = "",
        action: str = "",
        result: str = "",
        risk: str = "",
        limit: int = 50,
    ) -> List[AuditRecord]:
        """Query audit records with optional filters."""
        results = []
        for r in reversed(self._records):
            if agent and r.agent != agent:
                continue
            if action and r.action != action:
                continue
            if result and r.result != result:
                continue
            if risk and r.risk != risk:
                continue
            results.append(r)
            if len(results) >= limit:
                break
        return results

    def denied_events(self) -> List[AuditRecord]:
        """Get all denied events."""
        return self.query(result="denied")

    def high_risk_events(self) -> List[AuditRecord]:
        """Get all HIGH risk events."""
        return self.query(risk="HIGH")

    # ── Summary ────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """Produce an audit summary."""
        agent_counts: Dict[str, int] = {}
        action_counts: Dict[str, int] = {}
        for r in self._records:
            agent_counts[r.agent] = agent_counts.get(r.agent, 0) + 1
            action_counts[r.action] = action_counts.get(r.action, 0) + 1

        return {
            "total_events": len(self._records),
            "allowed": self._allowed_count,
            "denied": self._denied_count,
            "denial_rate": (
                self._denied_count / max(self._allowed_count + self._denied_count, 1)
            ),
            "top_agents": sorted(agent_counts.items(), key=lambda x: -x[1])[:5],
            "top_actions": sorted(action_counts.items(), key=lambda x: -x[1])[:5],
        }

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Export all records as dicts."""
        return [r.to_dict() for r in self._records]

    def clear(self) -> None:
        """Clear all records."""
        self._records.clear()
        self._denied_count = 0
        self._allowed_count = 0
