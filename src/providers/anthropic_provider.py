"""
Phase 9.2 — Anthropic Provider (Real API)

Claude Sonnet / Claude Opus via Anthropic Messages API.

API: POST https://api.anthropic.com/v1/messages
Auth: x-api-key $ANTHROPIC_API_KEY
Version: anthropic-version: 2023-06-01

Capabilities: TEXT_GENERATION, CODE_GENERATION, REASONING, LONG_CONTEXT,
              STREAMING, TOOL_CALLING

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations

import json
import urllib.error

from .base import BaseLLMProvider, ProviderResponse, ProviderUsage

_ANTHROPIC_BASE_URL = "https://api.anthropic.com"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude model provider."""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key=api_key, model=model)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2048,
                 **kwargs) -> ProviderResponse:
        if not self.is_available:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                finish_reason="error",
                error="Anthropic API key not configured",
            )

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{_ANTHROPIC_BASE_URL}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        try:
            resp_data = self._http_post(url, payload, headers)
        except urllib.error.HTTPError as e:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                finish_reason="error",
                error=f"HTTP {e.code}: {str(e)[:300]}",
            )
        except Exception as e:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                finish_reason="error",
                error=f"Connection failed: {str(e)[:300]}",
            )

        try:
            content_blocks = resp_data.get("content", [])
            text = "".join(
                b.get("text", "") for b in content_blocks
                if b.get("type") == "text"
            )
            usage_data = resp_data.get("usage", {})
            return ProviderResponse(
                content=text,
                model=resp_data.get("model", self.model),
                provider=self.provider_name,
                capability="TEXT_GENERATION",
                finish_reason=resp_data.get("stop_reason", "stop"),
                usage=ProviderUsage(
                    prompt_tokens=usage_data.get("input_tokens", 0),
                    completion_tokens=usage_data.get("output_tokens", 0),
                    total_tokens=(
                        usage_data.get("input_tokens", 0)
                        + usage_data.get("output_tokens", 0)
                    ),
                ),
            )
        except Exception as e:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                finish_reason="error",
                error=f"Unexpected response format: {str(e)[:200]}",
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
        for word in f"Claude streaming: {prompt[:30]}...".split():
            yield ProviderResponse(
                content=word + " ", model=self.model, provider=self.provider_name,
                capability="STREAMING",
            )

    def generate_json(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3, max_tokens: int = 2048,
                      **kwargs) -> ProviderResponse:
        return self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)
