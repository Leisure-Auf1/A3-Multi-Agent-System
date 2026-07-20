"""
Phase 9.2 — Secret Management (Environment Variables)

Reads API keys from environment variables. Zero hardcoded keys.

Usage:
    from src.config.secrets import get_api_key, get_all_configured_providers

    key = get_api_key("openai")      # reads OPENAI_API_KEY
    key = get_api_key("deepseek")    # reads DEEPSEEK_API_KEY

    configured = get_all_configured_providers()
    # → {"openai": True, "deepseek": False, ...}

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

# ── Environment variable mapping ──────────────────────────

# Maps provider name → env var name for API keys
_PROVIDER_ENV_MAP: Dict[str, str] = {
    "openai":     "OPENAI_API_KEY",
    "anthropic":  "ANTHROPIC_API_KEY",
    "google":     "GOOGLE_API_KEY",
    "qwen":       "DASHSCOPE_API_KEY",
    "deepseek":   "DEEPSEEK_API_KEY",
    "kimi":       "MOONSHOT_API_KEY",
    "grok":       "XAI_API_KEY",
    "spark":      "SPARK_API_KEY",
}

# Aliases mapped to canonical names
_PROVIDER_ALIASES: Dict[str, str] = {
    "claude":   "anthropic",
    "gemini":   "google",
    "moonshot": "kimi",
    "xai":      "grok",
}

# Provider human-readable names
PROVIDER_LABELS: Dict[str, str] = {
    "openai":    "GPT (OpenAI)",
    "anthropic": "Claude (Anthropic)",
    "google":    "Gemini (Google)",
    "qwen":      "通义千问 (Qwen)",
    "deepseek":  "DeepSeek",
    "kimi":      "Kimi (Moonshot)",
    "grok":      "Grok (xAI)",
    "spark":     "讯飞星火 (Spark)",
}

# Emoji per provider for UI display
PROVIDER_EMOJI: Dict[str, str] = {
    "openai":    "🤖",
    "anthropic": "🧠",
    "google":    "🔮",
    "qwen":      "☁️",
    "deepseek":  "🐋",
    "kimi":      "🌙",
    "grok":      "🚀",
    "spark":     "⭐",
}


def _resolve_provider(name: str) -> str:
    """Resolve alias to canonical provider name."""
    name = name.lower().strip()
    return _PROVIDER_ALIASES.get(name, name)


def get_api_key(provider: str) -> str:
    """
    Read API key from environment variable.

    Args:
        provider: Provider name (openai / anthropic / google / qwen /
                  deepseek / kimi / grok / spark, or aliases).

    Returns:
        API key string, or empty string if not set.
    """
    provider = _resolve_provider(provider)
    env_var = _PROVIDER_ENV_MAP.get(provider, "")
    if not env_var:
        return ""
    return os.environ.get(env_var, "").strip()


def has_api_key(provider: str) -> bool:
    """Check if an API key is configured in environment."""
    return bool(get_api_key(provider))


def get_all_configured_providers() -> Dict[str, bool]:
    """
    Check all 8 providers for configured API keys.

    Returns:
        Dict mapping canonical provider name → bool (has key).
    """
    return {name: bool(get_api_key(name)) for name in _PROVIDER_ENV_MAP}


def get_config_summary() -> Dict[str, dict]:
    """
    Get detailed configuration summary for all providers.

    Returns:
        Dict mapping provider name → {label, emoji, configured, key_preview}.
    """
    result = {}
    for name in _PROVIDER_ENV_MAP:
        key = get_api_key(name)
        configured = bool(key)
        preview = ""
        if configured:
            preview = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
        result[name] = {
            "label": PROVIDER_LABELS.get(name, name),
            "emoji": PROVIDER_EMOJI.get(name, "🔌"),
            "configured": configured,
            "key_preview": preview,
            "env_var": _PROVIDER_ENV_MAP[name],
        }
    return result


def get_env_var_name(provider: str) -> str:
    """Get the environment variable name for a provider."""
    provider = _resolve_provider(provider)
    return _PROVIDER_ENV_MAP.get(provider, "")
