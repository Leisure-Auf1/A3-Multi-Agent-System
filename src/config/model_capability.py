"""
Phase 8.3-E1 — LLM Capability Awareness Layer

ModelCapability: typed capability flags for LLM providers.
Provider capability registry: maps provider→model→capabilities.
require_capability(): unified guard for multimodal features.

Design:
- Does NOT modify Veritas-Core LLMProvider base class
- Does NOT modify src/core/
- Provider interface backward compatible (no method added to base)
- All capability declarations live in A3's config layer
"""

from __future__ import annotations
from enum import Flag, auto
from typing import Optional


# ──────────────────────────────────────────────
# Capability Flags
# ──────────────────────────────────────────────


class ModelCapability(Flag):
    """Capability flags for LLM providers and models.

    Each flag represents a distinct capability the model supports.
    Providers declare which capabilities their models support.

    Usage:
        caps = ModelCapability.TEXT | ModelCapability.IMAGE_INPUT
        if ModelCapability.IMAGE_GENERATION in caps:
            ...
    """

    TEXT_GENERATION = auto()       # 文本生成
    IMAGE_INPUT = auto()           # 图片理解 (vision)
    IMAGE_GENERATION = auto()      # 图片生成
    AUDIO_INPUT = auto()           # 语音输入
    AUDIO_GENERATION = auto()      # 语音合成/生成
    VIDEO_GENERATION = auto()      # 视频生成
    DOCUMENT_GENERATION = auto()   # PPT/PDF 文档生成
    CODE_GENERATION = auto()       # 代码生成
    TOOL_CALLING = auto()          # Function Calling / Tool Use
    STREAMING = auto()             # SSE 流式输出
    REASONING = auto()             # 深度推理 (chain-of-thought)
    LONG_CONTEXT = auto()          # 长上下文 (≥128K tokens)
    VIDEO_INPUT = auto()           # 视频理解
    PPT_GENERATION = auto()        # PPT 课件生成
    PDF_GENERATION = auto()        # PDF 文档生成

    # ── Compound capabilities ──────────────────

    TEXT_ONLY = TEXT_GENERATION | CODE_GENERATION | STREAMING
    MULTIMODAL_INPUT = IMAGE_INPUT | AUDIO_INPUT | VIDEO_INPUT
    MULTIMODAL_OUTPUT = IMAGE_GENERATION | AUDIO_GENERATION | VIDEO_GENERATION
    FULL_MULTIMODAL = MULTIMODAL_INPUT | MULTIMODAL_OUTPUT


# ──────────────────────────────────────────────
# Human-Readable Labels
# ──────────────────────────────────────────────

CAPABILITY_LABELS: dict[ModelCapability, str] = {
    ModelCapability.TEXT_GENERATION: "文本生成",
    ModelCapability.IMAGE_INPUT: "图片理解",
    ModelCapability.IMAGE_GENERATION: "图片生成",
    ModelCapability.AUDIO_INPUT: "语音识别",
    ModelCapability.AUDIO_GENERATION: "语音合成",
    ModelCapability.VIDEO_GENERATION: "视频生成",
    ModelCapability.DOCUMENT_GENERATION: "PPT/文档生成",
    ModelCapability.CODE_GENERATION: "代码生成",
    ModelCapability.TOOL_CALLING: "工具调用",
    ModelCapability.STREAMING: "流式输出",
    ModelCapability.REASONING: "深度推理",
    ModelCapability.LONG_CONTEXT: "长上下文",
    ModelCapability.VIDEO_INPUT: "视频理解",
    ModelCapability.PPT_GENERATION: "PPT生成",
    ModelCapability.PDF_GENERATION: "PDF生成",
}

CAPABILITY_ICONS: dict[ModelCapability, str] = {
    ModelCapability.TEXT_GENERATION: "📝",
    ModelCapability.IMAGE_INPUT: "🖼️",
    ModelCapability.IMAGE_GENERATION: "🎨",
    ModelCapability.AUDIO_INPUT: "🎤",
    ModelCapability.AUDIO_GENERATION: "🔊",
    ModelCapability.VIDEO_GENERATION: "🎬",
    ModelCapability.DOCUMENT_GENERATION: "📄",
    ModelCapability.CODE_GENERATION: "💻",
    ModelCapability.TOOL_CALLING: "🔧",
    ModelCapability.STREAMING: "🌊",
    ModelCapability.REASONING: "🧠",
    ModelCapability.LONG_CONTEXT: "📚",
    ModelCapability.VIDEO_INPUT: "📹",
    ModelCapability.PPT_GENERATION: "📊",
    ModelCapability.PDF_GENERATION: "📕",
}


