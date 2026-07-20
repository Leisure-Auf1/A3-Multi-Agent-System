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

SUPPORTED_PROVIDERS = frozenset({
    "deepseek", "openai", "anthropic", "google", "qwen",
    "kimi", "grok", "spark", "mock", "rule",
})

# Provider categorization for UI grouping
PRODUCTION_PROVIDERS = frozenset({
    "deepseek", "openai", "anthropic", "google", "qwen",
    "kimi", "grok", "spark",
})

DEMO_PROVIDERS = frozenset({"mock", "rule"})

# Full provider metadata for UI display (Phase 13.2)
PROVIDER_META = {
    "deepseek":   {"label": "DeepSeek",       "emoji": "🌊", "category": "production",
                   "models": ["deepseek-chat", "deepseek-v4-pro", "deepseek-reasoner"],
                   "default_model": "deepseek-chat",
                   "desc": "高性价比，中文能力强"},
    "openai":     {"label": "GPT (OpenAI)",    "emoji": "🤖", "category": "production",
                   "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                   "default_model": "gpt-4o",
                   "desc": "全球领先的AI能力"},
    "anthropic":  {"label": "Claude (Anthropic)", "emoji": "🧠", "category": "production",
                   "models": ["claude-sonnet", "claude-opus", "claude-haiku"],
                   "default_model": "claude-sonnet",
                   "desc": "深度推理，长上下文"},
    "google":     {"label": "Gemini (Google)", "emoji": "🔮", "category": "production",
                   "models": ["gemini-pro", "gemini-flash"],
                   "default_model": "gemini-pro",
                   "desc": "多模态理解与生成"},
    "qwen":       {"label": "通义千问 (Qwen)",  "emoji": "☁️", "category": "production",
                   "models": ["qwen3.5", "qwen-max", "qwen-plus"],
                   "default_model": "qwen3.5",
                   "desc": "阿里云大模型，国产领先"},
    "kimi":       {"label": "Kimi (Moonshot)", "emoji": "🌙", "category": "production",
                   "models": ["kimi-k3"],
                   "default_model": "kimi-k3",
                   "desc": "长文本理解专家"},
    "grok":       {"label": "Grok (xAI)",      "emoji": "🚀", "category": "production",
                   "models": ["grok"],
                   "default_model": "grok",
                   "desc": "xAI 实时推理模型"},
    "spark":      {"label": "讯飞星火 (Spark)",  "emoji": "⭐", "category": "production",
                   "models": ["spark-pro", "spark-lite", "spark-max"],
                   "default_model": "spark-pro",
                   "desc": "国产大模型，合规可靠"},
    "mock":       {"label": "Mock (演示模式)",    "emoji": "🎭", "category": "demo",
                   "models": ["mock-model-v1"],
                   "default_model": "mock-model-v1",
                   "desc": "本地演示模式 — 无需API Key"},
    "rule":       {"label": "Rule (纯规则)",      "emoji": "⚙️", "category": "demo",
                   "models": ["rule-v1"],
                   "default_model": "rule-v1",
                   "desc": "纯规则引擎 — 不调用AI模型"},
}

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
    language: str = "en"  # UI language: "en" or "zh"

    @property
    def is_configured(self) -> bool:
        """True if user has set an API key for a non-mock provider."""
        return bool(self.api_key) and self.provider not in ("mock", "rule")

    @property
    def provider_label(self) -> str:
        """Human-readable provider label from PROVIDER_META."""
        return PROVIDER_META.get(self.provider, {}).get("label", self.provider)

    @property
    def provider_emoji(self) -> str:
        """Provider emoji from PROVIDER_META."""
        return PROVIDER_META.get(self.provider, {}).get("emoji", "🔌")

    @property
    def provider_category(self) -> str:
        """Provider category: 'production' or 'demo'."""
        return PROVIDER_META.get(self.provider, {}).get("category", "production")

    def to_dict(self) -> dict:
        """Serialize for API response (API key hidden)."""
        return {
            "provider": self.provider,
            "model": self.model,
            "language": self.language,
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
    language = raw.get("language", "en")
    encrypted_key = raw.get("api_key", "")

    # Decrypt API key (pass provider for keyring lookup)
    api_key = ""
    if encrypted_key:
        try:
            api_key = decrypt_api_key(encrypted_key, provider=provider)
        except Exception:
            # Corrupted encryption → treat as unconfigured
            api_key = ""

    # Validate provider
    if provider not in SUPPORTED_PROVIDERS:
        provider = DEFAULT_CONFIG["provider"]

    return LLMConfig(provider=provider, model=model, api_key=api_key, language=language)


def save_llm_config(config: LLMConfig) -> None:
    """
    Save user LLM configuration to llm.json.

    API key is encrypted before writing.
    """
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    encrypted_key = ""
    if config.api_key:
        encrypted_key = encrypt_api_key(config.api_key, provider=config.provider)

    data = {
        "provider": config.provider,
        "model": config.model,
        "language": getattr(config, "language", "en"),
        "api_key": encrypted_key,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(path, 0o600)


# ── Phase 6.0 — Provider capability detection ──

@dataclass
class ProviderCapability:
    """Result of provider capability check."""

    provider: str
    model: str
    available: bool = False
    api_key_valid: bool = False
    model_available: bool = False
    chat_ok: bool = False
    latency_ms: float = 0.0
    error: str = ""

    @property
    def ready(self) -> bool:
        """True if provider is fully validated and ready to use."""
        return self.available and self.api_key_valid and self.model_available and self.chat_ok

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "available": self.available,
            "api_key_valid": self.api_key_valid,
            "model_available": self.model_available,
            "chat_ok": self.chat_ok,
            "ready": self.ready,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
        }


def validate_provider_capability(provider: str, model: str, api_key: str) -> ProviderCapability:
    """
    Validate that a provider/model/API-key combination works.

    Checks:
      1. Provider is supported
      2. API key is provided
      3. Provider can be instantiated
      4. Model responds to a chat completion

    This is called before saving user config to prevent broken setups.

    Returns ProviderCapability with detailed validation results.
    """
    import time
    from src.core.provider_factory import _build_from_config

    result = ProviderCapability(provider=provider, model=model)

    # ── Check 1: Provider supported ────────
    if provider not in SUPPORTED_PROVIDERS:
        result.error = f"Unsupported provider: {provider}"
        return result

    if provider in ("mock", "rule"):
        result.available = True
        result.api_key_valid = True
        result.model_available = True
        result.chat_ok = True
        return result

    # ── Check 2: API key present ───────────
    if not api_key or not api_key.strip():
        result.error = "API key is required"
        return result

    # ── Check 3: Build provider ────────────
    cfg = LLMConfig(provider=provider, model=model, api_key=api_key)
    t0 = time.time()

    try:
        provider_obj = _build_from_config(cfg)
    except Exception as e:
        result.latency_ms = (time.time() - t0) * 1000
        result.error = f"Failed to build provider: {e}"
        return result

    if provider_obj is None:
        result.error = f"Provider '{provider}' returned None"
        return result

    if not provider_obj.is_available:
        result.error = f"Provider '{provider}' is not available"
        return result

    result.available = True
    result.api_key_valid = True
    result.model_available = True

    # ── Check 4: Chat completion test ──────
    try:
        response = provider_obj.generate(
            prompt="ping",
            system_prompt="Reply with 'pong' only.",
            temperature=0.0,
            max_tokens=10,
        )
        result.latency_ms = (time.time() - t0) * 1000

        if response.success:
            result.chat_ok = True
        else:
            result.error = response.error or "Provider returned an error"
    except Exception as e:
        result.latency_ms = (time.time() - t0) * 1000
        result.error = str(e)

    return result
