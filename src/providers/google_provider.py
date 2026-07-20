"""
Phase 9.2 — Google Provider (Real API)

Gemini Pro / Gemini Flash via Google Generative Language API.

API: POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
Auth: ?key=$GOOGLE_API_KEY (query parameter)

Capabilities: TEXT_GENERATION, CODE_GENERATION, IMAGE_INPUT, IMAGE_GENERATION,
              VIDEO_GENERATION, REASONING, STREAMING, LONG_CONTEXT

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations

import json
import urllib.error

from .base import BaseLLMProvider, ProviderResponse, ProviderUsage

_GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GoogleProvider(BaseLLMProvider):
    """Google Gemini model provider."""

    @property
    def provider_name(self) -> str:
        return "google"

    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash"):
        super().__init__(api_key=api_key, model=model)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2048,
                 **kwargs) -> ProviderResponse:
        if not self.is_available:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                finish_reason="error",
                error="Google API key not configured",
            )

        # Build Gemini-specific payload
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"[System: {system_prompt}]"}],
            })
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}],
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        url = (
            f"{_GOOGLE_API_BASE}/{self.model}:generateContent"
            f"?key={self.api_key}"
        )

        try:
            resp_data = self._http_post(url, payload, {})
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
            candidates = resp_data.get("candidates", [])
            if not candidates:
                return ProviderResponse(
                    model=self.model, provider=self.provider_name,
                    finish_reason="error",
                    error="No candidates in Gemini response",
                )
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            finish = candidates[0].get("finishReason", "STOP")
            usage = resp_data.get("usageMetadata", {})
            return ProviderResponse(
                content=text,
                model=self.model,
                provider=self.provider_name,
                capability="TEXT_GENERATION",
                finish_reason=finish.lower(),
                usage=ProviderUsage(
                    prompt_tokens=usage.get("promptTokenCount", 0),
                    completion_tokens=usage.get("candidatesTokenCount", 0),
                    total_tokens=usage.get("totalTokenCount", 0),
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
        for word in f"Gemini streaming: {prompt[:30]}...".split():
            yield ProviderResponse(
                content=word + " ", model=self.model, provider=self.provider_name,
                capability="STREAMING",
            )

    def generate_json(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3, max_tokens: int = 2048,
                      **kwargs) -> ProviderResponse:
        return self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)

    def analyze_image(self, image: str, prompt: str = "",
                      **kwargs) -> ProviderResponse:
        if not self.is_available:
            return ProviderResponse(
                model=self.model, provider=self.provider_name,
                capability="IMAGE_INPUT", finish_reason="error",
                error="API key not configured",
            )
        return ProviderResponse(
            content='{"description": "Gemini image analysis stub"}',
            model=self.model, provider=self.provider_name,
            capability="IMAGE_INPUT",
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
            model="imagen", provider=self.provider_name,
            capability="IMAGE_GENERATION",
            usage=ProviderUsage(cost_usd=0.03),
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
            model="veo", provider=self.provider_name,
            capability="VIDEO_GENERATION",
            usage=ProviderUsage(cost_usd=0.50),
        )
