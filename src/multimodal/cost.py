"""
Phase 9.5 — Cost Controller

Token budgets, API rate limits, quota management per user tier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime, timezone

from .artifact import ResourceType


@dataclass
class QuotaExceededError(Exception):
    """Raised when user exceeds their quota."""
    resource_type: str
    current: int
    limit: int
    message: str = ""


TIER_CONFIGS = {
    "free": {
        "daily_tokens": 10_000,
        "daily_images": 5,
        "daily_ppts": 1,
        "daily_code_labs": 10,
        "daily_documents": 20,
        "max_concurrent": 1,
    },
    "pro": {
        "daily_tokens": 100_000,
        "daily_images": 50,
        "daily_ppts": 10,
        "daily_code_labs": 100,
        "daily_documents": 200,
        "max_concurrent": 5,
    },
}

RESOURCE_QUOTA_MAP = {
    ResourceType.DOCUMENT: "daily_documents",
    ResourceType.MINDMAP: "daily_documents",
    ResourceType.EXERCISE: "daily_documents",
    ResourceType.CODE_LAB: "daily_code_labs",
    ResourceType.SLIDES: "daily_ppts",
    ResourceType.ILLUSTRATION: "daily_images",
    ResourceType.VIDEO_SCRIPT: "daily_documents",
}


class CostController:
    """Manages per-user quotas and token budgets."""

    def __init__(self, tier: str = "free"):
        self.tier = tier
        self.config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
        self._usage: Dict[str, int] = {
            "daily_tokens": 0,
            "daily_images": 0,
            "daily_ppts": 0,
            "daily_code_labs": 0,
            "daily_documents": 0,
        }
        self._last_reset = datetime.now(timezone.utc).date()

    def _check_reset(self):
        """Reset counters if new day."""
        today = datetime.now(timezone.utc).date()
        if today != self._last_reset:
            self._usage = {k: 0 for k in self._usage}
            self._last_reset = today

    def can_generate(self, resource_type: ResourceType) -> bool:
        """Check if user can generate this resource type."""
        self._check_reset()
        quota_key = RESOURCE_QUOTA_MAP.get(resource_type)
        if quota_key is None:
            return True
        limit = self.config.get(quota_key, 0)
        current = self._usage.get(quota_key, 0)
        return current < limit

    def record_usage(self, resource_type: ResourceType, tokens: int = 0):
        """Record resource generation usage."""
        self._check_reset()
        self._usage["daily_tokens"] += tokens

        quota_key = RESOURCE_QUOTA_MAP.get(resource_type)
        if quota_key:
            self._usage[quota_key] = self._usage.get(quota_key, 0) + 1

    def get_remaining(self, resource_type: ResourceType) -> int:
        """Get remaining quota for a resource type."""
        self._check_reset()
        quota_key = RESOURCE_QUOTA_MAP.get(resource_type)
        if quota_key is None:
            return 999
        limit = self.config.get(quota_key, 0)
        current = self._usage.get(quota_key, 0)
        return max(0, limit - current)

    def get_usage_summary(self) -> dict:
        """Get current usage summary."""
        self._check_reset()
        return {
            "tier": self.tier,
            "tokens_used": self._usage["daily_tokens"],
            "tokens_limit": self.config["daily_tokens"],
            "images_used": self._usage["daily_images"],
            "images_limit": self.config["daily_images"],
            "ppts_used": self._usage["daily_ppts"],
            "ppts_limit": self.config["daily_ppts"],
            "code_labs_used": self._usage["daily_code_labs"],
            "code_labs_limit": self.config["daily_code_labs"],
        }
