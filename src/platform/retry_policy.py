"""
Phase 9.5-A — Retry Policy

Exponential backoff with jitter for transient failures.

Strategy:
    attempt 1: wait 1s
    attempt 2: wait 2s
    attempt 3: wait 4s
    ... (max 3 retries, max 60s total)

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .errors import RetryExhausted, PlatformError


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0      # seconds
    max_delay: float = 30.0       # seconds
    backoff_factor: float = 2.0   # exponential multiplier
    jitter: bool = True           # add random jitter
    timeout: float = 60.0         # total timeout for all attempts


class RetryPolicy:
    """
    Exponential backoff retry with jitter.

    Usage:
        policy = RetryPolicy(max_retries=3)
        try:
            result = policy.execute(lambda: api_call())
        except RetryExhausted:
            ...
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    def execute(self, fn: Callable, *args, **kwargs):
        """
        Execute fn with retry on failure.

        Args:
            fn: Callable to execute
            *args, **kwargs: Passed to fn

        Returns:
            Result of fn()

        Raises:
            RetryExhausted: All retries failed
        """
        last_error = None
        start_time = time.time()

        for attempt in range(self.config.max_retries + 1):  # 0-indexed: 0..max_retries
            try:
                return fn(*args, **kwargs)
            except PlatformError:
                raise  # Don't retry platform errors (rate limit, budget, etc.)
            except Exception as e:
                last_error = e
                if attempt >= self.config.max_retries:
                    break

                # Check total timeout
                if time.time() - start_time >= self.config.timeout:
                    break

                # Calculate delay
                delay = self.config.base_delay * (self.config.backoff_factor ** attempt)
                delay = min(delay, self.config.max_delay)

                if self.config.jitter:
                    delay *= 0.5 + random.random()  # 50%-150% jitter

                time.sleep(delay)

        raise RetryExhausted(
            message=f"All {self.config.max_retries + 1} attempts failed",
            user_message="❌ 服务暂时不可用，请稍后重试",
        )

    def delay_for_attempt(self, attempt: int) -> float:
        """Calculate delay for a specific attempt."""
        delay = self.config.base_delay * (self.config.backoff_factor ** attempt)
        delay = min(delay, self.config.max_delay)
        if self.config.jitter:
            delay *= 0.5 + random.random()
        return round(delay, 2)
