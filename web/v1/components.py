"""V1 Components — 5 Panel Streamlit Renderers.

Extracted from web/app.py (refactor — no behavior changes).

Each render_*() function takes a `st` module and data dicts.
Zero business logic — pure rendering.

Usage:
    from web.v1.components import (
        render_profile_completeness, render_dynamic_profile,
        render_learning_path, render_resource_cards, render_agent_trace,
    )
"""

from __future__ import annotations
from typing import Any, Dict, List


# ═══════════════════════════════════════════════════
# Panel 1: Profile Completeness
# ═══════════════════════════════════════════════════

def render_profile_completeness(
    profile_data: Dict[str, str],
    result: Any,
    agents: Dict[str, Any],
    st: Any,
) -> None:
    """Panel 1: 画像采集进度 (Completeness bar + filled/missing dimensions)."""
    from agents.profile_agent import ProfileAgent  # noqa: F811

    st.header("📊 Panel 1: 画像采集进度")

    defaults = ProfileAgent.DEFAULTS
    filled = sum(1 for k, v in profile_data.items() if v != defaults.get(k))
    total = len(defaults)
    pct = filled / total

    cols = st.columns([2, 1])
    with cols[0]:
        st.progress(pct, text=f"画像完整度: {filled}/{total} ({pct:.0%})")
    with cols[1]:
        st.metric("置信度", f"{result.confidence:.0%}")

    # 已获得 vs 待补充
    col_a, col_b = st.columns(2)
    dim_labels_cn = {
        "knowledge_base": "知识基础",
        "cognitive_style": "认知风格",
        "error_prone_bias": "易错倾向",
        "learning_pace": "学习节奏",
        "interaction_preference": "交互偏好",
        "frustration_threshold": "抗挫能力",
    }
    with col_a:
        st.caption("✅ 已获得")
        for dim, label in dim_labels_cn.items():
            v = profile_data.get(dim, "")
            if v and v != defaults.get(dim):
                st.markdown(f"- ✓ {label}: {v}")
    with col_b:
        st.caption("○ 待补充")
        for dim, label in dim_labels_cn.items():
            v = profile_data.get(dim, "")
            if not v or v == defaults.get(dim):
                st.markdown(f"- ○ {label}")


# ═══════════════════════════════════════════════════
# Panel 2: Dynamic Profile Cards
# ═══════════════════════════════════════════════════

def render_dynamic_profile(
    profile_data: Dict[str, str],
    result: Any,
    st: Any,
) -> None:
    """Panel 2: 动态画像 (6-column metric cards with emoji)."""
    st.header("📊 Panel 2: 动态画像")

    emoji_map = {
        "knowledge_base": {"junior_dev": "🔰", "mid_level": "📗", "senior": "🎖️"},
        "cognitive_style": {"visual_dominant": "👁️", "text_linear": "📖", "auditory": "👂"},
        "error_prone_bias": {"magic_syntax_blind": "🔮", "indentation_errors": "📐", "variable_scoping": "🔍", "type_mismatch": "🔢", "import_issues": "📦"},
        "learning_pace": {"fast_track": "⚡", "normal": "🚶", "deep_dive": "🔬"},
        "interaction_preference": {"code_sandbox": "💻", "quiz_first": "📝", "passive_read": "📚"},
        "frustration_threshold": {"low": "🫣", "medium": "😐", "high": "😤"},
    }
    dim_labels_cn = {
        "knowledge_base": "知识基础",
        "cognitive_style": "认知风格",
        "error_prone_bias": "易错倾向",
        "learning_pace": "学习节奏",
        "interaction_preference": "交互偏好",
        "frustration_threshold": "抗挫能力",
    }

    col_labels = list(profile_data.keys())
    cols = st.columns(len(col_labels))
    for i, key in enumerate(col_labels):
        val = profile_data.get(key, "")
        emoji = emoji_map.get(key, {}).get(val, "❓")
        cols[i].metric(dim_labels_cn.get(key, key), f"{emoji} {val}")

    st.caption(f"来源: {result.source} | 关键词: {', '.join(result.raw_keywords[:5])}")


# ═══════════════════════════════════════════════════
# Panel 3: Learning Path Visualization
# ═══════════════════════════════════════════════════

def render_learning_path(
    plan: Any,
    mastery: Dict[str, float],
    st: Any,
) -> None:
    """Panel 3: 学习路径可视化 (nodes with status + mastery coloring)."""
    st.header("🗺️ Panel 3: 学习路径")

    st.info(plan.strategy_rationale)

    for i, node in enumerate(plan.nodes):
        m = mastery.get(node.node_id, -1)
        if m >= 0.8:
            status = "✅ completed"
            status_color = "green"
        elif 0 < m < 0.3:
            status = "⚠️ weak"
            status_color = "orange"
        elif i == 0:
            status = "▶️ next"
            status_color = "blue"
        else:
            status = "⬜ pending"
            status_color = "gray"

        cols = st.columns([1, 3, 1, 1, 1])
        cols[0].metric("", f"#{i + 1}")
        cols[1].markdown(f"**{node.title}**  \n_{node.core_concept[:40]}_")
        cols[2].metric("深度", "🟢" * node.depth)
        cols[3].metric("练习", f"{node.exercise_count}题")
        cols[4].markdown(f":{status_color}[{status}]")
        if node.notes:
            st.caption(f"  📝 {node.notes}")

    st.metric("📊 总时长", f"{plan.total_minutes}分钟", f"{len(plan.nodes)}节点")


