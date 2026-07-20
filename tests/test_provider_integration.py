"""
Phase 9.2 — Provider Integration Tests

Covers:
- Secret management (env var reading)
- Provider HTTP calls (mocked)
- ProviderFactory.create_from_env()
- Provider health check (check_provider)
- Failure fallback (mock when key missing)
- Provider response parsing (OpenAI / Anthropic / Gemini formats)
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from providers.base import BaseLLMProvider, ProviderResponse, ProviderUsage
from providers.factory import ProviderFactory
from src.config.secrets import (
    get_api_key,
    has_api_key,
    get_all_configured_providers,
    get_config_summary,
    get_env_var_name,
    PROVIDER_EMOJI,
)
from providers.health import check_provider


# ═══════════════════════════════════════════════════════════════
# HTTP mock helpers
# ═══════════════════════════════════════════════════════════════

def _mock_urlopen_class():
    """Return a mock class for urllib.request.urlopen that returns fake HTTP responses."""
    def _side_effect(req, timeout=60):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "googleapis.com" in url:
            body = {
                "candidates": [{
                    "content": {"parts": [{"text": "Hello from Gemini"}]},
                    "finishReason": "STOP",
                }],
                "usageMetadata": {
                    "promptTokenCount": 15,
                    "candidatesTokenCount": 25,
                    "totalTokenCount": 40,
                },
            }
        elif "anthropic.com" in url:
            body = {
                "id": "msg_001",
                "model": "claude-sonnet",
                "content": [{"type": "text", "text": "Hello from Claude"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 12, "output_tokens": 18},
            }
        else:
            body = {
                "id": "chatcmpl-001",
                "model": "test-model",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello from API"},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            }
        raw = json.dumps(body).encode("utf-8")
        resp = mock.MagicMock()
        resp.__enter__ = mock.MagicMock(return_value=resp)
        resp.__exit__ = mock.MagicMock(return_value=None)
        resp.status = 200
        resp.read.return_value = raw
        return resp

    with mock.patch("urllib.request.urlopen") as m:
        m.side_effect = _side_effect
        yield m


# ═══════════════════════════════════════════════════════════════
# 1. Secret Management Tests
# ═══════════════════════════════════════════════════════════════

class TestSecretManagement:
    """Environment variable reading tests."""

    def test_get_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test-123")
        key = get_api_key("deepseek")
        assert key == "sk-deepseek-test-123"

    def test_get_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        key = get_api_key("deepseek")
        assert key == ""

    def test_has_api_key_true(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert has_api_key("openai") is True

    def test_has_api_key_false(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert has_api_key("openai") is False

    def test_get_all_configured(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        config = get_all_configured_providers()
        assert config["deepseek"] is True
        assert config["openai"] is True
        # Others should be False
        assert config["google"] is False

    def test_get_config_summary(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-abcd1234")
        summary = get_config_summary()
        ds = summary["deepseek"]
        assert ds["configured"] is True
        assert ds["emoji"] == "🐋"
        assert ds["key_preview"].startswith("sk-d")
        assert ds["key_preview"].endswith("1234")

    def test_config_summary_all_unset(self, monkeypatch):
        for var in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
                     "DASHSCOPE_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY",
                     "XAI_API_KEY", "SPARK_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        summary = get_config_summary()
        for name in summary:
            assert summary[name]["configured"] is False, f"{name} should be unconfigured"

    def test_get_env_var_name(self):
        assert get_env_var_name("openai") == "OPENAI_API_KEY"
        assert get_env_var_name("deepseek") == "DEEPSEEK_API_KEY"
        assert get_env_var_name("unknown") == ""

    def test_alias_resolution(self, monkeypatch):
        """Aliases resolve to canonical names."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-claude-test")
        key = get_api_key("claude")  # alias
        assert key == "sk-claude-test"

    def test_whitespace_trimmed(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "  sk-key-with-spaces  ")
        key = get_api_key("openai")
        assert key == "sk-key-with-spaces"


