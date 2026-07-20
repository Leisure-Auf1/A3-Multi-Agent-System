"""
Phase 9.3-A — Model Selector

Capability + Task + Availability + Quality + Cost comprehensive model selection.

Integrates:
    - ModelRouter (capability matching)
    - TaskPlanner (task type detection)
    - CostOptimizer (cost-tier routing)
    - FallbackManager (failure recovery)
    - Provider Health Check (availability filtering)

Flow:
    Agent request → TaskPlanner → TaskType
        → ModelRouter.find_models(task) → capability-matched candidates
        → Provider health filter → available models only
        → CostOptimizer.select_cost_optimal() → best model
        → FallbackManager (on failure)

Architecture: sits BETWEEN Agent and Provider. Agents NEVER call Provider directly.

Constraints: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.config.model_registry import ModelInfo, get_model
from src.config.model_router import ModelRouter, RouterResult
from src.config.task_capability import TaskType

from .task_planner import TaskPlanner
from .cost_optimizer import (
    select_cost_optimal,
    get_task_cost_tier,
    get_provider_cost_estimate,
    CostDecision,
)
from .fallback_manager import FallbackManager

logger = logging.getLogger(__name__)


@dataclass
class SelectionResult:
    """Result of orchestrated model selection."""

    success: bool
    task_type: str = ""
    model_id: str = ""
    model_info: Optional[ModelInfo] = None
    provider_name: str = ""
    cost_tier: str = ""
    cost_estimate: float = 0.0
    reason: str = ""
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    fallback_used: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task_type": self.task_type,
            "model_id": self.model_id,
            "display_name": self.model_info.display_name if self.model_info else "",
            "provider": self.provider_name,
            "cost_tier": self.cost_tier,
            "cost_estimate": f"${self.cost_estimate:.2f}/1M tokens",
            "reason": self.reason,
            "alternatives": [a.get("display_name", "") for a in self.alternatives[:3]],
            "fallback_used": self.fallback_used,
            "error": self.error,
        }


class ModelSelector:
    """
    Orchestrated model selection engine.

    Combines capability matching (ModelRouter), task planning (TaskPlanner),
    cost optimization (CostOptimizer), availability filtering, and
    failure fallback (FallbackManager) into a single decision.

    Usage:
        selector = ModelSelector()
        result = selector.select(
            user_request="帮我生成Python教材",
            agent_name="ContentGeneratorAgent",
        )
        if result.success:
            provider = ProviderFactory.create(result.provider_name, ...)
    """

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        planner: Optional[TaskPlanner] = None,
        fallback: Optional[FallbackManager] = None,
    ):
        self._router = router or ModelRouter()
        self._planner = planner or TaskPlanner()
        self._fallback = fallback or FallbackManager()
        self._pref_managers: Dict[str, Any] = {}  # Phase 9.4-B: lazy per-student

    # ── Public API ──────────────────────────────

    def select(
        self,
        user_request: str = "",
        agent_name: str = "",
        task_hint: str = "",
        preferred_provider: str = "",
        force_premium: bool = False,
        student_id: str = "",  # Phase 9.4-B: for preference-aware selection
    ) -> SelectionResult:
        """
        Select the best model for a given request.

        Args:
            user_request: Natural language user request
            agent_name: Name of the calling agent
            task_hint: Explicit TaskType hint
            preferred_provider: User's preferred provider
            force_premium: Force premium-tier model regardless of task

        Returns:
            SelectionResult with selected model details
        """
        # Step 1: Determine task type
        task_type = self._planner.plan(
            user_request=user_request,
            agent_name=agent_name,
            task_hint=task_hint,
        )

        # Step 2: Capability filtering via ModelRouter
        router_result = self._router.select_model(
            task=task_type.value,
            preferred_provider=preferred_provider,
        )

        if not router_result.success:
            return SelectionResult(
                success=False,
                task_type=task_type.value,
                reason=router_result.reason,
                error="No capable models found",
            )

        # Step 3: Build candidate list enriched with model info
        candidates = self._build_candidates(router_result)

        # Step 4: Filter by availability (health check)
        available = self._filter_available(candidates)

        if not available:
            # All candidates unavailable — try fallback
            fb_result = self._fallback.get_fallback(
                task_type.value,
                candidates,
                exclude_providers=set(),
            )
            if fb_result:
                return self._build_result(
                    task_type.value,
                    fb_result,
                    "All preferred models unavailable — using fallback",
                    fallback_used=True,
                )
            return SelectionResult(
                success=False,
                task_type=task_type.value,
                reason="All capable models are currently unavailable",
                error="No model available",
            )

        # Step 5: User preference boost (Phase 9.4-B)
        pref_reason = ""
        if student_id:
            pref_model = self._get_user_preferred_model(student_id, task_type.value)
            if pref_model:
                # Check if preferred model is in available candidates
                for c in available:
                    if c.get("model_id") == pref_model:
                        # Boost priority: push to front
                        available.remove(c)
                        available.insert(0, c)
                        pref_reason = f" — 用户偏好 {pref_model}"
                        break
                else:
                    # Preferred model not available for this task
                    from src.config.task_capability import TASK_LABELS
                    task_label = TASK_LABELS.get(task_type.value, task_type.value)
                    pref_reason = (
                        f" — 您偏好的模型不支持{task_label}，"
                        f"系统自动选择替代模型"
                    )

        # Step 6: Cost-optimized selection
        target_tier = "premium" if force_premium else get_task_cost_tier(task_type.value)
        cost_decision = select_cost_optimal(task_type.value, available)

        if not cost_decision:
            return SelectionResult(
                success=False,
                task_type=task_type.value,
                error="Cost optimization failed",
            )

        # Step 6: Verify capability (double-check)
        model_info = get_model(cost_decision.model_id)
        if model_info is None:
            return SelectionResult(
                success=False,
                task_type=task_type.value,
                error=f"Model {cost_decision.model_id} not in registry",
            )

        reason = cost_decision.reason + pref_reason
        return self._build_result(
            task_type.value,
            {
                "provider": cost_decision.provider,
                "model_id": cost_decision.model_id,
                "model_info": model_info,
                "priority": model_info.priority,
            },
            reason,
        )

    def select_with_fallback(
        self,
        user_request: str = "",
        agent_name: str = "",
        task_hint: str = "",
        preferred_provider: str = "",
    ) -> SelectionResult:
        """
        Select model with automatic fallback on failure.

        Returns immediately with the best choice. The caller is responsible
        for calling report_failure() if the API call fails, then retrying
        with select() to get the next fallback.
        """
        return self.select(
            user_request=user_request,
            agent_name=agent_name,
            task_hint=task_hint,
            preferred_provider=preferred_provider,
        )

    def report_failure(self, provider: str, model_id: str, error: str = ""):
        """Report a provider failure to the fallback manager."""
        self._fallback.record_failure(provider, model_id, error)

    def report_success(self, provider: str, model_id: str):
        """Report a successful API call to the fallback manager."""
        self._fallback.record_success(provider, model_id)

    # ── Internal ──────────────────────────────

    def _build_candidates(self, router_result: RouterResult) -> List[dict]:
        """Build enriched candidate list from RouterResult."""
        candidates = []
        if router_result.model_info:
            candidates.append({
                "provider": router_result.model_info.provider,
                "model_id": router_result.model_info.model_id,
                "model_info": router_result.model_info,
                "priority": router_result.model_info.priority,
                "display_name": router_result.model_info.display_name,
            })
        for alt in router_result.alternatives:
            candidates.append({
                "provider": alt.provider,
                "model_id": alt.model_id,
                "model_info": alt,
                "priority": alt.priority,
                "display_name": alt.display_name,
            })
        return candidates

    def _filter_available(self, candidates: List[dict]) -> List[dict]:
        """Filter candidates by provider availability."""
        available = []
        for c in candidates:
            provider = c["provider"]
            if self._fallback.is_available(provider):
                available.append(c)
        return available

    def _get_user_preferred_model(self, student_id: str, task_type: str) -> Optional[str]:
        """Get user's preferred model for a task type (Phase 9.4-B)."""
        if student_id not in self._pref_managers:
            from .user_preferences import UserPreferenceManager
            self._pref_managers[student_id] = UserPreferenceManager(student_id)
        return self._pref_managers[student_id].get_preferred_model(task_type)

    def _build_result(
        self,
        task_type: str,
        selected: dict,
        reason: str,
        fallback_used: bool = False,
    ) -> SelectionResult:
        """Build SelectionResult from selected model data."""
        model_info = selected.get("model_info") or get_model(selected["model_id"])
        provider = selected["provider"]

        return SelectionResult(
            success=True,
            task_type=task_type,
            model_id=selected["model_id"],
            model_info=model_info,
            provider_name=provider,
            cost_tier=get_task_cost_tier(task_type),
            cost_estimate=get_provider_cost_estimate(provider),
            reason=reason,
            fallback_used=fallback_used,
        )


# Module-level convenience
_default_selector: Optional[ModelSelector] = None


def select_model(
    user_request: str = "",
    agent_name: str = "",
    task_hint: str = "",
    preferred_provider: str = "",
) -> SelectionResult:
    """Convenience: select best model for a request."""
    global _default_selector
    if _default_selector is None:
        _default_selector = ModelSelector()
    return _default_selector.select(
        user_request=user_request,
        agent_name=agent_name,
        task_hint=task_hint,
        preferred_provider=preferred_provider,
    )
