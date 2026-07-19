"""
PR #3 — Chat UI Components

Thread list, message display, and chat input.
"""
from __future__ import annotations

import streamlit as st
from web.utils.api import A3APIClient, A3APIError


def render_chat_sidebar(api: A3APIClient) -> None:
    """Render chat thread list in sidebar. Returns selected thread_id."""
    st.sidebar.markdown("### 💬 Chat Threads")

    if st.sidebar.button("➕ New Chat", use_container_width=True):
        try:
            api.create_thread("New Chat")
            st.session_state.selected_thread = None
            st.rerun()
        except A3APIError as e:
            st.sidebar.error(f"Failed: {e.detail}")

    try:
        threads = api.get_threads() or []
    except A3APIError:
        threads = []

    st.session_state.thread_list = threads

    if not threads:
        st.sidebar.caption("No threads yet. Start a new chat!")
        st.session_state.selected_thread = None
        return

    for t in threads:
        tid = t.get("id", "")
        title = t.get("title", "Chat")[:30]
        updated = t.get("updated_at", "")[:10]

        active = st.session_state.get("selected_thread") == tid
        btn_label = f"{'🔵 ' if active else ''}{title}  _{updated}_"

        if st.sidebar.button(btn_label, key=f"thread_{tid}",
                             use_container_width=True):
            st.session_state.selected_thread = tid
            st.rerun()


def render_chat_main(api: A3APIClient) -> None:
    """Render main chat view: message history + input."""
    st.markdown("### 💬 Chat")

    thread_id = st.session_state.get("selected_thread")

    # ── Message History ──────────────────────────────
    messages = []
    if thread_id:
        try:
            messages = api.get_messages(thread_id) or []
        except A3APIError:
            st.warning("Could not load messages.")

    if messages:
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            with st.chat_message(role):
                st.markdown(content)
    elif thread_id:
        st.caption("No messages yet. Say hello!")
    else:
        st.info("👈 Select a thread from the sidebar or create a new chat.")

    # ── Chat Input ───────────────────────────────────
    prompt = st.chat_input("Type your message...",
                           disabled=(not thread_id))

    if prompt:
        # Echo user message
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = api.send_message(prompt, thread_id=thread_id)
                    content = result.get("content", "(no response)")
                    st.markdown(content)
                except A3APIError as e:
                    st.error(f"Error: {e.detail}")
