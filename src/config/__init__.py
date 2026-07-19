"""
Phase 4.0 — User LLM Configuration Layer

Provides user-configurable LLM settings that persist across sessions.
Reads/writes llm.json in platform-appropriate config directory.

Storage:
  Linux:   ~/.a3-agent/config/llm.json
  Windows: %APPDATA%/A3-Agent/config/llm.json

Usage:
    from src.config import load_llm_config, save_llm_config, LLMConfig

    cfg = load_llm_config()
    print(cfg.provider, cfg.model)

    cfg.provider = "deepseek"
    cfg.api_key = "sk-xxx"
    save_llm_config(cfg)
"""

from src.config.llm_config import LLMConfig, load_llm_config, save_llm_config, get_config_path
from src.config.secret_manager import encrypt_api_key, decrypt_api_key

__all__ = [
    "LLMConfig",
    "load_llm_config",
    "save_llm_config",
    "get_config_path",
    "encrypt_api_key",
    "decrypt_api_key",
]
