"""A3 Multi-Agent Intelligence Observatory — Dashboard V2 Standalone Demo

Standalone Streamlit entrypoint. Independent of V1 (web/app.py).

Architecture:
    app_v2.py  →  bootstrap + mode switch (this file)
    web/dashboard/data_providers.py  →  data access (live / demo fallback)
    web/dashboard/components.py      →  6 panel renderers

Modes:
    Demo (default):  get_demo_all() → instant showcase, zero dependencies
    Runtime:         reads EventBus singleton + persisted storage

Runtime data sources (priority order — NO agent creation):
    1. EventBus       → AgentEventBus.get_instance()  [singleton, shared with V1]
    2. TraceCollector  → AgentTraceCollector().load()   [persisted JSON]
    3. MemoryManager   → MemoryManager()                [same storage/ dir as V1]
    4. Evaluator       → AgentEvaluator()               [infrastructure, not agent]
    5. DecisionExplainer → DecisionExplainer()          [stateless]

NEVER created: ProfileAgent, PlannerAgent, ResourceRecommendationAgent, ContentAgent
"""

from __future__ import annotations
import sys
from pathlib import Path

# ── Path setup ──
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root / "src") not in sys.path:
    sys.path.insert(0, str(_project_root / "src"))

import streamlit as st

# ── Page config ──
st.set_page_config(
    page_title="A3 Intelligence Observatory",
    page_icon="🔬",
    layout="wide",
)
st.title("🔬 A3 Multi-Agent Intelligence Observatory")
st.caption("比赛展示版 Demo — 6-Panel Dashboard · Zero Core Changes")

# ── Dashboard imports ──
from web.dashboard import (
    get_demo_all,
    render_system_overview,
    render_student_intelligence,
    render_execution_timeline,
    render_explainability_panel,
    render_evaluation_dashboard,
    render_improvement_timeline,
)

# ═══════════════════════════════════════════════════
# Sidebar — Mode Selector
# ═══════════════════════════════════════════════════

with st.sidebar:
    st.header("🔬 Observatory V2")
    use_demo = st.checkbox("🎭 Demo Mode (展示用)", value=True)

    runtime_ok = False
    if not use_demo:
        st.caption("Runtime Mode: 读取共享基础设施")
        student_id = st.text_input("Student ID", "demo_student")

        # Check what data sources are available
        try:
            from core.event_bus import AgentEventBus
            bus = AgentEventBus.get_instance()
            bus_events = bus.event_count
        except Exception:
            bus_events = 0
            bus = None

        try:
            from core.agent_trace import AgentTraceCollector
            collector = AgentTraceCollector()
            saved_traces = len(collector.load(student_id)) if student_id else 0
        except Exception:
            saved_traces = 0
            collector = None

        try:
            from memory.memory_manager import MemoryManager
            memory = MemoryManager(auto_seed=False)
            student_exists = memory.students.exists(student_id)
        except Exception:
            student_exists = False
            memory = None

        st.caption(f"🟢 EventBus: {bus_events} events")
        st.caption(f"📁 Saved Traces: {saved_traces}")
        st.caption(f"👤 Student Data: {'✅' if student_exists else '❌ not found'}")

        runtime_ok = True

    st.divider()
    st.caption("6 Panels · Zero Core Changes")
    st.caption("Demo data: 9 agents, 8 concepts, 12 events")

# ═══════════════════════════════════════════════════
# Data Assembly
# ═══════════════════════════════════════════════════

if use_demo or not runtime_ok:
    # ── Demo Mode: instant showcase ──
    data = get_demo_all()

else:
    # ── Runtime Mode: read from shared infrastructure ──
    st.info("📡 Runtime Mode — 从共享基础设施读取数据")

    from web.dashboard import data_providers as dp
    from core.decision_explainer import DecisionExplainer
    from evaluation.agent_evaluator import AgentEvaluator

    explainer = DecisionExplainer()
    evaluator = AgentEvaluator()

    # Student memory data
    profile_data: dict = {}
    mastery_map: dict = {}
    if memory and student_exists:
        try:
            mem = memory.get_student_memory(student_id)
            profile_data = mem.profile_history[-1] if mem.profile_history else {}
            mastery_map = dict(getattr(mem, "mastery_map", {}))
        except Exception:
            pass

    # ── Assemble all 6 panels ──
    data = {
        "system": dp.get_system_overview(
            event_bus=bus,
            trace_collector=collector,
            memory_manager=memory,
            evaluator=evaluator,
        ),
        "student": dp.get_student_intelligence(
            student_id=student_id,
            memory_manager=memory,
            profile_dict=profile_data if profile_data else None,
        ),
        "timeline": dp.get_execution_timeline(
            trace_collector=collector,
            event_bus=bus,
            session_id=student_id,
        ),
        "explainability": dp.get_explainability_data(
            explainer=explainer,
            profile_dict=profile_data if profile_data else None,
            mastery_map=mastery_map if mastery_map else None,
        ),
        "evaluation": dp.get_evaluation_data(evaluator=evaluator),
        "improvement": dp.get_improvement_timeline(),
    }

# ═══════════════════════════════════════════════════
# Render 6 Panels
# ═══════════════════════════════════════════════════

render_system_overview(data["system"], st)

st.divider()
render_student_intelligence(data["student"], st)

st.divider()
render_execution_timeline(data["timeline"], st)

st.divider()
render_explainability_panel(data["explainability"], st)

st.divider()
render_evaluation_dashboard(data["evaluation"], st)

st.divider()
render_improvement_timeline(data["improvement"], st)
