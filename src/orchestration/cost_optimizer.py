"""
Phase 9.3-A — Cost Optimizer

Cost-tier model selection for the Model Orchestrator.
Routes simple tasks to low-cost models, high-quality tasks to premium models.

Cost tiers:
    economy — cheapest, for simple non-critical tasks (chat, profile, RAG)
    balanced — mid-range, default for most tasks (plan, material, grading)
    premium  — highest quality, for critical tasks (PPT, video, image gen)

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.config.task_capability import TaskType

# ── Cost tiers ──────────────────────────────────────

COST_TIER = {
    "economy": 0,
    "balanced": 1,
    "premium": 2,
}


# Provider estimated cost per 1M tokens (USD), used for ranking within tiers
_PROVIDER_COST_ESTIMATE: Dict[str, float] = {
    "openai":    2.50,   # GPT-4o
    "anthropic": 3.00,   # Claude
    "google":    1.25,   # Gemini
    "deepseek":  0.14,   # DeepSeek
    "qwen":      0.50,   # Qwen
    "moonshot":  2.00,   # Kimi
    "xai":       2.00,   # Grok
    "spark":     0.30,   # Spark
    "mock":      0.00,
    "rule":      0.00,
}


# Task → cost tier mapping
# Simple tasks use economy, complex/high-stakes tasks use premium
_TASK_COST_TIER: Dict[str, str] = {
    TaskType.CHAT:              "economy",
    TaskType.GENERATE_PROFILE:  "economy",
    TaskType.RAG_RETRIEVAL:     "economy",
    TaskType.GENERATE_PLAN:     "balanced",
    TaskType.GENERATE_MATERIAL: "balanced",
    TaskType.GRADE_ANSWER:      "balanced",
    TaskType.ANALYZE_ERROR:     "balanced",
    TaskType.GENERATE_VIDEO_SCRIPT: "balanced",
    TaskType.GENERATE_PPT:      "premium",
    TaskType.GENERATE_IMAGE:    "premium",
    TaskType.GENERATE_VIDEO:    "premium",
    TaskType.GENERATE_PDF:      "premium",
    TaskType.EXPORT_TEXTBOOK:   "premium",
    TaskType.CREATE_DIAGRAM:    "premium",
    TaskType.CREATE_MINDMAP:    "premium",
    TaskType.GENERATE_TEACHING_VIDEO: "premium",
    TaskType.IMAGE_UNDERSTANDING:     "balanced",
    TaskType.VIDEO_UNDERSTANDING:     "balanced",
}


# Provider → cost tier (which tier does this provider belong to for ranking)
# Override: DeepSeek/Qwen/Spark are economy-tier providers regardless of task
_PROVIDER_COST_TIER: Dict[str, str] = {
    "openai":    "premium",
    "anthropic": "premium",
    "google":    "premium",
    "deepseek":  "economy",
    "qwen":      "economy",
    "moonshot":  "balanced",
    "xai":       "balanced",
    "spark":     "economy",
    "mock":      "economy",
    "rule":      "economy",
}


@dataclass
class CostDecision:
    """Result of cost optimization."""
    target_tier: str         # economy / balanced / premium
    provider: str
    model_id: str
    cost_estimate: float     # USD per 1M tokens
    reason: str


def get_task_cost_tier(task_type: str) -> str:
    """Get the recommended cost tier for a task type."""
    return _TASK_COST_TIER.get(task_type, "balanced")


def get_provider_cost_estimate(provider: str) -> float:
    """Get estimated cost per 1M tokens for a provider."""
    return _PROVIDER_COST_ESTIMATE.get(provider.lower(), 1.0)


def get_provider_cost_tier(provider: str) -> str:
    """Get the cost tier classification for a provider."""
    return _PROVIDER_COST_TIER.get(provider.lower(), "balanced")


def rank_by_cost(
    candidates: List[dict],
    target_tier: str,
) -> List[dict]:
    """
    Rank model candidates by cost, within the target tier.

    For economy tasks: prefer economy providers first, then balanced.
    For balanced tasks: prefer balanced providers first, then economy.
    For premium tasks: any provider that meets capability requirements.

    Each candidate dict must have: 'provider', 'model_id', 'priority'.
    """
    def _score(c: dict) -> float:
        provider = c.get("provider", "").lower()
        cost = _PROVIDER_COST_ESTIMATE.get(provider, 2.0)
        provider_tier = _PROVIDER_COST_TIER.get(provider, "balanced")

        # Tier penalty: providers not in target tier get a penalty
        tier_penalty = {
            "economy": {"economy": 0, "balanced": 10, "premium": 20},
            "balanced": {"balanced": 0, "economy": 5, "premium": 10},
            "premium": {"premium": 0, "balanced": 5, "economy": 10},
        }.get(target_tier, {}).get(provider_tier, 10)

        # Lower cost = better; but priority (quality) also matters
        priority = c.get("priority", 50)
        # Score: higher priority wins, but cost penalty drags it down
        return priority - tier_penalty - cost

    return sorted(candidates, key=_score, reverse=True)


def select_cost_optimal(
    task_type: str,
    candidates: List[dict],
) -> Optional[CostDecision]:
    """
    Select the most cost-appropriate model from candidates.

    Args:
        task_type: TaskType value
        candidates: List of {provider, model_id, priority}

    Returns:
        CostDecision or None if no candidates
    """
    if not candidates:
        return None

    target_tier = get_task_cost_tier(task_type)
    ranked = rank_by_cost(candidates, target_tier)
    best = ranked[0]

    return CostDecision(
        target_tier=target_tier,
        provider=best["provider"],
        model_id=best["model_id"],
        cost_estimate=get_provider_cost_estimate(best["provider"]),
        reason=(
            f"Task '{task_type}' → tier '{target_tier}' "
            f"→ {best['provider']}/{best['model_id']} "
            f"(est. ${get_provider_cost_estimate(best['provider']):.2f}/1M tokens)"
        ),
    )
