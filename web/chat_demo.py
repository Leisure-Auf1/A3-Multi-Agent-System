"""
Phase 11.5 — Chat Demo UI (Streamlit)

End-to-end demonstration of the LLM-integrated A3 pipeline:
  1. Student conversation → Profile extraction
  2. Profile → Learning path (from Knowledge Base)
  3. Path → Resource generation

Usage:
    streamlit run web/chat_demo.py

Requirements:
    pip install streamlit
"""

from __future__ import annotations
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
from typing import Any, Dict, List

# ── Agent imports ──
from src.agents.profile_agent import ProfileAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.resource_generation_agent import ResourceGenerationAgent
from src.llm.provider import LLMProvider
from src.core.course_kb_loader import CourseKnowledgeBase
from src.core.llm_agent_adapter import LLMAgentAdapter
from src.core.provider_factory import create_provider, get_provider_info

# ──────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="A3 Chat Demo — LLM Integration",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 A3 Chat Demo — LLM-Integrated Pipeline")
st.caption("Phase 11.5: Conversation → Profile → Path → Resources")

# ──────────────────────────────────────────────
# Sidebar: Configuration
# ──────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    llm_mode = st.selectbox(
        "LLM Provider",
        ["mock", "spark", "none"],
        index=0,
        format_func=lambda x: {"mock": "🤖 Mock (Demo)", "spark": "🚀 Xunfei Spark", "none": "📏 Rule Only"}.get(x, x),
        help="mock = deterministic demo | spark = real Xunfei API | none = pure rule mode"
    )

    use_kb = st.checkbox("Use Knowledge Base", value=True,
                          help="When checked, PlannerAgent loads paths from the file-based KB. "
                               "Uncheck for hardcoded graph.")

    st.divider()
    info = get_provider_info() if llm_mode != "none" else {"provider": "None (rule-only)", "model": "N/A"}
    st.caption(f"**Provider:** {info.get('provider', 'Unknown')}")
    st.caption(f"**Model:** {info.get('model', 'N/A')}")
    if info.get("fallback_reason"):
        st.warning(f"⚠️ {info['fallback_reason']}")

# ──────────────────────────────────────────────
# Initialize Agents (cached)
# ──────────────────────────────────────────────

@st.cache_resource
def get_agents(llm_mode: str, use_kb_mode: bool):
    """Initialize all agents with caching."""
    agents = {}

    # Profile Agent
    profile_agent = ProfileAgent()
    provider = create_provider(llm_mode)
    if provider:
        profile_agent.set_llm_provider(provider)
    agents["profile"] = profile_agent

    # Planner Agent
    planner = PlannerAgent()
    if use_kb_mode:
        kb = CourseKnowledgeBase()
        kb.load()
        planner._kb_loader = kb
        planner._kb_loaded = True
        kb_graph = kb.to_knowledge_graph()
        planner.knowledge_graph.update(kb_graph)
    agents["planner"] = planner

    # Resource Generation Agent
    agents["resource"] = ResourceGenerationAgent()

    # LLM Adapter (for demo showcase)
    if provider:
        agents["adapter"] = LLMAgentAdapter(provider=provider)

    return agents

# ──────────────────────────────────────────────
# Helper: parse JSON safely
# ──────────────────────────────────────────────

import json

def safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None

# ──────────────────────────────────────────────
# Main UI
# ──────────────────────────────────────────────

# Chat input
st.subheader("💬 Student Conversation")
st.caption("Describe yourself and what you want to learn.")

# Pre-filled examples
example = st.selectbox(
    "Quick examples:",
    ["", "I'm a CS student with some Python experience. I learn best by looking at diagrams and writing code. I want to learn how to build multi-agent AI systems.",
     "我是网络工程专业，学过一些Python基础。我比较喜欢看图学习，不太喜欢纯文字。想快速上手Agent开发。",
     "No experience with programming. I prefer watching videos and taking things slow. I get frustrated easily."],
)

student_text = st.text_area(
    "Your description:",
    value=example if example else "",
    height=100,
    placeholder="Tell us about your background, learning preferences, and what you want to learn...",
)

