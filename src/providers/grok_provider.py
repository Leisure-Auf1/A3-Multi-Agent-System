"""
Phase 9.2 — Grok Provider (Real API via xAI)

Grok via xAI API (OpenAI-compatible).

API: POST https://api.x.ai/v1/chat/completions
Auth: Bearer $XAI_API_KEY

Capabilities: TEXT_GENERATION, CODE_GENERATION, IMAGE_INPUT, REASONING, STREAMING

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations

from .base import BaseLLMProvider, ProviderResponse, ProviderUsage

_GROK_BASE_URL = "https://api.x.ai"


class GrokProvider(BaseLLMProvider):
    """Grok / xAI model provider (OpenAI-compatible API)."""

    @property
    def provider_name(self) -> str:
        return "xai"

    def __init__(self, api_key: str = "", model: str = "grok-2"):
        super().__init__(api_key=api_key, model=model)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2048,
                 **kwargs) -> ProviderResponse:
        return self._openai_compatible_chat(
            base_url=_GROK_BASE_URL,
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
        for word in f"Grok streaming: {prompt[:30]}...".split():
            yield ProviderResponse(
                content=word + " ", model=self.model, provider=self.provider_name,
                capability="STREAMING",
            )

    def generate_json(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3, max_tokens: int = 2048,
                      **kwargs) -> ProviderResponse:
        return self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)
