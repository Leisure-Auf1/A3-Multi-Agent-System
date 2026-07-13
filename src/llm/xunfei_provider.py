"""
Phase 11 — Xunfei Spark Provider

Encapsulates Xunfei (讯飞) Spark Model API access.
Implements the LLMProvider interface for Spark compatibility.

Supports:
- Spark Lite / Pro / Max models
- Chat completions endpoint (OpenAI-compatible)
- System prompt injection
- Token usage tracking
- Error handling with graceful degradation

Configuration:
    export XF_API_KEY="your-api-key"           # Required (or XF_SPARK_API_KEY)
    export XF_APP_ID="your-app-id"             # Optional (Spark 3.x compat)
    export XF_API_SECRET="your-api-secret"     # Optional (Spark 3.x compat)
    export XF_SPARK_BASE_URL="https://spark-api.xf-yun.com/v1"  # Optional
    export LLM_MODEL="spark-pro"               # Optional (spark-lite|spark-pro|spark-max|spark-4.0-ultra)
"""

from __future__ import annotations
import json
import os
import ssl
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from src.llm.provider import LLMProvider, LLMResponse


# ──────────────────────────────────────────────
# Spark Model Catalog
# ──────────────────────────────────────────────

SPARK_MODELS = {
    "spark-lite": {
        "name": "Spark Lite",
        "max_tokens": 4096,
        "description": "Fast, lightweight model for simple tasks",
    },
    "spark-pro": {
        "name": "Spark Pro",
        "max_tokens": 8192,
        "description": "Balanced performance for most use cases",
    },
    "spark-max": {
        "name": "Spark Max",
        "max_tokens": 32768,
        "description": "Maximum capability for complex reasoning",
    },
    "spark-4.0-ultra": {
        "name": "Spark 4.0 Ultra",
        "max_tokens": 32768,
        "description": "Latest generation, best quality",
    },
}


class XunfeiSparkProvider(LLMProvider):
    """
    Xunfei Spark Model API provider.

    Uses OpenAI-compatible chat completions endpoint.

    Usage:
        provider = XunfeiSparkProvider(
            api_key=os.getenv("XF_SPARK_API_KEY"),
            model="spark-pro",
        )
        response = provider.generate("Explain AI in Chinese.")
        print(response.content)
    """

    DEFAULT_BASE_URL = "https://spark-api.xf-yun.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        app_id: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "spark-pro",
    ):
        # API key: XF_API_KEY > XF_SPARK_API_KEY > explicit
        _key = api_key or os.getenv("XF_API_KEY") or os.getenv("XUNFEI_API_KEY") or os.getenv("XF_SPARK_API_KEY", "")
        super().__init__(
            api_key=_key,
            base_url=base_url or os.getenv("XF_SPARK_BASE_URL", self.DEFAULT_BASE_URL),
            model=model or os.getenv("LLM_MODEL", "spark-pro"),
        )
        self.app_id = app_id or os.getenv("XF_APP_ID", "")
        self.api_secret = api_secret or os.getenv("XF_API_SECRET", "")
        self._model_config = SPARK_MODELS.get(self.model, SPARK_MODELS["spark-pro"])

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Call Xunfei Spark API to generate a response."""
        if not self.api_key:
            return LLMResponse(
                content="",
                model=self.model,
                error="XF_SPARK_API_KEY not configured. Set environment variable or pass api_key.",
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
            "max_tokens": min(max_tokens, self._model_config["max_tokens"]),
        }
        # Merge provider-specific kwargs
        payload.update(kwargs)

        return self._call_api(payload)

    def _call_api(self, payload: Dict[str, Any]) -> LLMResponse:
        """Execute the HTTP request to Spark API."""
        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                return self._parse_response(raw)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            return LLMResponse(
                content="",
                model=self.model,
                error=f"Spark API HTTP {e.code}: {error_body[:500]}",
                finish_reason="error",
            )
        except Exception as e:
            return LLMResponse(
                content="",
                model=self.model,
                error=f"Spark API error: {e}",
                finish_reason="error",
            )

    def _parse_response(self, raw: Dict[str, Any]) -> LLMResponse:
        """Parse Spark API response into standardized LLMResponse."""
        if "error" in raw:
            return LLMResponse(
                content="",
                model=self.model,
                error=raw["error"].get("message", str(raw["error"])),
                finish_reason="error",
                raw_response=raw,
            )

        choices = raw.get("choices", [])
        if not choices:
            return LLMResponse(
                content="",
                model=self.model,
                error="No choices in response",
                finish_reason="error",
                raw_response=raw,
            )

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        usage = raw.get("usage", {})
        return LLMResponse(
            content=content,
            model=raw.get("model", self.model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=raw,
        )

    @classmethod
    def list_models(cls) -> Dict[str, Dict[str, Any]]:
        """Return the catalog of available Spark models."""
        return SPARK_MODELS

    @property
    def max_context_tokens(self) -> int:
        return self._model_config["max_tokens"]

    def __repr__(self) -> str:
        status = "configured" if self.api_key else "unconfigured"
        return f"XunfeiSparkProvider(model={self.model!r}, status={status})"


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════╗")
    print("║  Xunfei Spark Provider — Demo   ║")
    print("╚══════════════════════════════════╝")
    print()

    # Show model catalog
    print("Available Spark Models:")
    for model_id, info in SPARK_MODELS.items():
        print(f"  {model_id:20s} — {info['name']:20s} ({info['description']})")
    print()

    provider = XunfeiSparkProvider(model="spark-pro")
    print(f"Provider: {provider}")
    print(f"Max context: {provider.max_context_tokens} tokens")
    print()

    if provider.is_available:
        print("Testing generate()...")
        response = provider.generate(
            prompt="Explain what AI is in one sentence.",
            system_prompt="You are a helpful AI assistant. Be concise.",
            temperature=0.5,
            max_tokens=100,
        )
        if response.success:
            print(f"Response: {response.content}")
            print(f"Tokens: {response.usage}")
        else:
            print(f"Error: {response.error}")
    else:
        print("⚠️  XF_SPARK_API_KEY not set. Skipping API call.")
        print("   Set environment variable to test: export XF_SPARK_API_KEY='your-key'")
