"""Dashboard V2 — Streamlit Rendering Components

Six pure rendering functions. Each takes a plain data dict and renders
one dashboard panel. Zero business logic — data transformation is in
data_providers.py.

Usage:
    from web.dashboard.components import render_system_overview
    render_system_overview(data)
"""

from __future__ import annotations

# All rendering functions expect `st` to be imported by the caller.
# We accept it as a module-like object for testability.


def render_system_overview(data: dict, st) -> None:
    """Panel 1: Agent topology + active agents + memory/trace/eval status."""

    st.header("🏗️ System Overview")
    st.caption("Agent 拓扑 · 实时状态 · 存储统计")

    topology = data.get("topology", {})
    memory = data.get("memory", {})
    evaluation = data.get("evaluation", {})
    agents = data.get("agents", [])

    # ── Top row: status cards ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🤖 总 Agent", topology.get("total_agents", 0),
              f"{topology.get('active_agents', 0)} active")
    c2.metric("🧠 学生记忆", memory.get("student_count", 0),
              f"{memory.get('trace_count', 0)} traces")
    c3.metric("📊 评估次数", evaluation.get("total_evaluations", 0),
              f"avg {evaluation.get('avg_score', 0):.0%}")
    c4.metric("📖 经验库", memory.get("experience_count", 0), "lessons")

    st.divider()

    # ── Agent table ──
    st.subheader("Agent Topology")

    # Header
    h1, h2, h3, h4, h5 = st.columns([3, 2, 1.5, 1.5, 1])
    h1.caption("**Agent**")
    h2.caption("**Status**")
    h3.caption("**Traces**")
    h4.caption("**Avg Latency**")
    h5.caption("**Errors**")

    for agent in agents:
        r1, r2, r3, r4, r5 = st.columns([3, 2, 1.5, 1.5, 1])
        r1.markdown(f"`{agent['name']}`")
        r2.markdown(agent.get("status", "⚪ idle"))
        r3.markdown(str(agent.get("trace_count", 0)))
        r4.markdown(f"{agent.get('avg_latency', 0):.0f}ms")
        error_count = agent.get("errors", 0)
        if error_count > 0:
            r5.markdown(f"🔴 {error_count}")
        else:
            r5.markdown("✅ 0")

    # ── Trace status mini-bar ──
    total_traces = memory.get("trace_count", 0)
    if total_traces > 0:
        st.caption(f"📈 共追踪 {total_traces} 个 Agent 执行事件")


# ═══════════════════════════════════════════════════