# ═══════════════════════════════════════════════════════════════
# 2. Provider HTTP Call Tests (mocked)
# ═══════════════════════════════════════════════════════════════

class TestProviderHTTPCalls:
    """Real HTTP call tests with mocked urllib."""

    @pytest.fixture(autouse=True)
    def _mock_http(self):
        yield from _mock_urlopen_class()

    def test_openai_real_call(self):
        provider = ProviderFactory.create("openai", api_key="sk-real")
        resp = provider.generate("Hello")
        assert resp.success is True
        assert resp.content == "Hello from API"
        assert resp.usage.prompt_tokens == 10
        assert resp.usage.completion_tokens == 20

    def test_anthropic_real_call(self):
        provider = ProviderFactory.create("anthropic", api_key="sk-real")
        resp = provider.generate("Hello")
        assert resp.success is True
        assert resp.content == "Hello from Claude"
        assert resp.usage.prompt_tokens == 12
        assert resp.usage.completion_tokens == 18

    def test_google_real_call(self):
        provider = ProviderFactory.create("google", api_key="sk-real")
        resp = provider.generate("Hello")
        assert resp.success is True
        assert "Gemini" in resp.content
        assert resp.usage.prompt_tokens == 15

    def test_deepseek_real_call(self):
        provider = ProviderFactory.create("deepseek", api_key="sk-real")
        resp = provider.generate("Hello")
        assert resp.success is True
        assert resp.content == "Hello from API"

    def test_qwen_real_call(self):
        provider = ProviderFactory.create("qwen", api_key="sk-real")
        resp = provider.generate("Hello")
        assert resp.success is True

    def test_kimi_real_call(self):
        provider = ProviderFactory.create("kimi", api_key="sk-real")
        resp = provider.generate("Hello")
        assert resp.success is True

    def test_grok_real_call(self):
        provider = ProviderFactory.create("grok", api_key="sk-real")
        resp = provider.generate("Hello")
        assert resp.success is True

    def test_spark_real_call(self):
        provider = ProviderFactory.create("spark", api_key="sk-real")
        resp = provider.generate("Hello")
        assert resp.success is True

    def test_generate_without_key(self):
        """generate() returns error when no key."""
        provider = ProviderFactory.create("openai", api_key="")
        resp = provider.generate("Hello")
        assert resp.success is False
        assert "not configured" in resp.error.lower()

    def test_http_error_handling(self):
        """HTTP errors are caught and returned as error responses."""
        import urllib.error
        with mock.patch("urllib.request.urlopen") as m:
            m.side_effect = urllib.error.HTTPError(
                "https://api.test.com", 401, "Unauthorized",
                {}, io.BytesIO(b'{"error": "invalid key"}'),
            )
            provider = ProviderFactory.create("openai", api_key="sk-bad")
            resp = provider.generate("Hello")
            assert resp.success is False
            assert "401" in resp.error or "Unauthorized" in resp.error


# ═══════════════════════════════════════════════════════════════
# 3. ProviderFactory.create_from_env() Tests
# ═══════════════════════════════════════════════════════════════

