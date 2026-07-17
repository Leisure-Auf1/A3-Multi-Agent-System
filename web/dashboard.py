"""
Phase 5.0 — Runtime Dashboard (Streamlit)

Real-time visualization of the Agent Runtime.

Usage:
    streamlit run web/dashboard.py
"""

from __future__ import annotations

import sys
import os

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import time
import streamlit as st
from src.runtime.snapshot import RuntimeBus, RuntimeSnapshot


# ── Page config ────────────────────────────

st.set_page_config(
    page_title="Veritas Core — Runtime Dashboard",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Veritas Core — Runtime Dashboard")
st.caption("Phase 5.0 · Agent Runtime State Machine Observability")

# ── Initialize bus ─────────────────────────

RuntimeBus.init()

# ── Sidebar: Controls ──────────────────────

with st.sidebar:
    st.header("Controls")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col2:
        if st.button("🗑️ Reset"):
            RuntimeBus.reset()
            st.rerun()

    auto_refresh = st.checkbox("Auto-refresh (2s)", value=False)
    st.divider()
    st.caption("Events pushed via RuntimeEventBus → Snapshot → Dashboard")

# ── Auto-refresh ───────────────────────────

if auto_refresh:
    time.sleep(2)
    st.rerun()

# ── Capture snapshot ───────────────────────

snapshot = RuntimeBus.snapshot()
metrics = RuntimeBus.get_metrics().summary()

# ── Row 1: State Overview ──────────────────

st.header("State Overview")

col1, col2, col3, col4 = st.columns(4)
with col1:
    state = snapshot.current_state or "N/A"
    st.metric("Current State", state)
with col2:
    score = snapshot.evaluation_score
    st.metric("Evaluation Score", score if score is not None else "N/A")
with col3:
    st.metric("Total Runs", metrics.get("total_runs", 0))
with col4:
    has_err = "⚠️ Yes" if snapshot.has_errors else "✅ No"
    st.metric("Has Errors", has_err)

if snapshot.last_error:
    st.warning(f"Last Error: {snapshot.last_error}")

# ── Row 2: Metrics ─────────────────────────

st.header("Metrics")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Success Rate", f"{metrics.get('success_rate', 0):.0%}")
with col2:
    st.metric("Avg Score", metrics.get("avg_score", "N/A"))
with col3:
    st.metric("Reflections", metrics.get("reflection_count", 0))
with col4:
    st.metric("Meta-Reflections", metrics.get("meta_reflection_count", 0))

col5, col6 = st.columns(2)
with col5:
    st.metric("Transitions", metrics.get("total_transitions", 0))
with col6:
    dur = metrics.get("avg_duration_ms", 0)
    st.metric("Avg Duration", f"{dur:.1f}ms")

# ── Row 3: State Timeline ──────────────────

st.header("State Transition Timeline")

timeline = snapshot.timeline
if timeline:
    timeline_data = [
        {
            "From": t.get("from", ""),
            "To": t.get("to", ""),
            "Status": t.get("status", ""),
            "Duration (ms)": f"{t.get('duration_ms', 0):.1f}",
            "Input": (t.get("input", "") or "")[:60],
            "Output": (t.get("output", "") or "")[:60],
        }
        for t in timeline
    ]
    st.dataframe(timeline_data, use_container_width=True, hide_index=True)
else:
    st.info("No transitions recorded yet. Run a pipeline to see data.")

# ── Row 4: Score History ───────────────────

st.header("Score History")
scores = metrics.get("scores", [])
if scores:
    st.line_chart({"score": scores})
else:
    st.info("No evaluation scores yet.")

# ── Row 5: Recent Events ───────────────────

st.header("Recent Events")
recent = snapshot.recent_events
if recent:
    for ev in reversed(recent[-10:]):
        etype = ev.get("event_type", "?")
        state_val = ev.get("state", "")
        status = ev.get("status", "")
        dur = ev.get("duration_ms", 0)
        ts = ev.get("timestamp", "")[:19]

        emoji = {"success": "✅", "error": "❌", "skipped": "⏭️"}.get(status, "•")
        st.text(
            f"{emoji} [{etype}] {state_val:<20} "
            f"{status:<8} {dur:>7.1f}ms  {ts}"
        )
else:
    st.info("No events recorded yet.")

# ── Footer ─────────────────────────────────

st.divider()
st.caption(f"Snapshot captured at: {snapshot.captured_at}")
