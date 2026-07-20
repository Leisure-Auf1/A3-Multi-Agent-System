"""
Phase 8.0 — Architecture Overview Page

Visual overview of the A3 multi-agent learning system architecture.
Shows the pipeline, layers, and trust/security model.

Imported by app_v3.py as a demo/overview tab.
"""

from __future__ import annotations

import streamlit as st


def render_architecture_overview() -> None:
    """
    Render the A3 architecture overview page.

    Call from app_v3.py:
        with tab_arch:
            render_architecture_overview()
    """

    st.markdown(
        '<div class="hero-title" style="font-size:2em;">🏗️ A3 系统架构</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-subtitle">'
        '12 个智能体协同 · 5 层架构 · 可信 AI 学习系统'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Architecture Diagram ────────────────
    st.markdown('<div class="section-header">📐 系统架构图</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#0D1117;border-radius:16px;padding:24px;font-family:monospace;font-size:0.82em;line-height:1.6;color:#C9D1D9;overflow-x:auto;">
    <pre style="margin:0;color:#C9D1D9;">
    ┌──────────────────────────────────────────────────────────────────┐
    │                     🖥️  <b>Presentation Layer</b>                       │
    │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐ │
    │  │  Streamlit UI   │  │   FastAPI v2    │  │   Desktop .exe   │ │
    │  │  (4 tabs + demo)│  │  (25 endpoints) │  │  (PyInstaller)   │ │
    │  └─────────────────┘  └─────────────────┘  └──────────────────┘ │
    └──────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼──────────────────────────────────┐
    │                     🤖  <b>Agent Pipeline Layer</b>                   │
    │                                                                │
    │  ProfileAgent ──▶ PlannerAgent ──▶ ResourceAgent                │
    │       │                                  │                      │
    │       └────────── EventBus ──────────────┘                      │
    │                      │                                          │
    │  ReviewAgent ◀── ReflectionAgent ◀── EvaluationAgent            │
    └──────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼──────────────────────────────────┐
    │                     🧠  <b>Intelligence Layer</b>                    │
    │                                                                │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
    │  │ LLM      │  │ RAG      │  │ Memory   │  │ Multimodal   │   │
    │  │ Provider │  │ Retriever│  │ Manager  │  │ Gateway      │   │
    │  │ Factory  │  │ TF-IDF   │  │ (SQLite) │  │ (7 types)    │   │
    │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
    └──────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼──────────────────────────────────┐
    │                     🔐  <b>Trust & Security Layer</b>               │
    │                                                                │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
    │  │ Review   │  │ User     │  │ Keyring  │  │ Auth         │   │
    │  │ Gate     │  │ Sim      │  │ Storage  │  │ (JWT/guest)  │   │
    │  │ (3-tier) │  │ (Persona)│  │ (OS)     │  │              │   │
    │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
    └──────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼──────────────────────────────────┐
    │                     💾  <b>Data Layer</b>                           │
    │                                                                │
    │  ┌──────────────────────────────────────────────────────────┐  │
    │  │  SQLite (WAL mode) — users · profiles · threads ·        │  │
    │  │  messages · resources · sessions · learning_records      │  │
    │  └──────────────────────────────────────────────────────────┘  │
    └──────────────────────────────────────────────────────────────────┘
                                    │
                            Veritas-Core 7.0.0
                     (Agent Runtime Framework)
    </pre>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Layer details ──────────────────────
    cols = st.columns(5)

    layers = [
        ("🖥️", "表现层", "Streamlit UI\nFastAPI\nDesktop .exe"),
        ("🤖", "Agent 层", "12 Agents\nEventBus\nTraceCollector"),
        ("🧠", "智能层", "LLM Factory\nRAG\nMemory\nMultimodal"),
        ("🔐", "信任层", "ReviewGate\nUserSim\nKeyring\nAuth"),
        ("💾", "数据层", "SQLite WAL\nProfiles\nThreads\nRecords"),
    ]

    for i, (icon, title, desc) in enumerate(layers):
        with cols[i]:
            st.markdown(f"""
            <div class="capability-card" style="text-align:center;padding:12px;">
                <div style="font-size:1.8em;">{icon}</div>
                <div class="capability-title">{title}</div>
                <div class="capability-desc">{desc.replace(chr(10), '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Agent details ──────────────────────
    st.markdown('<div class="section-header">🤖 Agent 详解</div>', unsafe_allow_html=True)

    agent_cols = st.columns(3)

    agents = [
        ("ProfileAgent", "👤", "学生画像提取", "6 维画像\nLLM + Rule 双模式"),
        ("PlannerAgent", "🗺️", "学习路径规划", "知识库驱动\n画像自适应"),
        ("ResourceAgent", "📚", "资源精准推荐", "5 类资源\n知识缺口匹配"),
        ("TutorAgent", "💬", "交互式教学", "流式对话\n5 种教学风格"),
        ("EvaluationAgent", "📊", "智能评测", "自动组卷\n薄弱点识别"),
        ("ReflectionAgent", "🔄", "学习反思", "Pipeline 后分析\n持续优化"),
    ]

    for i, (name, icon, role, desc) in enumerate(agents):
        with agent_cols[i % 3]:
            st.markdown(f"""
            <div class="profile-card">
                <div style="font-size:1.5em;margin-bottom:4px;">{icon}</div>
                <div style="font-weight:700;color:#1565C0;">{name}</div>
                <div style="font-size:0.82em;color:#78909C;">{role}</div>
                <div style="font-size:0.78em;color:#90A4AE;margin-top:4px;">{desc.replace(chr(10), ' · ')}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Pipeline flow ──────────────────────
    st.markdown('<div class="section-header">🔄 学习管道流程</div>', unsafe_allow_html=True)

    flow = [
        ("1", "学生输入", "描述学习目标"),
        ("2", "画像提取", "6 维自动分析"),
        ("3", "路径规划", "知识库匹配"),
        ("4", "资源推荐", "5 类型资源"),
        ("5", "质量评审", "ReviewGate 评分"),
        ("6", "学习反思", "持续优化"),
    ]

    flow_cols = st.columns(6)
    for i, (num, step, desc) in enumerate(flow):
        with flow_cols[i]:
            st.markdown(f"""
            <div style="text-align:center;padding:12px;border-radius:12px;
                        background:linear-gradient(135deg,#E3F2FD,#BBDEFB);">
                <div style="font-size:1.5em;font-weight:800;color:#1565C0;">{num}</div>
                <div style="font-weight:700;font-size:0.85em;color:#263238;">{step}</div>
                <div style="font-size:0.75em;color:#546E7A;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
        if i < 5:
            st.markdown(
                '<div style="text-align:center;color:#B0BEC5;font-size:1.2em;padding-top:20px;">→</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # ── Tech stack ─────────────────────────
    st.markdown('<div class="section-header">🛠️ 技术栈</div>', unsafe_allow_html=True)

    tech_data = [
        ("Python 3.10+", "核心语言"),
        ("FastAPI", "REST API"),
        ("Streamlit", "Web UI"),
        ("SQLite WAL", "数据存储"),
        ("Veritas-Core", "Agent 运行时"),
        ("Keyring", "密钥安全"),
        ("DeepSeek/OpenAI/Spark", "LLM 后端"),
        ("Docker", "容器化部署"),
        ("PyInstaller", "桌面打包"),
    ]

    tech_cols = st.columns(3)
    for i, (tech, purpose) in enumerate(tech_data):
        with tech_cols[i % 3]:
            st.markdown(f"**{tech}** — {purpose}")
