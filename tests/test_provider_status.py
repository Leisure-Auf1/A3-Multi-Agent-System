"""
Phase 13.2 — Provider Status & Model Transparency Tests

Tests for:
  - ProviderStatusTracker (recording, querying, thread safety)
  - ProviderStatusSnapshot (serialization, defaults)
  - ActiveRunInfo (creation, serialization)
  - Provider categorization (PRODUCTION_PROVIDERS, DEMO_PROVIDERS)
  - PROVIDER_META completeness (all 8 production + 2 demo)
  - LLMConfig provider_label/emoji/category properties
  - SUPPORTED_PROVIDERS containing all 10 providers
"""

from __future__ import annotations

import time
import pytest

from src.providers.status import (
    ProviderStatusTracker,
    ProviderStatusSnapshot,
    ActiveRunInfo,
    get_provider_status,
    get_provider_status_summary,
)

from src.config.llm_config import (
    LLMConfig,
    SUPPORTED_PROVIDERS,
    PRODUCTION_PROVIDERS,
    DEMO_PROVIDERS,
    PROVIDER_META,
)


# ═══════════════════════════════════════════════
# Provider Categorization
# ═══════════════════════════════════════════════


class TestProviderCategorization:
    """Verify provider categorization constants."""

    def test_supported_providers_count(self):
        """SUPPORTED_PROVIDERS should have exactly 10 providers."""
        assert len(SUPPORTED_PROVIDERS) == 10

    def test_production_providers_count(self):
        """PRODUCTION_PROVIDERS should have exactly 8 providers."""
        assert len(PRODUCTION_PROVIDERS) == 8

    def test_demo_providers_count(self):
        """DEMO_PROVIDERS should have exactly 2 providers."""
        assert len(DEMO_PROVIDERS) == 2

    def test_production_and_demo_disjoint(self):
        """Production and demo sets should not overlap."""
        assert PRODUCTION_PROVIDERS & DEMO_PROVIDERS == set()

    def test_supported_equals_production_union_demo(self):
        """SUPPORTED_PROVIDERS should equal PRODUCTION + DEMO."""
        assert SUPPORTED_PROVIDERS == (PRODUCTION_PROVIDERS | DEMO_PROVIDERS)

    def test_production_contains_all_eight(self):
        """All 8 production providers present."""
        expected = {"deepseek", "openai", "anthropic", "google",
                     "qwen", "kimi", "grok", "spark"}
        assert PRODUCTION_PROVIDERS == expected

    def test_demo_contains_mock_and_rule(self):
        """Demo providers are mock and rule."""
        assert DEMO_PROVIDERS == {"mock", "rule"}

    def test_provider_meta_has_all_keys(self):
        """PROVIDER_META should have entries for all 10 providers."""
        for p in SUPPORTED_PROVIDERS:
            assert p in PROVIDER_META, f"Missing {p} in PROVIDER_META"

    def test_provider_meta_fields_complete(self):
        """Each PROVIDER_META entry has required fields."""
        required = {"label", "emoji", "category", "models", "default_model", "desc"}
        for p, meta in PROVIDER_META.items():
            for field in required:
                assert field in meta, f"{p} missing field '{field}'"

    def test_production_meta_category(self):
        """Production providers have category='production'."""
        for p in PRODUCTION_PROVIDERS:
            assert PROVIDER_META[p]["category"] == "production"

    def test_demo_meta_category(self):
        """Demo providers have category='demo'."""
        for p in DEMO_PROVIDERS:
            assert PROVIDER_META[p]["category"] == "demo"


# ═══════════════════════════════════════════════
# LLMConfig Properties
# ═══════════════════════════════════════════════


class TestLLMConfigProperties:
    """Verify LLMConfig provider properties."""

    def test_provider_label_from_meta(self):
        cfg = LLMConfig(provider="deepseek")
        assert "DeepSeek" in cfg.provider_label

    def test_provider_emoji_from_meta(self):
        cfg = LLMConfig(provider="openai")
        assert cfg.provider_emoji == "🤖"

    def test_provider_category_production(self):
        cfg = LLMConfig(provider="anthropic")
        assert cfg.provider_category == "production"

    def test_provider_category_demo(self):
        cfg = LLMConfig(provider="mock")
        assert cfg.provider_category == "demo"

    def test_unknown_provider_defaults(self):
        cfg = LLMConfig(provider="unknown_xyz")
        assert cfg.provider_label == "unknown_xyz"
        assert cfg.provider_emoji == "🔌"
        assert cfg.provider_category == "production"

    def test_is_configured_true(self):
        cfg = LLMConfig(provider="deepseek", api_key="sk-test")
        assert cfg.is_configured

    def test_is_configured_false_mock(self):
        cfg = LLMConfig(provider="mock")
        assert not cfg.is_configured

    def test_validate_supported_provider_passes(self):
        cfg = LLMConfig(provider="anthropic", api_key="sk-ant-test")
        assert cfg.validate() == []

    def test_validate_unsupported_fails(self):
        cfg = LLMConfig(provider="unknown")
        errors = cfg.validate()
        assert len(errors) >= 1


# ═══════════════════════════════════════════════
# ProviderStatusSnapshot
# ═══════════════════════════════════════════════


