"""
Phase 4.0 — User LLM Configuration

Load, save, and validate user LLM configuration from llm.json.

Storage:
  Linux:   ~/.a3-agent/config/llm.json
  Windows: %APPDATA%/A3-Agent/config/llm.json

Schema:
  {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "api_key": "<encrypted>"
  }

Usage:
    from src.config.llm_config import LLMConfig, load_llm_config, save_llm_config

    cfg = load_llm_config()
    print(cfg.provider)  # "deepseek" or "mock"
    print(cfg.is_configured)  # True if api_key is set
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

from src.config.secret_manager import encrypt_api_key, decrypt_api_key


# ── Supported providers ────────────────────

SUPPORTED_PROVIDERS = frozenset({"deepseek", "openai", "spark", "mock", "rule"})

DEFAULT_CONFIG = {
    "provider": "mock",
    "model": "",
    "api_key": "",
}


# ── Config path ────────────────────────────

def get_config_dir() -> str:
    """Platform-appropriate config directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "A3-Agent", "config")
    else:
        return os.path.expanduser("~/.a3-agent/config")


def get_config_path() -> str:
    """Path to the llm.json config file."""
    return os.path.join(get_config_dir(), "llm.json")


# ── Data model ─────────────────────────────

@dataclass
class LLMConfig:
    """User LLM configuration."""

    provider: str = "mock"
    model: str = ""
    api_key: str = ""  # plaintext in memory, encrypted on disk

    @property
    def is_configured(self) -> bool:
        """True if user has set an API key for a non-mock provider."""
        return bool(self.api_key) and self.provider not in ("mock", "rule")

    @property
    def provider_label(self) -> str:
        """Human-readable provider label."""
        labels = {
            "deepseek": "DeepSeek",
            "openai": "OpenAI",
            "spark": "Spark",
            "mock": "Mock (演示)",
            "rule": "Rule (纯规则)",
        }
        return labels.get(self.provider, self.provider)

    def to_dict(self) -> dict:
        """Serialize for API response (API key hidden)."""
        return {
            "provider": self.provider,
            "model": self.model,
            "configured": self.is_configured,
        }

    def validate(self) -> list[str]:
        """Validate this configuration. Returns list of error messages."""
        errors = []
        if self.provider not in SUPPORTED_PROVIDERS:
            errors.append(
                f"Unsupported provider: {self.provider}. "
                f"Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
            )
        if self.provider not in ("mock", "rule") and not self.api_key.strip():
            errors.append("API key is required for non-mock providers.")
        return errors


# ── Persistence ────────────────────────────

def load_llm_config() -> LLMConfig:
    """
    Load user LLM configuration from llm.json.

    Returns default Mock config if file doesn't exist.
    """
    path = get_config_path()
    if not os.path.exists(path):
        return LLMConfig(**DEFAULT_CONFIG)

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, IOError):
        return LLMConfig(**DEFAULT_CONFIG)

    provider = raw.get("provider", DEFAULT_CONFIG["provider"])
    model = raw.get("model", DEFAULT_CONFIG["model"])
    encrypted_key = raw.get("api_key", "")

    # Decrypt API key
    api_key = ""
    if encrypted_key:
        try:
            api_key = decrypt_api_key(encrypted_key)
        except Exception:
            # Corrupted encryption → treat as unconfigured
            api_key = ""

    # Validate provider
    if provider not in SUPPORTED_PROVIDERS:
        provider = DEFAULT_CONFIG["provider"]

    return LLMConfig(provider=provider, model=model, api_key=api_key)


def save_llm_config(config: LLMConfig) -> None:
    """
    Save user LLM configuration to llm.json.

    API key is encrypted before writing.
    """
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    encrypted_key = ""
    if config.api_key:
        encrypted_key = encrypt_api_key(config.api_key)

    data = {
        "provider": config.provider,
        "model": config.model,
        "api_key": encrypted_key,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(path, 0o600)
