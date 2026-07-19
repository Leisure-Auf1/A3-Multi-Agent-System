"""
Phase 5.0 — First-Run Onboarding

Detects whether the user has launched A3 before, and manages
the onboarding state (welcome → provider selection → ready).

Usage:
    from src.config.onboarding import OnboardingState, detect_onboarding

    state = detect_onboarding()
    if state.is_first_run:
        show_welcome_page()
    if state.needs_config:
        show_provider_setup()
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from src.config.llm_config import get_config_path, load_llm_config, LLMConfig


@dataclass
class OnboardingState:
    """
    First-run onboarding state.

    Attributes:
        is_first_run: True if llm.json does not exist (never configured).
        needs_config: True if config exists but no API key is set.
        is_ready: True if a real provider is configured and ready.
        config: Current LLMConfig if it exists.
        provider: Current provider name.
        message: User-facing status message in Chinese.
    """

    is_first_run: bool = False
    needs_config: bool = False
    is_ready: bool = False
    config: LLMConfig | None = None
    provider: str = "mock"
    message: str = ""

    @property
    def show_onboarding(self) -> bool:
        """True if onboarding wizard should be shown (first run or needs config)."""
        return self.is_first_run or self.needs_config

    @property
    def show_demo_mode_warning(self) -> bool:
        """True if running in demo/mock mode (no real API key)."""
        return self.is_ready is False


def detect_onboarding() -> OnboardingState:
    """
    Detect the current onboarding state.

    Returns an OnboardingState indicating what the user needs to do next.

    Scenarios:
      - llm.json missing           → first_run=True,  show welcome
      - llm.json exists, no key    → needs_config=True, prompt setup
      - llm.json exists, has key   → is_ready=True,     skip onboarding
    """
    config_path = get_config_path()

    # ── First run: llm.json doesn't exist ──
    if not os.path.exists(config_path):
        return OnboardingState(
            is_first_run=True,
            needs_config=True,
            is_ready=False,
            config=None,
            provider="mock",
            message=(
                "🎉 欢迎使用 A3 智能学习伙伴！\n\n"
                "检测到你是第一次使用 A3。\n"
                "请在下方配置 AI 模型以解锁完整功能，"
                "或选择「Demo 模式」先体验。"
            ),
        )

    # ── Config exists: load and check ──
    cfg = load_llm_config()

    if cfg.is_configured:
        return OnboardingState(
            is_first_run=False,
            needs_config=False,
            is_ready=True,
            config=cfg,
            provider=cfg.provider,
            message=f"✅ 已配置 {cfg.provider_label} · {cfg.model or '默认模型'}",
        )

    # Config file exists but not configured (no API key for non-mock provider)
    return OnboardingState(
        is_first_run=False,
        needs_config=True,
        is_ready=False,
        config=cfg,
        provider=cfg.provider,
        message=(
            "⚠️ AI 模型未配置 API Key。\n\n"
            "当前使用 Demo 模式（模拟 AI 回复）。\n"
            "请进入 ⚙️ AI模型设置 输入你的 API Key，"
            "以解锁真实的 AI 多智能体学习体验。"
        ),
    )
