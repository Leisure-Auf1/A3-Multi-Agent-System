"""
Phase 9.5-A — Unified Error Types

Production-grade exceptions for the platform layer.
All errors carry a user-facing message in Chinese.

Architecture: does NOT modify Veritas-Core or src/core/.
"""


class PlatformError(Exception):
    """Base exception for platform layer."""
    def __init__(self, message: str = "", user_message: str = ""):
        super().__init__(message)
        self.user_message = user_message or message


class ProviderUnavailable(PlatformError):
    """Provider is unreachable or in cooldown."""
    pass


class RateLimitExceeded(PlatformError):
    """Provider or user rate limit hit."""
    pass


class TokenBudgetExceeded(PlatformError):
    """User's daily token budget exhausted."""
    pass


class ModelCapabilityError(PlatformError):
    """Selected model does not support the required capability."""
    pass


class RetryExhausted(PlatformError):
    """All retry attempts failed."""
    pass
