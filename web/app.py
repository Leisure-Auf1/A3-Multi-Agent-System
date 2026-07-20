"""
A3 AI Learning Assistant — Production UI (Phase 10.4-D)
=========================================================

Single entry point with onboarding → auth → 6-tab learning interface.

Tabs: Dashboard | Learning Pipeline | History | Workspace | Profile | Settings

All backend communication through FastAPI /api/v2/* via A3APIClient.
Zero direct src/ imports for pipeline operations.

Usage:
    streamlit run web/app.py
"""

from __future__ import annotations
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from web.utils.api import A3APIClient, A3APIError
from web.components.auth import render_auth_gate, render_logout
from web.components.chat import render_chat_sidebar, render_chat_main
from web.components.quiz_panel import render_quiz_panel


# ═══════════════════════════════════════════════
# Theme System
# ═══════════════════════════════════════════════

THEME_CSS = """
<style>
    /* A3 Dark Professional Theme */
    .stApp { background: #0d1117; }
    .stMetric { background: #161b22; border-radius: 8px; padding: 12px; border: 1px solid #30363d; }
    .stMetric label { color: #8b949e !important; font-size: 0.8rem; }
    .stMetric div[data-testid="stMetricValue"] { color: #58a6ff; font-size: 1.4rem; }
    .stButton > button { border-radius: 8px; font-weight: 500; transition: all 0.2s; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(88,166,255,0.3); }
    .stTextArea textarea { border-radius: 8px; border: 1px solid #30363d; background: #0d1117; }
    .stExpander { border: 1px solid #30363d; border-radius: 8px; }
    /* Progress bar */
    .stProgress > div > div { background: linear-gradient(90deg, #58a6ff, #3fb950); }
    /* Pipeline agent status */
    .agent-done { color: #3fb950; }
    .agent-running { color: #58a6ff; }
    .agent-waiting { color: #484f58; }
    .agent-error { color: #f85149; }
    /* Cards */
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin: 8px 0; }
    .card:hover { border-color: #58a6ff; }
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# Error Handler
# ═══════════════════════════════════════════════

def handle_api_error(e: A3APIError, context: str = "") -> None:
    """Consistent error display with recovery suggestions."""
    code = e.status
    detail = str(e.detail)[:200]

    if code == 401:
        st.error("🔒 Session expired. Please log in again.")
        if st.button("Go to Login"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
    elif code == 429:
        st.warning(f"⏳ Usage limit reached: {detail}")
        st.info("💡 Your daily token budget has been used. Try again tomorrow or upgrade your plan.")
    elif code == 422:
        st.warning(f"⚠️ Invalid input: {detail}")
    elif code >= 500:
        st.error(f"🛠️ Server error ({context}): {detail}")
        st.info("The AI backend encountered an issue. Please try again in a moment.")
        if st.button("🔄 Retry"):
            st.rerun()
    else:
        st.error(f"❌ Error ({context}): {detail}")


# ═══════════════════════════════════════════════
# Main Entry
# ═══════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="A3 AI Learning Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()

    # ── API Client ──
    if "api" not in st.session_state:
        st.session_state.api = A3APIClient()
    api: A3APIClient = st.session_state.api

    # ── Onboarding gate (first launch) ──
    if not st.session_state.get("_onboarded"):
        _render_onboarding_gate()
        if not st.session_state.get("_onboarded"):
            st.stop()

    # ── Auth Gate ──
    if not render_auth_gate(api):
        st.stop()

    # ── Session defaults ──
    for key, default in [
        ("active_tab", "dashboard"),
        ("learning_goal", ""),
        ("pipeline_result", None),
        ("pipeline_trace", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    user_id = st.session_state.get("user_id", "unknown")
    display_name = st.session_state.get("display_name", "User")

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(f"### 👤 {display_name}")
        st.caption(f"`{user_id[:12]}...`")

        # Phase 16.2-B: Active provider badge
        try:
            from src.config.llm_config import load_llm_config
            cfg = load_llm_config()
            if cfg.is_configured and cfg.provider not in ("mock", "rule"):
                provider_label = cfg.provider.title()
                st.success(f"🤖 **{provider_label}**")
                if cfg.model:
                    st.caption(f"`{cfg.model}`")
            else:
                st.info("🎭 **Demo Mode**")
                st.caption("No LLM configured")
        except Exception:
            st.info("🎭 **Demo Mode**")

        st.markdown("---")

        tabs = {
            "dashboard":  "🏠 Dashboard",
            "learning":   "🎓 Learning",
            "history":    "📜 History",
            "workspace":  "📂 Workspace",
            "profile":    "👤 Profile",
            "settings":   "⚙️ Settings",
        }
        for tab_key, tab_label in tabs.items():
            if st.button(
                tab_label,
                key=f"nav_{tab_key}",
                use_container_width=True,
                type="primary" if st.session_state.active_tab == tab_key else "secondary",
            ):
                st.session_state.active_tab = tab_key
                st.rerun()

        st.markdown("---")
        if st.session_state.active_tab == "chat":
            render_chat_sidebar(api)
        render_logout(api)

    # ── Tab Routing ──
    active = st.session_state.active_tab
    renderers = {
        "dashboard": _render_dashboard, "learning": _render_learning,
        "history": _render_history, "workspace": _render_workspace,
        "profile": _render_profile, "settings": _render_settings,
    }
    renderers.get(active, _render_dashboard)(api)


# ═══════════════════════════════════════════════
# Onboarding Gate
# ═══════════════════════════════════════════════

def _render_onboarding_gate() -> None:
    """Phase 16.2-B: Full onboarding page for first launch."""
    try:
        from web.onboarding_page import render_onboarding_page
        render_onboarding_page()
        if st.session_state.get("onboarding_done"):
            st.session_state._onboarded = True
    except Exception:
        # Fallback: minimal gate
        st.markdown("## 🤖 Welcome to A3 AI Learning Assistant")
        st.markdown("""
        Your personal AI tutor that understands **how** you learn.

        **What A3 does:**
        - 🧠 Analyzes your learning style from natural language
        - 🗺️ Builds personalized learning paths
        - 📚 Recommends resources matched to your profile
        - 📊 Tracks your progress and adapts
        """)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 Get Started", type="primary", use_container_width=True):
                st.session_state._onboarded = True
                st.rerun()
        with c2:
            if st.button("🎭 Try Demo", use_container_width=True):
                try:
                    from src.config.llm_config import LLMConfig, save_llm_config
                    save_llm_config(LLMConfig(provider="mock", model="", api_key=""))
                except Exception:
                    pass
                st.session_state._onboarded = True
                st.rerun()


# ═══════════════════════════════════════════════
# Tab: Dashboard
# ═══════════════════════════════════════════════

def _render_dashboard(api: A3APIClient) -> None:
    st.markdown("## 🏠 Dashboard")
    st.markdown("Your AI-powered learning command center.")

    # Phase 16.2-B: Show AI Engine status — Demo or real provider
    try:
        from src.config.llm_config import load_llm_config
        cfg = load_llm_config()
        is_demo = not cfg.is_configured or cfg.provider in ("mock", "rule")
    except Exception:
        is_demo = True
        cfg = None

    if is_demo:
        with st.container(border=True):
            c1, c2 = st.columns([1, 3])
            with c1:
                st.markdown("### 🎭")
            with c2:
                st.markdown("**Demo Mode** — exploring with rule-based AI.")
                st.caption("Configure an LLM API key in Settings for AI-powered features.")
    else:
        with st.container(border=True):
            c1, c2 = st.columns([1, 3])
            with c1:
                st.markdown("### 🤖")
            with c2:
                provider_label = cfg.provider.title() if cfg else "Unknown"
                model_name = cfg.model or ""
                st.markdown(f"**AI Mode — {provider_label}**")
                if model_name:
                    st.caption(f"Active model: `{model_name}`")

    # Quick stats row
    c1, c2, c3, c4 = st.columns(4)
    try:
        stats = api.get_learning_stats()
        c1.metric("📚 Sessions", stats.get("total_sessions", 0))
        c2.metric("⭐ Avg Score", f"{stats.get('avg_score', 0):.0f}%")
        c3.metric("⏱️ Total Time", f"{stats.get('total_duration_ms', 0) // 60000}min")
    except A3APIError:
        c1.metric("📚 Sessions", "--"); c2.metric("⭐ Avg Score", "--"); c3.metric("⏱️ Total Time", "--")

    try:
        usage = api.get_usage()
        c4.metric("🔢 Tokens", f"{usage.get('total_tokens_used', 0):,}")
    except A3APIError:
        c4.metric("🔢 Tokens", "--")

    st.markdown("---")

    # Phase 16.2: Memory Card — what AI remembers
    try:
        from veritas.memory.student_memory import StudentMemoryStore
        store = StudentMemoryStore()
        user_id = st.session_state.get("user_id", "")
        if user_id and store.exists(user_id):
            mem = store.load(user_id)
            mastery_count = len(mem.mastery_map)
            weak_count = sum(1 for v in mem.mastery_map.values() if isinstance(v, (int, float)) and v < 0.5)
            sessions = len(mem.session_summaries)
            interactions = mem.learning_behavior.get("interaction_count", 0)

            st.markdown("### 🧠 AI Memory")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Mastered Concepts", mastery_count)
            mc2.metric("Weak Areas", weak_count)
            mc3.metric("Sessions", sessions)
            mc4.metric("Interactions", interactions)

            # Show weak area labels if any
            if weak_count > 0:
                weak_labels = [
                    k for k, v in mem.mastery_map.items()
                    if isinstance(v, (int, float)) and v < 0.5
                ][:5]
                if weak_labels:
                    st.caption(f"Focus areas: {', '.join(weak_labels)}")
    except Exception:
        pass

    st.markdown("---")

    # Phase 16.2: Smart goal suggestions
    st.markdown("### 🎯 Try These")
    suggestions = [
        ("🐍", "Learn Python basics", "Variables, loops, functions"),
        ("🤖", "Understand machine learning", "Supervised vs unsupervised"),
        ("📊", "Master data structures", "Lists, trees, graphs, hash maps"),
    ]
    cols = st.columns(len(suggestions))
    for idx, (icon, goal, desc) in enumerate(suggestions):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{icon} {goal}**")
                st.caption(desc)
                if st.button(f"Try This", key=f"demo_goal_{idx}", use_container_width=True):
                    st.session_state.learning_goal = goal
                    st.session_state.active_tab = "learning"
                    st.rerun()

    st.markdown("---")

    # Quick Start
    st.markdown("### ✏️ Custom Goal")
    goal = st.text_area(
        "What do you want to learn today?",
        placeholder="e.g., I'm a CS student with basic Python. I want to understand multi-agent AI systems...",
        height=100, key="dash_goal",
    )
    if st.button("🚀 Start Learning", type="primary", disabled=not goal.strip()):
        st.session_state.learning_goal = goal.strip()
        st.session_state.active_tab = "learning"
        st.rerun()


# ═══════════════════════════════════════════════
# Tab: Learning Pipeline
# ═══════════════════════════════════════════════

PIPELINE_STAGES = [
    ("ProfileAgent", "🧠", "Analyzing your learning profile"),
    ("PlannerAgent", "🗺️", "Building learning path"),
    ("ContentGeneratorAgent", "📝", "Generating materials"),
    ("ResourceAgent", "📚", "Finding resources"),
    ("ReviewAgent", "🔍", "Quality review"),
    ("ReflectionAgent", "💭", "Reflecting on plan"),
    ("Memory", "💾", "Saving to memory"),
]


def _render_learning(api: A3APIClient) -> None:
    st.markdown("## 🎓 Learning Pipeline")

    goal = st.text_area(
        "Learning Goal",
        value=st.session_state.get("learning_goal", ""),
        placeholder="Describe your background and what you want to learn...",
        height=100, key="learn_goal",
    )

    c1, c2 = st.columns([1, 3])
    with c1:
        run_clicked = st.button("🚀 Run Pipeline", type="primary", use_container_width=True, disabled=not goal.strip())
    with c2:
        if st.session_state.get("learning_goal"):
            st.caption(f"Goal: _{st.session_state.learning_goal[:80]}..._")

    if run_clicked:
        st.session_state.learning_goal = goal.strip()
        _execute_pipeline_with_progress(api, goal.strip())

    # Show previous results
    result = st.session_state.get("pipeline_result")
    trace = st.session_state.get("pipeline_trace")
    if result:
        _render_pipeline_results(result, trace)


def _execute_pipeline_with_progress(api: A3APIClient, goal: str) -> None:
    """Execute pipeline with EventBus-driven progress visualization."""
    progress_bar = st.progress(0, "Starting pipeline...")
    status_text = st.empty()
    trace_container = st.container()

    try:
        status_text.info("🚀 Launching AI agents...")
        progress_bar.progress(5, "Initializing")

        result = api.run_pipeline(goal)

        # Extract trace from API response
        trace = result.get("trace", [])

        # Phase 16.1: Trace-driven agent progress (actual agents that ran)
        agents_in_trace = []
        seen = set()
        for t in trace:
            agent = t.get("agent", "")
            if agent and agent not in seen and agent != "System":
                seen.add(agent)
                agents_in_trace.append(agent)

        if agents_in_trace:
            completed = 0
            for i, agent_name in enumerate(agents_in_trace):
                pct = int((i + 1) / len(agents_in_trace) * 100)
                matching = [t for t in trace if t.get("agent") == agent_name]
                if matching:
                    dur = matching[-1].get("duration_ms", 0)
                    status_text.success(f"🤖 {agent_name} — {dur:.0f}ms")
                else:
                    status_text.info(f"🤖 {agent_name}")
                completed += 1
                progress_bar.progress(pct, f"{completed}/{len(agents_in_trace)} agents")
            status_text.success(f"✅ Pipeline complete — {completed} agents executed")
        else:
            progress_bar.progress(100, "Pipeline complete (rule-only)")
            status_text.success("✅ Pipeline complete")

        # Store results
        st.session_state.pipeline_result = result
        st.session_state.pipeline_trace = trace

    except A3APIError as e:
        handle_api_error(e, "pipeline execution")
        progress_bar.empty()
        status_text.empty()


def _render_pipeline_results(result: dict, trace: list | None) -> None:
    """Render pipeline results: plan, trace, evaluation, and model transparency."""
    st.markdown("---")
    st.markdown("### 📊 Pipeline Results")

    # ═══════════════════════════════════════════
    # Runtime Transparency (Phase 13.2)
    # ═══════════════════════════════════════════
    run_info = result.get("run_info", {})
    if run_info:
        with st.expander("⚡ AI Engine Details", expanded=False):
            c1, c2, c3 = st.columns(3)
            engine = run_info.get("engine", "N/A")
            model = run_info.get("model", "N/A")
            is_fb = run_info.get("is_fallback", False)

            c1.metric("AI Engine", engine)
            c2.metric("Model", model)
            gen_ms = run_info.get("generation_time_ms", 0)
            c3.metric("Generation Time", f"{gen_ms:.0f}ms" if gen_ms else "N/A")

            if is_fb:
                st.warning(
                    f"⚠️ **Fallback active** — {run_info.get('fallback_from', 'unknown')} "
                    f"→ {engine}. Reason: {run_info.get('fallback_reason', 'unknown')}"
                )
            else:
                tokens = run_info.get("tokens_used", 0)
                st.caption(f"Tokens used: {tokens:,}")

    # Phase 16.2: Memory saved indicator
    if result.get("memory_saved"):
        st.success("🧠 **AI remembered this session** — your learning profile has been updated.")

    # Phase 17.1: AI Execution Card — per-agent LLM usage
    if trace:
        llm_agents = []
        rule_agents = []
        for t in trace:
            meta = t.get("metadata", {})
            agent_name = t.get("agent", "")
            if agent_name in ("System", "Workflow"):
                continue
            if meta.get("llm_used") or meta.get("source") == "llm":
                llm_agents.append({"agent": agent_name, "provider": meta.get("provider","?"), "model": meta.get("model","")})
            else:
                rule_agents.append(agent_name)

        if llm_agents or rule_agents:
            with st.expander("🤖 AI Execution Card", expanded=False):
                # Provider info
                provider_name = llm_agents[0]["provider"] if llm_agents else "rule"
                model_name = llm_agents[0]["model"] if llm_agents else ""
                st.markdown(f"**Provider:** `{provider_name}`" + (f" · Model: `{model_name}`" if model_name else ""))
                
                # Counts
                c1, c2, c3 = st.columns(3)
                c1.metric("Agents (LLM)", len(llm_agents))
                c2.metric("Agents (Rule)", len(rule_agents))
                tokens = result.get("run_info", {}).get("tokens_used", 0)
                c3.metric("Tokens", f"{tokens:,}" if tokens else "—")
                
                # Per-agent breakdown
                if llm_agents:
                    st.caption("**LLM-powered agents:**")
                    for a in llm_agents:
                        st.success(f"🤖 {a['agent']}")
                if rule_agents:
                    st.caption("**Rule-based agents:**")
                    for a in rule_agents:
                        st.info(f"⚙️ {a}")

    # Quick summary
    c1, c2, c3 = st.columns(3)
    plan = result.get("plan", {})
    eval_data = result.get("evaluation", {})
    nodes = plan.get("nodes", [])
    c1.metric("Learning Nodes", len(nodes))
    c2.metric("Quality Score", f"{eval_data.get('score', 'N/A')}")
    c3.metric("Duration", f"{result.get('duration_ms', 0):.0f}ms")

    # Agent Trace (from v1 components)
    if trace:
        with st.expander("🔍 Agent Execution Trace", expanded=False):
            from web.v1.components import render_pipeline_progress
            # Convert dict trace to object-like for compatibility
            class TraceEvent:
                def __init__(self, d):
                    self.agent = d.get("agent", "")
                    self.action = d.get("action", "")
                    self.status = d.get("status", "success")
                    self.duration_ms = d.get("duration_ms", 0)
                    self.input_summary = d.get("input_summary", "")
                    self.output_summary = d.get("output_summary", "")
                    self.timestamp = d.get("timestamp", "")
            events = [TraceEvent(t) for t in trace]
            try:
                render_pipeline_progress(events, st)
            except Exception:
                for t in trace:
                    st.text(f"{t.get('agent', '?')}: {t.get('output_summary', '')[:80]}")

    # Learning Plan
    if nodes:
        with st.expander("🗺️ Learning Plan", expanded=True):
            for i, node in enumerate(nodes):
                st.markdown(f"**{i+1}. {node.get('title', 'Untitled')}**")
                concepts = node.get("concepts", [])
                if concepts:
                    st.caption(f"Concepts: {', '.join(concepts)}")
                est = node.get("estimated_hours", 1)
                st.caption(f"~{est}h")

    # Evaluation
    if eval_data:
        with st.expander("📊 Quality Evaluation", expanded=False):
            st.metric("Score", eval_data.get("score", "N/A"))
            if eval_data.get("passed"):
                st.success("✅ Passed quality gate")
            issues = eval_data.get("issues", [])
            if issues:
                st.warning(f"Issues found: {len(issues)}")

    # ═══════════════════════════════════════════
    # Phase 16.1: Reflection Output
    # ═══════════════════════════════════════════
    refl = result.get("reflection")
    if refl:
        with st.expander("💭 AI Reflection", expanded=False):
            source = refl.get("source", "rule")
            if source == "llm":
                st.success("🤖 AI-powered analysis")
            else:
                st.info("⚙️ Rule-based analysis")

            summary = refl.get("summary", "")
            if summary:
                st.markdown(summary[:500])

            achievements = refl.get("achievements", [])
            improvements = refl.get("improvements", [])

            if achievements:
                st.markdown("**Achievements:**")
                for a in achievements:
                    st.markdown(f"- ✅ {a}")

            if improvements:
                st.markdown("**Improvements:**")
                for imp in improvements:
                    st.markdown(f"- 📝 {imp}")

    # ═══════════════════════════════════════════
    # Phase 14.2: Generated Content
    # ═══════════════════════════════════════════
    content_data = result.get("content")
    if content_data:
        with st.expander("📝 AI-Generated Lesson", expanded=True):
            title = content_data.get("title", "Teaching Material")
            summary = content_data.get("overall_summary", "")
            chapters = content_data.get("chapters", [])
            gen_source = content_data.get("generation_source", "rule")

            st.markdown(f"### {title}")
            if summary:
                st.markdown(summary)
            if gen_source == "llm":
                st.success("🤖 Generated by AI")
            elif gen_source == "rule":
                st.info("⚙️ Template-generated (no AI configured)")

            if chapters:
                st.markdown("---")
                for ch in chapters:
                    ch_title = ch.get("title", "Untitled")
                    ch_content = ch.get("content", "")
                    with st.expander(f"📖 {ch_title}"):
                        st.markdown(ch_content[:3000] if ch_content else "(empty)")

    # ═══════════════════════════════════════════
    # Phase 14.2: Resource Cards
    # ═══════════════════════════════════════════
    resources_list = result.get("resources", [])
    if resources_list:
        with st.expander("📚 Recommended Resources", expanded=False):
            for res in resources_list:
                rtype = res.get("type", "unknown")
                rtitle = res.get("title", "Untitled")
                rreason = res.get("reason", "")
                rdifficulty = res.get("difficulty", "beginner")
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{rtitle}**")
                    c2.caption(f"`{rtype}` · {rdifficulty}")
                    if rreason:
                        st.caption(rreason)

    # ═══════════════════════════════════════════
    # Phase 16.1: Interactive Quiz Panel
    # ═══════════════════════════════════════════
    st.markdown("---")
    topic = result.get("goal", "")
    if topic:
        try:
            from src.core.provider_factory import create_provider
            provider = create_provider()
            render_quiz_panel(provider, topic)
        except Exception:
            st.caption("Quiz unavailable — configure an LLM provider in Settings")


# ═══════════════════════════════════════════════
# Tab: History
# ═══════════════════════════════════════════════

def _render_history(api: A3APIClient) -> None:
    st.markdown("## 📜 Learning History")

    try:
        records = api.get_learning_history()
        stats = api.get_learning_stats()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Runs", stats.get("total_sessions", len(records)))
        c2.metric("Avg Score", f"{stats.get('avg_score', 0):.0f}")
        c3.metric("Total Time", f"{stats.get('total_duration_ms', 0) // 60000}min")

        st.markdown("---")

        if not records:
            st.info("No learning history yet. Run the Learning Pipeline to get started!")
            return

        for r in records[-20:]:
            created = r.get('created_at', '')[:10]
            dur = r.get('duration_ms', 0)
            run_id = r.get('run_id', '')
            result_json = r.get('result_json')

            with st.expander(
                f"{r.get('agent', 'pipeline')} — {r.get('action', 'run')} "
                f"({created})",
            ):
                c1, c2, c3 = st.columns(3)
                c1.metric("Score", f"{r.get('score', 0):.0f}")
                c2.metric("Duration", f"{dur}ms")
                if r.get("course_id"):
                    c3.caption(f"Course: {r['course_id']}")

                # Phase 16.2: History replay — render result_json if available
                if result_json and isinstance(result_json, dict):
                    goal = result_json.get("goal", "")
                    plan_data = result_json.get("plan", {})
                    eval_data = result_json.get("evaluation", {})
                    content_data = result_json.get("content")
                    resources_list = result_json.get("resources", [])
                    refl = result_json.get("reflection")
                    mem_saved = result_json.get("memory_saved")

                    st.markdown("---")
                    st.markdown("#### 📋 Session Replay")

                    if goal:
                        st.caption(f"**Goal:** {goal}")

                    # Memory saved badge in replay
                    if mem_saved:
                        st.success("🧠 AI remembered this session")

                    # Plan
                    nodes = plan_data.get("nodes", [])
                    if nodes:
                        with st.expander("🗺️ Learning Plan", expanded=False):
                            for i, node in enumerate(nodes):
                                st.markdown(f"**{i+1}. {node.get('title', 'Untitled')}**")
                                concepts = node.get("concepts", [])
                                if concepts:
                                    st.caption(f"Concepts: {', '.join(concepts)}")

                    # Evaluation
                    if eval_data:
                        with st.expander("📊 Evaluation", expanded=False):
                            st.metric("Score", eval_data.get("score", "N/A"))
                            if eval_data.get("passed"):
                                st.success("✅ Passed quality gate")

                    # Reflection
                    if refl:
                        with st.expander("💭 AI Reflection", expanded=False):
                            s = refl.get("summary", "")
                            if s:
                                st.markdown(s[:300])
                            ach = refl.get("achievements", [])
                            imp = refl.get("improvements", [])
                            if ach:
                                st.markdown("**Achievements:**")
                                for a in ach[:3]:
                                    st.markdown(f"- ✅ {a}")
                            if imp:
                                st.markdown("**Improvements:**")
                                for i in imp[:3]:
                                    st.markdown(f"- 📝 {i}")

                    # Content
                    if content_data:
                        with st.expander("📝 Generated Lesson", expanded=False):
                            title = content_data.get("title", "Teaching Material")
                            chapters = content_data.get("chapters", [])
                            st.markdown(f"**{title}**")
                            if chapters:
                                for ch in chapters[:3]:
                                    st.caption(f"📖 {ch.get('title', 'Untitled')}")

                    # Resources
                    if resources_list:
                        with st.expander("📚 Resources", expanded=False):
                            for res in resources_list[:5]:
                                st.caption(f"• {res.get('title', 'Untitled')} ({res.get('type', '?')})")

                    # Artifact link
                    if run_id:
                        if st.button("📂 View Workspace Artifacts", key=f"replay_ws_{r['id']}"):
                            st.session_state.active_tab = "workspace"
                            st.rerun()

    except A3APIError as e:
        handle_api_error(e, "history")
        st.info("History will appear here after you run the learning pipeline.")


# ═══════════════════════════════════════════════
# Tab: Workspace (Artifact Browser)
# ═══════════════════════════════════════════════

def _render_workspace(api: A3APIClient) -> None:
    st.markdown("## 📂 Workspace")
    st.markdown("Your learning artifacts and generated materials.")

    user_id = st.session_state.get("user_id", "unknown")
    if user_id == "unknown":
        st.info("Log in to view your workspace.")
        return

    try:
        from src.workspace.manager import WorkspaceManager
        wm = WorkspaceManager()
        info = wm.get_workspace_info(user_id)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Materials", info.artifact_counts.get("materials", 0))
        c2.metric("Presentations", info.artifact_counts.get("ppt", 0))
        c3.metric("Images", info.artifact_counts.get("images", 0))
        c4.metric("Size", f"{info.total_size_bytes / 1024:.0f}KB")

        st.markdown("---")

        # Browse artifacts by category
        category = st.selectbox("Category", ["materials", "ppt", "images", "videos"])
        artifacts = wm.list_artifacts(user_id, category)

        if not artifacts:
            st.info(f"No {category} artifacts yet. Run the Learning Pipeline to generate some!")
            return

        for path in artifacts:
            filename = path.split("/")[-1]
            with st.expander(f"📄 {filename}"):
                try:
                    content = wm.load_artifact(user_id, category, filename)
                    if content:
                        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
                        if ext in ("json",):
                            st.json(content[:5000])
                        elif ext in ("md", "txt"):
                            st.markdown(content[:3000])
                        else:
                            st.code(content[:2000])
                        st.download_button(
                            f"⬇ Download {filename}",
                            content, file_name=filename,
                            key=f"dl_{filename}",
                        )
                except Exception:
                    st.caption("(binary file — cannot preview)")

    except ImportError:
        st.info("Workspace browser will be available after running the learning pipeline.")
    except Exception as e:
        st.warning(f"Could not load workspace: {e}")


# ═══════════════════════════════════════════════
# Tab: Profile
# ═══════════════════════════════════════════════

def _render_profile(api: A3APIClient) -> None:
    st.markdown("## 👤 Learning Profile")

    try:
        profile_data = api.get_profile()
        profile = profile_data.get("profile", {})
        source = profile_data.get("source", "stored")

        st.caption(f"Source: {source}")

        if profile:
            dims = [
                ("knowledge_base", "📚 Knowledge Base"),
                ("cognitive_style", "🧠 Cognitive Style"),
                ("error_prone_bias", "⚠️ Error Prone"),
                ("learning_pace", "⚡ Learning Pace"),
                ("interaction_preference", "🖐️ Interaction"),
                ("frustration_threshold", "🛡️ Frustration"),
            ]
            cols = st.columns(3)
            for i, (key, label) in enumerate(dims):
                val = profile.get(key, "unknown")
                with cols[i % 3]:
                    st.metric(label, str(val)[:30])

            # Try to show memory stats
            try:
                from veritas.memory.student_memory import StudentMemoryStore
                store = StudentMemoryStore()
                user_id = st.session_state.get("user_id", "")
                if user_id and store.exists(user_id):
                    mem = store.load(user_id)
                    st.markdown("---")
                    st.markdown("### 🧠 Memory Stats")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Interactions", mem.learning_behavior.get("interaction_count", 0))
                    c2.metric("Mastery Concepts", len(mem.mastery_map))
                    c3.metric("Sessions", len(mem.session_summaries))
            except Exception:
                pass
        else:
            st.info("No profile yet. Run the Learning Pipeline to create one!")

    except A3APIError as e:
        handle_api_error(e, "profile")


# ═══════════════════════════════════════════════
# Tab: Settings
# ═══════════════════════════════════════════════

def _render_settings(api: A3APIClient) -> None:
    st.markdown("## ⚙️ AI Provider Center")

    try:
        from web.settings_tab import render_settings_tab
        render_settings_tab()
    except ImportError:
        st.warning("Settings module not available.")
    except Exception as e:
        st.error(f"Settings error: {e}")


# ── Entry point ──────────────────────────────

if __name__ == "__main__":
    main()