# ═══════════════════════════════════════════════════
# Panel 4: Resource Recommendation Cards
# ═══════════════════════════════════════════════════

def render_resource_cards(
    resource_plan: Any,
    st: Any,
) -> None:
    """Panel 4: 推荐资源卡片 (resource type cards with priority)."""
    from agents.resource_recommendation_agent import RESOURCE_TYPES

    st.header("📦 Panel 4: 推荐资源")

    st.info(f"🎯 今日目标: **{resource_plan.today_goal}**")
    st.caption(resource_plan.reasoning)

    num_resources = len(resource_plan.recommended_resources)
    resource_cols = st.columns(min(num_resources, 3) or 1)
    for i, res in enumerate(resource_plan.recommended_resources):
        c = resource_cols[i % len(resource_cols)]
        with c:
            info = RESOURCE_TYPES.get(res.resource_type, {"icon": "📄", "label": res.resource_type})
            st.markdown(f"### {info['icon']} {res.title}")
            st.caption(f"**类型:** {info['label']} | **优先级:** {'⭐' * min(res.priority // 2, 5)}")
            st.caption(f"**原因:** {res.reason}")
            st.caption(f"**预计:** {res.estimated_minutes}分钟")


# ═══════════════════════════════════════════════════
# Panel 5: Agent Trace
# ═══════════════════════════════════════════════════

def render_agent_trace(
    events: List[Any],
    st: Any,
) -> None:
    """Panel 5: Agent Trace (EventBus timeline in expander)."""
    st.header("🔍 Panel 5: Agent Trace")

    with st.expander("查看执行时间线", expanded=False):
        if not events:
            st.caption("(无事件)")
        for evt in events:
            icon = "✅" if evt.status == "success" else "❌"
            st.markdown(
                f"`{evt.timestamp[11:19]}` {icon} **{evt.agent}** → `{evt.action}` "
                f"({evt.duration_ms:.0f}ms)"
            )
            if evt.input_summary:
                st.caption(f"  ↳ {evt.input_summary[:120]}")
            if evt.output_summary:
                st.caption(f"  ↳ {evt.output_summary[:120]}")


# ═══════════════════════════════════════════════════
# Panel 6: Multimodal Resource Cards
# ═══════════════════════════════════════════════════

