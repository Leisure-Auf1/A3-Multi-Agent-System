"""
Phase 4.7 — Rule Provider

Deterministic rule-based provider.
Always returns a configurable default response.
No API calls, no network, zero latency.

Use as the last fallback in a provider chain.
"""

from __future__ import annotations
from typing import Any, Callable, Dict, Optional

from src.llm.provider import LLMProvider, LLMResponse


class RuleProvider(LLMProvider):
    """
    Deterministic rule-based provider — always available.

    Usage:
        rp = RuleProvider(default_response="Using rule-based fallback.")
        response = rp.generate("any prompt")
        assert response.success is True

    With custom handler:
        def my_handler(prompt: str) -> str:
            return f"Echo: {prompt}"
        rp = RuleProvider(handler=my_handler)
    """

    def __init__(
        self,
        default_response: str = "Rule-based response.",
        handler: Optional[Callable[[str], str]] = None,
    ):
        super().__init__(api_key="rule-key", base_url="rule://local", model="rule-v1")
        self.default_response = default_response
        self._handler = handler
        self._call_count: int = 0

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        self._call_count += 1

        content = (
            self._handler(prompt)
            if self._handler
            else self.default_response
        )

        return LLMResponse(
            content=content,
            model=self.model,
            usage={
                "prompt_tokens": len(prompt) // 4,
                "completion_tokens": len(content) // 4,
                "total_tokens": (len(prompt) + len(content)) // 4,
            },
            finish_reason="stop",
            latency_ms=0.0,
        )

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def is_available(self) -> bool:
        return True  # Always available
