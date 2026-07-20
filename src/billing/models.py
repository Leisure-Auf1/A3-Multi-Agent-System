"""
Phase 9.5-B — Subscription / Billing Layer

Plan definitions for the multi-user platform.

Plans:
  free      — Basic access, limited tokens
  student   — Educational discount, moderate limits
  pro       — Full access, high limits

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanTier(str, Enum):
    """Subscription plan tiers."""
    FREE = "free"
    STUDENT = "student"
    PRO = "pro"


@dataclass
class Plan:
    """Subscription plan definition."""
    tier: PlanTier
    name: str                          # Human-readable name
    monthly_tokens: int                # Token quota per month
    model_access: tuple                # Accessible model providers
    storage_limit_mb: int              # Workspace storage limit
    max_sessions: int                  # Concurrent sessions
    multimodal: bool                   # Image/video/audio generation
    price_usd: float = 0.0             # Monthly price (0 for free)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "name": self.name,
            "monthly_tokens": self.monthly_tokens,
            "model_access": list(self.model_access),
            "storage_limit_mb": self.storage_limit_mb,
            "max_sessions": self.max_sessions,
            "multimodal": self.multimodal,
            "price_usd": self.price_usd,
        }


# ── Plan Definitions ────────────────────

PLANS: Dict[PlanTier, Plan] = {
    PlanTier.FREE: Plan(
        tier=PlanTier.FREE,
        name="Free",
        monthly_tokens=3_000_000,
        model_access=("mock", "rule"),
        storage_limit_mb=50,
        max_sessions=5,
        multimodal=False,
        price_usd=0.0,
    ),
    PlanTier.STUDENT: Plan(
        tier=PlanTier.STUDENT,
        name="Student",
        monthly_tokens=15_000_000,
        model_access=("mock", "rule", "deepseek", "qwen"),
        storage_limit_mb=200,
        max_sessions=15,
        multimodal=False,
        price_usd=4.99,
    ),
    PlanTier.PRO: Plan(
        tier=PlanTier.PRO,
        name="Pro",
        monthly_tokens=60_000_000,
        model_access=(
            "mock", "rule", "deepseek", "qwen",
            "openai", "anthropic", "google", "kimi", "grok", "spark",
        ),
        storage_limit_mb=1000,
        max_sessions=50,
        multimodal=True,
        price_usd=19.99,
    ),
}


@dataclass
class Subscription:
    """Active subscription for a user."""
    user_id: str
    plan: PlanTier = PlanTier.FREE
    started_at: str = ""
    expires_at: str = ""
    is_active: bool = True
    auto_renew: bool = False

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "plan": self.plan.value,
            "started_at": self.started_at,
            "expires_at": self.expires_at,
            "is_active": self.is_active,
            "auto_renew": self.auto_renew,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Subscription":
        plan = d.get("plan", "free")
        if isinstance(plan, str):
            try:
                plan = PlanTier(plan)
            except ValueError:
                plan = PlanTier.FREE
        return cls(
            user_id=d.get("user_id", ""),
            plan=plan,
            started_at=d.get("started_at", ""),
            expires_at=d.get("expires_at", ""),
            is_active=d.get("is_active", True),
            auto_renew=d.get("auto_renew", False),
        )


def get_plan(tier: PlanTier) -> Plan:
    """Get plan definition by tier."""
    return PLANS.get(tier, PLANS[PlanTier.FREE])
