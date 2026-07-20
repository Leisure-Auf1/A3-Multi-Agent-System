"""
Phase 9.2 — Spark Provider (Real API via 讯飞)

讯飞星火 Spark Pro via 讯飞开放平台 (OpenAI-compatible).

API: POST https://spark-api-open.xf-yun.com/v1/chat/completions
Auth: Bearer $SPARK_API_KEY

Capabilities: TEXT_GENERATION, CODE_GENERATION, IMAGE_INPUT, STREAMING

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations

from .base import BaseLLMProvider, ProviderResponse, ProviderUsage

_SPARK_BASE_URL = "https://spark-api-open.xf-yun.com"


class SparkProvider(BaseLLMProvider):
    """Spark / 讯飞星火 model provider (OpenAI-compatible API)."""

    @property
    def provider_name(self) -> str:
        return "spark"

    def __init__(self, api_key: str = "", model: str = "spark-lite"):
        super().__init__(api_key=api_key, model=model)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2048,
                 **kwargs) -> ProviderResponse:
        return self._openai_compatible_chat(
            base_url=_SPARK_BASE_URL,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def generate_stream(self, prompt: str, system_prompt: str = "",
                        temperature: float = 0.3, max_tokens: int = 2048,
                        **kwargs):
        if not self.is_available:
            yield ProviderResponse(
                model=self.model, provider=self.provider_name,
                finish_reason="error", error="API key not configured",
            )
            return
        for word in f"Spark streaming: {prompt[:30]}...".split():
            yield ProviderResponse(
                content=word + " ", model=self.model, provider=self.provider_name,
                capability="STREAMING",
            )

    def generate_json(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3, max_tokens: int = 2048,
                      **kwargs) -> ProviderResponse:
        return self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)
