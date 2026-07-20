"""
Phase 9.5-A — Production Reliability Layer

Provider and user rate limiting, token budgets, retry policy.

Modules:
    rate_limiter  — Provider RPM + User daily limits
    token_budget  — Per-student token budget with persistence
    retry_policy  — Exponential backoff with jitter
    errors        — Unified exception types

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from .rate_limiter import RateLimiter, UserRateLimiter
from .token_budget import TokenBudget, TokenBudgetManager
from .retry_policy import RetryPolicy, RetryConfig
from .errors import (
    PlatformError,
    ProviderUnavailable,
    RateLimitExceeded,
    TokenBudgetExceeded,
    ModelCapabilityError,
    RetryExhausted,
)

__all__ = [
    "RateLimiter", "UserRateLimiter",
    "TokenBudget", "TokenBudgetManager",
    "RetryPolicy", "RetryConfig",
    "PlatformError", "ProviderUnavailable",
    "RateLimitExceeded", "TokenBudgetExceeded",
    "ModelCapabilityError", "RetryExhausted",
]
