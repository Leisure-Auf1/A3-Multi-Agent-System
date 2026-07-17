"""
Phase 4.7 — LLM Provider Factory

Centralized provider creation with fallback chain support.

Usage:
    from src.llm.factory import create_provider

    # Single provider
    provider = create_provider("deepseek")

    # Fallback chain: try DeepSeek → fall back to Mock → Rule
    provider = create_provider("deepseek", fallback_chain=True)

    # Explicit chain order
    provider = create_provider("openai", fallback_providers=["deepseek", "rule"])
"""

from __future__ import annotations
import json
import os
from typing import Callable, Dict, List, Optional

from src.llm.provider import LLMProvider, LLMResponse
from src.llm.mock_provider import MockLLMProvider
from src.llm.xunfei_provider import XunfeiSparkProvider
from src.llm.deepseek_provider import DeepSeekProvider
from src.llm.openai_provider import OpenAIProvider
from src.llm.rule_provider import RuleProvider


# ── Provider builders ────────────────────


def _build_openai() -> Optional[LLMProvider]:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return None
    return OpenAIProvider(api_key=key)


def _build_deepseek() -> Optional[LLMProvider]:
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        return None
    return DeepSeekProvider(api_key=key)


def _build_spark() -> Optional[LLMProvider]:
    key = (os.getenv("XF_API_KEY")
           or os.getenv("XUNFEI_API_KEY")
           or os.getenv("XF_SPARK_API_KEY", ""))
    if not key:
        return None
    model = os.getenv("XUNFEI_MODEL", os.getenv("XF_SPARK_MODEL", "spark-pro"))
    return XunfeiSparkProvider(api_key=key, model=model)


def _build_mock() -> MockLLMProvider:
    provider = MockLLMProvider()
    _seed_mock_responses(provider)
    return provider


def _build_rule() -> RuleProvider:
    return RuleProvider()


_PROVIDER_BUILDERS: Dict[str, Callable[[], Optional[LLMProvider]]] = {
    "openai": _build_openai,
    "deepseek": _build_deepseek,
    "spark": _build_spark,
    "mock": _build_mock,
    "rule": _build_rule,
}


# ── Main factory ───────────────────────────

def create_provider(
    mode: str = "",
    fallback_chain: bool = False,
    fallback_providers: Optional[List[str]] = None,
) -> Optional[LLMProvider]:
    """
    Create an LLM provider.

    Args:
        mode: Provider mode name ("openai"|"deepseek"|"spark"|"mock"|"rule").
              Default: reads LLM_PROVIDER env var, then "mock".
        fallback_chain: If True, wrap in FallbackChain with defaults.
        fallback_providers: Explicit fallback order (overrides defaults).

    Returns:
        LLMProvider instance, or None for pure rule mode ("none").

    Priority:
        1. Explicit `mode` parameter
        2. LLM_PROVIDER environment variable
        3. "mock" (always available)
    """
    mode = mode or os.getenv("LLM_PROVIDER", "mock").lower()

    if mode in ("none", "rule_only"):
        return None  # Pure rule mode — no LLM calls

    # Build primary provider
    primary = _build_one(mode)

    # Fallback chain
    if fallback_chain:
        if fallback_providers:
            chain = [_build_one(n) for n in fallback_providers]
        else:
            chain = _default_fallback_chain(mode)
        return FallbackChain([primary] + [p for p in chain if p is not None])

    return primary


def _build_one(mode: str) -> Optional[LLMProvider]:
    """Build a single provider by name."""
    builder = _PROVIDER_BUILDERS.get(mode)
    if builder is None:
        return _build_mock()  # Unknown mode → mock
    return builder()


def _default_fallback_chain(primary_mode: str) -> List[Optional[LLMProvider]]:
    """Default chain: Mock → Rule (always available)."""
    return [_build_mock(), _build_rule()]


# ── Fallback Chain ─────────────────────────

