"""
Phase 8.3-E2-C — Model Router

Capability-driven model selection engine.
Routes A3 Agent tasks to the best available model based on declared capabilities.

Design:
- find_models(task): list models that satisfy ALL required capabilities
- select_model(task, preferred=None): pick the best model with priority heuristics
- Task priority heuristics: reasoning→Claude/GPT/DeepSeek, coding→DeepSeek/Kimi/GPT,
  multimodal→GPT/Gemini/Qwen, material→GPT/Claude/Qwen/Gemini

Constraints: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model_capability import ModelCapability
from .model_registry import ModelInfo, MODEL_REGISTRY, find_models_with_capability
from .task_capability import TaskType, TASK_REQUIREMENTS


# ──────────────────────────────────────────────
# Priority heuristics per task type
# ──────────────────────────────────────────────

# Task → preferred provider priority order
TASK_PROVIDER_PRIORITY: Dict[str, List[str]] = {
    TaskType.GENERATE_PLAN: ["openai", "anthropic", "deepseek"],
    TaskType.GENERATE_MATERIAL: ["openai", "anthropic", "qwen", "google"],
    TaskType.GENERATE_IMAGE: ["openai", "google"],
    TaskType.GENERATE_PPT: ["openai", "anthropic"],
    TaskType.GENERATE_VIDEO: ["google", "openai"],
    TaskType.GRADE_ANSWER: ["openai", "anthropic", "deepseek"],
    TaskType.ANALYZE_ERROR: ["openai", "anthropic", "deepseek"],
    TaskType.GENERATE_PROFILE: ["openai", "deepseek", "moonshot"],
    TaskType.RAG_RETRIEVAL: ["openai", "deepseek", "moonshot"],
    TaskType.CHAT: ["openai", "deepseek", "moonshot", "qwen"],
    # Phase 8.3-E3-A — multimodal task priorities
    TaskType.CREATE_DIAGRAM: ["openai", "google", "qwen"],
    TaskType.CREATE_MINDMAP: ["openai", "google", "qwen"],
    TaskType.GENERATE_PDF: ["openai", "google"],
    TaskType.EXPORT_TEXTBOOK: ["openai", "google", "anthropic"],
    TaskType.GENERATE_VIDEO_SCRIPT: ["openai", "anthropic", "deepseek"],
    TaskType.GENERATE_TEACHING_VIDEO: ["openai", "google"],
    TaskType.IMAGE_UNDERSTANDING: ["openai", "google", "qwen", "moonshot"],
    TaskType.VIDEO_UNDERSTANDING: ["google", "openai"],
}


@dataclass
class RouterResult:
    """Result of model routing."""

    success: bool
    task: str
    model_id: str = ""
    model_info: Optional[ModelInfo] = None
    reason: str = ""
    alternatives: List[ModelInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task": self.task,
            "model_id": self.model_id,
            "display_name": self.model_info.display_name if self.model_info else "",
            "provider": self.model_info.provider if self.model_info else "",
            "reason": self.reason,
            "alternatives": [m.display_name for m in self.alternatives[:3]],
        }


# ──────────────────────────────────────────────
# ModelRouter
# ──────────────────────────────────────────────


class ModelRouter:
    """Capability-driven model selection engine.

    Usage:
        router = ModelRouter()
        result = router.select_model(TaskType.GENERATE_MATERIAL)
        if result.success:
            print(f"Using: {result.model_info.display_name}")
    """

    def find_models(
        self,
        task: str,
        require_all: bool = True,
    ) -> List[ModelInfo]:
        """
        Find models that satisfy task requirements.

        Args:
            task: TaskType value (e.g. "generate_material")
            require_all: If True, all required caps must be met.
                         If False, models with ANY required cap are included.

        Returns:
            List of ModelInfo sorted by priority (highest first)
        """
        required = TASK_REQUIREMENTS.get(task, [])
        if not required:
            return sorted(
                MODEL_REGISTRY.values(),
                key=lambda m: m.priority, reverse=True,
            )

        candidates = []
        for model in MODEL_REGISTRY.values():
            if require_all:
                if all(cap in model.capabilities for cap in required):
                    candidates.append(model)
            else:
                if any(cap in model.capabilities for cap in required):
                    candidates.append(model)

        candidates.sort(key=lambda m: m.priority, reverse=True)
        return candidates

    def select_model(
        self,
        task: str,
        preferred_provider: str = "",
    ) -> RouterResult:
        """
        Select the best model for a given task.

        Prioritization:
        1. Preferred provider (if specified and capable)
        2. Task-specific provider priority (TASK_PROVIDER_PRIORITY)
        3. Model priority score (from registry)

        Args:
            task: TaskType value
            preferred_provider: Optional explicit provider preference

        Returns:
            RouterResult with selection details
        """
        capable = self.find_models(task, require_all=True)

        if not capable:
            return RouterResult(
                success=False,
                task=task,
                reason="当前没有支持该能力的模型。请尝试安装或配置支持多模态的模型。",
            )

        # ── Preferred provider override ─────
        if preferred_provider:
            for model in capable:
                if model.provider == preferred_provider:
                    return RouterResult(
                        success=True,
                        task=task,
                        model_id=model.model_id,
                        model_info=model,
                        reason=f"使用首选提供商 {preferred_provider} 的模型 {model.display_name}",
                        alternatives=[m for m in capable if m.model_id != model.model_id],
                    )

        # ── Task-specific provider priority ─
        provider_order = TASK_PROVIDER_PRIORITY.get(task, [])
        for provider in provider_order:
            for model in capable:
                if model.provider == provider:
                    return RouterResult(
                        success=True,
                        task=task,
                        model_id=model.model_id,
                        model_info=model,
                        reason=f"任务 {TASK_REQUIREMENTS.get(task, [])} → 优先选择 {provider} 的 {model.display_name}",
                        alternatives=[m for m in capable if m.model_id != model.model_id],
                    )

        # ── Fallback: highest priority ────
        best = capable[0]
        return RouterResult(
            success=True,
            task=task,
            model_id=best.model_id,
            model_info=best,
            reason=f"从 {len(capable)} 个候选模型中按优先级选择 {best.display_name}",
            alternatives=capable[1:],
        )

    def get_capable_providers(self, task: str) -> List[str]:
        """Get distinct providers that have models capable of this task."""
        models = self.find_models(task)
        seen = set()
        providers = []
        for m in models:
            if m.provider not in seen:
                providers.append(m.provider)
                seen.add(m.provider)
        return providers


# ──────────────────────────────────────────────
# Module-level convenience
# ──────────────────────────────────────────────

_router = ModelRouter()


def find_models(task: str) -> List[ModelInfo]:
    return _router.find_models(task)


def select_model(task: str, preferred_provider: str = "") -> RouterResult:
    return _router.select_model(task, preferred_provider=preferred_provider)
