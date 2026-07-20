"""
Phase 5.0 — Onboarding Welcome Page

First-run experience: shows A3 introduction, provider selection,
API key input, test connection, and save. Once complete, the
main app renders.

Imported by app_v3.py as a pre-screen gate.
"""

from __future__ import annotations

import time

import streamlit as st

from src.config.llm_config import (
    load_llm_config,
    save_llm_config,
    LLMConfig,
    SUPPORTED_PROVIDERS,
)
from src.config.error_helper import format_provider_error
from src.core.provider_factory import _build_from_config


# ── Provider presets (shared with settings_tab.py) ──

ONBOARDING_PROVIDERS = ["deepseek", "openai", "anthropic", "google", "qwen", "kimi", "grok", "spark", "mock"]

PROVIDER_LABELS = {
    "deepseek": "🌊 DeepSeek",
    "openai": "🤖 OpenAI",
    "anthropic": "🧠 Claude (Anthropic)",
    "google": "🔮 Gemini (Google)",
    "qwen": "☁️ 通义千问 (Qwen)",
    "kimi": "🌙 Kimi (Moonshot)",
    "grok": "🚀 Grok (xAI)",
    "spark": "⭐ 讯飞星火 (Spark)",
    "mock": "🎭 Demo 模式（先体验）",
}

PROVIDER_MODELS = {
    "deepseek": ["deepseek-chat", "deepseek-v4-pro", "deepseek-reasoner"],
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    "spark": ["spark-pro", "spark-lite", "spark-max"],
    "mock": ["mock-model-v1"],
}

PROVIDER_ACCOUNT_URLS = {
    "deepseek": "https://platform.deepseek.com/api_keys",
    "openai": "https://platform.openai.com/api-keys",
    "spark": "https://console.xfyun.cn/app/myapp",
}