# ──────────────────────────────────────────────
# Provider Capability Registry
# ──────────────────────────────────────────────

# Maps provider → model → set of capabilities.
# Default (empty model or unknown model) → provider-wide minimum caps.

PROVIDER_CAPABILITIES: dict[str, dict[str, ModelCapability]] = {
    "deepseek": {
        # All DeepSeek models
        "": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
        "deepseek-chat": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
        "deepseek-v4-pro": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
        "deepseek-reasoner": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
    },
    "openai": {
        "": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING | ModelCapability.TOOL_CALLING,
        "gpt-4o": ModelCapability.TEXT_GENERATION | ModelCapability.IMAGE_INPUT | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING | ModelCapability.TOOL_CALLING,
        "gpt-4o-mini": ModelCapability.TEXT_GENERATION | ModelCapability.IMAGE_INPUT | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING | ModelCapability.TOOL_CALLING,
        "gpt-4-turbo": ModelCapability.TEXT_GENERATION | ModelCapability.IMAGE_INPUT | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING | ModelCapability.TOOL_CALLING,
        "gpt-3.5-turbo": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
    },
    "spark": {
        "": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
        "spark-pro": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
        "spark-lite": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
        "spark-max": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
        "spark-4.0-ultra": ModelCapability.TEXT_GENERATION | ModelCapability.IMAGE_INPUT | ModelCapability.CODE_GENERATION | ModelCapability.STREAMING,
    },
    "mock": {
        "": (ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION
             | ModelCapability.STREAMING | ModelCapability.IMAGE_INPUT
             | ModelCapability.DOCUMENT_GENERATION),
        "mock-model-v1": (ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION
                          | ModelCapability.STREAMING | ModelCapability.IMAGE_INPUT
                          | ModelCapability.DOCUMENT_GENERATION),
    },
    "rule": {
        "": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION,
        "rule-v1": ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION,
    },
}


# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────


def get_provider_capabilities(
    provider: str,
    model: str = "",
) -> ModelCapability:
    """
    Get the capability set for a given provider and model.

    Falls back to provider-default (model="") if specific model unknown.
    Falls back to empty set if provider unknown.

    Args:
        provider: Provider name (deepseek, openai, spark, mock, rule)
        model: Optional model name

    Returns:
        ModelCapability flag set
    """
    provider_caps = PROVIDER_CAPABILITIES.get(provider, {})
    if not provider_caps:
        return ModelCapability(0)  # No capabilities known

    # Exact model match
    if model and model in provider_caps:
        return provider_caps[model]

    # Provider default (empty model key)
    if "" in provider_caps:
        return provider_caps[""]

    return ModelCapability(0)


def require_capability(
    capability: ModelCapability,
    provider: str,
    model: str = "",
) -> tuple[bool, Optional[str]]:
    """
    Check if a provider/model supports a required capability.

    Args:
        capability: Required ModelCapability (or combination)
        provider: Provider name
        model: Optional model name

    Returns:
        (supported: bool, error_message: Optional[str])

        If supported, error_message is None.
        If not, error_message is a user-friendly message suggesting alternatives.
    """
    current_caps = get_provider_capabilities(provider, model)

    if capability in current_caps:
        return True, None

    # Build user-friendly error
    cap_name = CAPABILITY_LABELS.get(capability, str(capability))
    provider_label = _provider_label(provider)
    model_label = f" ({model})" if model else ""

    # Find providers that DO support this capability
    alternatives = _find_capable_providers(capability)
    alt_text = ""
    if alternatives:
        alt_names = [_provider_label(p) for p in alternatives[:3]]
        alt_text = f" 支持此能力的模型: {', '.join(alt_names)}"

    return False, (
        f"当前模型 {provider_label}{model_label} 不支持{cap_name}。"
        f"{alt_text}"
    )


def has_capability(
    capability: ModelCapability,
    provider: str,
    model: str = "",
) -> bool:
    """Quick boolean check for a capability."""
    return capability in get_provider_capabilities(provider, model)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _provider_label(provider: str) -> str:
    return {
        "deepseek": "DeepSeek",
        "openai": "OpenAI",
        "spark": "讯飞星火",
        "mock": "Mock",
        "rule": "Rule",
    }.get(provider, provider)


def _find_capable_providers(capability: ModelCapability) -> list[str]:
    """Find providers that support a given capability."""
    capable = []
    for prov, models in PROVIDER_CAPABILITIES.items():
        # Check provider default
        if "" in models and capability in models[""]:
            capable.append(prov)
            continue
        # Check any model
        for caps in models.values():
            if capability in caps:
                capable.append(prov)
                break
    return capable


