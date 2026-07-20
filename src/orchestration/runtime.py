"""
Phase 9.3-B — Orchestrator Runtime

Production-grade model orchestration runtime.
All Agent model calls go through this layer. Agents NEVER call Provider directly.

Flow:
    Agent → OrchestratorRuntime.execute() → ModelSelector → ProviderFactory → Provider
        ↓ on failure
    FallbackManager → next best model → retry

Usage:
    runtime = OrchestratorRuntime()
    result = runtime.execute(
        task_type="generate_material",
        prompt="...",
        agent_name="ContentGeneratorAgent",
        student_id="student-001",
    )

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context import ExecutionResult, ModelExecutionContext
from .model_selector import ModelSelector, SelectionResult
from .fallback_manager import FallbackManager
from .task_planner import TaskPlanner
from .cost_optimizer import get_task_cost_tier

from src.config.task_capability import TaskType, TASK_REQUIREMENTS
from src.config.model_capability import ModelCapability, CAPABILITY_LABELS
from src.providers.factory import ProviderFactory
from src.providers.base import ProviderResponse

logger = logging.getLogger(__name__)


# ── Decision log path ──────────────────────────

def _get_decision_log_path(student_id: str) -> Path:
    """Get path to model_decisions.jsonl for a student."""
    base = Path(os.path.expanduser("~/.a3-agent/workspace"))
    return base / student_id / "history" / "model_decisions.jsonl"


class OrchestratorRuntime:
    """
    Production model orchestration runtime.

    Central entry point for all Agent → Model calls.
    Handles: task planning, model selection, capability check,
             provider execution, fallback, decision logging.

    Usage:
        runtime = OrchestratorRuntime()
        result = runtime.execute(
            task_type="generate_material",
            prompt="Generate a Python tutorial...",
            agent_name="ContentGeneratorAgent",
            student_id="student-001",
        )
    """

    def __init__(
        self,
        model_selector: Optional[ModelSelector] = None,
        fallback_manager: Optional[FallbackManager] = None,
    ):
        self._selector = model_selector or ModelSelector()
        self._fallback = fallback_manager or self._selector._fallback
        self._planner = TaskPlanner()

        # ── Runtime metrics (Phase 9.4-A) ──
        self.metrics: Dict[str, Any] = {
            "total_calls": 0,
            "success_calls": 0,
            "error_calls": 0,
            "fallback_calls": 0,
            "total_latency_ms": 0.0,
            "total_cost": 0.0,
        }

        # ── Platform layer (Phase 9.5-A) ──
        from src.platform.rate_limiter import RateLimiter, UserRateLimiter
        from src.platform.retry_policy import RetryPolicy
        self._rate_limiter = RateLimiter()
        self._user_rate_limiter = UserRateLimiter()
        self._retry_policy = RetryPolicy()

    # ── Public API ──────────────────────────

    def execute(
        self,
        task_type: str,
        prompt: str,
        agent_name: str = "",
        student_id: str = "",
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        **kwargs,
    ) -> ExecutionResult:
        """
        Execute a model call through the orchestrator.

        Full flow:
        1. Validate task_type against TaskType enum
        2. Capability check — verify required caps exist
        3. ModelSelector.select() — choose best model
        4. ProviderFactory.create() — instantiate provider
        5. provider.generate() — make API call
        6. On failure → FallbackManager → retry with next model
        7. Log decision to workspace model_decisions.jsonl

        Args:
            task_type: TaskType value (e.g. "generate_material")
            prompt: The user prompt to send
            agent_name: Name of calling agent
            student_id: Student identifier (for logging)
            system_prompt: Optional system prompt
            temperature: Generation temperature
            max_tokens: Max tokens

        Returns:
            ExecutionResult with content, model, provider, context
        """
        start_time = time.time()

        # ── Step 1: Validate task type ─────
        try:
            task = TaskType(task_type)
        except ValueError:
            return ExecutionResult(
                success=False,
                error=f"Unknown task type: '{task_type}'. Available: {[t.value for t in TaskType]}",
            )

        # ── Step 2: Capability check ───────
        required_caps = TASK_REQUIREMENTS.get(task.value, [])
        cap_labels = [CAPABILITY_LABELS.get(c, c.name) for c in required_caps if c]

        # ── Step 3: Model selection ────────
        selection = self._selector.select(
            agent_name=agent_name,
            task_hint=task.value,
        )

        if not selection.success:
            ctx = ModelExecutionContext(
                task_type=task.value,
                agent_name=agent_name,
                student_id=student_id,
                required_capabilities=cap_labels,
                success=False,
                error=selection.error,
                decision_reason=selection.reason,
            )
            return ExecutionResult(
                success=False,
                error=selection.error,
                context=ctx,
            )

        # ── Step 4: Platform checks (Phase 9.5-A) ──
        try:
            # Provider rate limit
            self._rate_limiter.check(selection.provider_name)
            # User rate limit
            if student_id:
                self._user_rate_limiter.check(student_id, tokens=max_tokens)
                # Token budget
                from src.platform.token_budget import TokenBudgetManager
                budget_mgr = TokenBudgetManager(student_id)
                budget_mgr.check_available(max_tokens)
        except Exception as e:
            user_msg = getattr(e, "user_message", str(e))
            ctx = ModelExecutionContext(
                task_type=task.value, agent_name=agent_name, student_id=student_id,
                success=False, error=user_msg,
            )
            return ExecutionResult(success=False, error=user_msg, context=ctx)

        # ── Step 5: Create provider ────────
        from src.config.secrets import get_api_key

        api_key = get_api_key(selection.provider_name)
        if not api_key:
            api_key = "mock-enabled"  # will fall through to mock internally

        # ── Step 5: Execute (with fallback) ─
        fallback_history: List[ModelExecutionContext] = []
        current_selection = selection
        excluded = set()

        for attempt in range(3):  # max 3 attempts
            provider = ProviderFactory.create(
                current_selection.provider_name,
                api_key=api_key,
                model=current_selection.model_id,
            )

            call_start = time.time()
            try:
                resp: ProviderResponse = provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                call_elapsed = (time.time() - call_start) * 1000

                if resp.success:
                    self._selector.report_success(
                        current_selection.provider_name,
                        current_selection.model_id,
                    )

                    # Record platform usage
                    self._rate_limiter.record(current_selection.provider_name)
                    if student_id:
                        total_tokens = resp.usage.prompt_tokens + resp.usage.completion_tokens
                        self._user_rate_limiter.record(student_id, tokens=total_tokens)
                        # Consume token budget
                        try:
                            from src.platform.token_budget import TokenBudgetManager
                            budget_mgr = TokenBudgetManager(student_id)
                            budget_mgr.consume(total_tokens, current_selection.provider_name)
                        except Exception:
                            pass

                    # Calculate cost estimate
                    est_cost = self._calc_cost(
                        current_selection.provider_name,
                        resp.usage.prompt_tokens,
                        resp.usage.completion_tokens,
                    )
                    fb_chain = [fb.selected_provider for fb in fallback_history if fb.selected_provider]

                    ctx = ModelExecutionContext(
                        task_type=task.value,
                        agent_name=agent_name,
                        student_id=student_id,
                        required_capabilities=cap_labels,
                        cost_tier=current_selection.cost_tier,
                        selected_model=current_selection.model_id,
                        selected_provider=current_selection.provider_name,
                        fallback_used=len(fallback_history) > 0,
                        decision_reason=current_selection.reason,
                        success=True,
                        response_content=resp.content[:200],
                        usage_prompt_tokens=resp.usage.prompt_tokens,
                        usage_completion_tokens=resp.usage.completion_tokens,
                        latency_ms=call_elapsed,
                        estimated_cost=est_cost,
                        fallback_chain=fb_chain,
                    )

                    # Update metrics
                    self._update_metrics(success=True, fallback=len(fb_chain) > 0,
                                        latency=call_elapsed, cost=est_cost)

                    self._log_decision(ctx)

                    return ExecutionResult(
                        success=True,
                        content=resp.content,
                        model=resp.model,
                        provider=current_selection.provider_name,
                        usage_prompt_tokens=resp.usage.prompt_tokens,
                        usage_completion_tokens=resp.usage.completion_tokens,
                        latency_ms=call_elapsed,
                        context=ctx,
                        fallback_history=fallback_history,
                    )

                # Provider returned error
                self._selector.report_failure(
                    current_selection.provider_name,
                    current_selection.model_id,
                    resp.error,
                )

                fb_ctx = ModelExecutionContext(
                    task_type=task.value,
                    agent_name=agent_name,
                    selected_model=current_selection.model_id,
                    selected_provider=current_selection.provider_name,
                    cost_tier=current_selection.cost_tier,
                    fallback_used=True,
                    decision_reason=f"Attempt {attempt+1} failed: {resp.error[:100]}",
                    success=False,
                    error=resp.error,
                    latency_ms=call_elapsed,
                )
                fallback_history.append(fb_ctx)

            except Exception as e:
                self._selector.report_failure(
                    current_selection.provider_name,
                    current_selection.model_id,
                    str(e),
                )
                fb_ctx = ModelExecutionContext(
                    task_type=task.value,
                    agent_name=agent_name,
                    selected_model=current_selection.model_id,
                    selected_provider=current_selection.provider_name,
                    fallback_used=True,
                    decision_reason=f"Attempt {attempt+1} exception: {str(e)[:100]}",
                    success=False,
                    error=str(e),
                )
                fallback_history.append(fb_ctx)

            # ── Get fallback model ─────────
            excluded.add(current_selection.provider_name)
            candidates = self._build_candidates_from_selection(current_selection)
            next_candidate = self._fallback.get_fallback(
                task.value, candidates, exclude_providers=excluded,
            )
            if next_candidate is None:
                break  # no more fallbacks

            # Create a new SelectionResult-like object for the fallback
            from .model_selector import SelectionResult as SelResult
            current_selection = SelResult(
                success=True,
                task_type=task.value,
                model_id=next_candidate["model_id"],
                model_info=next_candidate.get("model_info"),
                provider_name=next_candidate["provider"],
                cost_tier=get_task_cost_tier(task.value),
                cost_estimate=0.0,
                reason=f"Fallback attempt {attempt+2}: {next_candidate['provider']}/{next_candidate['model_id']}",
                fallback_used=True,
            )

        # All attempts exhausted
        error_ctx = ModelExecutionContext(
            task_type=task.value,
            agent_name=agent_name,
            student_id=student_id,
            required_capabilities=cap_labels,
            success=False,
            error="All models exhausted after 3 attempts",
        )
        self._update_metrics(success=False, fallback=True, latency=0, cost=0)
        self._log_decision(error_ctx)

        return ExecutionResult(
            success=False,
            error="All models exhausted after 3 attempts",
            context=error_ctx,
            fallback_history=fallback_history,
        )

    # ── Convenience for existing Agent pattern ─

    def chat(
        self,
        prompt: str,
        agent_name: str = "",
        student_id: str = "",
        system_prompt: str = "",
        **kwargs,
    ) -> ExecutionResult:
        """Convenience: execute a chat task."""
        return self.execute(
            task_type="chat",
            prompt=prompt,
            agent_name=agent_name,
            student_id=student_id,
            system_prompt=system_prompt,
            **kwargs,
        )

    # ── Internal ──────────────────────────

    def _build_candidates_from_selection(
        self, selection: SelectionResult,
    ) -> List[dict]:
        """Build candidate list from a selection result for fallback."""
        candidates = []
        if selection.model_info:
            candidates.append({
                "provider": selection.provider_name,
                "model_id": selection.model_id,
                "model_info": selection.model_info,
                "priority": selection.model_info.priority,
            })
        for alt in selection.alternatives:
            candidates.append({
                "provider": alt.get("display_name", ""),
                "model_id": alt.get("display_name", ""),
                "priority": 50,
            })
        return candidates

    def _update_metrics(self, success: bool, fallback: bool,
                         latency: float, cost: float):
        """Update runtime metrics counters."""
        self.metrics["total_calls"] += 1
        if success:
            self.metrics["success_calls"] += 1
        else:
            self.metrics["error_calls"] += 1
        if fallback:
            self.metrics["fallback_calls"] += 1
        self.metrics["total_latency_ms"] += latency
        self.metrics["total_cost"] += cost

    def _calc_cost(self, provider: str, prompt_tokens: int,
                   completion_tokens: int) -> float:
        """Calculate estimated USD cost for a call."""
        from .cost_optimizer import get_provider_cost_estimate
        rate = get_provider_cost_estimate(provider)
        total_tokens = prompt_tokens + completion_tokens
        return round(total_tokens / 1_000_000 * rate, 6)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current runtime metrics snapshot."""
        m = dict(self.metrics)
        n = m["total_calls"]
        m["avg_latency_ms"] = round(m["total_latency_ms"] / n, 1) if n else 0.0
        m["success_rate"] = round(m["success_calls"] / n * 100, 1) if n else 0.0
        m["fallback_rate"] = round(m["fallback_calls"] / n * 100, 1) if n else 0.0
        m["total_cost"] = round(m["total_cost"], 4)
        return m

    def _log_decision(self, ctx: ModelExecutionContext):
        """Write a decision log entry to workspace."""
        if not ctx.student_id:
            return
        try:
            path = _get_decision_log_path(ctx.student_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a") as f:
                f.write(ctx.to_json() + "\n")
        except Exception:
            pass  # decision logging is best-effort


# ── Module-level singleton ─────────────────

_default_runtime: Optional[OrchestratorRuntime] = None


def get_runtime() -> OrchestratorRuntime:
    """Get or create the default orchestrator runtime."""
    global _default_runtime
    if _default_runtime is None:
        _default_runtime = OrchestratorRuntime()
    return _default_runtime