class FallbackChain(LLMProvider):
    """
    Chain of responsibility: try each provider until one succeeds.

    Usage:
        chain = FallbackChain([DeepSeekProvider(), MockLLMProvider(), RuleProvider()])
        response = chain.generate("prompt")
        # Tries DeepSeek → falls back to Mock → Rule
    """

    def __init__(self, providers: List[Optional[LLMProvider]]):
        valid = [p for p in providers if p is not None]
        if not valid:
            raise ValueError("FallbackChain requires at least one provider")
        first = valid[0]
        super().__init__(
            api_key=first.api_key,
            base_url=first.base_url,
            model=first.model,
        )
        self._providers = valid
        self._last_provider: Optional[str] = None

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        errors = []
        for provider in self._providers:
            if not provider.is_available:
                errors.append(f"{type(provider).__name__}: unavailable")
                continue
            try:
                response = provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                if response.success:
                    self._last_provider = type(provider).__name__
                    return response
                errors.append(f"{type(provider).__name__}: {response.error}")
            except Exception as e:
                errors.append(f"{type(provider).__name__}: {e}")

        # All failed
        return LLMResponse(
            error=f"FallbackChain exhausted ({len(self._providers)} providers): {'; '.join(errors[-3:])}",
            finish_reason="error",
        )

    @property
    def last_provider(self) -> Optional[str]:
        return self._last_provider

    @property
    def is_available(self) -> bool:
        return any(p.is_available for p in self._providers)

    def __repr__(self) -> str:
        names = [type(p).__name__ for p in self._providers]
        return f"FallbackChain({', '.join(names)})"


# ── Mock seeding ───────────────────────────

def _seed_mock_responses(provider: MockLLMProvider):
    """Pre-seed mock with realistic demo responses."""
    provider.add_response(
        "画像分析",
        json.dumps({
            "knowledge_base": "mid_level",
            "cognitive_style": "visual_dominant",
            "error_prone_bias": "magic_syntax_blind",
            "learning_pace": "fast_track",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
            "reasoning": "学生有编程基础，偏好视觉化学习，希望快速上手实战。"
        }, ensure_ascii=False)
    )
    provider.add_response(
        "generate educational content",
        "## Multi-Agent Architecture\n\n"
        "Multi-agent systems use specialized agents with distinct roles. "
        "Each agent communicates through an EventBus and shares state via Memory.\n\n"
        "### Key Patterns\n"
        "1. **Pipeline**: Sequential agent execution\n"
        "2. **Router**: Conditional dispatch to specialized agents\n"
        "3. **Blackboard**: Shared memory workspace\n\n"
        "```python\n"
        "from src.core.event_bus import AgentEventBus\n"
        "bus = AgentEventBus.get_instance()\n"
        "bus.emit(agent='ProfileAgent', action='extract', status='success')\n"
        "```"
    )
    provider.add_response(
        "evaluate agent output",
        json.dumps({
            "correctness": 0.90, "personalization": 0.85,
            "explainability": 0.88, "efficiency": 0.82, "overall": 0.86,
            "reasoning": "Content is accurate and well-personalized."
        })
    )
    provider.add_response(
        "学习路径规划专家",
        json.dumps({
            "strategy_rationale": "基于画像按「概念图解→代码沙箱→综合实战」推进。",
            "node_adjustments": [],
        }, ensure_ascii=False)
    )
    provider.add_response(
        "学习反思分析专家",
        json.dumps({
            "summary": "本次规划达成学习目标，资源类型多样。",
            "improvements": ["追加自测巩固薄弱概念", "补充结构化图解资源"],
        }, ensure_ascii=False)
    )


# ── Info ───────────────────────────────────

def get_provider_info() -> dict:
    """Get information about the active provider configuration."""
    mode = os.getenv("LLM_PROVIDER", "mock").lower()
    info = {"mode": mode, "configured": True}

    if mode == "openai":
        key = os.getenv("OPENAI_API_KEY", "")
        info["provider"] = "OpenAIProvider"
        info["model"] = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        info["configured"] = bool(key)
    elif mode == "deepseek":
        key = os.getenv("DEEPSEEK_API_KEY", "")
        info["provider"] = "DeepSeekProvider"
        info["model"] = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        info["configured"] = bool(key)
    elif mode == "spark":
        key = (os.getenv("XF_API_KEY") or os.getenv("XUNFEI_API_KEY")
               or os.getenv("XF_SPARK_API_KEY", ""))
        info["provider"] = "XunfeiSparkProvider"
        info["model"] = os.getenv("XUNFEI_MODEL", os.getenv("XF_SPARK_MODEL", "spark-pro"))
        info["configured"] = bool(key)
    elif mode == "mock":
        info["provider"] = "MockLLMProvider"
        info["model"] = "mock-model-v1"
    elif mode in ("none", "rule_only"):
        info["provider"] = "None (rule-only)"
    else:
        info["provider"] = "MockLLMProvider (fallback)"
        info["model"] = "mock-model-v1"

    return info
