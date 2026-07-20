"""
Phase 9.0 — Provider Factory

Unified factory for creating LLM providers by name.

Usage:
    factory = ProviderFactory()
    provider = factory.create("openai", api_key="sk-...", model="gpt-4o")
    resp = provider.generate("Hello")

Supported providers: openai, claude/anthropic, gemini/google, qwen,
                     deepseek, kimi/moonshot, grok/xai, spark

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Type

from .base import BaseLLMProvider


# ── Provider registry ──────────────────────────

_PROVIDER_REGISTRY: Dict[str, str] = {
    "openai": "OpenAIProvider",
    "anthropic": "AnthropicProvider",
    "claude": "AnthropicProvider",       # alias
    "google": "GoogleProvider",
    "gemini": "GoogleProvider",           # alias
    "qwen": "QwenProvider",
    "deepseek": "DeepSeekProvider",
    "kimi": "KimiProvider",
    "moonshot": "KimiProvider",          # alias
    "grok": "GrokProvider",
    "xai": "GrokProvider",                # alias
    "spark": "SparkProvider",
}

# Provider human-readable names
PROVIDER_LABELS: Dict[str, str] = {
    "openai": "GPT (OpenAI)",
    "anthropic": "Claude (Anthropic)",
    "google": "Gemini (Google)",
    "qwen": "通义千问 (Qwen)",
    "deepseek": "DeepSeek",
    "kimi": "Kimi (Moonshot)",
    "grok": "Grok (xAI)",
    "spark": "讯飞星火 (Spark)",
}

# Default models per provider
PROVIDER_DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet",
    "google": "gemini-pro",
    "qwen": "qwen3.5",
    "deepseek": "deepseek-v3",
    "kimi": "kimi-k3",
    "grok": "grok",
    "spark": "spark-pro",
}


class ProviderFactory:
    """
    Factory for creating LLM providers.

    Supports lazy-loading to avoid importing all providers at once.

    Usage:
        provider = ProviderFactory.create("openai", api_key="sk-...")
        provider = ProviderFactory.create("deepseek", api_key="sk-...", model="deepseek-v3")
    """

    @staticmethod
    def create(
        provider_name: str,
        api_key: str = "",
        model: str = "",
    ) -> BaseLLMProvider:
        """
        Create a provider instance by name.

        Args:
            provider_name: Provider name (openai/claude/gemini/qwen/deepseek/kimi/grok/spark)
            api_key: API key for the provider
            model: Optional model override (uses default if empty)

        Returns:
            BaseLLMProvider instance

        Raises:
            ValueError: Unknown provider name
        """
        name = provider_name.lower().strip()

        if name not in _PROVIDER_REGISTRY:
            available = ", ".join(sorted(set(_PROVIDER_REGISTRY.values())))
            raise ValueError(
                f"Unknown provider: '{provider_name}'. "
                f"Available: openai, claude, gemini, qwen, deepseek, kimi, grok, spark"
            )

        model = model or PROVIDER_DEFAULT_MODELS.get(name, "")

        # Lazy-load provider class
        class_name = _PROVIDER_REGISTRY[name]

        if "OpenAI" in class_name:
            from .openai_provider import OpenAIProvider
            return OpenAIProvider(api_key=api_key, model=model)
        elif "Anthropic" in class_name:
            from .anthropic_provider import AnthropicProvider
            return AnthropicProvider(api_key=api_key, model=model)
        elif "Google" in class_name:
            from .google_provider import GoogleProvider
            return GoogleProvider(api_key=api_key, model=model)
        elif "Qwen" in class_name:
            from .qwen_provider import QwenProvider
            return QwenProvider(api_key=api_key, model=model)
        elif "DeepSeek" in class_name:
            from .deepseek_provider import DeepSeekProvider
            return DeepSeekProvider(api_key=api_key, model=model)
        elif "Kimi" in class_name:
            from .kimi_provider import KimiProvider
            return KimiProvider(api_key=api_key, model=model)
        elif "Grok" in class_name:
            from .grok_provider import GrokProvider
            return GrokProvider(api_key=api_key, model=model)
        elif "Spark" in class_name:
            from .spark_provider import SparkProvider
            return SparkProvider(api_key=api_key, model=model)

        raise ValueError(f"No implementation for provider class: {class_name}")

    @staticmethod
    def list_providers() -> Dict[str, str]:
        """List all supported providers with human-readable labels."""
        return {k: PROVIDER_LABELS.get(k, k) for k in PROVIDER_DEFAULT_MODELS}

    @staticmethod
    def get_default_model(provider_name: str) -> str:
        """Get the default model for a provider."""
        return PROVIDER_DEFAULT_MODELS.get(provider_name.lower(), "")

    @staticmethod
    def list_capable_providers(capability: str) -> list:
        """
        List providers that support a specific capability.

        Uses the existing ModelRegistry for capability lookup.
        """
        try:
            from src.config.model_capability import ModelCapability
            from src.config.model_registry import find_models_with_capability

            # Map capability string to ModelCapability
            cap_map = {c.name: c for c in ModelCapability}
            cap = cap_map.get(capability)
            if cap is None:
                return []

            models = find_models_with_capability(cap)
            providers = sorted(set(m.provider for m in models))
            return providers
        except ImportError:
            return []

    @staticmethod
    def create_from_env(
        provider_name: str = "",
        model: str = "",
    ) -> BaseLLMProvider:
        """
        Create a provider using environment variables for API keys.

        Reads API key from the appropriate env var:
            OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY,
            DASHSCOPE_API_KEY, DEEPSEEK_API_KEY, MOONSHOT_API_KEY,
            XAI_API_KEY, SPARK_API_KEY

        If provider_name is empty, tries DEEPSEEK_API_KEY first,
        then OPENAI_API_KEY, then falls back to mock.

        Args:
            provider_name: Provider to create. Empty = auto-detect.
            model: Optional model override.

        Returns:
            BaseLLMProvider instance (never None — falls back to mock).
        """
        from src.config.secrets import get_api_key

        # Auto-detect: try DeepSeek first, then OpenAI
        if not provider_name:
            for candidate in ["deepseek", "openai"]:
                key = get_api_key(candidate)
                if key:
                    provider_name = candidate
                    break

            if not provider_name:
                # No API key found — fall back to mock
                from src.core.provider_factory import create_provider
                return create_provider("mock")

        api_key = get_api_key(provider_name)
        if not api_key:
            # Key not in env — fall back to mock
            from src.core.provider_factory import create_provider
            return create_provider("mock")

        return ProviderFactory.create(provider_name, api_key=api_key, model=model)

    @staticmethod
    def create_all_from_env() -> Dict[str, BaseLLMProvider]:
        """
        Create all providers that have API keys configured in env.

        Returns:
            Dict mapping provider_name → BaseLLMProvider for configured providers only.
        """
        from src.config.secrets import get_api_key

        providers = {}
        for name in PROVIDER_DEFAULT_MODELS:
            key = get_api_key(name)
            if key:
                providers[name] = ProviderFactory.create(name, api_key=key)
        return providers
