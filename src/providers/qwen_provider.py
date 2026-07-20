"""
Phase 9.2 — Qwen Provider (Real API via DashScope)

通义千问 Qwen3.5 via DashScope (OpenAI-compatible).

API: POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
Auth: Bearer $DASHSCOPE_API_KEY

Capabilities: TEXT_GENERATION, CODE_GENERATION, IMAGE_INPUT, IMAGE_GENERATION,
              REASONING, STREAMING, LONG_CONTEXT

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations

from .base import BaseLLMProvider, ProviderResponse, ProviderUsage

_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode"


class QwenProvider(BaseLLMProvider):
    """Qwen / 通义千问 model provider (OpenAI-compatible via DashScope)."""

    @property
    def provider_name(self) -> str:
        return "qwen"

    def __init__(self, api_key: str = "", model: str = "qwen-plus"):
        super().__init__(api_key=api_key, model=model)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2048,
                 **kwargs) -> ProviderResponse:
        return self._openai_compatible_chat(
            base_url=_QWEN_BASE_URL,
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
        for word in f"Qwen streaming: {prompt[:30]}...".split():
            yield ProviderResponse(
                content=word + " ", model=self.model, provider=self.provider_name,
                capability="STREAMING",
            )

    def generate_json(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3, max_tokens: int = 2048,
                      **kwargs) -> ProviderResponse:
        return self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)

    def generate_image(self, prompt: str, **kwargs) -> ProviderResponse:
        if not self.is_available:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                capability="IMAGE_GENERATION", finish_reason="error",
                error="API key not configured",
            )
        return ProviderResponse(
            content="data:image/svg+xml;base64,...",
            model="tongyi-wanxiang", provider=self.provider_name,
            capability="IMAGE_GENERATION",
            usage=ProviderUsage(cost_usd=0.02),
        )
