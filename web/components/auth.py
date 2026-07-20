"""
PR #3 — Auth UI Components (i18n-ready, Phase 19.4)

Login, Register, and Guest login forms.
Manages st.session_state.{token, user_id, display_name}.
"""
from __future__ import annotations

import streamlit as st
from web.utils.api import A3APIClient, A3APIError
from web.i18n import t


def render_auth_gate(api: A3APIClient) -> bool:
    """Render login/register/gate gate.

    Returns True when user is authenticated (token in session_state).
    Returns False while awaiting login.
    """
    if st.session_state.get("token"):
        return True  # Already authenticated

    st.markdown(f"## 🤖 {t('auth.title')}")
    st.markdown("---")
    tab_login, tab_register, tab_guest = st.tabs(
        [t("auth.tab_login"), t("auth.tab_register"), t("auth.tab_guest")])

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
    email = st.text_input(t("auth.email"), key="login_email",
                          placeholder="you@example.com")
    password = st.text_input(t("auth.password"), type="password", key="login_password")
    if st.button(t("auth.btn_login"), type="primary", key="btn_login",
                 disabled=not (email and password)):
        try:
            result = api.login(email, password)
            _persist_auth(result)
            st.rerun()
        except A3APIError as e:
            st.error(t("auth.err_login", detail=e.detail))


def _render_register(api: A3APIClient) -> None:
    email = st.text_input(t("auth.email"), key="reg_email",
                          placeholder="you@example.com")
    name = st.text_input(t("auth.name"), key="reg_name")
    password = st.text_input(t("auth.password"), type="password", key="reg_password",
                             help=t("auth.pw_help"))
    if st.button(t("auth.btn_register"), type="primary", key="btn_register",
                 disabled=not (email and password)):
        try:
            result = api.register(email, password, name)
            _persist_auth(result)
            st.rerun()
        except A3APIError as e:
            st.error(t("auth.err_register", detail=e.detail))


def _render_guest(api: A3APIClient) -> None:
    name = st.text_input(t("auth.guest_name"), key="guest_name",
                         placeholder="Guest")
    if st.button(t("auth.btn_guest"), type="primary", key="btn_guest"):
        try:
            result = api.guest(name or "Guest")
            _persist_auth(result)
            st.rerun()
        except A3APIError as e:
            st.error(t("auth.err_guest", detail=e.detail))


def render_logout(api: A3APIClient) -> None:
    """Render logout button in sidebar."""
    if st.button(t("auth.logout"), use_container_width=True):
        try:
            api.logout(st.session_state.get("token"))
        except Exception:
            pass
        for key in ["token", "user_id", "display_name"]:
            st.session_state.pop(key, None)
        st.rerun()