def render_student_intelligence(data: dict, st) -> None:
    """Panel 2: Six-dim DynamicProfile + mastery_map + weak_points + preferences."""

    st.header("🎯 Student Intelligence Dashboard")
    st.caption("六维画像 · 掌握度热力图 · 弱点分析 · 学习偏好")

    profile = data.get("profile", {})
    mastery_map: dict = data.get("mastery_map", {})
    weak_points: list = data.get("weak_points", [])
    prefs = data.get("learning_preferences", {})
    summary = data.get("learning_summary", {})
    student_id = data.get("student_id", "demo_student")

    # ── Student identity ──
    st.metric("👤 Student ID", student_id,
              f"{data.get('interaction_count', 0)} interactions | avg {data.get('avg_score', 0)}")

    st.divider()

    # ── Six-dim profile cards ──
    st.subheader("📊 六维 DynamicProfile")

    dim_labels = {
        "knowledge_base": "知识基础",
        "cognitive_style": "认知风格",
        "error_prone_bias": "易错倾向",
        "learning_pace": "学习节奏",
        "interaction_preference": "交互偏好",
        "frustration_threshold": "抗挫能力",
    }
    dim_emoji = {
        "knowledge_base": {"junior_dev": "🔰", "mid_level": "📗", "senior": "🎖️"},
        "cognitive_style": {"visual_dominant": "👁️", "text_linear": "📖", "auditory": "👂"},
        "error_prone_bias": {"magic_syntax_blind": "🔮", "indentation_errors": "📐", "variable_scoping": "🔍", "type_mismatch": "🔢", "import_issues": "📦"},
        "learning_pace": {"fast_track": "⚡", "normal": "🚶", "deep_dive": "🔬"},
        "interaction_preference": {"code_sandbox": "💻", "quiz_first": "📝", "passive_read": "📚"},
        "frustration_threshold": {"low": "🫣", "medium": "😐", "high": "😤"},
    }

    dim_keys = list(dim_labels.keys())
    cols = st.columns(len(dim_keys))
    for i, key in enumerate(dim_keys):
        val = profile.get(key, "N/A")
        emoji = dim_emoji.get(key, {}).get(val, "❓")
        label = dim_labels.get(key, key)
        with cols[i]:
            st.metric(label, f"{emoji} {val}")

    st.divider()

    # ── Mastery heatmap ──
    st.subheader("🔥 掌握度热力图 (Mastery Map)")

    if mastery_map:
        sorted_items = sorted(mastery_map.items(), key=lambda x: x[1])
        for concept, score in sorted_items:
            if score >= 0.8:
                color = "green"
                icon = "🟢"
            elif score >= 0.5:
                color = "blue"
                icon = "🔵"
            elif score >= 0.3:
                color = "orange"
                icon = "🟠"
            else:
                color = "red"
                icon = "🔴"

            c1, c2 = st.columns([1, 4])
            c1.caption(concept)
            c2.progress(score, text=f"{icon} {score:.0%}")

    else:
        st.info("暂无掌握度数据")

    st.divider()

    # ── Weak points + Learning preferences ──
    c_left, c_right = st.columns(2)

    with c_left:
        st.subheader("⚠️ 学习弱点")
        if weak_points:
            for wp in weak_points[:5]:
                concept = wp.get("concept", "")
                count = wp.get("occurrence_count", 0)
                error_type = wp.get("error_type", "")
                st.markdown(
                    f"- **{concept}** ({error_type}) — 出现 {count} 次"
                )
        else:
            st.caption("(暂无弱点)")

    with c_right:
        st.subheader("🎨 学习偏好")
        prefs_display = {
            "认知风格": prefs.get("preferred_style", "N/A"),
            "学习节奏": prefs.get("avg_pace", "N/A"),
            "抗挫模式": prefs.get("frustration_pattern", "N/A"),
        }
        for label, val in prefs_display.items():
            st.markdown(f"- **{label}**: {val}")

    # ── Summary stats ──
    if summary:
        with st.expander("📋 学习摘要", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("总交互", summary.get("total_interactions", 0))
            c2.metric("平均分", summary.get("avg_score", 0))
            c3.metric("会话数", summary.get("total_sessions", 0))


# ═══════════════════════════════════════════════════

def render_execution_timeline(data: dict, st) -> None:
    """Panel 3: timestamp + agent_name + action + reasoning_type + latency + status."""

    st.header("📜 Agent Execution Timeline")
    st.caption("按时间排列的 Agent 执行追踪 — 推理类型 · 延迟 · 状态")

    events: list = data.get("events", [])
    stats = data.get("stats", {})

    # ── Stats row ──
    c1, c2, c3 = st.columns(3)
    c1.metric("📊 总事件", stats.get("total", 0))
    c2.metric("⚡ 平均延迟", f"{stats.get('avg_latency', 0):.0f}ms")
    c3.metric("🤖 Agent 数", len(stats.get("by_agent", {})))

    # ── Agent filter chips ──
    by_agent = stats.get("by_agent", {})
    if by_agent:
        agent_labels = [f"{a} ({c})" for a, c in sorted(by_agent.items())]
        st.caption(" | ".join(agent_labels))

    st.divider()

    # ── Timeline table ──
    if not events:
        st.info("暂无执行事件")
        return

    # Header
    h1, h2, h3, h4, h5, h6 = st.columns([2.5, 2, 2, 1.5, 1, 1])
    h1.caption("**Timestamp**")
    h2.caption("**Agent**")
    h3.caption("**Action**")
    h4.caption("**Reasoning**")
    h5.caption("**Latency**")
    h6.caption("**Status**")

    reasoning_colors = {
        "rule": "🟦", "heuristic": "🟩", "llm": "🟪",
        "memory": "🟧", "hybrid": "🟥",
    }

    for evt in events:
        ts = evt.get("timestamp", "")
        # Show only time portion
        if "T" in ts:
            ts_display = ts.split("T")[1][:12]
        else:
            ts_display = ts[:12]

        agent = evt.get("agent", "")
        action = evt.get("action", "")
        rtype = evt.get("reasoning_type", "heuristic")
        rtype_icon = reasoning_colors.get(rtype, "⬜")
        latency = evt.get("latency_ms", 0)
        status = evt.get("status", "success")
        status_icon = "✅" if status == "success" else "❌"

        r1, r2, r3, r4, r5, r6 = st.columns([2.5, 2, 2, 1.5, 1, 1])
        r1.caption(f"`{ts_display}`")
        r2.markdown(f"**{agent}**")
        r3.caption(f"`{action}`")
        r4.caption(f"{rtype_icon} {rtype}")
        r5.caption(f"{latency:.0f}ms")
        r6.markdown(status_icon)

    # ── Expandable detail ──
    with st.expander("查看事件详情", expanded=False):
        for evt in events:
            inp = evt.get("input_summary", "")
            out = evt.get("output_summary", "")
            if inp or out:
                st.markdown(
                    f"`{evt['agent']}` → `{evt['action']}`  \n"
                    f"  ↳ in: {inp}  \n"
                    f"  ↳ out: {out}"
                )


# ═══════════════════════════════════════════════════

def render_explainability_panel(data: dict, st) -> None:
    """Panel 4: decision + evidence + reason + confidence."""

    st.header("🔮 Decision Explainability Panel")
    st.caption("每个 Agent 决策的可解释性 — 证据链 · 置信度 · 备选方案")

    explanations: list = data.get("explanations", [])
    total = data.get("total_decisions", 0)
    avg_conf = data.get("avg_confidence", 0)

    c1, c2 = st.columns(2)
    c1.metric("📊 总决策数", total)
    c2.metric("🎯 平均置信度", f"{avg_conf:.0%}")

    st.divider()

    if not explanations:
        st.info("暂无决策解释")
        return

    for exp in explanations:
        agent = exp.get("agent", "")
        action = exp.get("action", "")
        decision = exp.get("decision", "")
        reason = exp.get("reason", "")
        confidence = exp.get("confidence", 0)
        evidence: list = exp.get("evidence", [])
        alternative = exp.get("alternative", "")

        # Confidence color
        if confidence >= 0.9:
            conf_color = "🟢"
        elif confidence >= 0.7:
            conf_color = "🟡"
        else:
            conf_color = "🔴"

        with st.container(border=True):
            c_title, c_conf = st.columns([4, 1])
            c_title.markdown(f"**{agent}** → `{action}`")
            c_conf.markdown(f"{conf_color} **{confidence:.0%}**")

            st.markdown(f"> **决策**: {decision}")
            st.markdown(f"> **理由**: {reason}")

            if evidence:
                st.caption(f"📎 证据: {' | '.join(evidence)}")

            if alternative:
                st.caption(f"🔄 备选: {alternative}")

    # ── Confidence distribution ──
    with st.expander("信心分布", expanded=False):
        if explanations:
            bins = {"高 (>0.9)": 0, "中 (0.7-0.9)": 0, "低 (<0.7)": 0}
            for e in explanations:
                c = e.get("confidence", 0)
                if c >= 0.9:
                    bins["高 (>0.9)"] += 1
                elif c >= 0.7:
                    bins["中 (0.7-0.9)"] += 1
                else:
                    bins["低 (<0.7)"] += 1

            cols = st.columns(3)
            for i, (label, count) in enumerate(bins.items()):
                pct = count / max(len(explanations), 1)
                cols[i].metric(label, count, f"{pct:.0%}")


# ═══════════════════════════════════════════════════

def render_evaluation_dashboard(data: dict, st) -> None:
    """Panel 5: Per-agent correctness/personalization/explainability/efficiency + overall."""

    st.header("📊 Agent Evaluation Dashboard")
    st.caption("四维评分: 正确性 · 个性化 · 可解释性 · 效率")

    agents: list = data.get("agents", [])
    avg_overall = data.get("avg_overall", 0)
    total = data.get("total_evaluations", 0)

    st.metric("📊 总体评分", f"{avg_overall:.0%}", f"{total} evaluations")

    st.divider()

    if not agents:
        st.info("暂无评估数据")
        return

    for agent in agents:
        name = agent.get("name", "")
        overall = agent.get("overall", 0)
        correctness = agent.get("correctness", 0)
        personalization = agent.get("personalization", 0)
        explainability = agent.get("explainability", 0)
        efficiency = agent.get("efficiency", 0)
        suggestions: list = agent.get("suggestions", [])

        # Overall color
        if overall >= 0.85:
            overall_color = "🟢"
        elif overall >= 0.6:
            overall_color = "🟡"
        else:
            overall_color = "🔴"

        with st.container(border=True):
            c_name, c_overall = st.columns([3, 1])
            c_name.markdown(f"### {name}")
            c_overall.metric("Overall", f"{overall_color} {overall:.0%}")

            # 4-dim bar chart
            dims = [
                ("正确性", correctness),
                ("个性化", personalization),
                ("可解释性", explainability),
                ("效率", efficiency),
            ]
            cols = st.columns(4)
            for i, (label, score) in enumerate(dims):
                with cols[i]:
                    st.metric(label, f"{score:.0%}")
                    st.progress(score)

            # Radar-like compact view
            st.caption(
                f"正确性 {'█'*int(correctness*10)}{'░'*(10-int(correctness*10))} {correctness:.0%}  "
                f"个性化 {'█'*int(personalization*10)}{'░'*(10-int(personalization*10))} {personalization:.0%}  "
                f"可解释性 {'█'*int(explainability*10)}{'░'*(10-int(explainability*10))} {explainability:.0%}  "
                f"效率 {'█'*int(efficiency*10)}{'░'*(10-int(efficiency*10))} {efficiency:.0%}"
            )

            if suggestions:
                st.caption("💡 " + " | ".join(suggestions))

    # ── Summary table ──
    with st.expander("评分矩阵", expanded=False):
        if agents:
            # Header
            cols = st.columns([2, 1, 1, 1, 1, 1])
            for i, h in enumerate(["Agent", "Correct", "Personal", "Explain", "Efficiency", "Overall"]):
                cols[i].caption(f"**{h}**")

            for agent in agents:
                cols = st.columns([2, 1, 1, 1, 1, 1])
                cols[0].markdown(f"`{agent['name']}`")
                cols[1].markdown(f"{agent['correctness']:.0%}")
                cols[2].markdown(f"{agent['personalization']:.0%}")
                cols[3].markdown(f"{agent['explainability']:.0%}")
                cols[4].markdown(f"{agent['efficiency']:.0%}")
                cols[5].markdown(f"**{agent['overall']:.0%}**")


# ═══════════════════════════════════════════════════

def render_improvement_timeline(data: dict, st) -> None:
    """Panel 6: failure → evaluation → reflection → experience → future strategy."""

    st.header("🔄 Self-Improvement Timeline")
    st.caption("闭环改进流程: 失败 → 评估 → 反思 → 经验累积 → 策略更新")

    timeline: list = data.get("timeline", [])
    pending = data.get("pending_suggestions", 0)
    exp_count = data.get("experience_count", 0)

    c1, c2 = st.columns(2)
    c1.metric("⏳ 待处理建议", pending)
    c2.metric("📖 经验库大小", exp_count)

    st.divider()

    if not timeline:
        st.info("暂无改进记录")
        return

    # ── Stage icons ──
    stage_config = {
        "failure": {"icon": "❌", "label": "Failure", "color": "red"},
        "evaluation": {"icon": "📊", "label": "Evaluation", "color": "orange"},
        "reflection": {"icon": "🔍", "label": "Reflection", "color": "blue"},
        "meta_reflection": {"icon": "🧠", "label": "Meta Reflection", "color": "purple"},
        "experience_memory": {"icon": "💾", "label": "Experience Memory", "color": "green"},
        "future_strategy": {"icon": "🚀", "label": "Future Strategy", "color": "violet"},
    }

    for i, item in enumerate(timeline):
        stage = item.get("stage", "unknown")
        config = stage_config.get(stage, {"icon": "⬜", "label": stage, "color": "gray"})

        # Vertical chain connector
        if i > 0:
            st.markdown(
                '<div style="text-align:center; color: gray; font-size: 20px;">⬇️</div>',
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            c_icon, c_content = st.columns([0.5, 5])
            c_icon.markdown(f"### {config['icon']}")
            c_content.markdown(f"**{config['label']}** — `{item.get('agent', '')}`")

            content = item.get("content", "")
            solution = item.get("solution", "")
            severity = item.get("severity", "")

            sev_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "")

            st.markdown(f"> {content}")
            if solution:
                st.caption(f"💡 **Solution**: {solution}")
            if severity:
                st.caption(f"{sev_icon} Severity: {severity}")

    # ── Legend ──
    with st.expander("流程说明", expanded=False):
        st.markdown("""
        ```
        ❌ FAILURE        → Agent 输出不达标
               ↓
        📊 EVALUATION     → AgentEvaluator 四维评分
               ↓
        🔍 REFLECTION     → MetaReflector 根因分析 + 改进方案
               ↓
        💾 EXPERIENCE     → 写入 ExperienceMemory 经验库
               ↓
        🚀 STRATEGY       → 下一轮自动注入优化策略
        ```
        """)


def render_trust_safety_panel(data: dict, st) -> None:
    """Panel 7: Trust & Safety — grounding, evaluation, review, hallucination."""

    st.header("🛡️ AI Trust & Safety")
    st.caption("Knowledge grounding · Evaluation · Hallucination control")

    grounding = data.get("grounding", {})
    evaluation = data.get("evaluation", {})
    review_gate = data.get("review_gate", {})
    hallucination = data.get("hallucination", {})

    # Row 1: Grounding + Evaluation
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📚 Knowledge Grounding")
        st.metric("Source", grounding.get("source", "KB")[:40])
        covered = grounding.get("covered", 0)
        total = grounding.get("total", 1)
        st.metric("Coverage", f"{covered}/{total} concepts")
        st.progress(
            grounding.get("confidence", 0.92),
            text=f"Confidence: {grounding.get('confidence', 0.92):.0%}"
        )

    with c2:
        st.subheader("📊 Evaluation Score")
        dims = evaluation.get("dimensions", {})
        for dim, score in dims.items():
            st.progress(score, text=f"{dim}: {score:.0%}")

    # Row 2: ReviewGate
    st.divider()
    st.subheader("🚪 ReviewGate Status")
    gates = review_gate.get("gates", [])
    gate_cols = st.columns(len(gates) if gates else 3)
    for i, gate in enumerate(gates):
        with gate_cols[i]:
            status = gate.get("status", "PASS")
            emoji = "✅" if status == "PASS" else "❌"
            st.markdown(f"### {emoji}")
            st.caption(f"**Gate {i+1}:** {gate.get('name', '')}")
            st.caption(gate.get("detail", ""))

    # Row 3: Hallucination check
    st.divider()
    st.subheader("🔍 Hallucination Control")
    items = hallucination.get("items", [])
    for item in items:
        icon = "✅" if item.get("status") == "pass" else "⚠️"
        st.markdown(f"{icon} {item.get('text', '')}")

    # Fallback status
    fb = hallucination.get("fallback", {})
    with st.expander("Fallback Status", expanded=False):
        st.caption(f"Available: {fb.get('available', True)}")
        st.caption(f"Active: {fb.get('active', False)}")
        st.caption(f"Reason: {fb.get('reason', 'N/A')}")


# ═══════════════════════════════════════════════════

def render_goal_progress(data: dict, st) -> None:
    """Panel 8: Phase 8.3-D2 — Long-term learning goal progress.

    Shows goal target, category, milestone completion,
    deadline urgency, and pending concepts.
    """
    st.header("🎯 Goal Progress")
    st.caption("长期学习目标追踪 — 里程碑进度 · 截止日期 · 待掌握概念")

    has_goal = data.get("has_goal", False)

    if not has_goal:
        st.info("📚 尚未设定长期学习目标。去设定一个目标吧！")
        with st.expander("💡 示例目标", expanded=False):
            st.markdown("""
            - 💼 **职业**: 成为 Python 后端工程师
            - 📝 **考试**: 通过 PCEP Python 认证
            - 🎯 **技能**: 掌握 Multi-Agent AI 系统开发
            - 🚀 **项目**: 构建智能客服系统
            """)
        return

    category_icon = data.get("category_icon", "📚")
    target = data.get("target", "")
    category = data.get("category", "general")
    target_level = data.get("target_level", "beginner")
    progress = data.get("progress", 0.0)
    completed_ms = data.get("completed_milestones", 0)
    total_ms = data.get("total_milestones", 0)
    deadline = data.get("deadline", "")
    days_remaining = data.get("days_remaining", None)
    is_overdue = data.get("is_overdue", False)
    next_ms = data.get("next_milestone", "")
    pending_concepts = data.get("pending_concepts", [])
    milestones = data.get("milestones", [])

    # ── Top row: Goal identity + Progress ──
    c1, c2, c3 = st.columns([3, 2, 1])

    with c1:
        st.markdown(f"### {category_icon} {target}")
        st.caption(f"类型: {category} | 目标水平: {target_level}")

    with c2:
        progress_color = "red" if is_overdue else "normal"
        st.metric(
            "📊 总体进度",
            f"{progress:.0%}",
            f"{completed_ms}/{total_ms} 里程碑",
        )
        # Overdue badge
        if is_overdue:
            st.error("⚠️ 已逾期!")

    with c3:
        if deadline:
            urgency_label = (
                "🔴 紧急" if is_overdue or (days_remaining is not None and days_remaining <= 3)
                else "🟡 注意" if days_remaining is not None and days_remaining <= 14
                else "🟢 充裕"
            )
            st.metric(
                "⏰ 截止日期",
                deadline[:10] if len(deadline) >= 10 else deadline,
                f"{days_remaining} 天后" if days_remaining is not None else "",
            )
            st.caption(urgency_label)

    st.divider()

    # ── Progress bar ──
    st.progress(progress, text=f"完成度: {progress:.0%} ({completed_ms}/{total_ms})")

    # ── Next milestone ──
    if next_ms:
        st.info(f"📍 **下一步**: {next_ms}")

    # ── Pending concepts ──
    if pending_concepts:
        st.caption(
            "📋 待掌握概念: "
            + " · ".join(pending_concepts[:8])
            + (f" ... (+{len(pending_concepts) - 8})" if len(pending_concepts) > 8 else "")
        )

    st.divider()

    # ── Milestone Timeline ──
    st.subheader("🗺️ 里程碑路线")

    for i, ms in enumerate(milestones):
        icon = ms.get("icon", "⏳")
        title = ms.get("title", f"Milestone {i + 1}")
        description = ms.get("description", "")
        completed = ms.get("completed", False)
        concepts = ms.get("target_concepts", [])
        est_days = ms.get("estimated_days", 0)
        completed_at = ms.get("completed_at", "")

        bg_color = "#e8f5e9" if completed else "#f5f5f5"
        border_color = "#4caf50" if completed else "#e0e0e0"

        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"{icon} **{title}**")
            c2.caption(f"⏱️ ~{est_days}天")

            if description:
                st.caption(description)

            if concepts:
                st.caption(f"📋 概念: {' · '.join(concepts)}")

            if completed and completed_at:
                st.caption(f"✅ 完成于: {completed_at}")

    # ── Summary ──
    st.divider()
    if progress >= 1.0:
        st.success(f"🎉 恭喜！你已完成 {target} 目标！")
    elif progress >= 0.5:
        st.info(f"💪 已完成过半 — {target} 指日可待！")
    else:
        st.caption(f"🚀 {target} — 继续加油！每天进步一点点。")
