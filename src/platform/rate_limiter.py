"""
Phase 9.5-A — Rate Limiter

Provider-level and user-level rate limiting with sliding windows.

Provider limits (requests per minute):
    openai:    60
    anthropic: 50
    google:    30
    deepseek:  30
    qwen:      30
    moonshot:  20
    xai:       20
    spark:     20
    mock:      999

User limits (per student_id):
    daily_requests: 500
    daily_tokens:   1,000,000

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .errors import RateLimitExceeded

# ── Provider limits (requests/minute) ───────────

PROVIDER_RPM: Dict[str, int] = {
    "openai":    60,
    "anthropic": 50,
    "google":    30,
    "deepseek":  30,
    "qwen":      30,
    "moonshot":  20,
    "xai":       20,
    "spark":     20,
    "mock":      999,
    "rule":      999,
}

# ── User limits ─────────────────────────────────

DEFAULT_USER_DAILY_REQUESTS = 500
DEFAULT_USER_DAILY_TOKENS = 1_000_000


@dataclass
class RateLimitState:
    """Per-provider sliding window state."""
    window_start: float = 0.0
    request_count: int = 0


class RateLimiter:
    """
    Provider-level rate limiter with sliding 1-minute windows.

    Usage:
        rl = RateLimiter()
        rl.check("openai")           # raises RateLimitExceeded if over limit
        rl.record("openai")          # record a successful request
        rl.remaining("openai")       # → int
    """

    def __init__(self, provider_limits: Optional[Dict[str, int]] = None):
        self._limits = provider_limits or dict(PROVIDER_RPM)
        self._windows: Dict[str, RateLimitState] = defaultdict(RateLimitState)

    def check(self, provider: str):
        """Check if provider has remaining capacity. Raises RateLimitExceeded."""
        limit = self._limits.get(provider.lower(), 30)
        state = self._windows[provider.lower()]

        now = time.time()
        # Reset window if > 60s elapsed
        if now - state.window_start >= 60:
            state.window_start = now
            state.request_count = 0

        if state.request_count >= limit:
            remaining_sec = 60 - (now - state.window_start)
            raise RateLimitExceeded(
                message=f"Rate limit exceeded for {provider}: {state.request_count}/{limit} rpm",
                user_message=f"❌ {provider} 当前请求繁忙，请等待 {remaining_sec:.0f}s 后重试",
            )

    def record(self, provider: str):
        """Record a successful request."""
        state = self._windows[provider.lower()]
        now = time.time()
        if now - state.window_start >= 60:
            state.window_start = now
            state.request_count = 0
        state.request_count += 1

    def remaining(self, provider: str) -> int:
        """Get remaining requests in current window."""
        limit = self._limits.get(provider.lower(), 30)
        state = self._windows[provider.lower()]
        now = time.time()
        if now - state.window_start >= 60:
            return limit
        return max(0, limit - state.request_count)

    def reset(self, provider: str = ""):
        """Reset rate limit for a provider or all."""
        if provider:
            self._windows.pop(provider.lower(), None)
        else:
            self._windows.clear()


class UserRateLimiter:
    """
    Per-user rate limiter with daily limits.

    Tracks: daily_requests and daily_tokens.

    Usage:
        url = UserRateLimiter()
        url.check("student-001", tokens=1000)
        url.record("student-001", tokens=500)
        url.remaining_requests("student-001")
    """

    def __init__(
        self,
        daily_requests: int = DEFAULT_USER_DAILY_REQUESTS,
        daily_tokens: int = DEFAULT_USER_DAILY_TOKENS,
    ):
        self._daily_requests = daily_requests
        self._daily_tokens = daily_tokens
        self._usage: Dict[str, dict] = defaultdict(
            lambda: {"requests": 0, "tokens": 0, "day_start": time.time()},
        )

    def _maybe_reset(self, student_id: str):
        """Reset daily counters if 24h elapsed."""
        u = self._usage[student_id]
        if time.time() - u["day_start"] >= 86400:
            u["requests"] = 0
            u["tokens"] = 0
            u["day_start"] = time.time()

    def check(self, student_id: str, tokens: int = 0):
        """Check user limits. Raises RateLimitExceeded."""
        self._maybe_reset(student_id)
        u = self._usage[student_id]

        if u["requests"] >= self._daily_requests:
            raise RateLimitExceeded(
                user_message=f"❌ 今日请求次数已达上限 ({self._daily_requests})，请明天再试",
            )
        if tokens > 0 and u["tokens"] + tokens > self._daily_tokens:
            raise RateLimitExceeded(
                user_message=f"❌ 今日 Token 用量已达上限 ({self._daily_tokens})，请明天再试",
            )

    def record(self, student_id: str, tokens: int = 0):
        """Record usage."""
        self._maybe_reset(student_id)
        u = self._usage[student_id]
        u["requests"] += 1
        u["tokens"] += tokens

    def remaining_requests(self, student_id: str) -> int:
        self._maybe_reset(student_id)
        return max(0, self._daily_requests - self._usage[student_id]["requests"])

    def remaining_tokens(self, student_id: str) -> int:
        self._maybe_reset(student_id)
        return max(0, self._daily_tokens - self._usage[student_id]["tokens"])

    def get_usage(self, student_id: str) -> dict:
        self._maybe_reset(student_id)
        u = self._usage[student_id]
        return {
            "requests": u["requests"],
            "tokens": u["tokens"],
            "remaining_requests": self.remaining_requests(student_id),
            "remaining_tokens": self.remaining_tokens(student_id),
        }

    def reset(self, student_id: str = ""):
        if student_id:
            self._usage.pop(student_id, None)
        else:
            self._usage.clear()
