"""
Phase 9.6-B — Request Context

Unified request-scoped context providing:
  - CurrentUser   (user_id, role, email, username)
  - CurrentPlan   (tier, limits, expiry)
  - CurrentPermission (max_tokens, model_access, multimodal, etc.)

This is the single source of truth for authorization decisions in
any API route or agent call.

Usage:
    from src.auth.context import RequestContext, build_context

    ctx = build_context(user_id="usr_1")
    if ctx.can_use_model("openai"):
        ...

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..user.permission import PermissionManager, Role
from ..billing.models import Plan, PlanTier, get_plan


# ── Data Models ──────────────────────────────

@dataclass
class CurrentUser:
    """User identity for the current request."""
    user_id: str
    username: str = ""
    email: str = ""
    role: str = "free"
    display_name: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_guest(self) -> bool:
        return self.user_id.startswith("guest_")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "display_name": self.display_name,
        }


@dataclass
class CurrentPlan:
    """Active subscription plan for the current request."""
    tier: str = "free"                  # PlanTier value
    monthly_tokens: int = 3_000_000
    model_access: List[str] = field(default_factory=lambda: ["mock", "rule"])
    storage_limit_mb: int = 50
    max_sessions: int = 5
    multimodal: bool = False
    price_usd: float = 0.0

    @classmethod
    def from_plan_tier(cls, tier: PlanTier) -> "CurrentPlan":
        plan = get_plan(tier)
        return cls(
            tier=plan.tier.value,
            monthly_tokens=plan.monthly_tokens,
            model_access=list(plan.model_access),
            storage_limit_mb=plan.storage_limit_mb,
            max_sessions=plan.max_sessions,
            multimodal=plan.multimodal,
            price_usd=plan.price_usd,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "monthly_tokens": self.monthly_tokens,
            "model_access": self.model_access,
            "storage_limit_mb": self.storage_limit_mb,
            "max_sessions": self.max_sessions,
            "multimodal": self.multimodal,
            "price_usd": self.price_usd,
        }


@dataclass
class CurrentPermission:
    """Effective permissions for the current request."""
    max_tokens: int = 100_000
    daily_requests: int = 20
    available_models: List[str] = field(default_factory=lambda: ["mock", "rule"])
    multimodal_access: bool = False
    max_sessions: int = 5
    storage_limit_mb: int = 50
    can_export: bool = True
    can_share: bool = False

    @classmethod
    def from_role(cls, role_str: str) -> "CurrentPermission":
        perm = PermissionManager.get_permission_for_role_str(role_str)
        return cls(
            max_tokens=perm.max_tokens,
            daily_requests=perm.daily_requests,
            available_models=list(perm.available_models),
            multimodal_access=perm.multimodal_access,
            max_sessions=perm.max_sessions,
            storage_limit_mb=perm.storage_limit_mb,
            can_export=perm.can_export,
            can_share=perm.can_share,
        )

    def can_use_model(self, provider: str) -> bool:
        return provider in self.available_models

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "daily_requests": self.daily_requests,
            "available_models": self.available_models,
            "multimodal_access": self.multimodal_access,
            "max_sessions": self.max_sessions,
            "storage_limit_mb": self.storage_limit_mb,
            "can_export": self.can_export,
            "can_share": self.can_share,
        }


# ── Unified Context ──────────────────────────

@dataclass
class RequestContext:
    """Complete request-scoped security context."""
    user: CurrentUser
    plan: CurrentPlan
    permission: CurrentPermission
    request_id: str = ""
    api_key_used: bool = False

    # ── Convenience methods ───────────────

    def can_use_model(self, provider: str) -> bool:
        """Check if current user can access a model provider."""
        return self.permission.can_use_model(provider)

    def can_generate_multimodal(self) -> bool:
        """Check if current user can generate images/video/audio."""
        return self.permission.multimodal_access

    def get_max_tokens(self) -> int:
        return self.permission.max_tokens

    def get_daily_limit(self) -> int:
        return self.permission.daily_requests

    def is_admin(self) -> bool:
        return self.user.is_admin

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user": self.user.to_dict(),
            "plan": self.plan.to_dict(),
            "permission": self.permission.to_dict(),
            "request_id": self.request_id,
            "api_key_used": self.api_key_used,
        }


# ── Builder ──────────────────────────────────

def build_context(
    user_id: str,
    request_id: str = "",
    api_key_used: bool = False,
) -> RequestContext:
    """Build a RequestContext from a user_id.

    Resolves:
      - User identity from UserManager
      - Role/permission from PermissionManager
      - Plan from Plan definitions

    Args:
        user_id: User identifier
        request_id: Optional request correlation ID
        api_key_used: Whether API key auth was used

    Returns:
        RequestContext with resolved user/plan/permission
    """
    from ..user.manager import UserManager

    um = UserManager()
    user = um.get_user(user_id)

    if user is None:
        # Unknown user → guest-free fallback
        cu = CurrentUser(user_id=user_id, username="unknown", role="free")
        perm = CurrentPermission.from_role("free")
        plan = CurrentPlan()
    else:
        cu = CurrentUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            display_name=user.display_name,
        )
        perm = CurrentPermission.from_role(user.role)
        # Map role to plan tier
        role_to_tier = {"free": PlanTier.FREE, "student": PlanTier.STUDENT, "pro": PlanTier.PRO}
        tier = role_to_tier.get(user.role, PlanTier.FREE)
        plan = CurrentPlan.from_plan_tier(tier)

    return RequestContext(
        user=cu,
        plan=plan,
        permission=perm,
        request_id=request_id,
        api_key_used=api_key_used,
    )
