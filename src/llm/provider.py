"""
Phase 11 — LLM Provider Interface

Abstract base class for LLM providers.
All providers must implement generate(prompt, **kwargs).

Design principles:
1. Single-method interface: one generate() call with prompt + kwargs
2. Provider-agnostic: works with any OpenAI-compatible API
3. Rule mode preserved: existing agents that don't use LLM are unaffected
4. Streaming support: providers MAY implement generate_stream() for SSE
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator, Optional


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str = ""
    model: str = ""
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    })
    finish_reason: str = "stop"  # stop | length | content_filter | error
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.content) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "error": self.error,
        }


class LLMProvider(ABC):
    """
    Abstract LLM provider interface.

    Usage:
        provider = XunfeiSparkProvider(api_key="...")
        response = provider.generate("Explain AI in 50 words.")
        print(response.content)
    """

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system-level instruction.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum tokens to generate.
            **kwargs: Provider-specific parameters.

        Returns:
            LLMResponse with content and metadata.
        """
        ...

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream tokens one at a time. Default: non-streaming fallback.

        Providers with streaming support should override this.
        """
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        # Yield content token-by-token (space-split as simulation)
        for token in response.content.split(" "):
            yield token + " "

    @property
    def is_available(self) -> bool:
        """Check if the provider is configured and reachable."""
        return bool(self.api_key)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r}, available={self.is_available})"
