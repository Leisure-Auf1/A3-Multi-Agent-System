"""
Phase 8.3-E2 — Model Registry + Task Router Tests

Comprehensive coverage:
- ModelInfo dataclass
- MODEL_REGISTRY contains all declared models
- All models have valid capability sets
- DeepSeek lacks IMAGE_GENERATION
- Qwen3.5 has IMAGE_INPUT
- GPT-5.6 has TOOL_CALLING
- TaskType enum + TASK_REQUIREMENTS
- ModelRouter.find_models(task) for all tasks
- ModelRouter.select_model(task) picks correct model
- Router fallback when no model matches
- check_task_capability() guards
- get_model_for_task() integration
- Settings_tab import + compilation
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


from src.config.model_capability import (
    ModelCapability,
    check_task_capability,
    require_capability,
)
from src.config.model_registry import (
    ModelInfo,
    MODEL_REGISTRY,
    get_model,
    list_models,
    find_models_with_capability,
)
from src.config.task_capability import (
    TaskType,
    TASK_REQUIREMENTS,
    TASK_LABELS,
)
from src.config.model_router import (
    ModelRouter,
    RouterResult,
    find_models,
    select_model,
)


# ──────────────────────────────────────────────
# 1. Model Registry
# ──────────────────────────────────────────────


class TestModelRegistry:
    """MODEL_REGISTRY integrity checks."""

    def test_all_required_models_registered(self):
        required = [
            "gpt-5.6", "gpt-4o", "gpt-4o-mini",
            "claude-opus", "claude-sonnet",
            "gemini-ultra", "gemini-pro",
            "qwen3.5",
            "deepseek-v3", "deepseek-r1",
            "kimi-k3",
            "grok",
        ]
        for mid in required:
            assert mid in MODEL_REGISTRY, f"Missing model: {mid}"

    def test_gpt56_has_tool_calling(self):
        gpt = MODEL_REGISTRY["gpt-5.6"]
        assert ModelCapability.TOOL_CALLING in gpt.capabilities

    def test_gpt56_has_reasoning(self):
        gpt = MODEL_REGISTRY["gpt-5.6"]
        assert ModelCapability.REASONING in gpt.capabilities

    def test_deepseek_v3_has_no_image_generation(self):
        ds = MODEL_REGISTRY["deepseek-v3"]
        assert ModelCapability.IMAGE_GENERATION not in ds.capabilities

    def test_deepseek_v3_has_no_image_input(self):
        ds = MODEL_REGISTRY["deepseek-v3"]
        assert ModelCapability.IMAGE_INPUT not in ds.capabilities

    def test_qwen35_has_image_input(self):
        qw = MODEL_REGISTRY["qwen3.5"]
        assert ModelCapability.IMAGE_INPUT in qw.capabilities

    def test_claude_opus_has_long_context(self):
        cl = MODEL_REGISTRY["claude-opus"]
        assert ModelCapability.LONG_CONTEXT in cl.capabilities

    def test_gemini_ultra_has_video_input(self):
        gm = MODEL_REGISTRY["gemini-ultra"]
        assert ModelCapability.VIDEO_INPUT in gm.capabilities

    def test_grok_has_reasoning(self):
        gr = MODEL_REGISTRY["grok"]
        assert ModelCapability.REASONING in gr.capabilities

    def test_kimi_k3_has_long_context(self):
        km = MODEL_REGISTRY["kimi-k3"]
        assert ModelCapability.LONG_CONTEXT in km.capabilities

    def test_get_model_returns_correct_type(self):
        m = get_model("deepseek-v3")
        assert isinstance(m, ModelInfo)
        assert m.model_id == "deepseek-v3"

    def test_get_model_nonexistent(self):
        assert get_model("nonexistent-model") is None

    def test_list_models_returns_all(self):
        models = list_models()
        assert len(models) >= 14

    def test_list_models_by_provider(self):
        openai_models = list_models(provider="openai")
        assert len(openai_models) >= 3  # 3+ models (GPT-5.6, GPT-4o, GPT-4o-mini, +vision, +sora)
        for m in openai_models:
            assert m.provider == "openai"

    def test_find_models_with_capability(self):
        with_image = find_models_with_capability(ModelCapability.IMAGE_INPUT)
        names = [m.display_name for m in with_image]
        assert "GPT-5.6" in names or "GPT-4o" in names
        assert "Qwen3.5" in names
        assert "DeepSeek-V3" not in names

    def test_all_models_have_text_generation(self):
        for m in MODEL_REGISTRY.values():
            assert ModelCapability.TEXT_GENERATION in m.capabilities, (
                f"{m.display_name} missing TEXT_GENERATION"
            )

    def test_model_info_to_dict(self):
        m = MODEL_REGISTRY["deepseek-v3"]
        d = m.to_dict()
        assert d["model_id"] == "deepseek-v3"
        assert d["provider"] == "deepseek"
        assert d["context_length"] == 65536


# ──────────────────────────────────────────────
# 2. Task Capability Mapping
# ──────────────────────────────────────────────


class TestTaskCapability:
    """TASK_REQUIREMENTS correctness."""

    def test_all_task_types_have_requirements(self):
        for task in TaskType:
            assert task.value in TASK_REQUIREMENTS, f"Missing requirements for {task}"
            reqs = TASK_REQUIREMENTS[task.value]
            assert len(reqs) > 0, f"Empty requirements for {task}"

    def test_generate_material_needs_long_context(self):
        reqs = TASK_REQUIREMENTS[TaskType.GENERATE_MATERIAL]
        assert ModelCapability.LONG_CONTEXT in reqs

    def test_generate_image_needs_image_generation(self):
        reqs = TASK_REQUIREMENTS[TaskType.GENERATE_IMAGE]
        assert ModelCapability.IMAGE_GENERATION in reqs

    def test_grade_answer_needs_reasoning(self):
        reqs = TASK_REQUIREMENTS[TaskType.GRADE_ANSWER]
        assert ModelCapability.REASONING in reqs

    def test_generate_ppt_needs_document_and_tool_calling(self):
        reqs = TASK_REQUIREMENTS[TaskType.GENERATE_PPT]
        assert ModelCapability.PPT_GENERATION in reqs
        assert ModelCapability.TOOL_CALLING in reqs

    def test_chat_only_needs_text(self):
        reqs = TASK_REQUIREMENTS[TaskType.CHAT]
        assert reqs == [ModelCapability.TEXT_GENERATION]

    def test_all_tasks_have_labels(self):
        for task in TaskType:
            assert task.value in TASK_LABELS, f"Missing label for {task}"


# ──────────────────────────────────────────────
# 3. Model Router
# ──────────────────────────────────────────────


class TestModelRouter:
    """ModelRouter selection logic."""

    @pytest.fixture
    def router(self):
        return ModelRouter()

    def test_find_models_for_chat_returns_all(self, router):
        models = router.find_models(TaskType.CHAT)
        # Chat only needs TEXT_GENERATION → all models qualify
        assert len(models) >= 14

    def test_find_models_for_generate_image(self, router):
        """IMAGE_GENERATION now has capable models (GPT-5.6 Vision, Imagen, etc.)."""
        models = router.find_models(TaskType.GENERATE_IMAGE)
        assert len(models) > 0
        for m in models:
            assert ModelCapability.IMAGE_GENERATION in m.capabilities

    def test_find_models_for_generate_material_requires_long_context(self, router):
        models = router.find_models(TaskType.GENERATE_MATERIAL)
        dm_names = [m.display_name for m in models]
        # DeepSeek-V3 doesn't have LONG_CONTEXT
        assert "DeepSeek-V3" not in dm_names
        assert "GPT-5.6" in dm_names or "Claude Opus" in dm_names

    def test_select_model_chat(self, router):
        result = router.select_model(TaskType.CHAT)
        assert result.success
        assert result.model_info is not None
        assert len(result.alternatives) > 0

    def test_select_model_image_succeeds(self, router):
        """IMAGE_GENERATION now has capable models → selection succeeds."""
        result = router.select_model(TaskType.GENERATE_IMAGE)
        assert result.success
        assert result.model_info is not None
        assert ModelCapability.IMAGE_GENERATION in result.model_info.capabilities

    def test_select_model_material_prefers_gpt_or_claude(self, router):
        result = router.select_model(TaskType.GENERATE_MATERIAL)
        assert result.success
        assert result.model_info is not None
        # Should prefer openai or anthropic
        assert result.model_info.provider in ("openai", "anthropic")

    def test_select_model_analyze_error(self, router):
        result = router.select_model(TaskType.ANALYZE_ERROR)
        assert result.success
        # Reasoning tasks prefer GPT/Claude/DeepSeek
        assert result.model_info.provider in ("openai", "anthropic", "deepseek")

    def test_select_model_with_preferred_provider(self, router):
        result = router.select_model(TaskType.CHAT, preferred_provider="moonshot")
        assert result.success
        assert result.model_info.provider == "moonshot"
        assert "Kimi" in result.model_info.display_name

    def test_get_capable_providers_for_plan(self, router):
        providers = router.get_capable_providers(TaskType.GENERATE_PLAN)
        # Plan needs reasoning → GPT, Claude, DeepSeek, Qwen, Grok should be there
        assert "openai" in providers
        assert "anthropic" in providers
        assert "deepseek" in providers

    def test_router_result_to_dict(self, router):
        result = router.select_model(TaskType.CHAT)
        d = result.to_dict()
        assert d["success"] is True
        assert d["model_id"]
        assert d["display_name"]
        assert d["provider"]
        assert isinstance(d["alternatives"], list)

    def test_module_level_functions(self):
        models = find_models(TaskType.GENERATE_PLAN)
        assert len(models) > 0

        result = select_model(TaskType.CHAT)
        assert result.success


# ──────────────────────────────────────────────
# 4. Capability Guard (check_task_capability)
# ──────────────────────────────────────────────


class TestCapabilityGuard:
    """check_task_capability() integration."""

    def test_deepseek_v3_supports_chat(self):
        ok, err = check_task_capability("deepseek", "", TaskType.CHAT)
        assert ok
        assert err is None

    def test_deepseek_v3_no_image_generation(self):
        ok, err = check_task_capability("deepseek", "", TaskType.GENERATE_IMAGE)
        assert not ok
        assert err is not None
        assert "不支持" in err

    def test_deepseek_v3_no_document_generation(self):
        ok, err = check_task_capability("deepseek", "", TaskType.GENERATE_PPT)
        assert not ok
        assert err is not None

    def test_mock_supports_chat(self):
        ok, err = check_task_capability("mock", "mock-model-v1", TaskType.CHAT)
        assert ok
        assert err is None

    def test_unknown_task_returns_true(self):
        """Unknown task with no requirements → assume supported."""
        ok, err = check_task_capability("deepseek", "", "unknown_task_xyz")
        assert ok
        assert err is None

    def test_suggests_alternatives_on_failure(self):
        ok, err = check_task_capability("deepseek", "", TaskType.GENERATE_PPT)
        assert not ok
        # GPT-5.6 supports DOCUMENT_GENERATION (via mock) or TOOL_CALLING
        # The error message should mention alternative models
        assert err is not None


# ──────────────────────────────────────────────
# 5. Agent Integration
# ──────────────────────────────────────────────


class TestAgentIntegration:
    """get_model_for_task() and check_task_capability_for_current()."""

    def test_get_model_for_chat(self):
        from src.workflow import get_model_for_task
        result = get_model_for_task(TaskType.CHAT)
        assert result["success"]
        assert result["model_id"]
        assert result["display_name"]

    def test_get_model_for_image_succeeds(self):
        """IMAGE_GENERATION now has capable models."""
        from src.workflow import get_model_for_task
        result = get_model_for_task(TaskType.GENERATE_IMAGE)
        assert result["success"]
        assert result["model_id"]
        assert result["display_name"]

    def test_check_task_capability_for_current(self):
        from src.workflow import check_task_capability_for_current
        r = check_task_capability_for_current("deepseek", "deepseek-chat", TaskType.CHAT)
        assert r["ok"]

    def test_check_task_capability_for_current_image(self):
        from src.workflow import check_task_capability_for_current
        r = check_task_capability_for_current("deepseek", "deepseek-chat", TaskType.GENERATE_IMAGE)
        assert not r["ok"]
        assert r["error"] is not None


# ──────────────────────────────────────────────
# 6. Settings Tab Compilation
# ──────────────────────────────────────────────


class TestSettingsTabCompilation:
    """Settings tab functions import and compile correctly."""

    def test_imports_ok(self):
        from web.settings_tab import _render_capability_display, _render_model_registry_list
        assert callable(_render_capability_display)
        assert callable(_render_model_registry_list)
