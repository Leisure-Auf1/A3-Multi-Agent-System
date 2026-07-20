"""
Phase 9.3-B — Model Execution Context

Structured context for every model call through the Orchestrator.
Used for debugging, logging, user display, and future evaluation.

Fields:
    task_type, agent_name, student_id, required_capabilities,
    cost_tier, selected_model, selected_provider, fallback_used,
    decision_reason, timestamp

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelExecutionContext:
    """Full execution context for a single orchestrator model call."""

    # ── Task identity ───────────────────
    task_type: str = ""                    # TaskType value (e.g. "generate_material")
    agent_name: str = ""                   # Calling agent (e.g. "ContentGeneratorAgent")
    student_id: str = ""                   # Student identifier

    # ── Capability requirements ─────────
    required_capabilities: List[str] = field(default_factory=list)

    # ── Selection result ────────────────
    cost_tier: str = ""                    # economy / balanced / premium
    selected_model: str = ""               # model_id from registry
    selected_provider: str = ""            # provider name
    fallback_used: bool = False            # whether fallback was triggered
    decision_reason: str = ""              # human-readable selection reason

    # ── Execution result ────────────────
    success: bool = False
    response_content: str = ""             # truncated response (first 200 chars)
    usage_prompt_tokens: int = 0
    usage_completion_tokens: int = 0
    latency_ms: float = 0.0
    error: str = ""
    estimated_cost: float = 0.0              # USD cost estimate
    fallback_chain: List[str] = field(default_factory=list)  # chain of providers tried

    # ── Metadata ────────────────────────
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for JSONL logging / API response."""
        return {
            "task_type": self.task_type,
            "agent_name": self.agent_name,
            "student_id": self.student_id,
            "required_capabilities": self.required_capabilities,
            "cost_tier": self.cost_tier,
            "selected_model": self.selected_model,
            "selected_provider": self.selected_provider,
            "fallback_used": self.fallback_used,
            "decision_reason": self.decision_reason,
            "success": self.success,
            "response_content": self.response_content[:200],
            "usage_prompt_tokens": self.usage_prompt_tokens,
            "usage_completion_tokens": self.usage_completion_tokens,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error[:500],
            "estimated_cost": round(self.estimated_cost, 6),
            "fallback_chain": self.fallback_chain,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ModelExecutionContext":
        """Deserialize from dict."""
        return cls(
            task_type=d.get("task_type", ""),
            agent_name=d.get("agent_name", ""),
            student_id=d.get("student_id", ""),
            required_capabilities=d.get("required_capabilities", []),
            cost_tier=d.get("cost_tier", ""),
            selected_model=d.get("selected_model", ""),
            selected_provider=d.get("selected_provider", ""),
            fallback_used=d.get("fallback_used", False),
            decision_reason=d.get("decision_reason", ""),
            success=d.get("success", False),
            response_content=d.get("response_content", ""),
            usage_prompt_tokens=d.get("usage_prompt_tokens", 0),
            usage_completion_tokens=d.get("usage_completion_tokens", 0),
            latency_ms=d.get("latency_ms", 0.0),
            error=d.get("error", ""),
            estimated_cost=d.get("estimated_cost", 0.0),
            fallback_chain=d.get("fallback_chain", []),
            timestamp=d.get("timestamp", time.time()),
            metadata=d.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def summary(self) -> str:
        """Human-readable one-line summary."""
        status = "✅" if self.success else "❌"
        fb = " [fallback]" if self.fallback_used else ""
        return (
            f"{status} {self.agent_name} → {self.task_type} "
            f"→ {self.selected_provider}/{self.selected_model} "
            f"({self.cost_tier}){fb} "
            f"in {self.latency_ms:.0f}ms"
        )


@dataclass
class ExecutionResult:
    """Result returned by OrchestratorRuntime.execute()."""

    success: bool
    content: str = ""
    model: str = ""
    provider: str = ""
    usage_prompt_tokens: int = 0
    usage_completion_tokens: int = 0
    latency_ms: float = 0.0
    error: str = ""
    context: Optional[ModelExecutionContext] = None
    fallback_history: List[ModelExecutionContext] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "content": self.content[:500] if self.content else "",
            "model": self.model,
            "provider": self.provider,
            "usage": {
                "prompt_tokens": self.usage_prompt_tokens,
                "completion_tokens": self.usage_completion_tokens,
            },
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
            "context": self.context.to_dict() if self.context else None,
            "fallback_count": len(self.fallback_history),
        }
