"""
Phase 9.0 — Base Provider

Unified LLM provider interface for the A3 AI Teacher Platform.

All providers (OpenAI, Claude, Gemini, Qwen, DeepSeek, Kimi, Grok, Spark)
must implement this base interface.

Architecture:
  Agent → ModelRouter → ProviderFactory → ConcreteProvider → API

Constraints: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import logging
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Unified Response
# ──────────────────────────────────────────────

@dataclass
class ProviderUsage:
    """Token usage tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
        }


@dataclass
class ProviderResponse:
    """
    Unified response from any provider.

    All providers must return this format regardless of backend.
    """
    content: str = ""                         # Response text / JSON string / base64
    model: str = ""                           # Model name (e.g. "gpt-4o")
    provider: str = ""                        # Provider name (e.g. "openai")
    usage: ProviderUsage = field(default_factory=ProviderUsage)
    capability: str = "TEXT_GENERATION"       # Primary capability used
    finish_reason: str = "stop"               # stop | length | error
    error: str = ""                           # Error message if any
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return not bool(self.error) and self.finish_reason != "error"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage.to_dict(),
            "capability": self.capability,
            "finish_reason": self.finish_reason,
            "error": self.error,
            "success": self.success,
            "metadata": self.metadata,
        }


# ──────────────────────────────────────────────
# Base Provider Interface
# ──────────────────────────────────────────────

class BaseLLMProvider(ABC):
    """
    Unified LLM provider interface.

    All model providers must implement these methods.
    Unsupported capabilities return ProviderResponse with error.

    Usage:
        provider = OpenAIProvider(api_key="sk-...")
        resp = provider.generate("Hello")
        if resp.success:
            print(resp.content)
    """

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model
        self._capabilities: List[str] = []

    # ── Core methods (all providers must implement) ──

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2048,
                 **kwargs) -> ProviderResponse:
        """Generate text completion."""
        ...

    @abstractmethod
    def generate_stream(self, prompt: str, system_prompt: str = "",
                        temperature: float = 0.3, max_tokens: int = 2048,
                        **kwargs):
        """Generate streaming text completion (yields ProviderResponse chunks)."""
        ...

    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3, max_tokens: int = 2048,
                      **kwargs) -> ProviderResponse:
        """Generate JSON-structured output."""
        ...

    # ── Multimodal methods (providers override if supported) ──

    def analyze_image(self, image: str, prompt: str = "",
                      **kwargs) -> ProviderResponse:
        """Analyze an image (vision). Override if supported."""
        return ProviderResponse(
            content="",
            model=self.model,
            provider=self.provider_name,
            capability="IMAGE_INPUT",
            finish_reason="error",
            error=f"{self.provider_name} does not support image analysis",
        )

    def generate_image(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate an image. Override if supported."""
        return ProviderResponse(
            content="",
            model=self.model,
            provider=self.provider_name,
            capability="IMAGE_GENERATION",
            finish_reason="error",
            error=f"{self.provider_name} does not support image generation",
        )

    def generate_video(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate a video. Override if supported."""
        return ProviderResponse(
            content="",
            model=self.model,
            provider=self.provider_name,
            capability="VIDEO_GENERATION",
            finish_reason="error",
            error=f"{self.provider_name} does not support video generation",
        )

    # ── Capability query ──

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g. 'openai', 'deepseek')."""
        ...

    def get_capabilities(self) -> List[str]:
        """
        Get the list of capability names this provider+model supports.

        Reads from A3's ModelRegistry for declared capabilities.
        """
        if self._capabilities:
            return self._capabilities

        try:
            from src.config.model_capability import (
                get_provider_capabilities, CAPABILITY_LABELS,
            )
            from src.config.model_capability import ModelCapability

            caps = get_provider_capabilities(self.provider_name, self.model or "")
            self._capabilities = [
                CAPABILITY_LABELS.get(c, c.name)
                for c in ModelCapability
                if c in caps and c in CAPABILITY_LABELS
            ]
        except ImportError:
            self._capabilities = ["TEXT_GENERATION"]
        return self._capabilities

    def has_capability(self, capability_name: str) -> bool:
        """Check if this provider supports a specific capability."""
        return capability_name in self.get_capabilities()

    def capability_summary(self) -> Dict[str, Any]:
        """Get structured capability summary for UI display."""
        try:
            from src.config.model_capability import get_capability_summary
            return get_capability_summary(self.provider_name, self.model or "")
        except ImportError:
            return {
                "provider": self.provider_name,
                "model": self.model or "default",
                "supported": [{"id": "TEXT_GENERATION", "label": "文本生成", "icon": "📝"}],
                "unsupported": [],
            }

    # ── Status ──

    @property
    def is_available(self) -> bool:
        """Check if the provider is ready (has API key configured)."""
        return bool(self.api_key)

    def validate(self) -> tuple[bool, str]:
        """
        Validate provider configuration.

        Returns:
            (valid: bool, message: str)
        """
        if not self.api_key:
            return False, f"{self.provider_name}: API key not configured"
        return True, "OK"

    # ── HTTP helpers (shared by subclasses) ──

    def _http_post(
        self,
        url: str,
        payload: dict,
        headers: dict,
        timeout: int = 60,
    ) -> dict:
        """
        Make an HTTP POST request with JSON payload.

        Returns parsed JSON response, or raises on error.
        """
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            start = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                elapsed = time.time() - start
                logger.debug(
                    "%s: HTTP %d in %.2fs",
                    self.provider_name, resp.status, elapsed,
                )
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            logger.warning("%s: HTTP %d — %s", self.provider_name, e.code, body[:500])
            raise
        except Exception as e:
            logger.warning("%s: request failed — %s", self.provider_name, e)
            raise

    def _openai_compatible_chat(
        self,
        base_url: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        auth_header: str = "Bearer",
        **kwargs,
    ) -> ProviderResponse:
        """
        Call an OpenAI-compatible /v1/chat/completions endpoint.

        Used by: OpenAI, DeepSeek, Qwen, Kimi, Grok, Spark.
        """
        if not self.is_available:
            return ProviderResponse(
                model=self.model,
                provider=self.provider_name,
                finish_reason="error",
                error=f"{self.provider_name} API key not configured",
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

        url = base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Authorization": f"{auth_header} {self.api_key}"}

        try:
            resp_data = self._http_post(url, payload, headers)
        except urllib.error.HTTPError as e:
            return ProviderResponse(
                model=self.model,
                provider=self.provider_name,
                finish_reason="error",
                error=f"HTTP {e.code}: {str(e)[:300]}",
            )
        except Exception as e:
            return ProviderResponse(
                model=self.model,
                provider=self.provider_name,
                finish_reason="error",
                error=f"Connection failed: {str(e)[:300]}",
            )

        try:
            choice = resp_data["choices"][0]
            content = choice["message"]["content"]
            usage_data = resp_data.get("usage", {})
            return ProviderResponse(
                content=content,
                model=resp_data.get("model", self.model),
                provider=self.provider_name,
                capability="TEXT_GENERATION",
                finish_reason=choice.get("finish_reason", "stop"),
                usage=ProviderUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                ),
            )
        except (KeyError, IndexError) as e:
            return ProviderResponse(
                model=self.model,
                provider=self.provider_name,
                finish_reason="error",
                error=f"Unexpected response format: {str(e)[:200]}",
            )
