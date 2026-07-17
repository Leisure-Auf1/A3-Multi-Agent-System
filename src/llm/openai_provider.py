"""
Phase 4.7 — OpenAI Provider

OpenAI-compatible provider for OpenAI API (gpt-4o, gpt-4o-mini, etc.).

Configuration:
    export OPENAI_API_KEY="sk-..."
    export OPENAI_BASE_URL="https://api.openai.com/v1"   # optional
    export OPENAI_MODEL="gpt-4o-mini"                     # optional

Also works with any OpenAI-compatible proxy (LiteLLM, local vLLM, etc.)
by setting OPENAI_BASE_URL to the proxy endpoint.
"""

from __future__ import annotations
import json, os, ssl, time, urllib.request, urllib.error
from typing import Any, Dict, Optional

from src.llm.provider import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider (and OpenAI-compatible proxies).

    Usage:
        provider = OpenAIProvider()
        response = provider.generate("Hello")
        print(response.content)

    For proxies:
        export OPENAI_BASE_URL="http://localhost:8000/v1"
        export OPENAI_MODEL="local-model"
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "",
    ):
        _key = api_key or os.getenv("OPENAI_API_KEY", "")
        super().__init__(
            api_key=_key,
            base_url=base_url or os.getenv("OPENAI_BASE_URL", self.DEFAULT_BASE_URL),
            model=model or os.getenv("OPENAI_MODEL", self.DEFAULT_MODEL),
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                error="OPENAI_API_KEY not configured",
                finish_reason="error",
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload.update(kwargs)

        return self._call_api(payload)

    def _call_api(self, payload: Dict[str, Any]) -> LLMResponse:
        t0 = time.time()
        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        req = urllib.request.Request(
            url, data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                return self._parse_response(raw, time.time() - t0)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            return LLMResponse(
                error=f"OpenAI HTTP {e.code}: {err_body[:400]}",
                finish_reason="error",
                latency_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return LLMResponse(
                error=f"OpenAI error: {e}",
                finish_reason="error",
                latency_ms=(time.time() - t0) * 1000,
            )

    def _parse_response(self, raw: Dict[str, Any], elapsed_s: float) -> LLMResponse:
        if "error" in raw:
            return LLMResponse(
                error=raw["error"].get("message", str(raw["error"])),
                finish_reason="error",
                raw_response=raw,
                latency_ms=elapsed_s * 1000,
            )

        choices = raw.get("choices", [])
        if not choices:
            return LLMResponse(
                error="No choices in response",
                finish_reason="error",
                raw_response=raw,
                latency_ms=elapsed_s * 1000,
            )

        choice = choices[0]
        message = choice.get("message", {})
        usage = raw.get("usage", {})

        return LLMResponse(
            content=message.get("content", ""),
            model=raw.get("model", self.model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=raw,
            latency_ms=elapsed_s * 1000,
        )
