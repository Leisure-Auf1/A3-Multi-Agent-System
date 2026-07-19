"""
Phase 4.0–5.0 — User Configuration Layer

Provides user-configurable LLM settings, onboarding, and error helpers.

Storage:
  Linux:   ~/.a3-agent/config/llm.json
  Windows: %APPDATA%/A3-Agent/config/llm.json

Usage:
    from src.config import load_llm_config, save_llm_config, LLMConfig
    from src.config import detect_onboarding, format_provider_error
"""

from src.config.llm_config import LLMConfig, load_llm_config, save_llm_config, get_config_path
from src.config.secret_manager import encrypt_api_key, decrypt_api_key

# Phase 5.0 — Onboarding & error handling
from src.config.onboarding import OnboardingState, detect_onboarding
from src.config.error_helper import format_provider_error

__all__ = [
    # Config
    "LLMConfig",
    "load_llm_config",
    "save_llm_config",
    "get_config_path",
    # Security
    "encrypt_api_key",
    "decrypt_api_key",
    # Onboarding
    "OnboardingState",
    "detect_onboarding",
    # Errors
    "format_provider_error",
]
