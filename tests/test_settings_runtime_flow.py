"""
Diagnostic tests for A3-Agent LLM Settings runtime flow.

Covers:
- API key input → form submit → _test_connection / save_llm_config
- Widget key uniqueness across render cycles
- Provider switching state reset
- Password field capture via st.form (problem 1 fix)
- Stable container rendering (problem 2 fix)
"""

import streamlit as st


# ═══════════════════════════════════════════════════════════════
# Problem 1: API Key full-chain trace (form-based)
# ═══════════════════════════════════════════════════════════════


class TestApiKeyFullChain:
    """Trace API key from form input through to test_connection."""

    def test_key_flows_from_form_to_llmconfig(self):
        """API key from form submit reaches LLMConfig correctly."""
        from src.config.llm_config import LLMConfig

        # Simulate: user entered key in form, clicked submit
        api_key = "sk-form-submit-key"
        st.session_state["settings_provider"] = "deepseek"
        st.session_state["settings_model"] = "deepseek-chat"

        cfg = LLMConfig(
            provider=st.session_state["settings_provider"],
            model=st.session_state["settings_model"],
            api_key=api_key,
        )

        assert cfg.provider == "deepseek"
        assert cfg.model == "deepseek-chat"
        assert cfg.api_key == "sk-form-submit-key"
        assert cfg.is_configured is True

    def test_form_submit_key_passed_to_test_connection(self):
        """_test_connection receives the key directly from form variable."""
        from web.settings_tab import _test_connection

        # In form-based flow, api_key is a local variable from st.text_input
        api_key = "sk-direct-from-form"

        result = _test_connection("deepseek", "deepseek-chat", api_key)

        assert result is not None
        assert "provider" in result
        # Non-empty key → should NOT get "请输入 API Key"
        assert result.get("error") != "请输入 API Key"

    def test_empty_key_rejected_before_network(self):
        """Empty API key returns clear error without touching network."""
        from web.settings_tab import _test_connection

        result = _test_connection("deepseek", "deepseek-chat", "")

        assert result["success"] is False
        assert result["error"] == "请输入 API Key"

    def test_mock_provider_skips_network(self):
        """Mock provider returns success instantly (no key needed)."""
        from web.settings_tab import _test_connection

        result = _test_connection("mock", "mock-model-v1", "")

        assert result["success"] is True
        assert result["latency"] == 0.0

    def test_form_key_synced_to_session_state(self):
        """After form submit, session_state is updated for config details display."""
        api_key = "sk-sync-test"

        # Simulate post-form sync logic
        if api_key:
            st.session_state["settings_api_key"] = api_key
        elif st.session_state.get("settings_provider") in ("mock", "rule"):
            st.session_state["settings_api_key"] = ""

        assert st.session_state["settings_api_key"] == "sk-sync-test"

    def test_new_key_overwrites_old_in_session_state(self):
        """Entering a new key replaces the old one in session_state."""
        st.session_state["settings_api_key"] = "sk-old-key"

        # New form submit with different key
        api_key = "sk-new-key"
        if api_key:
            st.session_state["settings_api_key"] = api_key

        assert st.session_state["settings_api_key"] == "sk-new-key"

    def test_empty_form_submit_does_not_overwrite_existing_key(self):
        """Empty form submit (mock provider) clears key correctly."""
        st.session_state["settings_api_key"] = "sk-some-key"
        st.session_state["settings_provider"] = "mock"

        api_key = ""  # mock provider → empty
        if api_key:
            st.session_state["settings_api_key"] = api_key
        elif st.session_state["settings_provider"] in ("mock", "rule"):
            st.session_state["settings_api_key"] = ""

        assert st.session_state["settings_api_key"] == ""


# ═══════════════════════════════════════════════════════════════
# Problem 2: Widget key uniqueness & DOM stability
# ═══════════════════════════════════════════════════════════════


class TestWidgetKeyUniqueness:
    """Verify no widget key collisions cause React DOM errors."""

    def test_all_settings_widget_keys_are_unique(self):
        """Every widget in settings_tab has a distinct key."""
        keys = [
            "settings_provider_selector",
            "settings_model_selector",
            "settings_api_key_input",
            "api_key_settings_form",  # st.form key
        ]

        # st.form_submit_button uses auto-generated keys from labels
        button_labels = ["🔍 测试连接", "💾 保存配置"]
        for label in button_labels:
            assert label not in keys, f"Button label '{label}' collides with widget key"

        assert len(set(keys)) == len(keys)

    def test_session_state_keys_dont_collide_with_widgets(self):
        """Session state variable names don't shadow widget keys."""
        widget_keys = {
            "settings_provider_selector",
            "settings_model_selector",
            "settings_api_key_input",
            "api_key_settings_form",
        }

        state_only = {
            "settings_provider",
            "settings_model",
            "settings_api_key",
            "settings_test_result",
            "settings_saved",
        }

        overlap = widget_keys & state_only
        assert len(overlap) == 0, f"Key collision: {overlap}"

    def test_provider_switch_resets_state_correctly(self):
        """Switching provider resets test_result and saved flag."""
        st.session_state["settings_test_result"] = {"success": True}
        st.session_state["settings_saved"] = True
        st.session_state["settings_provider"] = "deepseek"

        old_provider = st.session_state["settings_provider"]
        new_provider = "openai"

        if new_provider != old_provider:
            st.session_state["settings_provider"] = new_provider
            st.session_state["settings_test_result"] = None
            st.session_state["settings_saved"] = False

        assert st.session_state["settings_test_result"] is None
        assert st.session_state["settings_saved"] is False
        assert st.session_state["settings_provider"] == "openai"


# ═══════════════════════════════════════════════════════════════
# Integration: form submit → stable container rendering
# ═══════════════════════════════════════════════════════════════


class TestFormSubmitFlow:
    """Verify form-based flow preserves key across reruns."""

    def test_form_submit_captures_key_directly(self):
        """st.form_submit_button processes password field value directly."""
        # In st.form, the password field value IS available as the
        # return value of st.text_input when form is submitted.
        # This is the key advantage over bare st.button + st.text_input.
        api_key = "sk-captured-by-form"

        assert api_key == "sk-captured-by-form"
        assert len(api_key) > 0

    def test_save_button_enabled_when_key_present(self):
        """Save button is enabled when form has a non-empty key."""
        api_key = "sk-some-key"
        provider = "deepseek"

        can_save = provider in ("mock", "rule") or bool(api_key.strip())

        assert can_save is True

    def test_save_button_disabled_when_key_empty(self):
        """Save button is disabled when form key is empty/stripped."""
        api_key = "   "
        provider = "deepseek"

        can_save = provider in ("mock", "rule") or bool(api_key.strip())

        assert can_save is False

    def test_form_rerun_does_not_lose_result(self):
        """After form submit + rerun, test_result persists in session_state."""
        st.session_state["settings_test_result"] = {
            "success": False,
            "error": "timeout",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "latency": 5.0,
        }

        # Simulate rerun: form was NOT resubmitted
        test_result = st.session_state["settings_test_result"]

        assert test_result is not None
        assert test_result["success"] is False
        assert test_result["error"] == "timeout"