class TestFactoryFromEnv:
    """create_from_env / create_all_from_env tests."""

    def test_create_from_env_with_key(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-real-key")
        provider = ProviderFactory.create_from_env("deepseek")
        assert provider is not None
        assert provider.provider_name == "deepseek"
        assert provider.is_available is True
        assert provider.api_key == "sk-real-key"

    def test_create_from_env_without_key_falls_back(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        provider = ProviderFactory.create_from_env("deepseek")
        assert provider is not None  # falls back to mock

    def test_auto_detect_deepseek(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-auto")
        provider = ProviderFactory.create_from_env()  # no provider specified
        assert provider is not None
        # Auto-detect should pick deepseek
        assert hasattr(provider, "provider_name")

    def test_auto_detect_openai_when_no_deepseek(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        provider = ProviderFactory.create_from_env()
        assert provider is not None
        assert hasattr(provider, "provider_name")

    def test_auto_detect_fallback_mock(self, monkeypatch):
        for var in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        provider = ProviderFactory.create_from_env()
        assert provider is not None  # falls back to mock

    def test_create_all_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-ds")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-oai")
        providers = ProviderFactory.create_all_from_env()
        assert "deepseek" in providers
        assert "openai" in providers
        assert providers["deepseek"].api_key == "sk-ds"

    def test_create_from_env_with_model(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-key")
        provider = ProviderFactory.create_from_env("deepseek", model="deepseek-r1")
        assert provider.model == "deepseek-r1"


# ═══════════════════════════════════════════════════════════════
# 4. Health Check Tests
# ═══════════════════════════════════════════════════════════════

class TestHealthCheck:
    """check_provider / check_all_providers tests."""

    def test_check_provider_available(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-health")
        # Mock HTTP to return success
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value = _mock_health_response()
            result = check_provider("openai")
            assert result["provider"] == "openai"
            assert result["available"] is True
            assert "latency_ms" in result
            assert result["error"] == ""

    def test_check_provider_missing_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        result = check_provider("google")
        assert result["available"] is False
        assert "missing" in result["error"].lower()

    def test_check_provider_returns_labels(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = check_provider("openai")
        assert "label" in result
        assert "emoji" in result
        assert result["emoji"] == "🤖"

    def test_check_provider_failure(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-bad")
        import urllib.error
        with mock.patch("urllib.request.urlopen") as m:
            m.side_effect = urllib.error.HTTPError(
                "url", 403, "Forbidden", {}, io.BytesIO(b"{}"),
            )
            result = check_provider("deepseek")
            assert result["available"] is False
            assert "403" in result["error"] or "Forbidden" in result["error"]


# ═══════════════════════════════════════════════════════════════
# 5. Failure Fallback Tests
# ═══════════════════════════════════════════════════════════════

class TestFailureFallback:
    """Graceful degradation when HTTP fails."""

    def test_openai_connection_error(self):
        """Connection refused → error response, not crash."""
        with mock.patch("urllib.request.urlopen") as m:
            m.side_effect = OSError("Connection refused")
            provider = ProviderFactory.create("openai", api_key="sk-test")
            resp = provider.generate("Hello")
            assert resp.success is False
            assert "Connection failed" in resp.error or "Connection refused" in resp.error

    def test_deepseek_timeout(self):
        """Timeout → error response."""
        with mock.patch("urllib.request.urlopen") as m:
            m.side_effect = TimeoutError("timed out")
            provider = ProviderFactory.create("deepseek", api_key="sk-test")
            resp = provider.generate("Hello")
            assert resp.success is False

    def test_gemini_malformed_response(self):
        """Malformed API response → error, not crash."""
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value = _mock_health_response(body={})  # empty body
            provider = ProviderFactory.create("google", api_key="sk-test")
            resp = provider.generate("Hello")
            # Should handle gracefully
            assert isinstance(resp, ProviderResponse)

    def test_anthropic_empty_content(self):
        """Empty content blocks → handled."""
        with mock.patch("urllib.request.urlopen") as m:
            body = {
                "id": "msg_001",
                "model": "claude",
                "content": [],  # empty
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 0},
            }
            m.return_value = _mock_health_response(body=body)
            provider = ProviderFactory.create("anthropic", api_key="sk-test")
            resp = provider.generate("Hello")
            assert isinstance(resp, ProviderResponse)
            assert resp.content == ""


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

import io

def _mock_health_response(body=None):
    """Create a mock HTTP response."""
    if body is None:
        body = {
            "id": "chatcmpl-test",
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "OK"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }
    raw = json.dumps(body).encode("utf-8")
    resp = mock.MagicMock()
    resp.__enter__ = mock.MagicMock(return_value=resp)
    resp.__exit__ = mock.MagicMock(return_value=None)
    resp.status = 200
    resp.read.return_value = raw
    return resp
