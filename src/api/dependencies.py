"""
Phase 4.2.5 — API Dependencies (FastAPI dependency injection)

Provides:
  - get_provider()     → LLMProvider from request mode or env
  - get_workflow()     → A3Workflow with provider injected

Reuses src/core/provider_factory.py (zero new Provider logic).
"""

from __future__ import annotations
from functools import lru_cache
from typing import Optional

from src.core.provider_factory import create_provider
from src.core.event_bus import AgentEventBus
from veritas.llm.provider import LLMProvider
from src.workflow import A3Workflow


@lru_cache(maxsize=4)
def _cached_create_provider(mode: str) -> Optional[LLMProvider]:
    """Cache provider per mode to avoid repeated instantiation."""
    return create_provider(mode)


def get_provider(mode: str = "") -> Optional[LLMProvider]:
    """
    Create an LLM provider from the given mode.

    Priority:
      1. Explicit mode parameter ("mock" | "spark" | "rule")
      2. LLM_PROVIDER env var  →  "mock" by default

    Returns None for rule mode (pure rule-based pipeline).
    """
    if mode == "rule" or mode == "none":
        return None
    return _cached_create_provider(mode)


def get_workflow(
    provider_mode: str = "",
    student_id: str = "api_user",
) -> A3Workflow:
    """
    Create an A3Workflow instance with the given provider and student_id.

    Phase 4.2.6 — Each call receives an independent EventBus instance
    to isolate traces across concurrent API requests.
    """
    provider = get_provider(provider_mode)
    return A3Workflow(
        student_id=student_id,
        llm_provider=provider,
        bus=AgentEventBus(),  # 请求级独立实例
    )


def get_llm_provider() -> Optional[LLMProvider]:
    """
    FastAPI dependency: provide LLMProvider from environment.

    Priority:
      1. LLM_PROVIDER env var (e.g., "deepseek", "spark")
      2. Falls back to "mock" provider

    Returns None only if LLM_PROVIDER is explicitly "none" / "rule_only".
    """
    return get_provider()
