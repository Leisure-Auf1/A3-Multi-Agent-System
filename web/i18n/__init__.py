"""
A3 i18n thin layer — lightweight TOML-based locale switching.

Supports: en, zh-CN
Fallback chain: session_state.lang → LLMConfig.language → "en"

Usage:
    from web.i18n import t
    st.button(t("btn_login"))
    st.success(t("connected", latency=1.2))
"""
from __future__ import annotations

import os
import tomllib
from typing import Any

_CACHE: dict[str, dict[str, str]] = {}
_LOCALE_DIR = os.path.dirname(os.path.abspath(__file__))
_SUPPORTED = ("en", "zh")


def _load_locale(lang: str) -> dict[str, str]:
    """Load a TOML locale file (with caching)."""
    if lang in _CACHE:
        return _CACHE[lang]
    path = os.path.join(_LOCALE_DIR, f"{lang}.toml")
    if not os.path.exists(path):
        # Fallback to en
        path = os.path.join(_LOCALE_DIR, "en.toml")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    _CACHE[lang] = data
    return data


def _detect_lang() -> str:
    """Detect language from session_state or LLMConfig."""
    try:
        import streamlit as st
        lang = st.session_state.get("lang")
        if lang in _SUPPORTED:
            return lang
    except Exception:
        pass

    # Try LLMConfig
    try:
        from src.config.llm_config import load_llm_config
        cfg = load_llm_config()
        if getattr(cfg, "language", "en") in _SUPPORTED:
            return cfg.language
    except Exception:
        pass

    return "en"


def t(key: str, **kwargs: Any) -> str:
    """Translate a key, with optional parameter substitution.

    Args:
        key: Dot-separated locale key (e.g., "tab.dashboard")
        **kwargs: Values to substitute into the template string
                  (e.g., latency=1.2 → "{latency:.2f}s")

    Returns:
        Translated string, or the key itself if not found.
    """
    lang = _detect_lang()
    strings = _load_locale(lang)

    # Support nested keys: "tab.dashboard"
    value: Any = strings
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part, None)
        else:
            value = None
            break

    if value is None:
        # Fallback: try to find in en locale
        if lang != "en":
            en_strings = _load_locale("en")
            value = en_strings
            for part in key.split("."):
                if isinstance(value, dict):
                    value = value.get(part, None)
                else:
                    value = None
                    break

    if value is None or not isinstance(value, str):
        return key  # Key not found — return as-is

    # Parameter substitution
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value

    return value


def set_lang(lang: str) -> None:
    """Set language in session_state and persist to config."""
    if lang not in _SUPPORTED:
        return
    try:
        import streamlit as st
        st.session_state.lang = lang
    except Exception:
        pass

    # Persist to LLMConfig
    try:
        from src.config.llm_config import load_llm_config, save_llm_config
        cfg = load_llm_config()
        cfg.language = lang
        save_llm_config(cfg)
    except Exception:
        pass
