"""
A3 v4 — Product Streamlit UI (PR #3)
=====================================

Authenticated AI learning assistant using REST API bridge.
Zero direct src/ imports — all communication via FastAPI on port 8000.

Usage:
    streamlit run web/app_v4.py      # Direct
    streamlit run web/app.py         # HF Spaces (delegates here)
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from web.utils.api import A3APIClient, A3APIError
from web.components.auth import render_auth_gate, render_logout
from web.components.chat import render_chat_sidebar, render_chat_main


def main() -> None:
    """A3 v4 entry point. Auth gate → Sidebar + Chat."""

    # ═══════════════════════════════════════════════
    # Page Config
    # ═══════════════════════════════════════════════

    st.set_page_config(
        page_title="A3 AI Learning Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ═══════════════════════════════════════════════
    # API Client (cached per session)
    # ═══════════════════════════════════════════════

    if "api" not in st.session_state:
        st.session_state.api = A3APIClient()
    api: A3APIClient = st.session_state.api

    # ═══════════════════════════════════════════════
    # Auth Gate — blocks until authenticated
    # ═══════════════════════════════════════════════

    if not render_auth_gate(api):
        st.stop()  # Don't render anything past the gate

    # ═══════════════════════════════════════════════
    # Authenticated layout: Sidebar + Main
    # ═══════════════════════════════════════════════

    # ── Sidebar ────────────────────────────────────

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.display_name or 'User'}")
        st.caption(f"ID: `{st.session_state.user_id[:8]}...`")
        st.markdown("---")

        # Navigation
        st.markdown("**📋 Navigation**")
        st.markdown("💬 Chat")
        st.markdown("👤 Profile *(coming soon)*")
        st.markdown("📊 Progress *(coming soon)*")
        st.markdown("---")

        # Thread list
        render_chat_sidebar(api)
        st.markdown("---")
        render_logout(api)

    # ── Main Content ───────────────────────────────

    render_chat_main(api)


# ── Entry point ──────────────────────────────

if __name__ == "__main__":
    main()
