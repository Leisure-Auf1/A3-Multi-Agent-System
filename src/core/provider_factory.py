"""
Phase 14 — LLMProvider Factory

Centralized provider creation. Reads LLM_PROVIDER env var.
Supports: mock (default), spark (Xunfei), none (rule-only).

Usage:
    from src.core.provider_factory import create_provider
    provider = create_provider()
    adapter = LLMAgentAdapter(provider=provider)
"""

from __future__ import annotations
import json
import os
from typing import Optional

from src.llm.provider import LLMProvider
from src.llm.mock_provider import MockLLMProvider
from src.llm.xunfei_provider import XunfeiSparkProvider


def create_provider(mode: str = "") -> Optional[LLMProvider]:
    """
    Create an LLM provider based on configuration.

    Priority:
      1. Explicit `mode` parameter
      2. LLM_PROVIDER environment variable
      3. Default: mock

    Args:
        mode: "mock" | "spark" | "none" (empty = env or default)

    Returns:
        LLMProvider instance, or None for pure rule mode.
    """
    mode = mode or os.getenv("LLM_PROVIDER", "mock").lower()

    if mode == "spark":
        return _create_spark_provider()
    elif mode == "mock":
        return _create_mock_provider()
    else:
        return None  # Pure rule mode


def _create_spark_provider() -> Optional[LLMProvider]:
    """Create Xunfei Spark provider. Returns None if not configured."""
    api_key = (os.getenv("XF_API_KEY")
               or os.getenv("XUNFEI_API_KEY")
               or os.getenv("XF_SPARK_API_KEY", ""))
    if not api_key:
        # No key configured → fall back to mock with warning
        return _create_mock_provider()

    model = os.getenv("XUNFEI_MODEL", os.getenv("XF_SPARK_MODEL", "spark-pro"))
    return XunfeiSparkProvider(api_key=api_key, model=model)


def _create_mock_provider() -> MockLLMProvider:
    """Create a pre-seeded mock provider for demo/testing."""
    provider = MockLLMProvider()
    _seed_mock_responses(provider)
    return provider


def _seed_mock_responses(provider: MockLLMProvider):
    """Pre-seed mock with realistic competition demo responses."""
    # Profile extraction
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

    # Content generation
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

    # Evaluation
    provider.add_response(
        "evaluate agent output",
        json.dumps({
            "correctness": 0.90,
            "personalization": 0.85,
            "explainability": 0.88,
            "efficiency": 0.82,
            "overall": 0.86,
            "reasoning": "Content is accurate and well-personalized to the student profile."
        })
    )

    # Phase 4.2 — Planner LLM enhancement
    provider.add_response(
        "学习路径规划专家",
        json.dumps({
            "strategy_rationale": (
                "基于你的画像（有编程基础、视觉型学习者、偏好快速实战），"
                "本路径按「概念图解 → 代码沙箱 → 综合实战」推进，"
                "每个节点配 ✅/❌ 语法对比示例，控制单节点时长避免疲劳。"
            ),
            "node_adjustments": [],
        }, ensure_ascii=False)
    )

    # Phase 4.2 — Reflection LLM summary
    provider.add_response(
        "学习反思分析专家",
        json.dumps({
            "summary": (
                "本次规划达成学习目标：路径覆盖核心概念且节奏与画像匹配，"
                "资源类型多样（文档/练习/项目）。关键收获是先建立整体认知再动手实战的路线设计。"
            ),
            "improvements": [
                "建议在实战节点后追加一次自测以巩固薄弱概念",
                "可为视觉型学习者补充结构化图解资源",
            ],
        }, ensure_ascii=False)
    )


def get_provider_info() -> dict:
    """Get information about the active provider configuration."""
    mode = os.getenv("LLM_PROVIDER", "mock").lower()
    info = {
        "mode": mode,
        "provider": None,
        "model": None,
        "fallback_available": True,
    }

    if mode == "spark":
        api_key = (os.getenv("XF_API_KEY")
               or os.getenv("XUNFEI_API_KEY")
               or os.getenv("XF_SPARK_API_KEY", ""))
        if api_key:
            info["provider"] = "XunfeiSparkProvider"
            info["model"] = os.getenv("XUNFEI_MODEL", os.getenv("XF_SPARK_MODEL", "spark-pro"))
            info["configured"] = True
        else:
            info["provider"] = "MockLLMProvider (fallback)"
            info["model"] = "mock-model-v1"
            info["configured"] = False
            info["fallback_reason"] = "XUNFEI_API_KEY not set"
    elif mode == "mock":
        info["provider"] = "MockLLMProvider"
        info["model"] = "mock-model-v1"
        info["configured"] = True
    else:
        info["provider"] = "None (rule-only)"
        info["configured"] = True

    return info


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  LLMProviderFactory — Demo              ║")
    print("╚══════════════════════════════════════════╝")
    print()

    info = get_provider_info()
    print(f"Mode: {info['mode']}")
    print(f"Provider: {info['provider']}")
    print(f"Model: {info['model']}")
    print(f"Configured: {info['configured']}")
    if "fallback_reason" in info:
        print(f"Fallback: {info['fallback_reason']}")
    print()

    provider = create_provider()
    if provider:
        print(f"Created: {provider}")
        response = provider.generate("Hello, are you working?")
        print(f"Test response: {response.content[:100]}...")
        print(f"Success: {response.success}")
    else:
        print("No provider — rule mode active")