def get_capability_summary(provider: str, model: str = "") -> dict:
    """
    Get a structured summary of capabilities for display.

    Returns:
        {
            "provider": str,
            "model": str,
            "supported": [{id, label, icon}, ...],
            "unsupported": [{id, label, icon}, ...],
            "all_caps": ModelCapability value,
        }
    """
    caps = get_provider_capabilities(provider, model)

    # All known capabilities (from labels)
    all_caps = list(CAPABILITY_LABELS.keys())

    supported = []
    unsupported = []

    for cap in all_caps:
        entry = {
            "id": cap.name,
            "label": CAPABILITY_LABELS.get(cap, cap.name),
            "icon": CAPABILITY_ICONS.get(cap, "❓"),
        }
        if cap in caps:
            supported.append(entry)
        else:
            unsupported.append(entry)

    return {
        "provider": provider,
        "model": model,
        "provider_label": _provider_label(provider),
        "supported": supported,
        "unsupported": unsupported,
        "all_caps_value": caps.value,
    }


# ──────────────────────────────────────────────
# Phase 8.3-E2-D: Task Capability Guard
# ──────────────────────────────────────────────


def check_task_capability(
    provider: str,
    model: str,
    task_type: str,
) -> tuple[bool, Optional[str]]:
    """
    Check if a provider/model combo supports the capabilities required for a task.

    Uses the task capability mapping (src/config/task_capability.py) to determine
    required capabilities, then checks against the provider's declared capabilities.

    Args:
        provider: Provider name (deepseek, openai, spark, mock, rule)
        model: Model name
        task_type: TaskType string value (e.g. "generate_material", "generate_image")

    Returns:
        (supported: bool, error_message: Optional[str])
    """
    try:
        from src.config.task_capability import TASK_REQUIREMENTS
        from src.config.model_registry import MODEL_REGISTRY

        # Look up required capabilities for this task
        required_caps = TASK_REQUIREMENTS.get(task_type, [])
        if not required_caps:
            return True, None  # No specific requirements → any model works

        # Find the model_id from registry that matches provider+model
        model_id = _find_model_id(provider, model)
        model_info = MODEL_REGISTRY.get(model_id) if model_id else None

        if model_info is None:
            # Fall back to provider-level capability check
            current_caps = get_provider_capabilities(provider, model)
        else:
            current_caps = model_info.capabilities

        # Check each required capability
        missing = []
        for cap in required_caps:
            if cap not in current_caps:
                missing.append(cap)

        if not missing:
            return True, None

        # Build user-friendly error
        provider_label = _provider_label(provider)
        model_display = model_info.display_name if model_info else f"{provider_label} ({model or 'default'})"
        missing_names = [CAPABILITY_LABELS.get(c, c.name) for c in missing]

        # Find alternative models that support this task
        alternatives = _find_models_for_task(task_type, exclude_model=model_id)

        alt_text = ""
        if alternatives:
            alt_names = [m.display_name for m in alternatives[:3]]
            alt_text = f" 支持此任务的模型: {', '.join(alt_names)}"

        return False, (
            f"当前模型 {model_display} 不支持 {', '.join(missing_names)}。"
            f"{alt_text}"
        )

    except ImportError:
        return True, None  # Module not available → assume supported


def _find_model_id(provider: str, model: str) -> Optional[str]:
    """Find model_id in MODEL_REGISTRY that matches provider+model.
    Falls back to any model from the same provider if no exact match."""
    try:
        from src.config.model_registry import MODEL_REGISTRY
        # Exact model match first
        for mid, info in MODEL_REGISTRY.items():
            if info.provider == provider:
                if not model or model in mid or mid in model:
                    return mid
        # Fallback: return any model from this provider
        for mid, info in MODEL_REGISTRY.items():
            if info.provider == provider:
                return mid
    except ImportError:
        pass
    return None


def _find_models_for_task(task_type: str, exclude_model: Optional[str] = None):
    """Find alternative models that support a given task."""
    try:
        from src.config.task_capability import TASK_REQUIREMENTS
        from src.config.model_registry import MODEL_REGISTRY
        required = TASK_REQUIREMENTS.get(task_type, [])
        if not required:
            return []
        candidates = []
        for mid, info in MODEL_REGISTRY.items():
            if mid == exclude_model:
                continue
            if all(c in info.capabilities for c in required):
                candidates.append(info)
        return candidates
    except ImportError:
        return []
