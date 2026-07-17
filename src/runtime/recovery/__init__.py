"""
Phase 5.4 — Runtime Recovery Layer

Provides automatic recovery from runtime failures:
  - RecoveryStrategy: RETRY | CHECKPOINT_ROLLBACK | FALLBACK_AGENT | MEMORY_REPAIR | TERMINATE
  - RecoveryManager: failure → strategy → recovery execution
  - CheckpointManager: save/load/rollback context snapshots
  - ProviderFallback: DeepSeek → OpenAI → Mock fallback chain

Usage:
    from src.runtime.recovery import RecoveryManager, RecoveryStrategy, CheckpointManager

    recovery = RecoveryManager()
    recovery.save_checkpoint(ctx, "before_evaluate")
    result = recovery.execute_recovery(failure, ctx, handler)
    print(result.success, result.strategy)
"""

from .strategy import RecoveryStrategy, RecoveryConfig
from .checkpoint_manager import CheckpointManager, ContextSnapshot
from .recovery import RecoveryManager, RecoveryResult, ProviderFallback

__all__ = [
    "RecoveryStrategy",
    "RecoveryConfig",
    "CheckpointManager",
    "ContextSnapshot",
    "RecoveryManager",
    "RecoveryResult",
    "ProviderFallback",
]
