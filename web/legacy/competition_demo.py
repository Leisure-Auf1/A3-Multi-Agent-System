"""
Phase 8.0 — Competition Demo Mode

One-click competition demo: loads frozen fixtures, runs the full
agent pipeline, and displays results without requiring an API key.

Usage:
    from web.competition_demo import run_competition_demo
    result = run_competition_demo()
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

import streamlit as st

from src.workflow import A3Workflow
from src.core.provider_factory import create_provider

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demo", "fixtures",
)


def render_competition_demo() -> Optional[dict]:
    """
    Render the competition demo page with one-click pipeline execution.

    Returns the workflow_result dict after execution, or None if
    not yet run.

    Call from app_v3.py:
        with tab_compete:
            result = render_competition_demo()
            if result:
                st.session_state.workflow_result = result
    """

    st.markdown(
        '<div class="hero-title" style="font-size:2em;">🏆 比赛演示</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-subtitle">一键运行完整 Pipeline · 无需 API Key · 自动加载演示数据</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Demo instructions ──────────────────
    st.markdown('<div class="section-header">🎯 演示说明</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="capability-card">
        <div class="capability-icon">🏆</div>
        <div class="capability-title">比赛演示模式</div>
        <div class="capability-desc">
            点击下方按钮，A3 将自动运行完整的 6-Agent 学习管道。<br><br>
            ✅ <b>无需 API Key</b> — 使用内置 Mock Provider<br>
            ✅ <b>自动加载演示数据</b> — 预置学生画像 + 学习目标<br>
            ✅ <b>完整 Pipeline</b> — Profile → Plan → Resource → Review → Reflect<br>
            ✅ <b>实时时间线</b> — 每个 Agent 的执行状态和耗时<br>
            ✅ <b>可信评估</b> — ReviewGate 评分 + 置信度指标
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Demo input ─────────────────────────
    student_text = st.text_area(
        "学习目标（可修改以测试不同输入）",
        value=(
            "我是网络工程大二学生，Python基础一般，喜欢看图学习。"
            "想学习 Multi-Agent AI 系统开发。容易受挫，请耐心引导。"
        ),
        height=80,
        label_visibility="collapsed",
    )

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Run button ─────────────────────────
    if st.button("🚀 运行完整 Pipeline", type="primary", use_container_width=True):
        with st.spinner("🤖 12 个智能体正在协同工作中..."):
            result = _run_demo_pipeline(student_text)
            return result

    # ── Demo tips ──────────────────────────
    with st.expander("💡 演示技巧"):
        st.markdown("""
        **赛前准备**:
        1. 启动 A3 → 自动进入比赛演示 Tab
        2. 点击「运行完整 Pipeline」— 5 秒内完成
        3. 展示: 画像 Tab → 学习空间 Tab → 仪表盘 Tab
        4. 全程无需 API Key，不受网络影响

        **演讲要点**:
        - 🧠 12 个 Agent 通过 EventBus 协同，不是单一 LLM 调用
        - 👤 自然语言输入 → 自动 6 维画像提取
        - 🗺️ 知识库驱动的个性化学习路径
        - 📊 ReviewGate 三层评审机制
        - 🔐 API Key 系统密钥环加密存储
        - 🏗️ 5 层架构: 表现 → Agent → 智能 → 信任 → 数据
        """)

    return None


def _run_demo_pipeline(student_text: str) -> dict:
    """
    Run the competition demo pipeline with mock provider.

    Returns the workflow result as a dict for Streamlit session_state.
    """
    t_start = time.time()

    # Use user-configured provider if available; fall back to mock
    provider = create_provider() or create_provider("mock")

    workflow = A3Workflow(
        student_id="competition_demo",
        llm_provider=provider,
    )

    # Load demo profile
    profile = _load_fixture("sample_profile.json")
    user_profile = profile.get("profile") if profile else None

    result = workflow.run(
        user_goal=student_text,
        user_profile=user_profile,
        session_id="competition_demo_session",
    )

    total_ms = (time.time() - t_start) * 1000
    result_dict = result.to_dict()
    result_dict["total_duration_ms"] = total_ms

    return result_dict


def _load_fixture(name: str) -> dict:
    """Load a demo fixture JSON file."""
    path = os.path.join(FIXTURES_DIR, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}
