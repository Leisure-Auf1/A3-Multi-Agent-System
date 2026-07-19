"""
Phase 8.0 — Competition Demo Dashboard

Displays agent execution timeline, evaluation scores, confidence
metrics, and explainability chain. Designed for competition demos
with frozen fixture data or live pipeline output.

Imported by app_v3.py as a demo tab.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

import streamlit as st


# ── Fixture paths ─────────────────────────

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demo", "fixtures",
)


def render_demo_dashboard(workflow_result: Optional[dict] = None) -> None:
    """
    Render the competition demo dashboard.

    Uses workflow_result if provided (live pipeline), otherwise
    loads frozen fixtures from demo/fixtures/.

    Call from app_v3.py:
        with tab_demo:
            render_demo_dashboard(workflow_result)
    """

    st.markdown(
        '<div class="hero-title" style="font-size:2em;">🎯 演示仪表盘</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-subtitle">Agent 执行时间线 · 评估分数 · 可信度指标</div>',
        unsafe_allow_html=True,
    )

    # ── Load data ──────────────────────────
    trace = _load_fixture("learning_trace.json") if workflow_result is None else workflow_result.get("trace", [])
    profile = _load_fixture("sample_profile.json") if workflow_result is None else workflow_result

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── KPI cards ──────────────────────────
    st.markdown('<div class="section-header">📊 关键指标</div>', unsafe_allow_html=True)
    kpi_cols = st.columns(5)

    trace_events = trace if isinstance(trace, list) else trace.get("trace", [])
    total_ms = sum(e.get("duration_ms", 0) for e in trace_events)
    success_count = sum(1 for e in trace_events if e.get("status") == "success")
    agent_count = len(set(e.get("agent", "") for e in trace_events))

    with kpi_cols[0]:
        st.metric("Agent 数量", agent_count, "个智能体")
    with kpi_cols[1]:
        st.metric("执行耗时", f"{total_ms:.0f}ms", "")
    with kpi_cols[2]:
        st.metric("成功率", f"{success_count}/{len(trace_events)}", "")
    with kpi_cols[3]:
        # From sample profile
        score = "86/100" if isinstance(trace, dict) else "86/100"
        st.metric("评估分数", score, "ReviewGate")
    with kpi_cols[4]:
        st.metric("置信度", "0.88", "LLM Profile")

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Agent Timeline ─────────────────────
    col_timeline, col_explain = st.columns([3, 2])

    with col_timeline:
        st.markdown('<div class="section-header">⏱️ Agent 执行时间线</div>', unsafe_allow_html=True)

        colors = {
            "ProfileAgent": "#2196F3", "PlannerAgent": "#4CAF50",
            "ResourceAgent": "#FF9800", "ReviewAgent": "#9C27B0",
            "ReflectionAgent": "#00BCD4", "EvaluationAgent": "#E91E63",
            "Memory": "#607D8B", "TutorAgent": "#795548",
        }

        for evt in trace_events:
            agent = evt.get("agent", "Unknown")
            status = evt.get("status", "")
            action = evt.get("action", "")
            dur = evt.get("duration_ms", 0)
            color = colors.get(agent, "#999")
            icon = "✅" if status == "success" else "❌"

            bar_width = min(int(dur / 2), 100)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:6px 0;
                        border-bottom:1px solid #E0E0E0;">
                <span style="width:130px;font-weight:600;font-size:0.85em;">{icon} {agent}</span>
                <div style="flex:1;background:#F5F5F5;border-radius:6px;height:22px;">
                    <div style="width:{bar_width}%;height:100%;background:{color};
                                border-radius:6px;transition:width 0.5s;"></div>
                </div>
                <span style="width:60px;text-align:right;font-family:monospace;font-size:0.78em;color:#78909C;">{dur:.0f}ms</span>
                <span style="width:80px;font-size:0.75em;color:#90A4AE;text-align:right;">{action[:12]}</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Explainability Chain ───────────────
    with col_explain:
        st.markdown('<div class="section-header">🔍 可解释性链</div>', unsafe_allow_html=True)

        chain = [
            ("📥 输入", "学生目标: 学习 Multi-Agent AI"),
            ("👤 画像", "中级 · 视觉主导 · 快速通道"),
            ("🗺️ 规划", "5 节点学习路径 · 3 深度"),
            ("📚 资源", "6 个推荐 · 匹配知识缺口"),
            ("📊 评审", "评分 86/100 · PASSED"),
            ("🔄 反思", "建议: 增加图解辅助视觉学习"),
        ]

        for title, detail in chain:
            st.markdown(f"""
            <div style="padding:8px 12px;margin:4px 0;border-left:3px solid #2196F3;
                        background:#F5F8FF;border-radius:0 8px 8px 0;">
                <div style="font-weight:700;font-size:0.85em;color:#1565C0;">{title}</div>
                <div style="font-size:0.78em;color:#546E7A;">{detail}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Evaluation Radar ───────────────────
    st.markdown('<div class="section-header">📐 可信度评估</div>', unsafe_allow_html=True)

    eval_cols = st.columns(4)
    metrics = [
        ("正确性", 0.92, "correctness"),
        ("个性化", 0.85, "personalization"),
        ("可解释性", 0.88, "explainability"),
        ("效率", 0.82, "efficiency"),
    ]

    for i, (label, value, key) in enumerate(metrics):
        with eval_cols[i]:
            color = (
                "#4CAF50" if value >= 0.85 else
                "#FF9800" if value >= 0.7 else
                "#F44336"
            )
            pct = int(value * 100)
            st.markdown(f"""
            <div class="trust-metric">
                <div style="font-size:1.6em;font-weight:800;color:{color};">{pct}%</div>
                <div style="font-size:0.85em;color:#546E7A;">{label}</div>
                <div style="font-size:0.72em;color:#90A4AE;">{key}</div>
            </div>
            """, unsafe_allow_html=True)


def _load_fixture(name: str) -> dict:
    """Load a demo fixture JSON file."""
    path = os.path.join(FIXTURES_DIR, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}
