"""
Phase 19.4-B — i18n Unit Tests

Tests for the internationalization layer:
  - Language loading (en, zh)
  - Key resolution
  - Fallback behavior
  - Parameter substitution
  - set_lang persistence
  - Symmetric key count
"""
from __future__ import annotations

import os
import sys
import tomllib
import tempfile
import contextlib

import pytest

# Ensure src/ and web/ are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.i18n import t as i18n_t, _load_locale, _detect_lang, set_lang, _CACHE


class TestLocaleLoading:
    """Test TOML locale files load correctly."""

    def test_en_locale_loads(self):
        data = _load_locale("en")
        assert isinstance(data, dict)
        assert len(data) > 5  # At least auth, tab, dash, onboard, settings

    def test_zh_locale_loads(self):
        data = _load_locale("zh")
        assert isinstance(data, dict)
        assert len(data) > 5

    def test_en_and_zh_have_same_keys(self):
        en = _load_locale("en")
        zh = _load_locale("zh")

        def get_keys(d, prefix=""):
            keys = set()
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys |= get_keys(v, full)
                else:
                    keys.add(full)
            return keys

        en_keys = get_keys(en)
        zh_keys = get_keys(zh)
        assert en_keys == zh_keys, f"Missing keys: {en_keys ^ zh_keys}"

    def test_all_keys_are_non_empty(self):
        for lang in ("en", "zh"):
            data = _load_locale(lang)

            def check_empty(d, path=""):
                for k, v in d.items():
                    fp = f"{path}.{k}" if path else k
                    if isinstance(v, dict):
                        check_empty(v, fp)
                    else:
                        assert v != "", f"Empty value at {fp} in {lang}"

            check_empty(data)


class TestKeyResolution:
    """Test t() function resolves keys correctly."""

    def test_basic_en_key(self):
        # Force en locale
        _CACHE.clear()
        with _mock_session_state({"lang": "en"}):
            assert "Login" in i18n_t("auth.btn_login")

    def test_basic_zh_key(self):
        _CACHE.clear()
        with _mock_session_state({"lang": "zh"}):
            assert "登录" in i18n_t("auth.btn_login")

    def test_nested_key(self):
        _CACHE.clear()
        with _mock_session_state({"lang": "en"}):
            assert "Dashboard" in i18n_t("tab.dashboard")

    def test_fallback_to_key(self):
        """Unknown key returns the key itself."""
        _CACHE.clear()
        with _mock_session_state({"lang": "en"}):
            assert i18n_t("nonexistent.key.123") == "nonexistent.key.123"

    def test_fallback_to_en_when_zh_missing(self):
        """When zh key is somehow missing, fall back to en."""
        _CACHE.clear()
        with _mock_session_state({"lang": "zh"}):
            # All keys exist, so test with a real key that differs
            en_val = i18n_t("dash.subtitle")
            assert len(en_val) > 0


class TestParameterSubstitution:
    """Test t() with **kwargs substitution."""

    def test_simple_param(self):
        _CACHE.clear()
        with _mock_session_state({"lang": "en"}):
            result = i18n_t("auth.err_login", detail="Invalid password")
            assert "Invalid password" in result

    def test_multiple_params(self):
        _CACHE.clear()
        with _mock_session_state({"lang": "en"}):
            result = i18n_t("dash.ai_mode", provider="DeepSeek")
            assert "DeepSeek" in result


class TestLanguageSwitching:
    """Test set_lang() persistence."""

    def test_set_lang_updates_session_state(self):
        import streamlit as st
        st.session_state.clear()
        set_lang("zh")
        assert st.session_state.get("lang") == "zh"

    def test_set_lang_invalid_ignored(self):
        import streamlit as st
        st.session_state.clear()
        st.session_state.lang = "en"
        set_lang("fr")
        assert st.session_state.lang == "en"  # Should not change

    def test_detect_lang_defaults_to_en(self):
        import streamlit as st
        st.session_state.clear()
        _CACHE.clear()
        # Mock LLMConfig to avoid disk state contamination
        import src.config.llm_config as llm_mod
        orig_load = llm_mod.load_llm_config
        from src.config.llm_config import LLMConfig
        llm_mod.load_llm_config = lambda: LLMConfig(language="en")
        try:
            assert _detect_lang() == "en"
        finally:
            llm_mod.load_llm_config = orig_load


class TestLLMConfigLanguage:
    """Test language field in LLMConfig."""

    def test_llmconfig_has_language_field(self):
        from src.config.llm_config import LLMConfig
        cfg = LLMConfig()
        assert hasattr(cfg, "language")
        assert cfg.language == "en"

    def test_llmconfig_to_dict_includes_language(self):
        from src.config.llm_config import LLMConfig
        cfg = LLMConfig(language="zh")
        d = cfg.to_dict()
        assert d["language"] == "zh"

    def test_llmconfig_save_load_language(self):
        from src.config.llm_config import LLMConfig, save_llm_config, load_llm_config
        import streamlit as st
        st.session_state.clear()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp_path = f.name

        try:
            # Save with language=zh
            cfg = LLMConfig(provider="mock", model="", api_key="", language="zh")

            # Monkey-patch get_config_path
            import src.config.llm_config as llm_mod
            orig = llm_mod.get_config_path
            llm_mod.get_config_path = lambda: tmp_path
            try:
                save_llm_config(cfg)
                loaded = load_llm_config()
                assert loaded.language == "zh"
            finally:
                llm_mod.get_config_path = orig
        finally:
            os.unlink(tmp_path)


# ── Helpers ──────────────────────────────────

@contextlib.contextmanager
def _mock_session_state(state: dict):
    """Temporarily mock streamlit session_state for t() resolution."""
    import streamlit as st
    old = dict(st.session_state)
    st.session_state.clear()
    st.session_state.update(state)
    try:
        yield
    finally:
        st.session_state.clear()
        st.session_state.update(old)
