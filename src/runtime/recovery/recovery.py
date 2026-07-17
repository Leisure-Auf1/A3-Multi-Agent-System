"""
Phase 5.4 — Recovery Manager + Provider Fallback

RecoveryManager: orchestrates failure → strategy → recovery execution.
ProviderFallback: LLM provider chain DeepSeek → OpenAI → Mock.

Integration:
    # With RuntimeEngine
    engine = RuntimeEngine(
        session_id="demo",
        policy_engine=policy,
        recovery_manager=RecoveryManager(),
    )
    # When policy says RETRY → RecoveryManager executes retry with fallback

Backward Compat:
    When recovery_manager is None → engine behaves identically to Phase 5.2.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import time

from .strategy import RecoveryStrategy, RecoveryConfig
from .checkpoint_manager import CheckpointManager


# ──────────────────────────────────────────────
# RecoveryResult
# ──────────────────────────────────────────────


@dataclass
class RecoveryResult:
    """
    Result of a single recovery attempt.

    Fields:
        strategy: Which strategy was attempted.
        success: Whether recovery succeeded.
        detail: Human-readable description.
        duration_ms: Time spent executing the recovery.
        metadata: Strategy-specific data (retry count, checkpoint name, etc.).
    """
    strategy: RecoveryStrategy
    success: bool
    detail: str = ""
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "success": self.success,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


# ──────────────────────────────────────────────
# ProviderFallback
# ──────────────────────────────────────────────


class ProviderFallback:
    """
    LLM provider fallback chain.

    Tries each registered provider in order to execute a function.
    When one provider fails (exception), the next is tried.

    Default chain: DeepSeek → OpenAI → Mock

    Usage:
        pf = ProviderFallback()
        pf.register("deepseek", deepseek_provider)
        pf.register("openai", openai_provider)
        pf.register("mock", mock_provider)

        result, provider_name = pf.try_with_fallback(
            lambda p: p.generate("hello")
        )
        print(f"Served by: {provider_name}")
    """

    def __init__(self, provider_order: Optional[List[str]] = None):
        self._order = provider_order or ["deepseek", "openai", "mock"]
        self._available: Dict[str, Any] = {}
        self._last_success: Optional[str] = None

    def register(self, name: str, provider: Any) -> None:
        """
        Register a named provider for fallback.

        Args:
            name: Provider name matching an entry in provider_order.
            provider: An object with a callable interface.
        """
        self._available[name] = provider

    def unregister(self, name: str) -> None:
        """Remove a registered provider."""
        self._available.pop(name, None)

    def try_with_fallback(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> tuple:
        """
        Execute fn with each available provider until one succeeds.

        Args:
            fn: Callable receiving (provider, *args, **kwargs).
            *args, **kwargs: Additional arguments passed to fn.

        Returns:
            Tuple of (result, provider_name).

        Raises:
            RuntimeError: If all providers in the chain fail.
        """
        last_error = None
        for name in self._order:
            provider = self._available.get(name)
            if provider is None:
                continue
            try:
                result = fn(provider, *args, **kwargs)
                self._last_success = name
                return result, name
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(
            f"ProviderFallback exhausted ({self._order}): {last_error}"
        )

    @property
    def last_provider(self) -> Optional[str]:
        """Name of the provider that succeeded last."""
        return self._last_success

    @property
    def provider_order(self) -> List[str]:
        """Current fallback order."""
        return list(self._order)

    @property
    def registered_providers(self) -> List[str]:
        """Names of registered providers."""
        return list(self._available.keys())


# ──────────────────────────────────────────────
# RecoveryManager
# ──────────────────────────────────────────────


class RecoveryManager:
    """
    Orchestrates runtime recovery: failure → strategy → execution.

    Integrates with RuntimePolicyEngine decisions. When the policy
    returns RETRY, RecoveryManager executes the recovery action.

    Architecture:
        FailureDetector → FailureEvent
               ↓
        RuntimePolicyEngine → RuntimeDecision (RETRY)
               ↓
        RecoveryManager.select_strategy(failure) → RecoveryStrategy
               ↓
        RecoveryManager.execute_recovery(failure, ctx, handler) → RecoveryResult

    Backward compatibility:
        When recovery_manager is None, RuntimeEngine behaves identically
        to Phase 5.2 — no recovery layer, just the policy engine.

    Usage:
        recovery = RecoveryManager()
        recovery.save_checkpoint(ctx, "before_eval")

        failure = FailureEvent(failure_type="EXCEPTION", ...)
        result = recovery.execute_recovery(failure, ctx, handler)
        if result.success:
            print("Recovered:", result.detail)
    """

    def __init__(
        self,
        config: Optional[RecoveryConfig] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        provider_fallback: Optional[ProviderFallback] = None,
    ):
        self.config = config or RecoveryConfig()
        self._checkpoints = checkpoint_manager or CheckpointManager()
        self._provider_fallback = provider_fallback or ProviderFallback()
        self._retry_counts: Dict[str, int] = {}
        self._history: List[RecoveryResult] = []

    # ── Strategy Selection ────────────────────

    def select_strategy(self, failure: Any) -> RecoveryStrategy:
        """
        Select the appropriate recovery strategy for a failure event.

        Mapping:
            EXCEPTION         → RETRY
            TIMEOUT           → RETRY
            LOW_SCORE         → CHECKPOINT_ROLLBACK
            REPEATED_TRANSITION → TERMINATE
            MEMORY_FAILURE    → MEMORY_REPAIR
        """
        ft = getattr(failure, 'failure_type', '')

        if ft == "EXCEPTION":
            return RecoveryStrategy.RETRY
        elif ft == "TIMEOUT":
            return RecoveryStrategy.RETRY
        elif ft == "LOW_SCORE":
            return RecoveryStrategy.CHECKPOINT_ROLLBACK
        elif ft == "REPEATED_TRANSITION":
            return RecoveryStrategy.TERMINATE
        elif ft == "MEMORY_FAILURE":
            return RecoveryStrategy.MEMORY_REPAIR
        return RecoveryStrategy.TERMINATE

    # ── Recovery Execution ────────────────────

    def execute_recovery(
        self,
        failure: Any,
        context: Any,
        handler: Optional[Callable[[Any], None]] = None,
        strategy: Optional[RecoveryStrategy] = None,
    ) -> RecoveryResult:
        """
        Execute a recovery action for the given failure.

        Args:
            failure: FailureEvent from FailureDetector.
            context: RuntimeContext to operate on.
            handler: State handler to re-execute (for RETRY/FALLBACK_AGENT).
            strategy: Override auto-selected strategy.

        Returns:
            RecoveryResult describing the outcome.
        """
        t0 = time.time()
        strategy = strategy or self.select_strategy(failure)

        result = self._execute(strategy, failure, context, handler)
        result.duration_ms = (time.time() - t0) * 1000
        self._history.append(result)
        return result

    def _execute(
        self,
        strategy: RecoveryStrategy,
        failure: Any,
        context: Any,
        handler: Optional[Callable[[Any], None]],
    ) -> RecoveryResult:
        """Dispatch to the appropriate recovery implementation."""
        if strategy == RecoveryStrategy.RETRY:
            return self._retry_recovery(failure, context, handler)
        elif strategy == RecoveryStrategy.CHECKPOINT_ROLLBACK:
            return self._rollback_recovery(failure, context)
        elif strategy == RecoveryStrategy.FALLBACK_AGENT:
            return self._fallback_recovery(failure, context, handler)
        elif strategy == RecoveryStrategy.MEMORY_REPAIR:
            return self._memory_repair_recovery(failure, context)
        elif strategy == RecoveryStrategy.TERMINATE:
            return RecoveryResult(
                strategy=strategy,
                success=True,
                detail="Execution terminated by recovery policy",
            )
        return RecoveryResult(
            strategy=strategy, success=False, detail="Unknown strategy"
        )

    # ── Strategy Implementations ──────────────

    def _retry_recovery(
        self,
        failure: Any,
        context: Any,
        handler: Optional[Callable[[Any], None]],
    ) -> RecoveryResult:
        """Attempt to re-execute the failed handler (with retry limits)."""
        failure_state = getattr(failure, 'state', None)
        state_key = failure_state.name if failure_state is not None else "unknown"
        count = self._retry_counts.get(state_key, 0)

        if count >= self.config.max_retries:
            return RecoveryResult(
                strategy=RecoveryStrategy.RETRY,
                success=False,
                detail=(
                    f"Max retries ({self.config.max_retries}) exceeded "
                    f"for {state_key}"
                ),
                metadata={"retries": count, "state": state_key},
            )

        self._retry_counts[state_key] = count + 1

        if handler is None:
            return RecoveryResult(
                strategy=RecoveryStrategy.RETRY,
                success=False,
                detail=f"No handler provided for retry on {state_key}",
            )

        # Delay before retry (skip on first attempt)
        if self.config.retry_delay_seconds > 0 and count > 0:
            time.sleep(self.config.retry_delay_seconds)

        try:
            handler(context)
            return RecoveryResult(
                strategy=RecoveryStrategy.RETRY,
                success=True,
                detail=(
                    f"Retry {count + 1}/{self.config.max_retries} "
                    f"succeeded for {state_key}"
                ),
                metadata={"retries": count + 1, "state": state_key},
            )
        except Exception as e:
            return RecoveryResult(
                strategy=RecoveryStrategy.RETRY,
                success=False,
                detail=f"Retry {count + 1} failed: {e}",
                metadata={
                    "retries": count + 1,
                    "state": state_key,
                    "error": str(e),
                },
            )

    def _rollback_recovery(
        self,
        failure: Any,
        context: Any,
    ) -> RecoveryResult:
        """Restore context to the last saved checkpoint."""
        if not self.config.checkpoint_rollback_enabled:
            return RecoveryResult(
                strategy=RecoveryStrategy.CHECKPOINT_ROLLBACK,
                success=False,
                detail="Checkpoint rollback disabled in config",
            )

        latest = self._checkpoints.latest()
        if latest is None:
            return RecoveryResult(
                strategy=RecoveryStrategy.CHECKPOINT_ROLLBACK,
                success=False,
                detail="No checkpoint available for rollback",
            )

        self._checkpoints.rollback(context, latest.name)
        return RecoveryResult(
            strategy=RecoveryStrategy.CHECKPOINT_ROLLBACK,
            success=True,
            detail=f"Rolled back to checkpoint '{latest.name}'",
            metadata={"checkpoint": latest.name},
        )

    def _fallback_recovery(
        self,
        failure: Any,
        context: Any,
        handler: Optional[Callable[[Any], None]],
    ) -> RecoveryResult:
        """Execute handler with a fallback provider (handled by ProviderFallback)."""
        if handler is None:
            return RecoveryResult(
                strategy=RecoveryStrategy.FALLBACK_AGENT,
                success=False,
                detail="No handler for fallback execution",
            )

        try:
            handler(context)
            last = self._provider_fallback.last_provider or "default"
            return RecoveryResult(
                strategy=RecoveryStrategy.FALLBACK_AGENT,
                success=True,
                detail=f"Fallback agent succeeded, using {last}",
                metadata={"provider": last},
            )
        except Exception as e:
            return RecoveryResult(
                strategy=RecoveryStrategy.FALLBACK_AGENT,
                success=False,
                detail=f"Fallback agent failed: {e}",
                metadata={"error": str(e)},
            )

    def _memory_repair_recovery(
        self,
        failure: Any,
        context: Any,
    ) -> RecoveryResult:
        """Clear corrupted memory/reflection state."""
        if not self.config.memory_repair_enabled:
            return RecoveryResult(
                strategy=RecoveryStrategy.MEMORY_REPAIR,
                success=False,
                detail="Memory repair disabled in config",
            )

        repaired = []
        if hasattr(context, 'errors'):
            context.errors.clear()
            repaired.append("errors")

        if hasattr(context, 'meta_reflection'):
            context.meta_reflection = None
            repaired.append("meta_reflection")

        if hasattr(context, 'reflection'):
            context.reflection = None
            repaired.append("reflection")

        return RecoveryResult(
            strategy=RecoveryStrategy.MEMORY_REPAIR,
            success=True,
            detail=f"Memory repaired: cleared {', '.join(repaired) if repaired else 'nothing'}",
            metadata={"repaired": repaired},
        )

    # ── Checkpoint Convenience ────────────────

    def save_checkpoint(self, ctx: Any, name: Optional[str] = None) -> str:
        """Save a named checkpoint of the current context state."""
        return self._checkpoints.save(ctx, name)

    def rollback_to(self, ctx: Any, name: str) -> bool:
        """Restore context from a named checkpoint."""
        return self._checkpoints.rollback(ctx, name)

    # ── Query ─────────────────────────────────

    @property
    def checkpoints(self) -> CheckpointManager:
        return self._checkpoints

    @property
    def provider_fallback(self) -> ProviderFallback:
        return self._provider_fallback

    @property
    def history(self) -> List[RecoveryResult]:
        return list(self._history)

    def reset(self) -> None:
        """Reset all state: retry counts, history, and checkpoints."""
        self._retry_counts.clear()
        self._history.clear()
        self._checkpoints.clear()
