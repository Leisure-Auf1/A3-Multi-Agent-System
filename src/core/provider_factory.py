"""
Phase 4.7 — Provider Factory (backward-compatible re-export)

Phase 4.0 adds user LLM configuration layer:
  Priority: user config (llm.json) > env var > mock > rule

DEPRECATED: Import directly from veritas.llm instead.
This module exists for backward compatibility only.

Usage (preferred):
    from veritas.llm import create_provider, get_provider_info

Usage (backward compat):
    from src.core.provider_factory import create_provider
"""

from __future__ import annotations
import os
from typing import List, Optional

# Re-export from new canonical location
from veritas.llm.factory import create_provider as _veritas_create_provider
from veritas.llm.factory import get_provider_info
from veritas.llm.provider import LLMProvider

# Phase 4.0 — User LLM configuration
from src.config.llm_config import load_llm_config, LLMConfig


def _build_from_config(cfg: LLMConfig) -> Optional[LLMProvider]:
    """Build a provider directly from user configuration."""
    provider_name = cfg.provider

    if provider_name == "deepseek":
        from veritas.llm.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider(api_key=cfg.api_key, model=cfg.model or "deepseek-chat")

    if provider_name == "openai":
        from veritas.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=cfg.api_key, model=cfg.model or "gpt-4o-mini")

    if provider_name == "spark":
        from veritas.llm.xunfei_provider import XunfeiSparkProvider
        return XunfeiSparkProvider(api_key=cfg.api_key, model=cfg.model or "spark-pro")

    if provider_name == "anthropic":
        from src.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=cfg.api_key, model=cfg.model or "claude-sonnet")

    if provider_name == "google":
        from src.providers.google_provider import GoogleProvider
        return GoogleProvider(api_key=cfg.api_key, model=cfg.model or "gemini-pro")

    if provider_name == "qwen":
        from src.providers.qwen_provider import QwenProvider
        return QwenProvider(api_key=cfg.api_key, model=cfg.model or "qwen3.5")

    if provider_name == "kimi":
        from src.providers.kimi_provider import KimiProvider
        return KimiProvider(api_key=cfg.api_key, model=cfg.model or "kimi-k3")

    if provider_name == "grok":
        from src.providers.grok_provider import GrokProvider
        return GrokProvider(api_key=cfg.api_key, model=cfg.model or "grok")

    # mock / rule / unrecognized → delegate to Veritas factory
    return None


def create_provider(
    mode: str = "",
    fallback_chain: bool = False,
    fallback_providers: Optional[List[str]] = None,
) -> Optional[LLMProvider]:
    """
    Create an LLM provider with user config layer.

    Priority:
      1. Explicit `mode` parameter (e.g., "deepseek", "mock")
      2. User config from llm.json (if configured)
      3. LLM_PROVIDER environment variable
      4. "mock" (always available fallback)

    If user has saved a config with an API key, it takes precedence
    over environment variables unless an explicit mode is passed.

    Returns None for pure rule mode ("none" / "rule_only").
    """
    # If explicit mode is provided, delegate entirely to Veritas factory
    if mode:
        return _veritas_create_provider(
            mode=mode,
            fallback_chain=fallback_chain,
            fallback_providers=fallback_providers,
        )

    # No explicit mode — check user config
    cfg = load_llm_config()
    if cfg.is_configured:
        provider = _build_from_config(cfg)
        if provider is not None and provider.is_available:
            return provider
        # User config exists but provider build failed → fall through

    # No user config or build failed → delegate to Veritas factory
    return _veritas_create_provider(
        mode=mode,
        fallback_chain=fallback_chain,
        fallback_providers=fallback_providers,
    )


__all__ = ["create_provider", "get_provider_info", "LLMProvider"]
