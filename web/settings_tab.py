"""
Phase 13.2 — Streamlit Settings Tab (⚙️ AI Provider Center)

Redesigned with provider categorization, runtime status, and model transparency.

Features:
  - Production Models section (8 providers with connection status)
  - Demo & Offline Models section (mock / rule)
  - Provider selector with runtime status indicators
  - Model selector (from PROVIDER_META presets)
  - API Key input (password-masked)
  - Test connection + runtime recording
  - Save configuration
  - Provider health summary from ProviderStatusTracker
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
    PRODUCTION_PROVIDERS,
    DEMO_PROVIDERS,
    PROVIDER_META,
    get_config_path,
)
from src.core.provider_factory import _build_from_config
from src.providers.status import ProviderStatusTracker, ActiveRunInfo


def _meta_label(provider: str) -> str:
    """Get display label from PROVIDER_META."""
    meta = PROVIDER_META.get(provider, {})
    return f"{meta.get('emoji', '')} {meta.get('label', provider)}"


def _meta_desc(provider: str) -> str:
    """Get description from PROVIDER_META."""
    return PROVIDER_META.get(provider, {}).get("desc", "")


def _status_icon(provider: str) -> str:
    """Get connection status icon from runtime tracker."""
    try:
        tracker = ProviderStatusTracker.get_instance()
        snap = tracker.get_snapshot(provider)
        if snap.connected:
            return "🟢"
        if snap.check_error:
            return "🔴"
        return "⚪"
    except Exception:
        return "⚪"


def _default_model(provider: str) -> str:
    """Get default model for a provider from PROVIDER_META."""
    meta = PROVIDER_META.get(provider, {})
    models = meta.get("models", [""])
    return models[0] if models else ""


def render_settings_tab() -> None:
    """Render the AI Provider Center with categorized providers and runtime status."""

    st.markdown(
        '<div class="hero-title" style="font-size:2em;">⚙️ AI Provider Center</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-subtitle">Configure your AI engine — production models and offline demos</div>',
        unsafe_allow_html=True,
    )

    current = load_llm_config()
    config_path = get_config_path()

    # First launch detection
    if not os.path.exists(config_path):
        st.warning(
            "🔔 **No AI provider configured — running in Demo mode.**\n\n"
            "Select a production model below and enter your API Key "
            "to unlock the full multi-agent AI learning experience.",
            icon="🔔",
        )

    # Session state init
    for key, default in [
        ("settings_provider", current.provider),
        ("settings_model", current.model or _default_model(current.provider)),
        ("settings_api_key", ""),
        ("settings_test_result", None),
        ("settings_saved", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ═══════════════════════════════════════════
    # Section: Production Models
    # ═══════════════════════════════════════════
    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
    st.markdown("### 🚀 Production Models")
    st.caption("Connect real AI engines with your API key. Status shows runtime connection state.")

    production_list = sorted(PRODUCTION_PROVIDERS)
    for p in production_list:
        meta = PROVIDER_META.get(p, {})
        status_icon = _status_icon(p)
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.markdown(f"**{meta.get('emoji', '')} {meta.get('label', p)}**")
                st.caption(meta.get("desc", ""))
            with c2:
                models_str = ", ".join(meta.get("models", [])[:3])
                st.caption(f"Models: `{models_str}`")
            with c3:
                st.markdown(f"### {status_icon}")

    # ═══════════════════════════════════════════
    # Section: Demo & Offline Models
    # ═══════════════════════════════════════════
    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
    st.markdown("### 🎭 Demo & Offline Models")
    st.caption("No API key required — explore the system with preset responses.")

    demo_list = sorted(DEMO_PROVIDERS)
    for p in demo_list:
        meta = PROVIDER_META.get(p, {})
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{meta.get('emoji', '')} {meta.get('label', p)}**")
                st.caption(meta.get("desc", ""))
            with c2:
                st.success("Always On")

    # ═══════════════════════════════════════════
    # Provider selector + configuration
    # ═══════════════════════════════════════════
    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
    st.markdown("### ⚡ Active Provider Configuration")

    provider_options = sorted(SUPPORTED_PROVIDERS)
    current_idx = (
        provider_options.index(current.provider)
        if current.provider in provider_options
        else 0
    )

    selected_provider = st.selectbox(
        "Select AI Provider",
        options=provider_options,
        index=current_idx,
        format_func=lambda p: _meta_label(p),
        label_visibility="collapsed",
        key="settings_provider_selector",
    )

    if selected_provider != st.session_state.settings_provider:
        st.session_state.settings_provider = selected_provider
        st.session_state.settings_model = _default_model(selected_provider)
        st.session_state.settings_test_result = None
        st.session_state.settings_saved = False

    provider = st.session_state.settings_provider

    # Description
    desc = _meta_desc(provider)
    if desc:
        st.caption(desc)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # Model selector
    col_left, col_right = st.columns(2)
    with col_left:
        meta = PROVIDER_META.get(provider, {})
        models = meta.get("models", [""])
        model_idx = 0
        if st.session_state.settings_model in models:
            model_idx = models.index(st.session_state.settings_model)

        selected_model = st.selectbox(
            "Model",
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

    # API Key + Actions
    with st.form("api_key_settings_form", clear_on_submit=False):
        if provider in DEMO_PROVIDERS:
            st.markdown('<div class="section-header">🔑 API Key</div>', unsafe_allow_html=True)
            st.caption(f"{_meta_label(provider)} does not require an API Key")
            api_key = ""
        else:
            st.markdown('<div class="section-header">🔑 API Key</div>', unsafe_allow_html=True)
            api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="Paste your API key...",
                label_visibility="collapsed",
                key="settings_api_key_input",
            )

        btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 1])
        with btn_col1:
            test_clicked = st.form_submit_button(
                "🔍 Test Connection",
                use_container_width=True,
                type="secondary",
            )
        with btn_col2:
            can_save = provider in DEMO_PROVIDERS or bool(api_key.strip())
            save_clicked = st.form_submit_button(
                "💾 Save Configuration",
                use_container_width=True,
                type="primary",
                disabled=not can_save,
            )

    # Process form
    if api_key:
        st.session_state.settings_api_key = api_key
    elif provider in DEMO_PROVIDERS:
        st.session_state.settings_api_key = ""

    if test_clicked:
        with st.status(
            f"Testing {_meta_label(provider)}...",
            expanded=True,
        ) as status:
            result = _test_connection(provider, st.session_state.settings_model, api_key)
            st.session_state.settings_test_result = result
            st.session_state.settings_saved = False
            if result["success"]:
                status.update(
                    label=f"✅ Connected! ({result['latency']:.1f}s)",
                    state="complete",
                )
            else:
                status.update(
                    label=f"❌ Failed: {result.get('error', 'Unknown error')}",
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
        st.success(f"✅ Saved — {_meta_label(provider)}")

    # Status display
    test_result = st.session_state.settings_test_result
    if test_result is not None:
        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
        if test_result["success"]:
            st.success(
                f"✅ Connection verified! Latency: {test_result['latency']:.2f}s "
                f"({_meta_label(test_result['provider'])}"
                f" · {test_result['model']})"
            )
            st.caption("Connection verified. Click 'Save Configuration' to persist.")
        else:
            error_msg = test_result.get("error", "Unknown error")
            st.error(f"❌ Connection failed: {error_msg}")
            with st.expander("💡 Troubleshooting"):
                hints = _get_error_hints(error_msg)
                for hint in hints:
                    st.markdown(f"- {hint}")

    elif st.session_state.settings_saved:
        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
        st.info(
            f"✅ Active: **{_meta_label(provider)}**"
            + (f" · {st.session_state.settings_model}" if st.session_state.settings_model else "")
        )

    elif current.is_configured:
        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
        st.info(
            f"📋 Saved: **{_meta_label(current.provider)}**"
            + (f" · {current.model}" if current.model else "")
        )

    # Config details
    with st.expander("📋 Configuration Details"):
        st.json({
            "config_path": config_path,
            "exists": os.path.exists(config_path),
            "current_provider": current.provider,
            "current_configured": current.is_configured,
        })


# ── Helpers ────────────────────────────────


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


# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# Model Capability & Registry Display (Phase 8.3-E2)
# ═══════════════════════════════════════════════════════════════

def _render_capability_display(model_info):
    """Render capability badges for a single model."""
    from src.config.model_capability import CAPABILITY_ICONS, CAPABILITY_LABELS, ModelCapability

    caps = []
    for cap in ModelCapability:
        if cap in model_info.capabilities and cap in CAPABILITY_LABELS:
            icon = CAPABILITY_ICONS.get(cap, "?")
            label = CAPABILITY_LABELS[cap]
            caps.append(f"{icon}{label}")
    return " | ".join(caps) if caps else ""


def _render_model_registry_list():
    """Render the full model registry list in settings tab."""
    from src.config.model_registry import list_models
    from src.config.model_capability import CAPABILITY_ICONS, CAPABILITY_LABELS

    models = list_models()
    if not models:
        st.caption("No models registered")
        return

    for m in models:
        cap_all = [
            cap for cap in m.capabilities.__class__
            if cap in m.capabilities and cap in CAPABILITY_LABELS
        ]
        cap_supported = [
            cap for cap in cap_all
            if cap in m.capabilities
        ]
        cap_unsupported = [cap for cap in cap_all if cap not in m.capabilities]

        sup_count = len(cap_supported)
        total_count = sup_count + len(cap_unsupported)

        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{m.display_name}**")
            c2.caption(f"\U0001f4ca {sup_count}/{total_count} \u80fd\u529b")

            st.caption(
                f"`{m.provider}` \u00b7 context: {m.context_length // 1000}K"
                + (f" \u00b7 streaming" if m.supports_streaming else "")
                + (f" \u00b7 tags: {', '.join(m.tags)}" if m.tags else "")
            )

            chips = []
            for cap in cap_all:
                icon = CAPABILITY_ICONS.get(cap, "?")
                label = CAPABILITY_LABELS.get(cap, cap.name)
                if cap in m.capabilities:
                    chips.append(f"\u2705{icon}{label}")
            st.caption(" | ".join(chips[:6]) + (" ..." if len(chips) > 6 else ""))

# Model Status Page (Phase 9.2)
# ═══════════════════════════════════════════════════════════════

def render_model_status_page():
    """Render the model connection status page."""
    from src.config.secrets import get_config_summary

    st.markdown("### 🌐 模型连接状态")
    st.caption("显示所有支持的 AI 模型 Provider 的 API Key 配置状态")

    summary = get_config_summary()

    for provider_name, info in summary.items():
        emoji = info["emoji"]
        label = info["label"]
        configured = info["configured"]
        env_var = info["env_var"]

        if configured:
            status_icon = "🟢"
            status_text = "已配置"
            detail = f'Key: {info["key_preview"]}'
        else:
            status_icon = "⚪"
            status_text = "未配置"
            detail = f"缺少环境变量: `{env_var}`"

        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 3, 2])
            with c1:
                st.markdown(f"### {emoji}")
            with c2:
                st.markdown(f"**{label}**")
                st.caption(detail)
            with c3:
                st.markdown(f"{status_icon} **{status_text}**")

    configured_count = sum(1 for v in summary.values() if v["configured"])
    total_count = len(summary)
    st.divider()
    tail = " — 全部就绪 ✅" if configured_count == total_count else " — 设置环境变量后重启应用"
    st.caption(f"📊 已配置 {configured_count}/{total_count} 个 Provider{tail}")

    with st.expander("💡 如何配置 API Key？"):
        st.markdown('''**方式1: 环境变量**
```
export OPENAI_API_KEY="sk-your-key"
export DEEPSEEK_API_KEY="sk-your-key"
```
**方式2: 设置页** — 在「AI模型设置」标签页中选择 Provider，输入 API Key 并保存。

**支持的环境变量:**
- OPENAI_API_KEY — OpenAI GPT
- ANTHROPIC_API_KEY — Anthropic Claude
- GOOGLE_API_KEY — Google Gemini
- DASHSCOPE_API_KEY — 阿里通义千问
- DEEPSEEK_API_KEY — DeepSeek
- MOONSHOT_API_KEY — Moonshot Kimi
- XAI_API_KEY — xAI Grok
- SPARK_API_KEY — 讯飞星火
''')


# ═══════════════════════════════════════════════════════════════
# Orchestrator Dashboard (Phase 9.4-A)
# ═══════════════════════════════════════════════════════════════

def render_orchestrator_dashboard():
    """Render the model orchestration dashboard in settings."""
    from src.orchestration.analytics import DecisionAnalytics
    from src.orchestration.runtime import get_runtime

    st.markdown("### \U0001f916 \u6a21\u578b\u8c03\u5ea6\u4e2d\u5fc3")
    st.caption("\u663e\u793a Orchestrator \u7684\u6a21\u578b\u9009\u62e9\u51b3\u7b56\u3001\u5386\u53f2\u7edf\u8ba1\u548c\u8fd0\u884c\u6307\u6807")

    # Runtime metrics
    runtime = get_runtime()
    metrics = runtime.get_metrics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("\u8bf7\u6c42\u6570", metrics.get("total_calls", 0))
    with col2:
        st.metric("\u6210\u529f\u7387", f"{metrics.get('success_rate', 0)}%")
    with col3:
        st.metric("Fallback\u7387", f"{metrics.get('fallback_rate', 0)}%")
    with col4:
        st.metric("\u5e73\u5747\u5ef6\u8fdf", f"{metrics.get('avg_latency_ms', 0)}ms")

    if metrics.get("total_cost", 0) > 0:
        st.caption(f"\U0001f4b0 \u4f30\u7b97\u6210\u672c: ${metrics['total_cost']:.4f}")

    st.divider()

    # Last decision
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**\U0001f4cb \u5386\u53f2\u7edf\u8ba1**")
        # Try analytics for a demo student
        try:
            analytics = DecisionAnalytics("demo-student")
            summary = analytics.get_summary()
            if summary["total_requests"] > 0:
                st.caption(f"\u8bf7\u6c42: {summary['total_requests']} | Fallback: {summary['fallback_rate']}%")
                if summary.get("models"):
                    model_text = " | ".join(
                        f"{m}: {c}" for m, c in list(summary["models"].items())[:3]
                    )
                    st.caption(f"\u6a21\u578b: {model_text}")
                if summary.get("task_distribution"):
                    task_text = " | ".join(
                        f"{t}: {c}" for t, c in list(summary["task_distribution"].items())[:5]
                    )
                    st.caption(f"\u4efb\u52a1: {task_text}")
            else:
                st.caption("\u6682\u65e0\u5386\u53f2\u6570\u636e")
        except Exception:
            st.caption("\u6682\u65e0\u5386\u53f2\u6570\u636e")


# User Model Preferences Display (Phase 9.4-B)

def render_model_preferences():
    """Render user model preference display in settings."""
    from src.orchestration.user_preferences import UserPreferenceManager

    st.markdown("### User Model Preferences")
    st.caption("Models adapt to your usage patterns over time")

    # Try loading preferences for a demo student
    try:
        mgr = UserPreferenceManager("demo-student")
        prefs = mgr.get_all_preferences()

        if not prefs:
            st.info("No learned preferences yet. Use the AI Teacher and rate responses to build preferences.")
        else:
            for task_type, tp in sorted(prefs.items()):
                stars = int(tp.quality_score * 5)
                star_str = chr(0x2B50) * stars
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{task_type}**")
                        st.caption(f"Model: `{tp.preferred_model}` | Provider: `{tp.preferred_provider}`")
                    with c2:
                        st.markdown(f"{star_str}")
                    st.caption(f"Used {tp.use_count} times | Quality: {tp.quality_score:.0%}")
            st.divider()
            st.caption("Preferences are learned from your ratings and usage patterns.")
    except Exception:
        st.caption("Preferences not available")
