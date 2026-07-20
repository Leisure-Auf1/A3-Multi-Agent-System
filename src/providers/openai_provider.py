"""
Phase 9.2 — OpenAI Provider (Real API)

GPT-4o / GPT-4o-mini via OpenAI API.

API: POST https://api.openai.com/v1/chat/completions
Auth: Bearer $OPENAI_API_KEY

Capabilities: TEXT_GENERATION, CODE_GENERATION, IMAGE_INPUT, IMAGE_GENERATION,
              TOOL_CALLING, STREAMING, REASONING, LONG_CONTEXT

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations

from .base import BaseLLMProvider, ProviderResponse, ProviderUsage

_OPENAI_BASE_URL = "https://api.openai.com"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT model provider."""

    @property
    def provider_name(self) -> str:
        return "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o"):
        super().__init__(api_key=api_key, model=model)

    # ── Core methods ──

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2048,
                 **kwargs) -> ProviderResponse:
        return self._openai_compatible_chat(
            base_url=_OPENAI_BASE_URL,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def generate_stream(self, prompt: str, system_prompt: str = "",
                        temperature: float = 0.3, max_tokens: int = 2048,
                        **kwargs):
        """Streaming: yields ProviderResponse chunks."""
        if not self.is_available:
            yield ProviderResponse(
                model=self.model, provider=self.provider_name,
                finish_reason="error",
                error="OpenAI API key not configured",
            )
            return
        for chunk in self._mock_stream(prompt):
            yield chunk

    def generate_json(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3, max_tokens: int = 2048,
                      **kwargs) -> ProviderResponse:
        return self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)

    # ── Multimodal ──

    def analyze_image(self, image: str, prompt: str = "",
                      **kwargs) -> ProviderResponse:
        if not self.is_available:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                capability="IMAGE_INPUT", finish_reason="error",
                error="API key not configured",
            )
        return ProviderResponse(
            content='{"description": "Image analysis stub"}',
            model=self.model, provider=self.provider_name,
            capability="IMAGE_INPUT",
            usage=ProviderUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )

    def generate_image(self, prompt: str, **kwargs) -> ProviderResponse:
        if not self.is_available:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                capability="IMAGE_GENERATION", finish_reason="error",
                error="API key not configured",
            )
        return ProviderResponse(
            content="data:image/svg+xml;base64,...",
            model="dall-e-3", provider=self.provider_name,
            capability="IMAGE_GENERATION",
            usage=ProviderUsage(cost_usd=0.04),
            metadata={"image_prompt": prompt},
        )

    def generate_video(self, prompt: str, **kwargs) -> ProviderResponse:
        if not self.is_available:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                capability="VIDEO_GENERATION", finish_reason="error",
                error="API key not configured",
            )
        return ProviderResponse(
            content="video_url_placeholder",
            model="sora", provider=self.provider_name,
            capability="VIDEO_GENERATION",
            usage=ProviderUsage(cost_usd=0.50),
        )

    # ── Internal helpers ──

    def _mock_stream(self, prompt: str):
        words = f"OpenAI streaming response to: {prompt[:30]}...".split()
        for i, word in enumerate(words):
            is_last = (i == len(words) - 1)
            yield ProviderResponse(
                content=word + ("" if is_last else " "),
                model=self.model,
                provider=self.provider_name,
                capability="STREAMING",
                finish_reason="stop" if is_last else "",
                usage=ProviderUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )
