"""V1 Pipeline — Agent initialization + pipeline execution.

Extracted from web/app.py (refactor — no behavior changes).

Usage:
    from web.v1 import get_agents, run_pipeline

    agents = get_agents()
    results = run_pipeline(student_id, student_text, course, agents)
"""

from __future__ import annotations
import sys, time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import streamlit as st

# ── Ensure src/ on path ──
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root / "src") not in sys.path:
    sys.path.insert(0, str(_project_root / "src"))

from core.agent_router import DynamicProfile, AgentRouter
from core.event_bus import AgentEventBus
from agents.profile_agent import ProfileAgent
from agents.planner_agent import PlannerAgent, PlanNode
from agents.resource_recommendation_agent import ResourceRecommendationAgent, RESOURCE_TYPES
from agents.conversation_profile_agent import ConversationProfileAgent, PROFILE_DIMENSIONS
from memory.memory_manager import MemoryManager


# ═══════════════════════════════════════════════════
# Agent Initialization
# ═══════════════════════════════════════════════════

@st.cache_resource
def get_agents() -> Dict[str, Any]:
    """Create and cache all agent instances."""
    return {
        "profile": ProfileAgent(),
        "planner": PlannerAgent(),
        "router": AgentRouter(),
        "memory": MemoryManager(auto_seed=True),
        "conversation": ConversationProfileAgent(),
        "recommender": ResourceRecommendationAgent(),
    }


# ═══════════════════════════════════════════════════
# Sidebar — Student Input
# ═══════════════════════════════════════════════════

def render_sidebar() -> Tuple[str, str, str, bool]:
    """Render sidebar controls. Returns (student_id, student_text, course, extract_btn)."""
    with st.sidebar:
        st.header("👤 学生输入")
        student_id = st.text_input("学生ID", "demo_student")
        student_text = st.text_area(
            "描述你的学习情况",
            value="我是编程小白，零基础。看视频学，看到@装饰器就头大。容易放弃。想快速上手写代码。",
            height=120,
        )
        course = st.selectbox("课程", ["python_advanced", "python_basics", "multi_agent_ai"])
        extract_btn = st.button("🚀 开始分析", use_container_width=True)

        st.divider()
        st.caption("🟢 EventBus active — events tracked below")

    return student_id, student_text, course, extract_btn


# ═══════════════════════════════════════════════════
# Pipeline Execution
# ═══════════════════════════════════════════════════

def run_pipeline(
    student_id: str,
    student_text: str,
    course: str,
    agents: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute the V1 pipeline: profile extract → plan → recommend.

    Returns a dict with all results for rendering.
    """
    bus = AgentEventBus.get_instance()
    bus.start_session(student_id)

    # ── Step 1: Profile extraction ──
    t0 = time.time()
    result = agents["profile"].extract(student_text)
    profile = result.profile
    profile_data = profile.to_dict()
    bus.emit(
        "ProfileAgent", "extract",
        input_summary=student_text[:100],
        output_summary=f"confidence={result.confidence:.2f}",
        duration_ms=(time.time() - t0) * 1000,
    )

    agents["memory"].update_student_memory(student_id, profile=profile_data)

    # ── Step 2: Learning plan ──
    t0 = time.time()
    mem = agents["memory"].get_student_memory(student_id)
    plan = agents["planner"].plan(profile, course_id=course, student_memory=mem)
    bus.emit(
        "PlannerAgent", "generate_plan",
        input_summary=f"course={course}, profile={profile.knowledge_base}",
        output_summary=f"nodes={len(plan.nodes)}, minutes={plan.total_minutes}",
        duration_ms=(time.time() - t0) * 1000,
    )

    # ── Step 3: Resource recommendation ──
    t0 = time.time()
    mastery = getattr(mem, "mastery_map", {})
    resource_plan = agents["recommender"].recommend(
        student_id, mem, learning_plan_nodes=plan.nodes,
    )
    bus.emit(
        "ResourceRecommendationAgent", "recommend",
        input_summary=f"student={student_id}, mastery={len(mastery)}concepts",
        output_summary=f"resources={len(resource_plan.recommended_resources)}, minutes={resource_plan.total_minutes}",
        duration_ms=(time.time() - t0) * 1000,
    )

    events = bus.get_timeline()

    return {
        "profile": profile,
        "profile_data": profile_data,
        "result": result,
        "mem": mem,
        "plan": plan,
        "mastery": mastery,
        "resource_plan": resource_plan,
        "events": events,
    }
