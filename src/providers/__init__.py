"""
Phase 9.2 — Provider Layer Package

Real API integrations for 8 providers:
    OpenAI, Anthropic (Claude), Google (Gemini), Qwen (DashScope),
    DeepSeek, Kimi (Moonshot), Grok (xAI), Spark (讯飞星火)

Architecture: does NOT modify Veritas-Core or src/core/
"""

from .base import BaseLLMProvider, ProviderResponse, ProviderUsage
from .factory import ProviderFactory
from .health import check_provider, check_all_providers

__all__ = [
    "BaseLLMProvider", "ProviderResponse", "ProviderUsage",
    "ProviderFactory",
    "check_provider", "check_all_providers",
]