def render_onboarding_page() -> None:
    """
    Render the first-run onboarding welcome page.

    Shows:
      1. A3 introduction
      2. Provider selection
      3. API Key input
      4. Test connection
      5. Save & enter

    On completion, sets st.session_state.onboarding_done = True
    and triggers a rerun so main() renders the normal tabs.
    """

    # ── Session state init ──────────────────
    for key, default in [
        ("onboarding_step", "welcome"),    # welcome | setup | done
        ("onboarding_provider", "deepseek"),
        ("onboarding_model", "deepseek-chat"),
        ("onboarding_api_key", ""),
        ("onboarding_test_result", None),  # None | {"success": bool, ...}
        ("onboarding_saving", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    step = st.session_state.onboarding_step

    # ═══════════════════════════════════════════════
    # STEP 1: Welcome
    # ═══════════════════════════════════════════════
    if step == "welcome":
        _render_welcome()
        return

    # ═══════════════════════════════════════════════
    # STEP 2: Provider Setup
    # ═══════════════════════════════════════════════
    _render_setup()


# ── Sub-renderers ──────────────────────────

def _render_welcome() -> None:
    """Welcome / introduction screen."""

    # Hero
    st.markdown("""
    <div style="text-align:center;padding:2em 0 1em;">
        <div style="font-size:4em;">🤖</div>
        <div class="hero-title" style="font-size:2.8em;margin-top:0.3em;">
            A3 智能学习伙伴
        </div>
        <div class="hero-subtitle" style="font-size:1.2em;margin-top:0.5em;">
            9 个 AI 智能体协同 · 个性化学习路径 · 资源精准推荐
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Feature cards
    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header" style="text-align:center;">🚀 开始之前</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="capability-card" style="text-align:center;">
            <div class="capability-icon" style="font-size:2.2em;">🧠</div>
            <div class="capability-title">多智能体协同</div>
            <div class="capability-desc">
                9 个专用 AI Agent 通过 EventBus 协作，<br>
                不是简单的单次对话，是真正的多 Agent Pipeline
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="capability-card" style="text-align:center;">
            <div class="capability-icon" style="font-size:2.2em;">👤</div>
            <div class="capability-title">个性化学习画像</div>
            <div class="capability-desc">
                自然语言描述学习目标 → 6 维自动画像提取<br>
                知识基础 · 认知风格 · 学习节奏 · 等等
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;padding:1em;color:#78909C;font-size:0.95em;">
        配置 AI 模型后，A3 将用你的 API Key 调用大模型<br>
        所有数据本地存储，不上传你的 API Key
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🚀 开始配置", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = "setup"
            st.rerun()
    with col_b:
        if st.button("🎭 先体验 Demo", use_container_width=True):
            # Save mock config and skip
            cfg = LLMConfig(provider="mock", model="", api_key="")
            save_llm_config(cfg)
            st.session_state.onboarding_done = True
            st.rerun()


def _render_setup() -> None:
    """Provider setup screen (step 2)."""

    st.markdown("""
    <div style="text-align:center;padding:1em 0;">
        <div class="hero-title" style="font-size:2em;">⚙️ 配置 AI 模型</div>
        <div class="hero-subtitle">选择你的大模型提供商，输入 API Key 即可开始</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Provider selector ──────────────────
    provider = st.session_state.onboarding_provider
    provider_idx = ONBOARDING_PROVIDERS.index(provider) if provider in ONBOARDING_PROVIDERS else 0

    st.markdown('<div class="section-header">🤖 选择提供商</div>', unsafe_allow_html=True)
    selected_provider = st.selectbox(
        "提供商",
        options=ONBOARDING_PROVIDERS,
        index=provider_idx,
        format_func=lambda p: PROVIDER_LABELS.get(p, p),
        label_visibility="collapsed",
    )

    if selected_provider != provider:
        st.session_state.onboarding_provider = selected_provider
        st.session_state.onboarding_model = PROVIDER_MODELS.get(selected_provider, [""])[0]
        st.session_state.onboarding_api_key = ""
        st.session_state.onboarding_test_result = None
        st.rerun()

    provider = st.session_state.onboarding_provider

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Model selector ─────────────────────
    if provider != "mock":
        st.markdown('<div class="section-header">🧩 模型版本</div>', unsafe_allow_html=True)
        models = PROVIDER_MODELS.get(provider, [""])
        model_idx = 0
        current_model = st.session_state.onboarding_model
        if current_model in models:
            model_idx = models.index(current_model)

        selected_model = st.selectbox(
            "模型",
            options=models,
            index=model_idx,
            label_visibility="collapsed",
        )
        if selected_model != current_model:
            st.session_state.onboarding_model = selected_model
            st.session_state.onboarding_test_result = None

        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── API Key input ──────────────────────
    if provider == "mock":
        st.success("🎭 Demo 模式不需要 API Key。你可以直接开始体验！")
    else:
        api_url = PROVIDER_ACCOUNT_URLS.get(provider, "")
        st.markdown('<div class="section-header">🔑 API Key</div>', unsafe_allow_html=True)

        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder=f"输入你的 {PROVIDER_LABELS.get(provider, provider)} API Key...",
            label_visibility="collapsed",
        )
        if api_key:
            st.session_state.onboarding_api_key = api_key
            st.session_state.onboarding_test_result = None

        if api_url:
            st.caption(f"📋 还没有 API Key？👉 [获取 {PROVIDER_LABELS.get(provider, provider)} API Key]({api_url})")

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Test connection ────────────────────
    test_result = st.session_state.onboarding_test_result

    if test_result is not None:
        if test_result["success"]:
            st.success(f"✅ 连接成功！延迟: {test_result.get('latency', 0):.2f}s")
        else:
            _render_test_error(provider, test_result)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Action buttons ─────────────────────
    btn1, btn2, btn3 = st.columns([2, 2, 1])

    with btn1:
        can_test = provider == "mock" or bool(st.session_state.onboarding_api_key.strip())
        if st.button("🔍 测试连接", use_container_width=True, disabled=not can_test):
            with st.spinner("正在测试连接..."):
                result = _test_connection(
                    provider,
                    st.session_state.onboarding_model,
                    st.session_state.onboarding_api_key,
                )
                st.session_state.onboarding_test_result = result
                st.rerun()

    with btn2:
        can_save = provider == "mock" or (
            test_result is not None
            and test_result["success"]
            and bool(st.session_state.onboarding_api_key.strip())
        )
        label = "🎭 进入 Demo" if provider == "mock" else "💾 保存并开始使用"
        if st.button(label, use_container_width=True, type="primary", disabled=False if provider == "mock" else not can_save):
            cfg = LLMConfig(
                provider=provider,
                model=st.session_state.onboarding_model,
                api_key=st.session_state.onboarding_api_key if provider != "mock" else "",
            )
            save_llm_config(cfg)
            st.session_state.onboarding_done = True
            st.rerun()

    with btn3:
        if st.button("← 返回", use_container_width=True):
            st.session_state.onboarding_step = "welcome"
            st.rerun()


def _render_test_error(provider: str, test_result: dict) -> None:
    """Render a user-friendly test connection error."""
    raw_error = test_result.get("error", "未知错误")
    err = format_provider_error(provider, raw_error)

    with st.container(border=True):
        st.error(f"❌ {err['title']}")
        st.markdown(f"**原因**: {err['reason']}")
        st.markdown(f"**解决办法**:\n{err['solution']}")

        if err.get("api_url"):
            st.markdown(f"🔗 [管理 {PROVIDER_LABELS.get(provider, provider)} API Key]({err['api_url']})")

        with st.expander("🔍 技术详情"):
            st.code(raw_error)


def _test_connection(provider: str, model: str, api_key: str) -> dict:
    """Test LLM provider connection. Returns {success, provider, model, latency, error}."""
    if provider == "mock":
        return {"success": True, "provider": "mock", "model": "mock", "latency": 0.0, "error": ""}

    if not api_key.strip():
        return {"success": False, "provider": provider, "model": model, "latency": 0.0, "error": "请输入 API Key"}

    cfg = LLMConfig(provider=provider, model=model, api_key=api_key)
    t0 = time.time()

    try:
        provider_obj = _build_from_config(cfg)
        if provider_obj is None or not provider_obj.is_available:
            return {
                "success": False,
                "provider": provider,
                "model": model,
                "latency": 0.0,
                "error": f"Provider '{provider}' 不可用",
            }

        response = provider_obj.generate(
            prompt="ping",
            system_prompt="Reply with 'pong' only.",
            temperature=0.0,
            max_tokens=10,
        )
        latency = time.time() - t0

        if response.success:
            return {"success": True, "provider": provider, "model": model, "latency": round(latency, 2), "error": ""}
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
        return {"success": False, "provider": provider, "model": model, "latency": round(latency, 2), "error": str(e)}
