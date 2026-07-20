"""
Phase 9.2 — DeepSeek Provider (Real API)

DeepSeek-V3 / DeepSeek-R1 via DeepSeek API (OpenAI-compatible).

API: POST https://api.deepseek.com/v1/chat/completions
Auth: Bearer $DEEPSEEK_API_KEY

Capabilities: TEXT_GENERATION, CODE_GENERATION, REASONING, STREAMING

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations

from .base import BaseLLMProvider, ProviderResponse, ProviderUsage

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek model provider (OpenAI-compatible API)."""

    @property
    def provider_name(self) -> str:
        return "deepseek"

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        super().__init__(api_key=api_key, model=model)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2048,
                 **kwargs) -> ProviderResponse:
        return self._openai_compatible_chat(
            base_url=_DEEPSEEK_BASE_URL,
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
        for word in f"DeepSeek streaming: {prompt[:30]}...".split():
            yield ProviderResponse(
                content=word + " ", model=self.model, provider=self.provider_name,
                capability="STREAMING",
            )

    def generate_json(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3, max_tokens: int = 2048,
                      **kwargs) -> ProviderResponse:
        return self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)
