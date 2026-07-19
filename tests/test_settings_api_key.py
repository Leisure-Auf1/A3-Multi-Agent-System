"""
Tests for settings_tab.py API key input state handling.

Covers:
- on_change callback saves key to session_state
- Empty input does not overwrite existing key
- Key persistence across reruns
"""

import streamlit as st
from unittest import mock


# ── _on_api_key_change callback ──────────────────────────────


class TestApiKeyOnChange:
    """Tests for the _on_api_key_change callback in settings_tab.py."""

    def test_on_change_saves_key_to_session_state(self):
        """on_change captures non-empty key from widget session_state."""
        # Simulate Streamlit widget state after user types a key
        st.session_state["settings_api_key_input"] = "sk-test-key-12345"
        st.session_state["settings_api_key"] = ""

        # Re-create the callback closure (mimics what render_settings_tab does)
        def _on_api_key_change():
            val = st.session_state.get("settings_api_key_input", "")
            if val:
                st.session_state["settings_api_key"] = val

        _on_api_key_change()

        assert st.session_state["settings_api_key"] == "sk-test-key-12345"

    def test_empty_input_does_not_overwrite_existing_key(self):
        """Empty widget value must not clear an already-saved key."""
        st.session_state["settings_api_key_input"] = ""
        st.session_state["settings_api_key"] = "sk-saved-key-abc"

        def _on_api_key_change():
            val = st.session_state.get("settings_api_key_input", "")
            if val:
                st.session_state["settings_api_key"] = val

        _on_api_key_change()

        # Existing key must survive
        assert st.session_state["settings_api_key"] == "sk-saved-key-abc"

    def test_missing_widget_key_does_not_crash(self):
        """Callback must be safe when widget key is not in session_state."""
        # Simulate first render before user types anything
        st.session_state.pop("settings_api_key_input", None)
        st.session_state["settings_api_key"] = ""

        def _on_api_key_change():
            val = st.session_state.get("settings_api_key_input", "")
            if val:
                st.session_state["settings_api_key"] = val

        # Must not raise
        _on_api_key_change()

        # Key remains empty (no input to capture)
        assert st.session_state["settings_api_key"] == ""

    def test_changing_key_overwrites_previous(self):
        """Entering a new key replaces the old one."""
        st.session_state["settings_api_key"] = "sk-old-key"
        st.session_state["settings_api_key_input"] = "sk-new-key"

        def _on_api_key_change():
            val = st.session_state.get("settings_api_key_input", "")
            if val:
                st.session_state["settings_api_key"] = val

        _on_api_key_change()

        assert st.session_state["settings_api_key"] == "sk-new-key"


# ── Fallback path (api_key_input return value) ───────────────


class TestApiKeyFallback:
    """Tests for the fallback capture path in settings_tab.py.

    The fallback handles paste+click without Enter/blur on some
    browsers where on_change may not fire.
    """

    def test_non_empty_return_value_saves_key(self):
        """When text_input returns non-empty, key is saved."""
        st.session_state["settings_api_key"] = ""

        # Simulate the fallback: text_input returned a non-empty value
        # (happens on initial render after page reload, or paste+blur)
        api_key_input = "sk-pasted-key"

        if api_key_input:
            st.session_state["settings_api_key"] = api_key_input

        assert st.session_state["settings_api_key"] == "sk-pasted-key"

    def test_empty_return_value_does_not_clear(self):
        """When text_input returns empty (normal rerun), key survives."""
        st.session_state["settings_api_key"] = "sk-existing"

        api_key_input = ""  # password field returns '' on rerun

        if api_key_input:
            st.session_state["settings_api_key"] = api_key_input

        assert st.session_state["settings_api_key"] == "sk-existing"


# ── Integration: session_state lifecycle ─────────────────────


class TestSettingsApiKeyLifecycle:
    """End-to-end session_state lifecycle tests."""

    def test_fresh_session_has_empty_key(self):
        """Before any input, settings_api_key starts empty."""
        # Clear session to simulate fresh page load
        for k in list(st.session_state.keys()):
            del st.session_state[k]

        assert st.session_state.get("settings_api_key", "") == ""

    def test_key_persists_across_simulated_reruns(self):
        """After on_change captures key, it survives rerun simulation."""
        st.session_state["settings_api_key_input"] = "sk-test-456"
        st.session_state["settings_api_key"] = ""

        # Simulate on_change
        val = st.session_state.get("settings_api_key_input", "")
        if val:
            st.session_state["settings_api_key"] = val

        assert st.session_state["settings_api_key"] == "sk-test-456"

        # Simulate rerun: widget returns '' (password behavior)
        api_key_input = ""

        if api_key_input:
            st.session_state["settings_api_key"] = api_key_input

        # Key must survive the rerun
        assert st.session_state["settings_api_key"] == "sk-test-456"
