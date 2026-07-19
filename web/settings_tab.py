"""
Phase 4.0 — Streamlit Settings Tab (⚙️ AI模型设置)

User LLM configuration UI component. Imported by app_v3.py as a 4th tab.

Features:
  - Provider selector (DeepSeek / OpenAI / Spark / Mock)
  - Model selector (with presets per provider)
  - API Key input (password-masked)
  - Test connection button
  - Save configuration button
  - Status display (connected / failed / unconfigured)
  - First-launch detection with demo mode notification
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

import streamlit as st

from src.config.llm_config import (
    load_llm_config,
    save_llm_config,
    LLMConfig,
    SUPPORTED_PROVIDERS,
    get_config_path,
)
from src.core.provider_factory import _build_from_config


# ── Provider presets ───────────────────────

PROVIDER_LABELS = {
    "deepseek": "🌊 DeepSeek",
    "openai": "🤖 OpenAI",
    "spark": "🚀 讯飞星火 (Spark)",
    "mock": "🎭 Mock (演示模式)",
    "rule": "⚙️ Rule (纯规则)",
}

PROVIDER_MODELS = {
    "deepseek": ["deepseek-chat", "deepseek-v4-pro", "deepseek-reasoner"],
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "spark": ["spark-pro", "spark-lite", "spark-max"],
    "mock": ["mock-model-v1"],
    "rule": ["rule-v1"],
}

PROVIDER_DESCRIPTIONS = {
    "deepseek": "DeepSeek 大模型 — 高性价比，中文能力强",
    "openai": "OpenAI GPT 系列 — 全球领先的AI能力",
    "spark": "讯飞星火大模型 — 国产大模型，合规可靠",
    "mock": "本地演示模式 — 无需API Key，使用预设回复",
    "rule": "纯规则引擎 — 不调用任何AI模型",
}


def render_settings_tab() -> None:
    """
    Render the AI Model Settings tab.

    Call this from app_v3.py:
        with tab_settings:
            render_settings_tab()
    """

    st.markdown(
        '<div class="hero-title" style="font-size:2em;">⚙️ AI模型设置</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-subtitle">配置你的大语言模型，让A3智能体为你服务</div>',
        unsafe_allow_html=True,
    )

    # Load current config
    current = load_llm_config()

    # ── First launch detection ──────────────
    config_path = get_config_path()
    if not os.path.exists(config_path):
        st.warning(
            "🔔 **未配置AI模型，当前使用 Demo 模式。**\n\n"
            "请在下方的设置中输入你的 API Key，"
            "以解锁真实的 AI 多智能体学习体验。",
            icon="🔔",
        )

    # ── Session state init ──────────────────
    for key, default in [
        ("settings_provider", current.provider),
        ("settings_model", current.model or _default_model(current.provider)),
        ("settings_api_key", ""),  # Never pre-fill API key
        ("settings_test_result", None),
        ("settings_saved", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Provider selector ───────────────────
    st.markdown('<div class="section-header">🤖 模型提供商</div>', unsafe_allow_html=True)

    provider_options = list(SUPPORTED_PROVIDERS)
    current_idx = (
        provider_options.index(current.provider)
        if current.provider in provider_options
        else 0
    )

    selected_provider = st.selectbox(
        "选择模型提供商",
        options=provider_options,
        index=current_idx,
        format_func=lambda p: PROVIDER_LABELS.get(p, p),
        label_visibility="collapsed",
        key="settings_provider_selector",
    )

    # Update session state on provider change
    if selected_provider != st.session_state.settings_provider:
        st.session_state.settings_provider = selected_provider
        st.session_state.settings_model = _default_model(selected_provider)
        st.session_state.settings_test_result = None
        st.session_state.settings_saved = False

    provider = st.session_state.settings_provider

    # Provider description
    desc = PROVIDER_DESCRIPTIONS.get(provider, "")
    if desc:
        st.caption(desc)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Model selector ──────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-header">🧩 模型版本</div>', unsafe_allow_html=True)
        models = PROVIDER_MODELS.get(provider, [""])
        model_idx = 0
        if st.session_state.settings_model in models:
            model_idx = models.index(st.session_state.settings_model)

        selected_model = st.selectbox(
            "模型",
            options=models,
            index=model_idx,
            label_visibility="collapsed",
            key="settings_model_selector",
        )
        if selected_model != st.session_state.settings_model:
            st.session_state.settings_model = selected_model
            st.session_state.settings_test_result = None
            st.session_state.settings_saved = False

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── API Key + Actions (wrapped in st.form) ─
    #
    # st.form batches all widget states before processing submit.
    # This guarantees the password field value is captured even when
    # the user pastes a key and clicks submit without pressing Enter.
    # Ref: Streamlit docs — Form execution model.
    with st.form("api_key_settings_form", clear_on_submit=False):
        # ── API Key input ──────────────────
        if provider in ("mock", "rule"):
            st.markdown('<div class="section-header">🔑 API Key</div>', unsafe_allow_html=True)
            st.caption(f"{PROVIDER_LABELS.get(provider)} 无需 API Key")
            api_key = ""
        else:
            st.markdown('<div class="section-header">🔑 API Key</div>', unsafe_allow_html=True)
            api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="输入你的 API Key...",
                label_visibility="collapsed",
                key="settings_api_key_input",
            )

        # ── Action buttons ─────────────────
        btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 1])

        with btn_col1:
            test_clicked = st.form_submit_button(
                "🔍 测试连接",
                use_container_width=True,
                type="secondary",
            )

        with btn_col2:
            can_save = provider in ("mock", "rule") or bool(api_key.strip())
            save_clicked = st.form_submit_button(
                "💾 保存配置",
                use_container_width=True,
                type="primary",
                disabled=not can_save,
            )

    # ── Process form submission ─────────────
    # These run AFTER the form context exits, when form data is committed.

    # Sync key to session_state (for display in "配置详情" etc.)
    if api_key:
        st.session_state.settings_api_key = api_key
    elif provider in ("mock", "rule"):
        st.session_state.settings_api_key = ""

    if test_clicked:
        with st.status(
            f"正在连接 {PROVIDER_LABELS.get(provider, provider)}...",
            expanded=True,
        ) as status:
            result = _test_connection(provider, st.session_state.settings_model, api_key)
            st.session_state.settings_test_result = result
            st.session_state.settings_saved = False
            if result["success"]:
                status.update(
                    label=f"✅ 连接成功! ({result['latency']:.1f}s)",
                    state="complete",
                )
            else:
                status.update(
                    label=f"❌ 连接失败: {result.get('error', '未知错误')}",
                    state="error",
                )

    if save_clicked:
        cfg = LLMConfig(
            provider=provider,
            model=st.session_state.settings_model,
            api_key=api_key,
        )
        save_llm_config(cfg)
        st.session_state.settings_saved = True
        st.session_state.settings_test_result = None
        st.success(f"✅ 配置已保存 — {PROVIDER_LABELS.get(provider, provider)}")

    # ── Status display (stable containers) ─
    # Always rendered — never conditionally removed from the widget tree.
    # This prevents React DOM removeChild errors caused by
    # spinner/expander appearing and disappearing between renders.

    test_result = st.session_state.settings_test_result
    if test_result is not None:
        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
        if test_result["success"]:
            st.success(
                f"✅ 连接成功！延迟: {test_result['latency']:.2f}s "
                f"({PROVIDER_LABELS.get(test_result['provider'], test_result['provider'])}"
                f" · {test_result['model']})"
            )
            st.caption("连接已验证，点击「保存配置」以保存设置。")
        else:
            error_msg = test_result.get("error", "未知错误")
            st.error(f"❌ 连接失败: {error_msg}")
            with st.expander("💡 故障排除建议"):
                hints = _get_error_hints(error_msg)
                for hint in hints:
                    st.markdown(f"- {hint}")

    elif st.session_state.settings_saved:
        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
        st.info(
            f"✅ 当前使用: **{PROVIDER_LABELS.get(provider, provider)}**"
            + (f" · {st.session_state.settings_model}" if st.session_state.settings_model else "")
        )

    elif current.is_configured:
        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
        st.info(
            f"📋 已保存配置: **{PROVIDER_LABELS.get(current.provider, current.provider)}**"
            + (f" · {current.model}" if current.model else "")
        )

    # ── Current config info ─────────────────
    with st.expander("📋 配置详情"):
        st.json({
            "config_path": config_path,
            "exists": os.path.exists(config_path),
            "current_provider": current.provider,
            "current_configured": current.is_configured,
        })


# ── Helpers ────────────────────────────────

def _default_model(provider: str) -> str:
    """Get default model for a provider."""
    models = PROVIDER_MODELS.get(provider, [""])
    return models[0] if models else ""


def _test_connection(provider: str, model: str, api_key: str) -> dict:
    """
    Test LLM provider connection.

    Returns dict with: success, provider, model, latency, error.
    """
    if provider in ("mock", "rule"):
        return {
            "success": True,
            "provider": provider,
            "model": model,
            "latency": 0.0,
            "error": "",
        }

    if not api_key.strip():
        return {
            "success": False,
            "provider": provider,
            "model": model,
            "latency": 0.0,
            "error": "请输入 API Key",
        }

    cfg = LLMConfig(provider=provider, model=model, api_key=api_key)
    t0 = time.time()

    try:
        provider_instance = _build_from_config(cfg)
        if provider_instance is None or not provider_instance.is_available:
            return {
                "success": False,
                "provider": provider,
                "model": model,
                "latency": 0.0,
                "error": f"Provider '{provider}' 不可用",
            }

        response = provider_instance.generate(
            prompt="ping",
            system_prompt="Reply with 'pong' only.",
            temperature=0.0,
            max_tokens=10,
        )
        latency = time.time() - t0

        if response.success:
            return {
                "success": True,
                "provider": provider,
                "model": model,
                "latency": round(latency, 2),
                "error": "",
            }
        else:
            return {
                "success": False,
                "provider": provider,
                "model": model,
                "latency": round(latency, 2),
                "error": response.error or "Provider 返回错误",
            }

    except Exception as e:
        latency = time.time() - t0
        return {
            "success": False,
            "provider": provider,
            "model": model,
            "latency": round(latency, 2),
            "error": str(e),
        }

def _get_error_hints(error_msg: str) -> list[str]:
    """Return troubleshooting hints based on error message content."""
    hints = []
    error_lower = error_msg.lower()

    if "api key" in error_lower or "401" in error_msg or "unauthorized" in error_lower:
        hints.append("API Key 无效或格式错误 — 请检查 Key 是否完整复制")
        hints.append("确认 Key 以 'sk-' 开头且在提供商控制台处于激活状态")
    elif "timeout" in error_lower or "connect" in error_lower:
        hints.append("网络连接超时 — 请检查网络或代理设置")
        hints.append("如果使用代理，确认代理地址和端口正确")
    elif "rate" in error_lower or "429" in error_msg:
        hints.append("请求频率过高 — 请稍后再试")
    elif "model" in error_lower:
        hints.append("模型不可用 — 尝试选择其他模型")
    else:
        hints.append("请确认 API Key 格式正确且网络连通")
        hints.append(f"错误详情: {error_msg}")

    hints.append("如果问题持续，请尝试 Demo 模式 (Mock) 体验系统功能")
    return hints
