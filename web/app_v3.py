"""
A3 v3.x — Unified Pipeline UI (A3Workflow Runtime)
====================================================
Professional 3-tab AI learning assistant. Uses A3Workflow.run()
for all pipeline execution — zero hardcoded agent calls.

Usage:
    streamlit run web/app_v3.py      # Direct
    streamlit run app.py             # HF Spaces (delegates to this file)
"""

from __future__ import annotations
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from src.workflow import A3Workflow
from src.core.provider_factory import create_provider


def main():
    """A3 Streamlit entry point. Callable from app.py for HF Spaces."""

    # ═══════════════════════════════════════════════
    # Page Config
    # ═══════════════════════════════════════════════

    st.set_page_config(
        page_title="A3 智能学习伙伴", page_icon="🤖",
        layout="wide", initial_sidebar_state="collapsed",
    )

    # ═══════════════════════════════════════════════
    # Professional CSS
    # ═══════════════════════════════════════════════

    st.markdown("""
    <style>
        .hero-title { font-size: 2.6em; font-weight: 800; letter-spacing: -0.02em;
                      background: linear-gradient(135deg, #1565C0, #2196F3);
                      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                      margin-bottom: 0.15em; }
        .hero-subtitle { font-size: 1.15em; color: #546E7A; font-weight: 400; margin-bottom: 1.8em; }
        .section-header { font-size: 1.3em; font-weight: 700; color: #1565C0; margin: 1em 0 0.5em; }
        .capability-card { border: 1px solid #E3F2FD; border-radius: 14px; padding: 20px;
                           background: linear-gradient(135deg, #FAFAFA, #F5F5F5);
                           transition: all 0.2s; height: 100%; }
        .capability-card:hover { border-color: #2196F3; box-shadow: 0 2px 12px rgba(33,150,243,0.12); }
        .capability-icon { font-size: 1.8em; margin-bottom: 8px; }
        .capability-title { font-weight: 700; font-size: 1.05em; color: #263238; margin-bottom: 4px; }
        .capability-desc { font-size: 0.85em; color: #607D8B; line-height: 1.4; }
        .profile-card { border: 2px solid #E3F2FD; border-radius: 14px; padding: 18px;
                        background: #fff; margin: 6px 0; }
        .profile-card-label { font-size: 0.82em; color: #78909C; font-weight: 500; margin-bottom: 2px; }
        .profile-card-value { font-size: 1.3em; color: #1565C0; font-weight: 700; }
        .profile-card-dim { font-size: 0.78em; color: #90A4AE; }
        .resource-card { border: 2px solid #E0E0E0; border-radius: 14px; padding: 18px;
                         background: #fff; text-align: center; transition: all 0.15s; }
        .resource-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
        .trust-metric { text-align: center; padding: 16px 8px; border-radius: 12px;
                        background: linear-gradient(135deg, #F1F8E9, #E8F5E9); margin: 4px 0; }
        .timeline-item { display: flex; align-items: center; gap: 12px;
                         padding: 8px 12px; border-left: 3px solid #E0E0E0; margin: 4px 0; }
        .timeline-item.done { border-left-color: #4CAF50; }
        .timeline-time { font-family: monospace; font-size: 0.82em; color: #90A4AE; min-width: 75px; }
        .timeline-agent { font-weight: 600; font-size: 0.92em; min-width: 140px; }
        .timeline-action { font-size: 0.85em; color: #546E7A; }
        .timeline-latency { font-family: monospace; font-size: 0.78em; color: #90A4AE; margin-left: auto; }
        .node-card { border: 2px solid #E3F2FD; border-radius: 12px; padding: 14px 18px;
                     background: #fff; margin: 8px 0; }
        .node-level { font-weight: 800; font-size: 0.9em; color: #2196F3; }
        .node-title { font-weight: 700; font-size: 1.05em; color: #263238; }
        .node-concept { font-size: 0.82em; color: #607D8B; margin-top: 2px; }
        .node-meta { font-size: 0.78em; color: #90A4AE; margin-top: 4px; }
        .node-arrow { text-align: center; color: #B0BEC5; font-size: 1.2em; margin: 2px 0; }
        .divider-custom { margin: 1.5em 0; border: none; border-top: 1px solid #E0E0E0; }
    </style>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════
    # Navigation tabs
    # ═══════════════════════════════════════════════

    tab1, tab2, tab3 = st.tabs(["🏠 学习助手", "👤 学习画像", "📚 学习空间"])

    # ═══════════════════════════════════════════════
    # Cached workflow (Phase 4.2 — provider-aware)
    # ═══════════════════════════════════════════════

    @st.cache_resource
    def init_workflow(provider_mode: str) -> A3Workflow:
        """A3Workflow instance per provider mode (mock | spark | rule)."""
        provider = None
        if provider_mode in ("mock", "spark"):
            provider = create_provider(provider_mode)
        return A3Workflow(student_id="app_v3_user", llm_provider=provider)

    # ═══════════════════════════════════════════════
    # Session state
    # ═══════════════════════════════════════════════

    for key, default in [
        ("workflow_result", None),
        ("student_text", ""),
        ("pipeline_run", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ═══════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════

    def _radar_values(dims: dict) -> dict:
        maps = {
            "knowledge_base": {"junior_dev": 0.33, "mid_level": 0.66, "senior": 1.0},
            "cognitive_style": {"visual_dominant": 0.8, "text_linear": 0.5, "auditory": 0.6},
            "error_prone_bias": {"magic_syntax_blind": 0.3, "indentation_errors": 0.5,
                                 "variable_scoping": 0.5, "type_mismatch": 0.5, "import_issues": 0.5},
            "learning_pace": {"fast_track": 0.85, "normal": 0.5, "deep_dive": 0.7},
            "interaction_preference": {"code_sandbox": 0.85, "quiz_first": 0.5, "passive_read": 0.35},
            "frustration_threshold": {"low": 0.25, "medium": 0.6, "high": 0.9},
        }
        return {k: maps.get(k, {}).get(str(dims.get(k, "")), 0.5) for k in maps}

    def _get_profile_dims(result_dict: dict) -> dict:
        profile = result_dict.get("profile") or {}
        inner = profile.get("profile") if isinstance(profile, dict) else profile
        if isinstance(inner, dict):
            dim_keys = {"knowledge_base", "cognitive_style", "error_prone_bias",
                         "learning_pace", "interaction_preference", "frustration_threshold"}
            return {k: v for k, v in inner.items() if k in dim_keys}
        return {}

    def _get_profile_source_conf(result_dict: dict) -> tuple:
        profile = result_dict.get("profile") or {}
        source = profile.get("source", "rule") if isinstance(profile, dict) else "rule"
        confidence = profile.get("confidence", 0.7) if isinstance(profile, dict) else 0.7
        return source, float(confidence)

    def _plan_nodes(result_dict: dict) -> list:
        lp = result_dict.get("learning_plan") or {}
        return lp.get("nodes", [])

    RESOURCE_TYPE_MAP = {
        "documentation": ("document", "📄", "#1565C0", "课程讲义"),
        "video": ("video", "🎬", "#C62828", "视频"),
        "exercise": ("exercise", "✏️", "#E65100", "练习题"),
        "article": ("document", "📄", "#1565C0", "阅读材料"),
        "project": ("code", "💻", "#2E7D32", "项目实战"),
    }

    def _render_resource_cards(resources: list) -> None:
        if not resources:
            st.caption("暂无推荐资源")
            return
        for row_start in range(0, len(resources), 3):
            cols = st.columns(3)
            for j, r in enumerate(resources[row_start:row_start + 3]):
                rtype = r.get("type", "documentation")
                mapped = RESOURCE_TYPE_MAP.get(rtype, ("document", "📄", "#999", rtype))
                _, icon, color, label = mapped
                title = r.get("title", "")[:35]
                reason = r.get("reason", "")[:80]
                with cols[j]:
                    st.markdown(f"""<div class="resource-card" style="border-color:{color};">
                        <div style="font-size:2.2em;">{icon}</div>
                        <div style="font-weight:700;color:{color};font-size:1.05em;">{label}</div>
                        <div style="font-size:0.82em;color:#78909C;margin-top:2px;">{title}</div>
                    </div>""", unsafe_allow_html=True)
                    with st.expander("详情"):
                        st.caption(f"**推荐理由**: {reason}")
                        st.caption(f"难度: {r.get('difficulty', '-')} · 预计: {r.get('estimated_minutes', '-')}min")

    def _render_timeline(trace: list) -> None:
        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">⏱️ Agent 执行时间线</div>', unsafe_allow_html=True)
        if not trace:
            st.caption("运行分析后显示 Agent 执行时间线")
            return
        for evt in trace:
            icon = "✅" if evt.get("status") == "success" else "❌"
            ts = (evt.get("timestamp", "")[11:19]) if evt.get("timestamp") else "--:--:--"
            agent = evt.get("agent", "?")
            action = evt.get("action", "")
            latency = evt.get("duration_ms", 0)
            st.markdown(f"""
            <div class="timeline-item done">
                <div class="timeline-time">{ts}</div>
                <div class="timeline-agent">{icon} {agent}</div>
                <div class="timeline-action">{action}</div>
                <div class="timeline-latency">{latency:.0f}ms</div>
            </div>
            """, unsafe_allow_html=True)

    def _render_trust_panel(result_dict: dict) -> None:
        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">🛡️ AI 可信度</div>', unsafe_allow_html=True)
        ev = result_dict.get("evaluation") or {}
        score = ev.get("score", 0)
        passed = ev.get("passed", False)
        plan = result_dict.get("learning_plan") or {}
        nodes_count = len(plan.get("nodes", []))
        trust_cols = st.columns(4)
        with trust_cols[0]:
            st.markdown('<div class="trust-metric">', unsafe_allow_html=True)
            st.metric("知识覆盖", f"{nodes_count}", "个学习节点")
            st.caption("来自 PlannerAgent")
            st.markdown('</div>', unsafe_allow_html=True)
        with trust_cols[1]:
            st.markdown('<div class="trust-metric">', unsafe_allow_html=True)
            st.metric("综合评估", f"{score}/100", "ReviewGate")
            st.caption("Correctness · Relevance · Safety")
            st.markdown('</div>', unsafe_allow_html=True)
        with trust_cols[2]:
            st.markdown('<div class="trust-metric">', unsafe_allow_html=True)
            st.markdown("### 🟢" if passed else "### 🟡")
            st.caption(f"**质量评审: {'通过' if passed else '待改进'}**")
            refl = result_dict.get("reflection") or {}
            st.caption(refl.get("summary", "")[:50] if refl.get("summary") else "ReflectionAgent 已评估")
            st.markdown('</div>', unsafe_allow_html=True)
        with trust_cols[3]:
            st.markdown('<div class="trust-metric">', unsafe_allow_html=True)
            st.markdown("### ✅" if result_dict.get("memory_saved") else "### ⚠️")
            st.caption("**Memory 持久化**")
            st.caption("已保存" if result_dict.get("memory_saved") else "未保存")
            st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════
    # ═══════════════  TAB 1: HOME  ═══════════════
    # ═══════════════════════════════════════════════

    with tab1:
        st.markdown('<div class="hero-title">A3 智能学习伙伴</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="hero-subtitle">'
            '基于<span style="color:#1565C0;font-weight:600;">讯飞星火大模型</span> · '
            '<span style="font-weight:600;">12 个智能体协同</span> · '
            '个性化学习路径 · 资源精准推荐</div>',
            unsafe_allow_html=True)

        caps = [
            ("🧠", "多智能体协同", "12 个专用 Agent\nEventBus + Memory 协作"),
            ("👤", "自然语言画像", "6 维学习画像\nLLM + 规则双模式"),
            ("🗺️", "个性化路径", "知识库驱动\n画像动态调整"),
            ("🎨", "资源推荐", "5 类个性化资源\n基于知识缺口推送"),
            ("📊", "可信评估", "ReviewGate 评分\nPost-Execution Reflection"),
            ("🚀", "讯飞星火", "Spark 大模型\n多模型兼容接口"),
        ]
        cap_cols = st.columns(3)
        for i, (icon, title, desc) in enumerate(caps):
            with cap_cols[i % 3]:
                st.markdown(f"""
                <div class="capability-card">
                    <div class="capability-icon">{icon}</div>
                    <div class="capability-title">{title}</div>
                    <div class="capability-desc">{desc.replace(chr(10), '<br>')}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

        col_input, col_examples = st.columns([3, 1])
        with col_input:
            st.markdown('<div class="section-header">✏️ 告诉我你的学习目标</div>', unsafe_allow_html=True)
            student_text = st.text_area(
                "学习目标",
                value=st.session_state.get("student_text", ""),
                placeholder="例如：我是网络工程大二学生，Python基础一般，喜欢看图和动手写代码。想学习Multi-Agent AI系统开发。容易受挫，请耐心引导。",
                height=105, label_visibility="collapsed",
            )
        with col_examples:
            st.caption("💡 快速示例")
            if st.button("🎓 多智能体AI", use_container_width=True):
                st.session_state.student_text = "我是网络工程大二学生，Python基础一般，喜欢看图学习。想学习Multi-Agent AI系统开发。"
                st.rerun()
            if st.button("🐍 Python进阶", use_container_width=True):
                st.session_state.student_text = "我有Python基础，想深入学习装饰器和生成器。我是文字型学习者。"
                st.rerun()
            if st.button("🤖 Agent开发", use_container_width=True):
                st.session_state.student_text = "我是后端开发，想快速上手AI Agent开发。时间紧，直接上实战。容易受挫。"
                st.rerun()

        # ── Provider Selector (Phase 4.2) ──
        PROVIDER_OPTIONS = {
            "🤖 Mock (演示 LLM)": "mock",
            "🚀 Xunfei Spark": "spark",
            "⚙️ Rule (纯规则)": "rule",
        }
        col_provider, col_mode = st.columns([3, 2])
        with col_provider:
            provider_label = st.radio(
                "Provider",
                list(PROVIDER_OPTIONS.keys()),
                horizontal=True,
                label_visibility="collapsed",
            )
        provider_mode = PROVIDER_OPTIONS[provider_label]
        workflow = init_workflow(provider_mode)

        with col_mode:
            if workflow.llm_provider is not None:
                _model = getattr(workflow.llm_provider, "model", "?")
                st.caption(f"当前模式: 🤖 LLM Mode ({_model})")
            else:
                st.caption("当前模式: ⚙️ Rule Mode")

        # 使用 text_area 返回值判断 (手动输入无 key 绑定, session_state 不会自动同步)
        btn_disabled = not (student_text or "").strip()
        if st.button("🚀 开始分析", type="primary", use_container_width=True, disabled=btn_disabled):
            st.session_state.pipeline_run = True
            st.session_state.student_text = (student_text or "").strip()
            st.rerun()

        if st.session_state.pipeline_run:
            text = st.session_state.student_text
            t_total_start = time.time()

            st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-header">🔄 智能体协同工作中...</div>', unsafe_allow_html=True)

            with st.spinner("🤖 12 个智能体正在协同工作..."):
                result = workflow.run(
                    user_goal=text,
                    knowledge_gaps=[],
                    session_id="app_v3_demo",
                )

            total_lat = (time.time() - t_total_start) * 1000

            trace = result.trace or []
            step_map = {}
            for t in trace:
                agent = t.get("agent", "")
                if agent not in ("System", "Workflow"):
                    step_map[agent] = t

            display_order = ["ProfileAgent", "PlannerAgent", "ResourceAgent",
                              "ReviewAgent", "ReflectionAgent", "Memory"]
            for agent in display_order:
                t = step_map.get(agent)
                icon = "✅" if (t and t.get("status") == "success") else "⏳"
                out = t.get("output", "")[:60] if t else "..."
                lat = f"{t.get('duration_ms', 0):.0f}ms" if t else ""
                st.write(f"{icon} **{agent}** — {out} {lat}")

            st.session_state.workflow_result = result.to_dict()
            st.session_state.pipeline_run = False

            st.success(f"🎉 分析完成！12 个智能体协同工作，总耗时 {total_lat:.0f}ms")
            st.info("👆 点击上方 **学习画像** 和 **学习空间** 标签查看详细结果")

        elif not st.session_state.workflow_result:
            st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-header">🔬 核心技术</div>', unsafe_allow_html=True)
            landing_items = [
                ("🧠 多智能体协同", "12 个专用 Agent 通过 EventBus + Memory 协作, 非单一 LLM 调用"),
                ("👤 自然语言画像", "6 维学习画像自动提取 · LLM + 规则双模式 · 带置信度"),
                ("🗺️ 个性化路径", "知识库驱动 · 画像动态调整深度/策略"),
                ("🎨 资源推荐", "5 类个性化资源 · 基于知识缺口的精准推送"),
                ("📊 可信评估", "统一 ReviewGate 评分 · Post-Execution Reflection"),
                ("🚀 讯飞星火", "Xunfei Spark 大模型核心推理 · 多模型兼容 · 规则 fallback"),
            ]
            for icon_title, desc in landing_items:
                st.markdown(f"**{icon_title}** — {desc}")

    # ═══════════════════════════════════════════════
    # ═══════════════  TAB 2: PROFILE  ═════════════
    # ═══════════════════════════════════════════════

    with tab2:
        st.markdown('<div class="hero-title" style="font-size:2em;">👤 个人学习画像</div>', unsafe_allow_html=True)

        result_dict = st.session_state.workflow_result
        if not result_dict:
            st.info("👈 请先在 **学习助手** 页面输入学习目标并点击「开始分析」")
        else:
            dims = _get_profile_dims(result_dict)
            source, confidence = _get_profile_source_conf(result_dict)

            source_badge = {
                "llm": "🤖 讯飞星火分析", "rule": "📏 规则引擎",
                "rule+memory": "🧠 规则+记忆", "preset": "⚙️ 预置画像",
            }.get(source, source)
            c1, c2, c3 = st.columns(3)
            c1.metric("分析引擎", source_badge)
            c2.metric("置信度", f"{confidence:.0%}")
            c3.metric("输入来源", "自然语言对话")

            st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

            radar_col, cards_col = st.columns([2, 3])
            with radar_col:
                st.markdown('<div class="section-header">📐 六维雷达图</div>', unsafe_allow_html=True)
                values = _radar_values(dims)
                labels_cn = {
                    "knowledge_base": "知识基础", "cognitive_style": "认知风格",
                    "error_prone_bias": "易错倾向", "learning_pace": "学习节奏",
                    "interaction_preference": "交互偏好", "frustration_threshold": "抗挫能力",
                }
                chart_data = {"维度": list(labels_cn.values()), "得分": list(values.values())}
                st.bar_chart(chart_data, x="维度", y="得分", height=280)

            with cards_col:
                st.markdown('<div class="section-header">📋 维度详情</div>', unsafe_allow_html=True)
                dim_config = {
                    "knowledge_base": ("📚 知识基础", {"junior_dev": "初级开发", "mid_level": "中级水平", "senior": "高级资深"}),
                    "cognitive_style": ("🧠 认知风格", {"visual_dominant": "视觉主导", "text_linear": "文本线性", "auditory": "听觉偏好"}),
                    "error_prone_bias": ("⚠️ 易错倾向", {"magic_syntax_blind": "语法糖盲区", "indentation_errors": "缩进错误", "variable_scoping": "作用域混淆", "type_mismatch": "类型不匹配", "import_issues": "导入问题"}),
                    "learning_pace": ("⚡ 学习节奏", {"fast_track": "快速通道", "normal": "标准节奏", "deep_dive": "深度钻研"}),
                    "interaction_preference": ("🖐️ 交互偏好", {"code_sandbox": "代码实战", "quiz_first": "测验优先", "passive_read": "阅读为主"}),
                    "frustration_threshold": ("🛡️ 抗挫能力", {"low": "容易受挫", "medium": "中等承受", "high": "抗压性强"}),
                }
                sub_cols = st.columns(3)
                for i, (key, (label, val_map)) in enumerate(dim_config.items()):
                    value = dims.get(key, "unknown")
                    display = val_map.get(str(value), str(value))
                    with sub_cols[i % 3]:
                        st.markdown(f"""
                        <div class="profile-card">
                            <div class="profile-card-label">{label}</div>
                            <div class="profile-card-value">{display}</div>
                            <div class="profile-card-dim">原始值: {value}</div>
                        </div>
                        """, unsafe_allow_html=True)

            with st.expander("🔍 原始数据"):
                st.json(dims)

            refl = result_dict.get("reflection") or {}
            if refl:
                st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
                st.markdown('<div class="section-header">🔍 学习反思</div>', unsafe_allow_html=True)
                st.info(refl.get("summary", str(refl)) if isinstance(refl, dict) else str(refl))

    # ═══════════════════════════════════════════════
    # ═══════════════  TAB 3: LEARNING SPACE  ══════
    # ═══════════════════════════════════════════════

    with tab3:
        st.markdown('<div class="hero-title" style="font-size:2em;">📚 个性化学习空间</div>', unsafe_allow_html=True)

        result_dict = st.session_state.workflow_result
        if not result_dict:
            st.info("👈 请先在 **学习助手** 页面输入学习目标并点击「开始分析」")
        else:
            plan = result_dict.get("learning_plan") or {}
            nodes = plan.get("nodes", [])
            resources = result_dict.get("resources") or []

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("学习节点", f"{len(nodes)} 个")
            c2.metric("总时长", f"{plan.get('total_minutes', 0)} 分钟")
            c3.metric("画像策略", plan.get("profile_summary", "-")[:15])
            c4.metric("记忆保存", "✅ 已持久化" if result_dict.get("memory_saved") else "❌ 未保存")

            st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-header">🗺️ 学习路径</div>', unsafe_allow_html=True)

            if not nodes:
                st.caption("暂未生成学习路径")
            else:
                for i, node in enumerate(nodes):
                    depth = node.get("depth", 1)
                    depth_icons = {1: "🟢 入门", 2: "🟡 进阶", 3: "🔴 深入"}.get(depth, "⚪")
                    st.markdown(f"""
                    <div class="node-card">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <div class="node-level">L{i+1:02d}</div>
                            <div style="flex:1;">
                                <div class="node-title">{node.get('title', '?')}</div>
                                <div class="node-concept">{node.get('core_concept', '')[:100]}</div>
                                <div class="node-meta">{depth_icons} · {node.get('exercise_count', 0)} 练习题 · {node.get('estimated_minutes', 0)} 分钟 · 策略: {node.get('teaching_strategy', 'standard')}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if i < len(nodes) - 1:
                        st.markdown('<div class="node-arrow">↓</div>', unsafe_allow_html=True)

            st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-header">🎨 推荐资源</div>', unsafe_allow_html=True)
            _render_resource_cards(resources)

            ev = result_dict.get("evaluation") or {}
            if ev:
                st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
                st.markdown('<div class="section-header">📊 质量评估</div>', unsafe_allow_html=True)
                sc1, sc2 = st.columns(2)
                sc1.metric("评分", f"{ev.get('score', 0)}/100")
                sc2.metric("状态", "✅ 通过" if ev.get("passed") else "❌ 未通过")

            _render_trust_panel(result_dict)
            _render_timeline(result_dict.get("trace") or [])

            st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
            st.caption(
                f"🚀 流水线总耗时: {result_dict.get('total_duration_ms', 0):.0f}ms · "
                f"路径: {len(nodes)} 节点 · "
                f"资源: {len(resources)} 项 · "
                f"状态: {'成功' if result_dict.get('success') else '有错误'}"
            )


# ── Entry points ──────────────────────────────

if __name__ == "__main__":
    main()
