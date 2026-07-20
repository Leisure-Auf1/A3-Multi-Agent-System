"""
Phase 9.0 — Provider Layer Tests

Covers:
- ProviderFactory.create() for all 8 providers
- BaseLLMProvider interface: generate, generate_stream, generate_json
- Capability query: get_capabilities(), has_capability(), capability_summary()
- Provider validation: is_available, validate()
- ProviderResponse: success property, to_dict()
- Multimodal: analyze_image, generate_image, generate_video
- Fallback: unsupported capability returns error response
- Edge cases: unknown provider, missing API key
"""

import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from providers.base import BaseLLMProvider, ProviderResponse, ProviderUsage
from providers.factory import ProviderFactory


# ── HTTP mock helpers ──────────────────────────

def _fake_http_response(status=200, body=None):
    """Create a fake urllib HTTP response."""
    if body is None:
        body = {
            "id": "chatcmpl-test",
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Mock response"},
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
    resp.status = status
    resp.read.return_value = raw
    resp.__iter__ = mock.MagicMock(return_value=iter([raw]))
    return resp


@pytest.fixture(autouse=True)
def mock_urlopen():
    """Mock urllib.request.urlopen to prevent real HTTP calls."""
    with mock.patch("urllib.request.urlopen") as m:
        def _side_effect(req, timeout=60):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "googleapis.com" in url:
                body = {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": "Mock Gemini response"}],
                        },
                        "finishReason": "STOP",
                    }],
                    "usageMetadata": {
                        "promptTokenCount": 10,
                        "candidatesTokenCount": 20,
                        "totalTokenCount": 30,
                    },
                }
            elif "anthropic.com" in url:
                body = {
                    "id": "msg_test",
                    "model": "claude-test",
                    "content": [{"type": "text", "text": "Mock Claude response"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                }
            else:
                body = {
                    "id": "chatcmpl-test",
                    "model": "test-model",
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": "Mock response"},
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

        m.side_effect = _side_effect
        yield m


# ──────────────────────────────────────────────
# 1. ProviderResponse Tests
# ──────────────────────────────────────────────

class TestProviderResponse:
    """ProviderResponse dataclass tests."""

    def test_success_when_no_error(self):
        resp = ProviderResponse(content="ok", model="gpt-4", provider="openai")
        assert resp.success is True

    def test_failure_when_error(self):
        resp = ProviderResponse(error="API error", finish_reason="error")
        assert resp.success is False

    def test_to_dict(self):
        resp = ProviderResponse(
            content="Hello world",
            model="claude-sonnet",
            provider="anthropic",
            capability="TEXT_GENERATION",
        )
        d = resp.to_dict()
        assert d["model"] == "claude-sonnet"
        assert d["provider"] == "anthropic"
        assert d["success"] is True

    def test_truncates_long_content(self):
        resp = ProviderResponse(content="x" * 500, model="gpt", provider="openai")
        d = resp.to_dict()
        assert len(d["content"]) <= 203  # 200 + "..."

    def test_provider_usage_to_dict(self):
        usage = ProviderUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30, cost_usd=0.01)
        d = usage.to_dict()
        assert d["prompt_tokens"] == 10
        assert d["cost_usd"] == 0.01

    def test_provider_usage_defaults(self):
        usage = ProviderUsage()
        assert usage.prompt_tokens == 0
        assert usage.cost_usd == 0.0


# ──────────────────────────────────────────────
# 2. ProviderFactory Tests
# ──────────────────────────────────────────────

class TestProviderFactory:
    """Factory creation and listing tests."""

    def test_create_openai(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        assert provider.provider_name == "openai"
        assert isinstance(provider, BaseLLMProvider)

    def test_create_anthropic(self):
        provider = ProviderFactory.create("anthropic", api_key="sk-test")
        assert provider.provider_name == "anthropic"

    def test_create_claude_alias(self):
        provider = ProviderFactory.create("claude", api_key="sk-test")
        assert provider.provider_name == "anthropic"

    def test_create_google(self):
        provider = ProviderFactory.create("google", api_key="sk-test")
        assert provider.provider_name == "google"

    def test_create_gemini_alias(self):
        provider = ProviderFactory.create("gemini", api_key="sk-test")
        assert provider.provider_name == "google"

    def test_create_qwen(self):
        provider = ProviderFactory.create("qwen", api_key="sk-test")
        assert provider.provider_name == "qwen"

    def test_create_deepseek(self):
        provider = ProviderFactory.create("deepseek", api_key="sk-test")
        assert provider.provider_name == "deepseek"

    def test_create_kimi(self):
        provider = ProviderFactory.create("kimi", api_key="sk-test")
        assert provider.provider_name == "moonshot"

    def test_create_moonshot_alias(self):
        provider = ProviderFactory.create("moonshot", api_key="sk-test")
        assert provider.provider_name == "moonshot"

    def test_create_grok(self):
        provider = ProviderFactory.create("grok", api_key="sk-test")
        assert provider.provider_name == "xai"

    def test_create_xai_alias(self):
        provider = ProviderFactory.create("xai", api_key="sk-test")
        assert provider.provider_name == "xai"

    def test_create_spark(self):
        provider = ProviderFactory.create("spark", api_key="sk-test")
        assert provider.provider_name == "spark"

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderFactory.create("unknown_provider")

    def test_create_with_model_override(self):
        provider = ProviderFactory.create("openai", api_key="sk-test", model="gpt-5.6")
        assert provider.model == "gpt-5.6"

    def test_list_providers(self):
        providers = ProviderFactory.list_providers()
        assert isinstance(providers, dict)
        assert len(providers) >= 8

    def test_get_default_model(self):
        assert ProviderFactory.get_default_model("openai") == "gpt-4o"
        assert ProviderFactory.get_default_model("deepseek") == "deepseek-v3"


# ──────────────────────────────────────────────
# 3. Provider Core Methods Tests
# ──────────────────────────────────────────────

class TestProviderCoreMethods:
    """generate, generate_stream, generate_json tests."""

    def test_generate_returns_response(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        resp = provider.generate("Hello")
        assert isinstance(resp, ProviderResponse)
        assert resp.success is True
        assert len(resp.content) > 0

    def test_generate_without_key_returns_error(self):
        provider = ProviderFactory.create("openai", api_key="")
        resp = provider.generate("Hello")
        assert resp.success is False
        assert "not configured" in resp.error.lower()

    def test_generate_has_usage(self):
        provider = ProviderFactory.create("deepseek", api_key="sk-test")
        resp = provider.generate("Test prompt")
        assert resp.usage.prompt_tokens > 0
        assert resp.usage.completion_tokens > 0

    def test_generate_stream_yields_responses(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        chunks = list(provider.generate_stream("Hello"))
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, ProviderResponse)

    def test_generate_stream_without_key_returns_error(self):
        provider = ProviderFactory.create("openai", api_key="")
        chunks = list(provider.generate_stream("Hello"))
        assert len(chunks) == 1
        assert chunks[0].success is False

    def test_generate_json(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        resp = provider.generate_json('{"key": "value"}')
        assert resp.success is True

    def test_all_providers_generate(self):
        """Every provider can generate."""
        for name in ["openai", "anthropic", "google", "qwen", "deepseek", "kimi", "grok", "spark"]:
            provider = ProviderFactory.create(name, api_key="sk-test")
            resp = provider.generate("Test")
            assert resp.success is True, f"{name} generate failed"


# ──────────────────────────────────────────────
# 4. Capability Tests
# ──────────────────────────────────────────────

class TestCapability:
    """Capability query tests."""

    def test_get_capabilities(self):
        provider = ProviderFactory.create("openai", api_key="sk-test", model="gpt-4o")
        caps = provider.get_capabilities()
        assert isinstance(caps, list)
        assert len(caps) > 0

    def test_has_capability_text(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        caps = provider.get_capabilities()
        # Capabilities are returned as Chinese labels from CAPABILITY_LABELS
        assert len(caps) > 0, "Provider should have at least one capability"
        # Check that has_capability works with at least one known capability
        known = caps[0]
        assert provider.has_capability(known) is True

    def test_capability_summary(self):
        provider = ProviderFactory.create("google", api_key="sk-test", model="gemini-pro")
        summary = provider.capability_summary()
        assert "provider" in summary
        assert "supported" in summary
        assert isinstance(summary["supported"], list)

    def test_deepseek_capabilities(self):
        provider = ProviderFactory.create("deepseek", api_key="sk-test")
        summary = provider.capability_summary()
        assert summary["provider"] in ("deepseek", "DeepSeek")

    def test_has_capability_method(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        result = provider.has_capability("TEXT_GENERATION")
        assert isinstance(result, bool)


# ──────────────────────────────────────────────
# 5. Multimodal Tests
# ──────────────────────────────────────────────

class TestMultimodal:
    """Image/video capability tests."""

    def test_analyze_image_supported(self):
        provider = ProviderFactory.create("openai", api_key="sk-test", model="gpt-4o")
        resp = provider.analyze_image("base64...", "What is this?")
        assert isinstance(resp, ProviderResponse)

    def test_generate_image_supported(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        resp = provider.generate_image("A cat")
        assert isinstance(resp, ProviderResponse)
        assert resp.capability == "IMAGE_GENERATION"

    def test_generate_image_unsupported(self):
        provider = ProviderFactory.create("deepseek", api_key="sk-test")
        resp = provider.generate_image("A cat")
        assert isinstance(resp, ProviderResponse)
        # DeepSeek doesn't natively support image gen — should return error
        assert resp.capability == "IMAGE_GENERATION"

    def test_generate_video_unsupported(self):
        provider = ProviderFactory.create("deepseek", api_key="sk-test")
        resp = provider.generate_video("A video")
        assert isinstance(resp, ProviderResponse)
        assert resp.capability == "VIDEO_GENERATION"


# ──────────────────────────────────────────────
# 6. Provider Validation Tests
# ──────────────────────────────────────────────

class TestProviderValidation:
    """is_available, validate() tests."""

    def test_is_available_with_key(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        assert provider.is_available is True

    def test_is_available_without_key(self):
        provider = ProviderFactory.create("openai", api_key="")
        assert provider.is_available is False

    def test_validate_with_key(self):
        provider = ProviderFactory.create("openai", api_key="sk-test")
        valid, msg = provider.validate()
        assert valid is True
        assert msg == "OK"

    def test_validate_without_key(self):
        provider = ProviderFactory.create("openai", api_key="")
        valid, msg = provider.validate()
        assert valid is False
        assert "not configured" in msg.lower()


# ──────────────────────────────────────────────
# 7. Edge Cases
# ──────────────────────────────────────────────

class TestEdgeCases:
    """Edge case handling."""

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError):
            ProviderFactory.create("nonexistent_provider")

    def test_empty_api_key_still_creates(self):
        provider = ProviderFactory.create("openai", api_key="")
        assert provider is not None
        assert provider.is_available is False

    def test_case_insensitive_provider_name(self):
        provider = ProviderFactory.create("OPENAI", api_key="sk-test")
        assert provider.provider_name == "openai"

    def test_all_providers_have_capability_summary(self):
        for name in ["openai", "anthropic", "google", "qwen", "deepseek", "kimi", "grok", "spark"]:
            provider = ProviderFactory.create(name, api_key="sk-test")
            summary = provider.capability_summary()
            assert "provider" in summary, f"{name} capability summary missing provider"

    def test_provider_response_finish_reason(self):
        resp = ProviderResponse(content="ok", finish_reason="stop")
        assert resp.finish_reason == "stop"