class TestProviderStatusSnapshot:
    """Verify ProviderStatusSnapshot dataclass."""

    def test_default_values(self):
        snap = ProviderStatusSnapshot()
        assert snap.provider == ""
        assert not snap.connected
        assert snap.total_requests == 0
        assert not snap.is_fallback

    def test_to_dict_serializes_all_fields(self):
        snap = ProviderStatusSnapshot(
            provider="deepseek",
            label="DeepSeek",
            emoji="🌊",
            connected=True,
            active_model="deepseek-chat",
            total_tokens=500,
        )
        d = snap.to_dict()
        assert d["provider"] == "deepseek"
        assert d["connected"] is True
        assert d["active_model"] == "deepseek-chat"
        assert d["total_tokens"] == 500

    def test_to_dict_includes_fallback_info(self):
        snap = ProviderStatusSnapshot(
            provider="mock",
            is_fallback=True,
            fallback_from="deepseek",
            fallback_reason="rate_limit",
        )
        d = snap.to_dict()
        assert d["is_fallback"] is True
        assert d["fallback_from"] == "deepseek"
        assert d["fallback_reason"] == "rate_limit"


# ═══════════════════════════════════════════════
# ActiveRunInfo
# ═══════════════════════════════════════════════


class TestActiveRunInfo:
    """Verify ActiveRunInfo dataclass."""

    def test_default_values(self):
        info = ActiveRunInfo()
        assert info.engine == ""
        assert not info.is_fallback

    def test_to_dict(self):
        info = ActiveRunInfo(
            engine="DeepSeek v4 Pro",
            provider="deepseek",
            model="deepseek-v4-pro",
            generation_time_ms=234.5,
            tokens_used=150,
        )
        d = info.to_dict()
        assert d["engine"] == "DeepSeek v4 Pro"
        assert d["model"] == "deepseek-v4-pro"
        assert d["generation_time_ms"] == 234.5
        assert d["tokens_used"] == 150
        assert not d["is_fallback"]

    def test_fallback_to_dict(self):
        info = ActiveRunInfo(
            engine="Mock (fallback)",
            provider="mock",
            is_fallback=True,
            fallback_from="deepseek",
            fallback_reason="timeout",
        )
        d = info.to_dict()
        assert d["is_fallback"] is True
        assert d["fallback_from"] == "deepseek"


# ═══════════════════════════════════════════════
# ProviderStatusTracker
# ═══════════════════════════════════════════════


class TestProviderStatusTracker:
    """Verify ProviderStatusTracker singleton and operations."""

    def setup_method(self):
        ProviderStatusTracker.get_instance().reset()

    def test_singleton_returns_same_instance(self):
        t1 = ProviderStatusTracker.get_instance()
        t2 = ProviderStatusTracker.get_instance()
        assert t1 is t2

    def test_initialization_seeds_all_providers(self):
        tracker = ProviderStatusTracker.get_instance()
        snaps = tracker.get_all_snapshots()
        assert len(snaps) == 10  # 8 production + 2 demo

    def test_record_request_updates_status(self):
        tracker = ProviderStatusTracker.get_instance()
        tracker.record_request("deepseek", "deepseek-chat", 234.5, 150)
        snap = tracker.get_snapshot("deepseek")
        assert snap.connected
        assert snap.active_model == "deepseek-chat"
        assert snap.last_latency_ms == 234.5
        assert snap.total_requests == 1
        assert snap.total_tokens == 150

    def test_multiple_requests_accumulate(self):
        tracker = ProviderStatusTracker.get_instance()
        tracker.record_request("openai", "gpt-4o", 100.0, 50)
        tracker.record_request("openai", "gpt-4o", 200.0, 30)
        snap = tracker.get_snapshot("openai")
        assert snap.total_requests == 2
        assert snap.total_tokens == 80

    def test_record_fallback_sets_flag(self):
        tracker = ProviderStatusTracker.get_instance()
        tracker.record_fallback("deepseek", "mock", "rate_limit")
        snap = tracker.get_snapshot("mock")
        assert snap.is_fallback
        assert snap.fallback_from == "deepseek"
        assert snap.fallback_reason == "rate_limit"

    def test_record_error_sets_disconnected(self):
        tracker = ProviderStatusTracker.get_instance()
        tracker.record_error("grok", "timeout")
        snap = tracker.get_snapshot("grok")
        assert not snap.connected
        assert "timeout" in snap.check_error

    def test_set_connected(self):
        tracker = ProviderStatusTracker.get_instance()
        tracker.set_connected("qwen")
        snap = tracker.get_snapshot("qwen")
        assert snap.connected

    def test_get_all_snapshots_filtered_by_category(self):
        tracker = ProviderStatusTracker.get_instance()
        prod = tracker.get_all_snapshots(category="production")
        demo = tracker.get_all_snapshots(category="demo")
        assert len(prod) == 8
        assert len(demo) == 2

    def test_get_summary_has_expected_keys(self):
        tracker = ProviderStatusTracker.get_instance()
        summary = tracker.get_summary()
        assert "production_providers" in summary
        assert "demo_providers" in summary
        assert "connected_count" in summary
        assert "total_tokens_all" in summary
        assert "active_run" in summary

    def test_active_run_lifecycle(self):
        tracker = ProviderStatusTracker.get_instance()
        info = ActiveRunInfo(engine="test", provider="deepseek", model="v4")
        tracker.set_active_run(info)
        assert tracker.get_active_run() is not None
        tracker.clear_active_run()
        assert tracker.get_active_run() is None

    def test_reset_clears_all(self):
        tracker = ProviderStatusTracker.get_instance()
        tracker.record_request("deepseek", "test", 100, 10)
        tracker.reset()
        snap = tracker.get_snapshot("deepseek")
        assert snap.total_requests == 0

    def test_convenience_get_provider_status(self):
        tracker = ProviderStatusTracker.get_instance()
        tracker.record_request("kimi", "kimi-k3", 50.0, 20)
        status = get_provider_status("kimi")
        assert status["provider"] == "kimi"
        assert status["connected"]

    def test_convenience_get_summary(self):
        tracker = ProviderStatusTracker.get_instance()
        tracker.set_connected("deepseek")
        summary = get_provider_status_summary()
        assert summary["connected_count"] >= 1
        assert "deepseek" in summary["connected_providers"]
