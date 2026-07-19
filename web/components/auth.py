"""
PR #3 — Auth UI Components

Login, Register, and Guest login forms.
Manages st.session_state.{token, user_id, display_name}.
"""
from __future__ import annotations

import streamlit as st
from web.utils.api import A3APIClient, A3APIError


def render_auth_gate(api: A3APIClient) -> bool:
    """Render login/register/gate gate.

    Returns True when user is authenticated (token in session_state).
    Returns False while awaiting login.
    """
    if st.session_state.get("token"):
        return True  # Already authenticated

    st.markdown("## 🤖 A3 AI Learning Assistant")
    st.markdown("---")
    tab_login, tab_register, tab_guest = st.tabs(
        ["🔑 Login", "📝 Register", "👤 Guest"])

    with tab_login:
        _render_login(api)
    with tab_register:
        _render_register(api)
    with tab_guest:
        _render_guest(api)

    return st.session_state.get("token") is not None


def _persist_auth(result) -> None:
    """Store auth result in session state."""
    st.session_state.token = result.token
    st.session_state.user_id = result.user_id
    st.session_state.display_name = result.display_name
    api = st.session_state.get("api")
    if api:
        api.set_token(result.token)


def _render_login(api: A3APIClient) -> None:
    email = st.text_input("Email", key="login_email",
                          placeholder="you@example.com")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", type="primary", key="btn_login",
                 disabled=not (email and password)):
        try:
            result = api.login(email, password)
            _persist_auth(result)
            st.rerun()
        except A3APIError as e:
            st.error(f"Login failed: {e.detail}")


def _render_register(api: A3APIClient) -> None:
    email = st.text_input("Email", key="reg_email",
                          placeholder="you@example.com")
    name = st.text_input("Display Name", key="reg_name")
    password = st.text_input("Password", type="password", key="reg_password",
                             help="Minimum 4 characters")
    if st.button("Create Account", type="primary", key="btn_register",
                 disabled=not (email and password)):
        try:
            result = api.register(email, password, name)
            _persist_auth(result)
            st.rerun()
        except A3APIError as e:
            st.error(f"Registration failed: {e.detail}")


def _render_guest(api: A3APIClient) -> None:
    name = st.text_input("Your Name (optional)", key="guest_name",
                         placeholder="Guest")
    if st.button("Continue as Guest", type="primary", key="btn_guest"):
        try:
            result = api.guest(name or "Guest")
            _persist_auth(result)
            st.rerun()
        except A3APIError as e:
            st.error(f"Guest login failed: {e.detail}")


def render_logout(api: A3APIClient) -> None:
    """Render logout button in sidebar."""
    if st.button("🚪 Logout", use_container_width=True):
        try:
            api.logout(st.session_state.get("token"))
        except Exception:
            pass
        for key in ["token", "user_id", "display_name"]:
            st.session_state.pop(key, None)
        st.rerun()
