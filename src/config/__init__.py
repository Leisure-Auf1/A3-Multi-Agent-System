"""
Phase 4.0–6.0 — User Configuration Layer

Provides user-configurable LLM settings, onboarding, error helpers,
system keyring integration, and provider capability detection.

Storage:
  Linux:   ~/.a3-agent/config/llm.json
  Windows: %APPDATA%/A3-Agent/config/llm.json
"""

from src.config.llm_config import (
    LLMConfig,
    load_llm_config,
    save_llm_config,
    get_config_path,
    ProviderCapability,
    validate_provider_capability,
)
from src.config.secret_manager import (
    encrypt_api_key,
    decrypt_api_key,
    delete_api_key,
    get_storage_backend,
)
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
    "delete_api_key",
    "get_storage_backend",
    # Capability detection
    "ProviderCapability",
    "validate_provider_capability",
    # Onboarding
    "OnboardingState",
    "detect_onboarding",
    # Errors
    "format_provider_error",
]
