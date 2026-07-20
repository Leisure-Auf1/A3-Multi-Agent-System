"""
Phase 8.3-E2-A — Model Registry

Central registry of AI models with declared capabilities.
Provides structured ModelInfo for routing decisions.

Design:
- Does NOT modify Veritas-Core
- Each entry declares capabilities as ModelCapability flags
- Used by ModelRouter and check_task_capability()
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from .model_capability import ModelCapability


@dataclass
class ModelInfo:
    """Structured metadata for a registered AI model."""

    model_id: str                           # Registry key (e.g. "gpt-5.6")
    provider: str                           # Provider name (openai, anthropic, ...)
    display_name: str                       # Human-readable name (e.g. "GPT-5.6")
    capabilities: ModelCapability           # Capability flag set
    context_length: int = 8192              # Max context window in tokens
    supports_streaming: bool = True         # Whether SSE streaming is available
    priority: int = 50                      # Default priority (higher = preferred)
    tags: List[str] = field(default_factory=list)  # e.g. ["reasoning", "coding"]

    @property
    def has_capability(self, cap: ModelCapability) -> bool:
        return cap in self.capabilities

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "capabilities": self.capabilities.value,
            "context_length": self.context_length,
            "supports_streaming": self.supports_streaming,
            "priority": self.priority,
            "tags": self.tags,
        }


# ──────────────────────────────────────────────
# Model Registry
# ──────────────────────────────────────────────

MODEL_REGISTRY: Dict[str, ModelInfo] = {}

def _reg(model_id: str, provider: str, display: str, caps: ModelCapability,
         ctx: int = 8192, streaming: bool = True, priority: int = 50,
         tags: list = None) -> None:
    MODEL_REGISTRY[model_id] = ModelInfo(
        model_id=model_id,
        provider=provider,
        display_name=display,
        capabilities=caps,
        context_length=ctx,
        supports_streaming=streaming,
        priority=priority,
        tags=tags or [],
    )


M = ModelCapability  # shorthand

# ── OpenAI Models ──────────────────────────────────

_reg("gpt-5.6", "openai", "GPT-5.6",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.REASONING | M.IMAGE_INPUT |
    M.TOOL_CALLING | M.STREAMING | M.LONG_CONTEXT | M.PPT_GENERATION,
    ctx=256000, priority=95, tags=["reasoning", "coding", "multimodal"])

_reg("gpt-4o", "openai", "GPT-4o",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.IMAGE_INPUT |
    M.TOOL_CALLING | M.STREAMING | M.PPT_GENERATION,
    ctx=128000, priority=90, tags=["coding", "multimodal"])

_reg("gpt-4o-mini", "openai", "GPT-4o Mini",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.TOOL_CALLING | M.STREAMING,
    ctx=128000, priority=70, tags=["coding"])

# ── Anthropic Models ───────────────────────────────

_reg("claude-opus", "anthropic", "Claude Opus",
    M.TEXT_GENERATION | M.REASONING | M.LONG_CONTEXT | M.CODE_GENERATION |
    M.STREAMING | M.TOOL_CALLING,
    ctx=200000, priority=90, tags=["reasoning", "long_context"])

_reg("claude-sonnet", "anthropic", "Claude Sonnet",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.STREAMING | M.LONG_CONTEXT,
    ctx=200000, priority=80, tags=["coding"])

# ── Google Models ──────────────────────────────────

_reg("gemini-ultra", "google", "Gemini Ultra",
    M.TEXT_GENERATION | M.IMAGE_INPUT | M.VIDEO_INPUT | M.REASONING |
    M.STREAMING | M.LONG_CONTEXT,
    ctx=1000000, priority=88, tags=["multimodal", "reasoning"])

_reg("gemini-pro", "google", "Gemini Pro",
    M.TEXT_GENERATION | M.IMAGE_INPUT | M.STREAMING | M.LONG_CONTEXT,
    ctx=128000, priority=75, tags=["multimodal"])

# ── Qwen Models ────────────────────────────────────

_reg("qwen3.5", "qwen", "Qwen3.5",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.IMAGE_INPUT | M.REASONING |
    M.STREAMING | M.LONG_CONTEXT,
    ctx=131072, priority=85, tags=["multimodal", "coding", "reasoning"])

# ── DeepSeek Models ────────────────────────────────

_reg("deepseek-v3", "deepseek", "DeepSeek-V3",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.REASONING | M.STREAMING,
    ctx=65536, priority=82, tags=["coding", "reasoning"])

_reg("deepseek-r1", "deepseek", "DeepSeek-R1",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.REASONING | M.STREAMING,
    ctx=65536, priority=80, tags=["reasoning"])

# ── Kimi / Moonshot ────────────────────────────────

_reg("kimi-k3", "moonshot", "Kimi K3",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.LONG_CONTEXT | M.STREAMING,
    ctx=128000, priority=78, tags=["long_context", "coding"])

# ── xAI / Grok ─────────────────────────────────────

_reg("grok", "xai", "Grok",
    M.TEXT_GENERATION | M.REASONING | M.STREAMING,
    ctx=131072, priority=72, tags=["reasoning"])

# ── Phase 8.3-E3-A: Vision / Multimodal Models ─────

_reg("gpt-5.6-vision", "openai", "GPT-5.6 Vision",
    M.TEXT_GENERATION | M.IMAGE_INPUT | M.IMAGE_GENERATION |
    M.CODE_GENERATION | M.TOOL_CALLING | M.REASONING |
    M.STREAMING | M.LONG_CONTEXT | M.PPT_GENERATION | M.PDF_GENERATION,
    ctx=256000, priority=96, tags=["vision", "multimodal", "image_gen"])

_reg("sora", "openai", "Sora",
    M.VIDEO_GENERATION | M.TEXT_GENERATION | M.STREAMING,
    ctx=8192, priority=85, tags=["video_gen"])

_reg("imagen", "google", "Imagen",
    M.IMAGE_GENERATION | M.TEXT_GENERATION,
    ctx=4096, priority=84, tags=["image_gen"])

_reg("veo", "google", "Veo",
    M.VIDEO_GENERATION | M.TEXT_GENERATION,
    ctx=8192, priority=83, tags=["video_gen"])

_reg("gemini-ultra-vision", "google", "Gemini Ultra Vision",
    M.TEXT_GENERATION | M.IMAGE_INPUT | M.IMAGE_GENERATION |
    M.VIDEO_INPUT | M.VIDEO_GENERATION | M.REASONING |
    M.STREAMING | M.LONG_CONTEXT | M.PPT_GENERATION | M.PDF_GENERATION,
    ctx=1000000, priority=94, tags=["full_multimodal", "vision", "video_gen", "image_gen"])

_reg("qwen-vl", "qwen", "Qwen-VL",
    M.TEXT_GENERATION | M.IMAGE_INPUT | M.IMAGE_GENERATION |
    M.CODE_GENERATION | M.STREAMING | M.LONG_CONTEXT | M.REASONING,
    ctx=131072, priority=86, tags=["vision", "multimodal", "image_gen"])

_reg("tongyi-wanxiang", "qwen", "通义万相",
    M.IMAGE_GENERATION | M.TEXT_GENERATION,
    ctx=4096, priority=82, tags=["image_gen"])

_reg("kimi-vision", "moonshot", "Kimi Vision",
    M.TEXT_GENERATION | M.IMAGE_INPUT | M.CODE_GENERATION |
    M.LONG_CONTEXT | M.STREAMING,
    ctx=128000, priority=80, tags=["vision", "long_context"])

_reg("grok-vision", "xai", "Grok Vision",
    M.TEXT_GENERATION | M.IMAGE_INPUT | M.REASONING | M.STREAMING,
    ctx=131072, priority=74, tags=["vision", "reasoning"])

# ── Legacy / Compat ────────────────────────────────

_reg("mock-model-v1", "mock", "Mock (演示)",
    M.TEXT_GENERATION | M.CODE_GENERATION | M.IMAGE_INPUT |
    M.TOOL_CALLING | M.STREAMING | M.DOCUMENT_GENERATION | M.PPT_GENERATION,
    ctx=8192, priority=10, tags=["demo"])

_reg("rule-v1", "rule", "Rule (纯规则)",
    M.TEXT_GENERATION | M.CODE_GENERATION,
    ctx=0, streaming=False, priority=5, tags=["rule"])


# ──────────────────────────────────────────────
# Registry Queries
# ──────────────────────────────────────────────


def get_model(model_id: str) -> ModelInfo | None:
    """Get a model by its registry ID."""
    return MODEL_REGISTRY.get(model_id)


def list_models(provider: str = "") -> list[ModelInfo]:
    """List all models, optionally filtered by provider."""
    if provider:
        return [m for m in MODEL_REGISTRY.values() if m.provider == provider]
    return list(MODEL_REGISTRY.values())


def find_models_with_capability(capability: ModelCapability) -> list[ModelInfo]:
    """Find all models that support a specific capability."""
    return [m for m in MODEL_REGISTRY.values() if capability in m.capabilities]
