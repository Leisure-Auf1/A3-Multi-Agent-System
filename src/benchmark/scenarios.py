"""
Phase 5.6 — Benchmark Failure Scenarios & Injection

Defines failure scenarios and injectors for benchmarking the Runtime
Recovery Layer. Injectors wrap state handlers to simulate real-world
failures WITHOUT modifying agent business logic.

Usage:
    from src.benchmark import FailureScenario, FailureInjector

    injector = FailureInjector()
    handler = injector.wrap("profile", original_handler, FailureScenario.AGENT_EXCEPTION)
    # handler will fail once then succeed
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class FailureScenario(Enum):
    """
    Benchmark failure scenarios for testing Runtime recovery.

    NORMAL:           No failure injected — baseline measurement.
    LLM_TIMEOUT:      Simulates LLM provider timeout.
    AGENT_EXCEPTION:  Handler raises an exception.
    MEMORY_FAILURE:   Corrupted memory/reflection state.
    LOW_SCORE:        Evaluation returns a low score.
    """
    NORMAL = "normal"
    LLM_TIMEOUT = "llm_timeout"
    AGENT_EXCEPTION = "agent_exception"
    MEMORY_FAILURE = "memory_failure"
    LOW_SCORE = "low_score"

    @property
    def label(self) -> str:
        return _LABELS.get(self, self.value)


_LABELS = {
    FailureScenario.NORMAL: "正常执行",
    FailureScenario.LLM_TIMEOUT: "LLM 超时",
    FailureScenario.AGENT_EXCEPTION: "Agent 异常",
    FailureScenario.MEMORY_FAILURE: "记忆损坏",
    FailureScenario.LOW_SCORE: "低分评估",
}


@dataclass
class InjectionConfig:
    """
    Configuration for failure injection.

    Controls when and how failures are triggered.
    """
    fail_on_attempt: int = 1
    """Which attempt triggers the failure (1-indexed). Default: fail on first."""

    recover_on_retry: bool = True
    """If True, the handler succeeds on subsequent retry attempts."""

    exception_message: str = "Injected failure for benchmark"
    """Exception message when AGENT_EXCEPTION is used."""

    timeout_seconds: float = 31.0
    """Simulated timeout duration (ms) for LLM_TIMEOUT."""

    memory_corrupt_fields: List[str] = field(default_factory=lambda: ["errors", "reflection"])
    """Fields to corrupt for MEMORY_FAILURE."""

    low_score_value: int = 35
    """Score value for LOW_SCORE scenario."""


class FailureInjector:
    """
    Injects failures into state handlers for benchmarking.

    Wraps the original handler to simulate specific failure scenarios.
    Does NOT modify the handler itself — just intercepts calls.

    Usage:
        injector = FailureInjector()
        wrapped = injector.wrap(
            agent_name="profile",
            handler=original_handler,
            scenario=FailureScenario.AGENT_EXCEPTION,
        )
        engine.register_handler(AgentState.PROFILE, wrapped)
    """

    def __init__(self):
        self._attempt_counts: Dict[str, int] = {}
        self._injected: Dict[str, List[Dict[str, Any]]] = {}
        self.reset()

    def reset(self) -> None:
        """Reset all injection state."""
        self._attempt_counts.clear()
        self._injected.clear()

    def wrap(
        self,
        agent_name: str,
        handler: Callable[[Any], None],
        scenario: FailureScenario,
        config: Optional[InjectionConfig] = None,
    ) -> Callable[[Any], None]:
        """
        Wrap a handler to inject failures.

        Args:
            agent_name: Agent identifier for tracking attempts.
            handler: The original state handler.
            scenario: Which failure to inject.
            config: Injection configuration (uses defaults if None).

        Returns:
            A wrapped callable with the same signature.
        """
        cfg = config or InjectionConfig()
        agent_name = agent_name or "unknown"

        def wrapped(ctx: Any) -> None:
            key = agent_name
            count = self._attempt_counts.get(key, 0) + 1
            self._attempt_counts[key] = count

            should_fail = self._should_fail(scenario, count, cfg)

            if not should_fail:
                # Success path — call original handler
                handler(ctx)
                return

            # ── Failure path ──────────────────
            self._record_injection(key, scenario, count)

            if scenario == FailureScenario.NORMAL:
                handler(ctx)

            elif scenario == FailureScenario.AGENT_EXCEPTION:
                raise RuntimeError(cfg.exception_message)

            elif scenario == FailureScenario.LLM_TIMEOUT:
                # Simulate timeout by raising an exception
                raise TimeoutError(
                    f"LLM timeout after {cfg.timeout_seconds}s"
                )

            elif scenario == FailureScenario.MEMORY_FAILURE:
                # Corrupt context memory
                for field in cfg.memory_corrupt_fields:
                    if hasattr(ctx, field):
                        if field == "errors":
                            ctx.errors.append("CORRUPTED_MEMORY")
                        else:
                            setattr(ctx, field, {"corrupted": True, "error": "memory failure"})
                handler(ctx)

            elif scenario == FailureScenario.LOW_SCORE:
                # Inject a low evaluation score
                handler(ctx)
                if hasattr(ctx, 'evaluation'):
                    ctx.evaluation = {"score": cfg.low_score_value, "issues": ["injected low score"]}

        return wrapped

    # ── Internal ─────────────────────────────

    def _should_fail(
        self,
        scenario: FailureScenario,
        attempt: int,
        config: InjectionConfig,
    ) -> bool:
        """Determine if this attempt should fail."""
        if scenario == FailureScenario.NORMAL:
            return False

        if not config.recover_on_retry:
            # Always fail
            return True

        # Fail on the specified attempt, succeed on others
        return attempt == config.fail_on_attempt

    def _record_injection(
        self,
        agent_name: str,
        scenario: FailureScenario,
        attempt: int,
    ) -> None:
        """Record an injection event for benchmark analysis."""
        if agent_name not in self._injected:
            self._injected[agent_name] = []
        self._injected[agent_name].append({
            "scenario": scenario.value,
            "attempt": attempt,
        })

    # ── Query ────────────────────────────────

    @property
    def injection_log(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all injection events."""
        return dict(self._injected)

    @property
    def total_injections(self) -> int:
        return sum(len(v) for v in self._injected.values())
