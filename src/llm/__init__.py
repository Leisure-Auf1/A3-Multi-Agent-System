"""
Phase 4.7 — LLM Provider Abstraction Layer

Unified LLM interface. All LLM calls flow through LLMProvider.
Supports: OpenAI, DeepSeek, Spark, Mock, Rule + FallbackChain.

Usage:
    from src.llm import create_provider
    provider = create_provider("deepseek", fallback_chain=True)
    response = provider.generate("Hello")
"""

from src.llm.provider import LLMProvider, LLMResponse
from src.llm.mock_provider import MockLLMProvider
from src.llm.xunfei_provider import XunfeiSparkProvider
from src.llm.openai_provider import OpenAIProvider
from src.llm.deepseek_provider import DeepSeekProvider
from src.llm.rule_provider import RuleProvider
from src.llm.factory import create_provider, FallbackChain, get_provider_info

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "MockLLMProvider",
    "XunfeiSparkProvider",
    "OpenAIProvider",
    "DeepSeekProvider",
    "RuleProvider",
    "FallbackChain",
    "create_provider",
    "get_provider_info",
]
