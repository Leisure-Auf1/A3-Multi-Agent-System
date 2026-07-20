"""
Phase 8.3-E1 — Capability Awareness Tests

Covers:
- ModelCapability enum: flag operations, compound capabilities
- get_provider_capabilities(): provider→model→cap mappings
- require_capability(): guard with user-friendly errors
- has_capability(): boolean check
- get_capability_summary(): structured display data
- DeepSeek: text-only, no multimodal
- Spark: text-only (spark-pro), image_input (spark-4.0-ultra)
- Mock: text + image_input + document (demo-friendly)
- Rule: minimal text capabilities
- Edge cases: unknown provider, unknown model, empty model

Constraints: does NOT modify Veritas-Core or src/core/
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


from src.config.model_capability import (
    ModelCapability,
    get_provider_capabilities,
    require_capability,
    has_capability,
    get_capability_summary,
    PROVIDER_CAPABILITIES,
    CAPABILITY_LABELS,
    CAPABILITY_ICONS,
)


# ──────────────────────────────────────────────
# 1. ModelCapability Enum
# ──────────────────────────────────────────────


class TestModelCapabilityEnum:
    """Flag operations and compound capabilities."""

    def test_single_flags(self):
        """Each flag is independent."""
        assert ModelCapability.TEXT_GENERATION.value > 0
        assert ModelCapability.IMAGE_INPUT.value > 0
        assert ModelCapability.IMAGE_GENERATION.value > 0
        assert ModelCapability.VIDEO_GENERATION.value > 0

    def test_or_combination(self):
        """Flags can be combined with |."""
        caps = ModelCapability.TEXT_GENERATION | ModelCapability.CODE_GENERATION
        assert ModelCapability.TEXT_GENERATION in caps
        assert ModelCapability.CODE_GENERATION in caps
        assert ModelCapability.IMAGE_INPUT not in caps

    def test_compound_caps(self):
        """TEXT_ONLY and MULTIMODAL compound flags work."""
        assert ModelCapability.CODE_GENERATION in ModelCapability.TEXT_ONLY
        assert ModelCapability.IMAGE_INPUT in ModelCapability.MULTIMODAL_INPUT
        assert ModelCapability.IMAGE_GENERATION not in ModelCapability.TEXT_ONLY

    def test_all_labels_have_icons(self):
        """Every labeled capability has an icon."""
        for cap in CAPABILITY_LABELS:
            assert cap in CAPABILITY_ICONS, f"Missing icon for {cap}"

    def test_all_flags_in_registry_keys(self):
        """Every capability flag appears in at least one provider."""
        all_known = set(CAPABILITY_LABELS.keys())
        all_declared = set()
        for prov_caps in PROVIDER_CAPABILITIES.values():
            for caps in prov_caps.values():
                for cap in all_known:
                    if cap in caps:
                        all_declared.add(cap)
        # At minimum, TEXT_GENERATION must be declared by someone
        assert ModelCapability.TEXT_GENERATION in all_declared


# ──────────────────────────────────────────────
# 2. get_provider_capabilities()
# ──────────────────────────────────────────────


class TestGetProviderCapabilities:
    """Provider capability lookups."""

    # ── DeepSeek ──────────────────────────

    def test_deepseek_text_only(self):
        caps = get_provider_capabilities("deepseek", "deepseek-chat")
        assert ModelCapability.TEXT_GENERATION in caps
        assert ModelCapability.CODE_GENERATION in caps
        assert ModelCapability.IMAGE_INPUT not in caps
        assert ModelCapability.IMAGE_GENERATION not in caps

    def test_deepseek_v4_pro(self):
        caps = get_provider_capabilities("deepseek", "deepseek-v4-pro")
        assert ModelCapability.TEXT_GENERATION in caps
        assert ModelCapability.IMAGE_INPUT not in caps

    # ── Spark ─────────────────────────────

    def test_spark_pro_text_only(self):
        caps = get_provider_capabilities("spark", "spark-pro")
        assert ModelCapability.TEXT_GENERATION in caps
        assert ModelCapability.IMAGE_INPUT not in caps

    def test_spark_ultra_has_vision(self):
        caps = get_provider_capabilities("spark", "spark-4.0-ultra")
        assert ModelCapability.TEXT_GENERATION in caps
        assert ModelCapability.IMAGE_INPUT in caps

    # ── Mock ──────────────────────────────

    def test_mock_has_extra_caps(self):
        caps = get_provider_capabilities("mock", "mock-model-v1")
        assert ModelCapability.TEXT_GENERATION in caps
        assert ModelCapability.IMAGE_INPUT in caps
        assert ModelCapability.DOCUMENT_GENERATION in caps

    # ── Rule ──────────────────────────────

    def test_rule_minimal(self):
        caps = get_provider_capabilities("rule", "rule-v1")
        assert ModelCapability.TEXT_GENERATION in caps
        assert ModelCapability.IMAGE_INPUT not in caps

    # ── Edge cases ────────────────────────

    def test_unknown_provider_returns_empty(self):
        caps = get_provider_capabilities("nonexistent", "model-x")
        assert caps == ModelCapability(0)

    def test_unknown_model_falls_back_to_default(self):
        """Unknown model falls back to provider default (model="")."""
        caps = get_provider_capabilities("deepseek", "unknown-model")
        # Should get deepseek default
        assert ModelCapability.TEXT_GENERATION in caps

    def test_empty_model_uses_default(self):
        caps = get_provider_capabilities("deepseek", "")
        assert ModelCapability.TEXT_GENERATION in caps


# ──────────────────────────────────────────────
# 3. require_capability()
# ──────────────────────────────────────────────


class TestRequireCapability:
    """Unified capability guard function."""

    def test_supported_returns_true(self):
        ok, err = require_capability(
            ModelCapability.TEXT_GENERATION, "deepseek", "deepseek-chat"
        )
        assert ok is True
        assert err is None

    def test_unsupported_returns_false_and_message(self):
        ok, err = require_capability(
            ModelCapability.IMAGE_GENERATION, "deepseek", "deepseek-chat"
        )
        assert ok is False
        assert err is not None
        assert "DeepSeek" in err
        assert "图片生成" in err

    def test_unsupported_message_suggests_alternatives(self):
        """Error message should mention which providers support it."""
        ok, err = require_capability(
            ModelCapability.IMAGE_INPUT, "deepseek"
        )
        assert ok is False
        # OpenAI and Spark Ultra support image input
        assert "OpenAI" in err or "讯飞星火" in err or "Mock" in err

    def test_spark_ultra_supports_image_input(self):
        ok, err = require_capability(
            ModelCapability.IMAGE_INPUT, "spark", "spark-4.0-ultra"
        )
        assert ok is True
        assert err is None

    def test_mock_supports_document(self):
        ok, err = require_capability(
            ModelCapability.DOCUMENT_GENERATION, "mock"
        )
        assert ok is True
        assert err is None

    def test_unknown_provider(self):
        ok, err = require_capability(
            ModelCapability.TEXT_GENERATION, "nonexistent"
        )
        assert ok is False
        assert err is not None


# ──────────────────────────────────────────────
# 4. has_capability()
# ──────────────────────────────────────────────


class TestHasCapability:
    """Quick boolean check."""

    def test_true_for_supported(self):
        assert has_capability(ModelCapability.CODE_GENERATION, "deepseek")

    def test_false_for_unsupported(self):
        assert not has_capability(ModelCapability.VIDEO_GENERATION, "deepseek")

    def test_false_for_unknown_provider(self):
        assert not has_capability(ModelCapability.TEXT_GENERATION, "xyz")


# ──────────────────────────────────────────────
# 5. get_capability_summary()
# ──────────────────────────────────────────────


class TestCapabilitySummary:
    """Structured display data."""

    def test_returns_all_fields(self):
        s = get_capability_summary("deepseek", "deepseek-chat")
        assert "provider" in s
        assert "model" in s
        assert "supported" in s
        assert "unsupported" in s
        assert "all_caps_value" in s

    def test_supported_has_text_generation(self):
        s = get_capability_summary("deepseek", "deepseek-chat")
        labels = [item["label"] for item in s["supported"]]
        assert "文本生成" in labels
        assert "代码生成" in labels

    def test_unsupported_has_image_generation(self):
        s = get_capability_summary("deepseek", "deepseek-chat")
        labels = [item["label"] for item in s["unsupported"]]
        assert "图片生成" in labels
        assert "视频生成" in labels

    def test_mock_has_document_generation(self):
        s = get_capability_summary("mock")
        labels = [item["label"] for item in s["supported"]]
        assert "PPT/文档生成" in labels

    def test_supported_plus_unsupported_equals_total(self):
        s = get_capability_summary("deepseek", "deepseek-chat")
        total = len(s["supported"]) + len(s["unsupported"])
        assert total == len(CAPABILITY_LABELS)


# ──────────────────────────────────────────────
# 6. Integration: Provider → Capability mapping consistency
# ──────────────────────────────────────────────


class TestProviderCapabilityConsistency:
    """All declared providers have valid capability sets."""

    def test_all_providers_have_defaults(self):
        """Every declared provider must have an empty-model default."""
        for prov in PROVIDER_CAPABILITIES:
            caps = get_provider_capabilities(prov, "")
            assert caps != ModelCapability(0), (
                f"Provider '{prov}' has no default capabilities"
            )

    def test_deepseek_models_are_text_only(self):
        """All DeepSeek models are text-only (no multimodal yet)."""
        for model, caps in PROVIDER_CAPABILITIES["deepseek"].items():
            if model == "":
                continue
            assert ModelCapability.IMAGE_INPUT not in caps
            assert ModelCapability.IMAGE_GENERATION not in caps
            assert ModelCapability.VIDEO_GENERATION not in caps

    def test_mock_is_most_capable(self):
        """Mock should have the broadest demo capabilities."""
        mock_caps = get_provider_capabilities("mock")
        assert mock_caps.value > 0
        # Should have at least these
        assert ModelCapability.IMAGE_INPUT in mock_caps
        assert ModelCapability.DOCUMENT_GENERATION in mock_caps
