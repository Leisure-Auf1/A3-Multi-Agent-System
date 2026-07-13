"""
Phase 11 — Mock LLM Provider

Deterministic mock provider for testing.
Generates predictable responses based on prompt content.
No API calls, no network, no cost.

Use for:
- Unit tests that need LLM output
- Offline development
- CI/CD pipelines
"""

from __future__ import annotations
from typing import Any, Callable, Dict, Optional

from src.llm.provider import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock LLM provider.

    Generates responses based on:
    1. A response map (prompt patterns → responses)
    2. A fallback function (generates generic responses)

    Usage:
        mock = MockLLMProvider()
        mock.add_response("What is AI?", "AI stands for Artificial Intelligence.")
        response = mock.generate("What is AI?")
        assert response.content == "AI stands for Artificial Intelligence."
    """

    def __init__(
        self,
        model: str = "mock-model-v1",
        default_response: str = "This is a mock response.",
    ):
        super().__init__(api_key="mock-key", base_url="mock://local", model=model)
        self._response_map: Dict[str, str] = {}
        self._fallback: Optional[Callable[[str], str]] = None
        self.default_response = default_response
        self._call_history: list = []  # Track all calls for assertions

    def add_response(self, prompt_pattern: str, response: str):
        """Map a prompt pattern to a specific response."""
        self._response_map[prompt_pattern] = response

    def set_fallback(self, fn: Callable[[str], str]):
        """Set a custom fallback generator for unmatched prompts."""
        self._fallback = fn

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a mock response. Checks response map, then fallback, then default."""
        self._call_history.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        # Check exact matches
        for pattern, response in self._response_map.items():
            if pattern in prompt:
                return LLMResponse(
                    content=response,
                    model=self.model,
                    usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(response) // 4, "total_tokens": (len(prompt) + len(response)) // 4},
                    finish_reason="stop",
                )

        # Use fallback function
        if self._fallback:
            content = self._fallback(prompt)
            return LLMResponse(
                content=content,
                model=self.model,
                usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(content) // 4, "total_tokens": (len(prompt) + len(content)) // 4},
                finish_reason="stop",
            )

        # Default response
        return LLMResponse(
            content=self.default_response,
            model=self.model,
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(self.default_response) // 4, "total_tokens": (len(prompt) + len(self.default_response)) // 4},
            finish_reason="stop",
        )

    def generate_error(self, error_message: str = "Mock error") -> LLMResponse:
        """Return an error response (for testing error handling)."""
        return LLMResponse(
            content="",
            model=self.model,
            error=error_message,
            finish_reason="error",
        )

    @property
    def call_count(self) -> int:
        return len(self._call_history)

    def last_call(self) -> Optional[Dict[str, Any]]:
        return self._call_history[-1] if self._call_history else None

    @property
    def is_available(self) -> bool:
        return True  # Mock is always available
