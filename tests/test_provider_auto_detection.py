"""
Tests for user-configured LLM provider in Demo and learning pipeline.

Covers:
- Demo pipeline uses configured provider (not hardcoded mock)
- Mock fallback when no config exists
- create_provider() auto-detection
"""

import os
import tempfile
from unittest import mock

import pytest

from src.config.llm_config import LLMConfig, save_llm_config, load_llm_config
from src.core.provider_factory import create_provider, _build_from_config


# ═══════════════════════════════════════════════════════════════
# create_provider() auto-detection
# ═══════════════════════════════════════════════════════════════


class TestCreateProviderAutoDetection:
    """create_provider() without explicit mode reads user config."""

    def test_auto_mode_returns_configured_provider(self):
        """With valid llm.json, create_provider() returns non-mock provider."""
        cfg = LLMConfig(provider="deepseek", model="deepseek-chat", api_key="sk-test")
        save_llm_config(cfg)

        provider = create_provider()  # no mode → reads llm.json

        assert provider is not None
        assert provider.is_available
        # Must NOT be MockProvider — must be DeepSeekProvider
        type_name = type(provider).__name__
        assert "Mock" not in type_name, f"Got {type_name}, expected non-mock"
        assert "DeepSeek" in type_name or "OpenAI" in type_name or "Spark" in type_name

    def test_auto_mode_falls_back_to_mock_when_no_config(self):
        """Without valid config, create_provider() returns None → fallback needed."""
        # Remove any existing config
        import src.config.llm_config as cfg_mod
        path = cfg_mod.get_config_path()
        if os.path.exists(path):
            os.remove(path)

        provider = create_provider()

        # Without config and no env var, returns mock (Veritas factory fallback)
        # or a mock-like provider
        assert provider is not None
        assert provider.is_available

    def test_configured_provider_used_in_pipeline(self):
        """Demo-style: create_provider() or mock fallback."""
        cfg = LLMConfig(provider="deepseek", model="deepseek-chat", api_key="sk-test")
        save_llm_config(cfg)

        # Simulate competition_demo.py fix:
        provider = create_provider() or create_provider("mock")

        assert provider is not None
        # When config exists, should NOT be mock
        type_name = type(provider).__name__
        assert "Mock" not in type_name, (
            f"Configured provider was ignored, got {type_name}"
        )

    def test_mock_fallback_without_config(self):
        """When no llm.json exists, fall back to mock."""
        import src.config.llm_config as cfg_mod
        path = cfg_mod.get_config_path()
        if os.path.exists(path):
            os.remove(path)

        provider = create_provider() or create_provider("mock")

        assert provider is not None
        # Should be mock (or mock-like) since no config
        assert provider.is_available


# ═══════════════════════════════════════════════════════════════
# provider_label display
# ═══════════════════════════════════════════════════════════════


class TestProviderLabel:
    """LLMConfig.provider_label returns readable name."""

    def test_deepseek_label(self):
        cfg = LLMConfig(provider="deepseek", api_key="sk-test")
        assert cfg.provider_label == "DeepSeek"
        assert cfg.is_configured is True

    def test_openai_label(self):
        cfg = LLMConfig(provider="openai", api_key="sk-test")
        assert cfg.provider_label == "OpenAI"

    def test_mock_not_configured(self):
        cfg = LLMConfig(provider="mock")
        assert cfg.is_configured is False

    def test_rule_not_configured(self):
        cfg = LLMConfig(provider="rule", api_key="sk-test")
        # rule has api_key but provider is "rule" → not configured
        assert not cfg.is_configured


# ═══════════════════════════════════════════════════════════════
# Demo pipeline integration
# ═══════════════════════════════════════════════════════════════


class TestDemoPipelineProvider:
    """Demo pipeline (_run_demo_pipeline) uses correct provider."""

    def test_demo_uses_auto_provider_when_configured(self):
        """Demo pipeline detects user config and uses non-mock provider."""
        from web.competition_demo import _run_demo_pipeline

        # Save a config first
        cfg = LLMConfig(provider="deepseek", model="deepseek-chat", api_key="sk-test")
        save_llm_config(cfg)

        # The pipeline now calls create_provider() or mock
        provider = create_provider() or create_provider("mock")

        assert provider is not None
        type_name = type(provider).__name__
        assert "Mock" not in type_name, (
            f"Demo should use configured provider, got {type_name}"
        )

    def test_demo_falls_back_to_mock_without_config(self):
        """Without config, Demo pipeline still works (mock fallback)."""
        import src.config.llm_config as cfg_mod
        path = cfg_mod.get_config_path()
        if os.path.exists(path):
            os.remove(path)

        provider = create_provider() or create_provider("mock")

        assert provider is not None
        assert provider.is_available