if st.button("🚀 Run Pipeline", type="primary", disabled=not student_text.strip()):
    agents = get_agents(llm_mode, use_kb)

    # ════════════════════════════════════════
    # Step 1: Profile Extraction
    # ════════════════════════════════════════
    st.divider()
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("👤 Step 1: Profile Extraction")

        with st.spinner("Extracting profile..."):
            t0 = time.time()
            if llm_mode != "none":
                result = agents["profile"].extract_with_provider(student_text)
            else:
                result = agents["profile"].extract(student_text)
            latency = (time.time() - t0) * 1000

        profile = result.profile
        source_badge = "🤖 LLM" if result.source == "llm" else "📏 Rule"
        if result.source == "llm+memory":
            source_badge = "🧠 LLM+Memory"

        st.metric("Source", source_badge)
        st.metric("Confidence", f"{result.confidence:.0%}")
        st.metric("Latency", f"{latency:.0f}ms")

        # 6-dim display
        dims = profile.to_dict()
        dim_labels = {
            "knowledge_base": "📚 Knowledge",
            "cognitive_style": "🧠 Style",
            "error_prone_bias": "⚠️ Error Bias",
            "learning_pace": "⚡ Pace",
            "interaction_preference": "🖐️ Interaction",
            "frustration_threshold": "🛡️ Frustration",
        }
        for key, label in dim_labels.items():
            st.caption(f"{label}: **{dims.get(key, 'N/A')}**")

    with col2:
        st.subheader("📊 Profile Details")
        st.json(profile.to_dict(), expanded=False)

    # ════════════════════════════════════════
    # Step 2: Learning Path
    # ════════════════════════════════════════
    st.divider()
    st.subheader("🗺️ Step 2: Learning Path")

    with st.spinner("Planning learning path..."):
        t0 = time.time()
        planner = agents["planner"]

        if use_kb:
            plan = planner.plan_from_kb(profile, course_id="ai_ma_101",
                                         goal_text=student_text)
        else:
            plan = planner.plan(profile, course_id="multi_agent_ai",
                                goal_text=student_text)
        plan_latency = (time.time() - t0) * 1000

    # Stats row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nodes", len(plan.nodes))
    c2.metric("Total Time", f"{plan.total_minutes} min")
    c3.metric("Strategy", plan.strategy_rationale.split(" | ")[0] if " | " in plan.strategy_rationale else plan.strategy_rationale[:40])
    c4.metric("KB Source", "📁 File KB" if use_kb and planner.kb_available else "💾 Hardcoded")

    # Node table
    st.caption("Path Nodes:")
    header_cols = st.columns([2, 3, 1, 1, 1, 1])
    header_cols[0].caption("**Node**")
    header_cols[1].caption("**Concept**")
    header_cols[2].caption("**Depth**")
    header_cols[3].caption("**Exercises**")
    header_cols[4].caption("**Minutes**")
    header_cols[5].caption("**Strategy**")

    for node in plan.nodes[:10]:  # Show first 10
        row = st.columns([2, 3, 1, 1, 1, 1])
        row[0].markdown(f"**{node.title}**")
        row[1].caption(node.core_concept[:60])
        row[2].markdown("🔴" * node.depth + "⚪" * (3 - node.depth))
        row[3].caption(f"{node.exercise_count}")
        row[4].caption(f"{node.estimated_minutes}min")
        row[5].caption(node.teaching_strategy)

    if len(plan.nodes) > 10:
        st.caption(f"... and {len(plan.nodes) - 10} more nodes")

    # ════════════════════════════════════════
    # Step 3: Resource Generation
    # ════════════════════════════════════════
    st.divider()
    st.subheader("🎨 Step 3: Resource Generation")

    with st.spinner("Generating resources..."):
        t0 = time.time()
        # Extract concepts from first 4 nodes
        concepts = [n.core_concept for n in plan.nodes[:4]]
        topic = plan.nodes[0].title if plan.nodes else "Multi-Agent AI"
        resources = agents["resource"].generate_all(topic, concepts)
        res_latency = (time.time() - t0) * 1000

    st.caption(f"Generated 5 resource types in {res_latency:.0f}ms")

    # Display resource cards
    MODAL_STYLES = {
        "document": {"icon": "📄", "color": "#2196F3"},
        "mindmap": {"icon": "🧠", "color": "#9C27B0"},
        "exercise": {"icon": "✏️", "color": "#FF9800"},
        "code": {"icon": "💻", "color": "#4CAF50"},
        "video": {"icon": "🎬", "color": "#F44336"},
    }

    resource_cols = st.columns(min(len(resources), 3))
    for i, (rtype, data) in enumerate(resources.items()):
        style = MODAL_STYLES.get(rtype, {"icon": "📄", "color": "#999"})
        with resource_cols[i % len(resource_cols)]:
            st.markdown(f"""
            <div style="border:2px solid {style['color']};border-radius:12px;padding:12px;margin:4px 0;
                 background:linear-gradient(135deg,{style['color']}08,{style['color']}03);">
                <span style="font-size:1.5em;">{style['icon']}</span><br>
                <strong>{data.get('title', rtype)[:40]}</strong>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Preview"):
                if rtype == "mindmap" and "mermaid_code" in data:
                    st.code(data["mermaid_code"][:500], language="mermaid")
                elif rtype == "document" and "sections" in data:
                    for s in data["sections"][:2]:
                        st.caption(f"**{s.get('heading', '')}**: {s.get('content', '')[:100]}...")
                elif rtype == "exercise" and "questions" in data:
                    st.caption(f"{len(data['questions'])} questions, {data.get('total_points', 0)} pts")
                elif rtype == "code" and "starter_code" in data:
                    st.code(data["starter_code"][:300], language=data.get("language", "python"))
                else:
                    st.caption("Preview available")

    # ════════════════════════════════════════
    # Summary Footer
    # ════════════════════════════════════════
    st.divider()
    st.subheader("📋 Pipeline Summary")

    summary_cols = st.columns(4)
    total_latency = latency + plan_latency + res_latency
    summary_cols[0].metric("Total Latency", f"{total_latency:.0f}ms")
    summary_cols[1].metric("Profile Source", source_badge)
    summary_cols[2].metric("KB Used", "✅" if (use_kb and planner.kb_available) else "❌")
    summary_cols[3].metric("Resources", f"{len(resources)} types")

    st.success(f"""
    ✅ **Pipeline Complete**
    - Profile: {result.source} mode, {len(plan.nodes)} learning nodes
    - Path: {plan.strategy_rationale[:80]}...
    - Resources: {', '.join(resources.keys())}
    - Knowledge: {planner.kb_available and '📁 File KB' or '💾 Hardcoded graph'}
    """)

else:
    # Landing page
    st.info("👆 Enter your learning goals above and click **Run Pipeline** to see the LLM-integrated demo.")

    st.markdown("""
    ### 🔄 Pipeline Flow

    ```
    Student Conversation (Natural Language)
            │
            ▼
    ┌─────────────────────┐
    │ ProfileAgent        │  LLM mode: MockLLMProvider
    │ (extract_with_      │  Rule mode: keyword matching
    │  provider)          │
    └────────┬────────────┘
             │  6-dim DynamicProfile
             ▼
    ┌─────────────────────┐
    │ PlannerAgent        │  KB mode: knowledge_base/ chapters
    │ (plan_from_kb)      │  Fallback: DEFAULT_KNOWLEDGE_GRAPH
    └────────┬────────────┘
             │  LearningPlan (nodes)
             ▼
    ┌─────────────────────┐
    │ ResourceGeneration  │  5 types: document, mindmap,
    │ Agent               │  exercises, code, video
    └─────────────────────┘
    ```

    ### 🧪 Mode Comparison

    | Feature | LLM Mode | Rule Mode |
    |:--------|:---------|:----------|
    | Profile | MockLLMProvider (JSON output) | Keyword matching |
    | Latency | ~50ms (mock) | <5ms |
    | KB Path | File-based chapters | Hardcoded graph |
    | Resources | 5 multimodal types | 5 multimodal types |
    """)
