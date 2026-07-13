"""A3 个性化教学系统 — Streamlit Web Demo v2

Bootstrap entrypoint. All V1 logic lives in web/v1/ (extracted).

Architecture:
    app.py           → page config + bootstrap (this file)
    web/v1/pipeline.py  → agent init + pipeline execution
    web/v1/components.py → 5 panel Streamlit renderers
"""

import sys
from pathlib import Path

# ── Ensure src/ on path ──
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root / "src") not in sys.path:
    sys.path.insert(0, str(_project_root / "src"))

import streamlit as st

# ── Page config ──
st.set_page_config(page_title="A3 智能学习平台", page_icon="🎓", layout="wide")
st.title("🎓 A3 个性化智能学习平台")
st.caption("Multi-Agent System — 可展示 · 可解释 · 可评测")

# ── V1 imports ──
from web.v1 import get_agents, run_pipeline
from web.v1 import (
    render_profile_completeness,
    render_dynamic_profile,
    render_learning_path,
    render_resource_cards,
    render_agent_trace,
)
from web.v1.pipeline import render_sidebar
from web.v1.components import render_landing

# ── Agents ──
agents = get_agents()

# ── Sidebar ──
student_id, student_text, course, extract_btn = render_sidebar()

# ── Landing page ──
if not extract_btn and "pipeline_done" not in st.session_state:
    render_landing(st)
    st.stop()

# ── Pipeline execution ──
if extract_btn or "pipeline_done" in st.session_state:
    if extract_btn:
        st.session_state["pipeline_done"] = False
        st.rerun()

    results = run_pipeline(student_id, student_text, course, agents)

    # ── Render panels ──
    render_profile_completeness(results["profile_data"], results["result"], agents, st)
    render_dynamic_profile(results["profile_data"], results["result"], st)
    render_learning_path(results["plan"], results["mastery"], st)
    render_resource_cards(results["resource_plan"], st)
    render_agent_trace(results["events"], st)

    st.success(
        f"✅ Pipeline 完成 — {len(results['events'])} 个事件, "
        f"{results['resource_plan'].total_minutes}分钟推荐"
    )

    if not st.session_state.get("pipeline_done"):
        st.session_state["pipeline_done"] = True
