"""
Phase 9.3-A — Fallback Manager

API failure auto-switch with circuit breaker pattern.
Tracks per-provider failure counts and cooldown periods.

Flow:
    API call fails → report_failure(provider, model)
        → failure_count++
        → if count >= threshold → circuit breaker OPEN (cooldown)
        → select() excludes failed providers
        → returns next best available model

    API call succeeds → report_success(provider, model)
        → reset failure_count

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

# ── Circuit breaker config ─────────────────────────

# Max consecutive failures before provider is excluded
DEFAULT_FAILURE_THRESHOLD = 2

# Cooldown period in seconds before retrying a failed provider
DEFAULT_COOLDOWN_SECONDS = 30

# Max fallback attempts per request
MAX_FALLBACK_ATTEMPTS = 3


@dataclass
class ProviderState:
    """Per-provider failure tracking."""
    provider: str
    failure_count: int = 0
    last_failure_time: float = 0.0
    last_failure_error: str = ""
    cooldown_until: float = 0.0
    success_count: int = 0

    @property
    def is_in_cooldown(self) -> bool:
        """Whether the provider is currently in cooldown."""
        if self.cooldown_until == 0:
            return False
        if time.time() > self.cooldown_until:
            # Cooldown expired → reset
            return False
        return True

    @property
    def is_excluded(self) -> bool:
        """Whether provider should be excluded from selection."""
        return self.is_in_cooldown


class FallbackManager:
    """
    Manages provider fallback with circuit breaker pattern.

    Tracks failures per provider and auto-excludes providers that
    repeatedly fail within a short window.

    Usage:
        fm = FallbackManager()
        fm.record_failure("openai", "gpt-4o", "timeout")
        fm.record_failure("openai", "gpt-4o", "timeout")
        # Now openai is excluded — is_available("openai") → False
    """

    def __init__(
        self,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ):
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._states: Dict[str, ProviderState] = {}

    def _get_state(self, provider: str) -> ProviderState:
        """Get or create provider state."""
        provider = provider.lower()
        if provider not in self._states:
            self._states[provider] = ProviderState(provider=provider)
        return self._states[provider]

    def is_available(self, provider: str) -> bool:
        """Check if a provider is currently available (not in cooldown)."""
        state = self._get_state(provider)
        if state.is_excluded:
            return False
        return True

    def record_failure(self, provider: str, model_id: str = "", error: str = ""):
        """Record an API failure for a provider."""
        state = self._get_state(provider)
        state.failure_count += 1
        state.last_failure_time = time.time()
        state.last_failure_error = error

        if state.failure_count >= self._failure_threshold:
            state.cooldown_until = time.time() + self._cooldown_seconds

    def record_success(self, provider: str, model_id: str = ""):
        """Record a successful API call — resets failure count."""
        state = self._get_state(provider)
        state.failure_count = 0
        state.cooldown_until = 0.0
        state.success_count += 1

    def get_fallback(
        self,
        task_type: str,
        candidates: List[dict],
        exclude_providers: Optional[Set[str]] = None,
    ) -> Optional[dict]:
        """
        Get the next available fallback model from candidates.

        Args:
            task_type: TaskType value
            candidates: List of {provider, model_id, model_info, priority}
            exclude_providers: Additional providers to exclude

        Returns:
            Best available candidate dict, or None
        """
        excluded = exclude_providers or set()

        for c in candidates:
            provider = c["provider"]
            if provider in excluded:
                continue
            if self.is_available(provider):
                return c

        return None

    def get_excluded_providers(self) -> List[str]:
        """List providers currently in cooldown."""
        return [
            s.provider for s in self._states.values()
            if s.is_excluded
        ]

    def get_provider_stats(self) -> Dict[str, dict]:
        """Get statistics for all tracked providers."""
        return {
            s.provider: {
                "failure_count": s.failure_count,
                "success_count": s.success_count,
                "is_excluded": s.is_excluded,
                "last_error": s.last_failure_error[:100] if s.last_failure_error else "",
                "cooldown_remaining": max(0, s.cooldown_until - time.time()),
            }
            for s in self._states.values()
            if s.failure_count > 0 or s.success_count > 0
        }

    def reset(self, provider: str = ""):
        """Reset failure tracking for a provider or all."""
        if provider:
            provider = provider.lower()
            if provider in self._states:
                del self._states[provider]
        else:
            self._states.clear()
