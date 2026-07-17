"""
Phase 9.5 — Base Provider

Abstract provider with 3-level fallback chain.
Level 1: External API
Level 2: Rule-based local generator
Level 3: Mock artifact (never fails)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class ProviderResult:
    """Output from a provider generation."""
    content: str = ""
    content_format: str = "markdown"
    file_path: str = ""
    media_urls: List[str] = field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0
    provider_name: str = "unknown"
    fallback_level: int = 0       # 0=API, 1=Rule, 2=Mock


class BaseProvider(ABC):
    """Abstract provider with 3-level fallback."""

    name: str = "base"
    cost_per_token: float = 0.0

    def generate(
        self,
        topic: str = "",
        title: str = "",
        concepts: Optional[List[str]] = None,
        profile: Optional[Dict[str, Any]] = None,
        learning_goal: str = "",
        student_level: str = "beginner",
    ) -> ProviderResult:
        concepts = concepts or []
        profile = profile or {}

        if self._api_available():
            try:
                return self._generate_via_api(
                    topic, title, concepts, profile, learning_goal, student_level)
            except Exception:
                pass

        try:
            return self._generate_via_rules(
                topic, title, concepts, profile, learning_goal, student_level)
        except Exception:
            pass

        return self._generate_mock(topic, title)

    @abstractmethod
    def _api_available(self) -> bool: ...

    @abstractmethod
    def _generate_via_api(self, topic, title, concepts, profile, goal, level) -> ProviderResult: ...

    @abstractmethod
    def _generate_via_rules(self, topic, title, concepts, profile, goal, level) -> ProviderResult: ...

    @abstractmethod
    def _generate_mock(self, topic: str, title: str) -> ProviderResult: ...
