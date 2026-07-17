"""
Phase 5.4 — Recovery Strategy

Defines the recovery strategies available to the RecoveryManager.
Each strategy maps a failure scenario to a recovery action.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import List


class RecoveryStrategy(Enum):
    """
    Recovery actions the RecoveryManager can execute.

    RETRY:               Re-execute the failed state handler.
    CHECKPOINT_ROLLBACK: Restore context to the last saved checkpoint.
    FALLBACK_AGENT:      Switch to a fallback provider and re-execute.
    MEMORY_REPAIR:       Clear corrupted memory/reflection state.
    TERMINATE:           Stop execution gracefully.
    """
    RETRY = "retry"
    CHECKPOINT_ROLLBACK = "checkpoint_rollback"
    FALLBACK_AGENT = "fallback_agent"
    MEMORY_REPAIR = "memory_repair"
    TERMINATE = "terminate"


@dataclass
class RecoveryConfig:
    """
    Configuration for the RecoveryManager.

    Controls retry limits, delays, and which recovery strategies are enabled.
    """
    max_retries: int = 3
    """Maximum retry attempts per state before escalation."""

    retry_delay_seconds: float = 1.0
    """Delay between retry attempts (seconds)."""

    checkpoint_rollback_enabled: bool = True
    """Whether checkpoint rollback is allowed."""

    fallback_providers: List[str] = field(default_factory=lambda: ["deepseek", "openai", "mock"])
    """Ordered list of fallback providers for FALLBACK_AGENT strategy."""

    memory_repair_enabled: bool = True
    """Whether memory repair is allowed."""

    terminate_on_exhaustion: bool = True
    """If True, escalate to TERMINATE when all recovery strategies are exhausted."""