def render_multimodal_cards(
    resources: Dict[str, Any],
    st: Any,
) -> None:
    """Panel 6: 多模态资源卡片 — document, mindmap, video, code.

    Displays rich resource cards with type-specific visual styling.
    Each card type has a distinct icon, color, and preview.

    Args:
        resources: Dict with resource types as keys:
            {"document": CourseNotes.to_dict(),
             "mindmap": MindMap.to_dict(),
             "video": VideoScript.to_dict(),
             "code": CodeLab.to_dict(),
             "exercise": Exercise.to_dict()}
    """
    st.header("🎨 多模态资源")

    if not resources:
        st.caption("(暂无多模态资源 — 运行 ResourceGenerationAgent 生成)")
        return

    # Resource type configurations
    MODAL_CONFIG = {
        "document":  {"icon": "📄", "color": "#2196F3", "label": "课程讲义", "preview": "内容预览"},
        "mindmap":   {"icon": "🧠", "color": "#9C27B0", "label": "思维导图", "preview": "结构预览"},
        "video":     {"icon": "🎬", "color": "#F44336", "label": "视频脚本", "preview": "场景概览"},
        "code":      {"icon": "💻", "color": "#4CAF50", "label": "代码实验", "preview": "代码预览"},
        "exercise":  {"icon": "✏️", "color": "#FF9800", "label": "练习题", "preview": "题目预览"},
        "extended_reading": {"icon": "📖", "color": "#795548", "label": "拓展阅读", "preview": "参考文献"},
    }

    # Layout: 2-3 cards per row
    resource_items = list(resources.items())
    cols_per_row = min(len(resource_items), 3) or 1

    for row_start in range(0, len(resource_items), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (rtype, data) in enumerate(resource_items[row_start:row_start + cols_per_row]):
            config = MODAL_CONFIG.get(rtype, MODAL_CONFIG["document"])
            with cols[j]:
                _render_single_multimodal_card(rtype, data, config, st)


def _render_single_multimodal_card(
    rtype: str,
    data: Dict[str, Any],
    config: Dict[str, str],
    st: Any,
) -> None:
    """Render a single multimodal resource card."""
    title = data.get("title", "Untitled")
    topic = data.get("topic", data.get("central_topic", ""))

    # Card container with colored border
    border_color = config["color"]
    st.markdown(f"""
    <div style="
        border: 2px solid {border_color};
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        background: linear-gradient(135deg, {border_color}08, {border_color}03);
    ">
        <div style="font-size: 2em; margin-bottom: 4px;">{config['icon']}</div>
        <div style="font-weight: bold; font-size: 1.1em; color: {border_color}; margin-bottom: 4px;">
            {config['label']}
        </div>
        <div style="font-weight: 600; margin-bottom: 4px;">{title}</div>
    """, unsafe_allow_html=True)

    if topic:
        st.caption(f"**主题:** {topic}")

    # Type-specific preview content
    with st.expander(f"{config['preview']}", expanded=False):
        if rtype == "document":
            sections = data.get("sections", [])
            for s in sections[:3]:
                st.markdown(f"**{s.get('heading', 'Section')}**")
                st.caption(s.get("content", "")[:200] + ("..." if len(s.get("content", "")) > 200 else ""))
            if "key_concepts" in data:
                st.caption(f"关键概念: {', '.join(data['key_concepts'][:5])}")

        elif rtype == "mindmap":
            mermaid = data.get("mermaid_code", "")
            if mermaid:
                st.code(mermaid, language="mermaid")
            branches = data.get("branches", [])
            for b in branches[:5]:
                st.caption(f"• {b.get('name', '')}")

        elif rtype == "video":
            st.metric("时长", f"{data.get('duration_seconds', 0) // 60}分{data.get('duration_seconds', 0) % 60}秒")
            scenes = data.get("scenes", [])
            for s in scenes[:3]:
                st.caption(f"🎞️ {s.get('title', '')} ({s.get('duration', '')})")

        elif rtype == "code":
            st.caption(f"**语言:** {data.get('language', 'python')}")
            starter = data.get("starter_code", "")
            if starter:
                st.code(starter, language=data.get("language", "python"))
            hints = data.get("hints", [])
            if hints:
                st.caption(f"💡 提示: {' | '.join(hints[:2])}")

        elif rtype == "exercise":
            questions = data.get("questions", [])
            st.metric("总分", f"{data.get('total_points', 0)}分")
            for q in questions[:3]:
                st.markdown(f"**{q.get('question', '')[:100]}...** ({q.get('points', 0)}分)")
                if q.get("type"):
                    st.caption(f"类型: {q['type']}")

        elif rtype == "extended_reading":
            references = data.get("references", [])
            st.caption(f"**{len(references)} 篇推荐阅读**")
            for ref in references[:3]:
                st.caption(f"📖 {ref.get('title', '')[:60]}")
                st.caption(f"   难度: {ref.get('difficulty', 'N/A')} | 来源: {ref.get('source', '')[:40]}")

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# Landing Page
# ═══════════════════════════════════════════════════

def render_landing(st: Any) -> None:
    """Render the landing page when no pipeline has been run."""
    st.info("👈 输入学生描述，点击「开始分析」")
    st.markdown("""
    ### 📐 架构
    ```
    Student → ProfileAgent → StudentMemory
    → PlannerAgent → ResourceRecommendationAgent
    → ContentAgent → ReviewGate → UserSim → FeedbackLoop
    ```
    """)


# ═══════════════════════════════════════════════════
# Pipeline Progress (Phase 14 — EventBus-driven)
# ═══════════════════════════════════════════════════

def render_pipeline_progress(events: list, st: Any) -> None:
    """Show real pipeline progress from EventBus timeline."""

    st.header("🔄 Generation Progress")
    st.caption("Real-time agent execution from EventBus")

    if not events:
        st.caption("(No events yet — run the pipeline first)")
        return

    pipeline_order = [
        "ProfileAgent", "PlannerAgent",
        "ResourceGenerationAgent", "AgentEvaluator",
        "MetaReflector",
    ]

    completed = 0
    for agent_name in pipeline_order:
        matching = [e for e in events if hasattr(e, "agent") and e.agent == agent_name]
        if matching:
            latest = matching[-1]
            status_icon = "✅" if getattr(latest, "status", "success") == "success" else "❌"
            output = getattr(latest, "output_summary", "")[:80]
            latency = getattr(latest, "duration_ms", 0)
            st.markdown(f"{status_icon} **{agent_name}** — {output} *({latency:.0f}ms)*")
            completed += 1
        else:
            st.markdown(f"⏳ {agent_name} — waiting...")

    pct = completed / max(len(pipeline_order), 1)
    st.progress(pct, text=f"{completed}/{len(pipeline_order)} agents completed")

    if completed > 0:
        total_ms = sum(
            getattr(e, "duration_ms", 0) for e in events
            if hasattr(e, "agent") and e.agent in pipeline_order
        )
        st.success(f"Pipeline complete: {completed} agents in {total_ms:.0f}ms")
