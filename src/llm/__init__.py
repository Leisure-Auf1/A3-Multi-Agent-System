"""
Phase 11 — LLM Provider Abstraction Layer

Provides a clean interface for LLM backends.
Supports: real providers (Xunfei Spark, configurable backends), mock provider for testing.
Does NOT break existing AgentRouter rule mode — the router delegates to providers.
"""

from src.llm.provider import LLMProvider
from src.llm.mock_provider import MockLLMProvider
from src.llm.xunfei_provider import XunfeiSparkProvider

__all__ = [
    "LLMProvider",
    "MockLLMProvider",
    "XunfeiSparkProvider",
]
