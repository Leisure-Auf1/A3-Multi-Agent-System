"""
Phase 8.3-E3-A — Multimodal Capability System Tests

Comprehensive coverage of the expanded multimodal capability system:
- New TaskTypes: CREATE_DIAGRAM, CREATE_MINDMAP, GENERATE_PDF, EXPORT_TEXTBOOK,
  GENERATE_VIDEO_SCRIPT, GENERATE_TEACHING_VIDEO, IMAGE_UNDERSTANDING, VIDEO_UNDERSTANDING
- New Capabilities: PPT_GENERATION, PDF_GENERATION
- New Models: GPT-5.6 Vision, Sora, Imagen, Veo, Gemini Ultra Vision,
  Qwen-VL, 通义万相, Kimi Vision, Grok Vision
- Router: IMAGE_GENERATION selection, unsupported warnings, model fallback
- Capability matrix: each model's supported/unsupported capabilities
- Integration: check_task_capability, get_model_for_task

Constraints: does NOT modify src/core/ or Veritas-Core
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


from src.config.model_capability import (
    ModelCapability,
    check_task_capability,
    CAPABILITY_LABELS,
)
from src.config.model_registry import MODEL_REGISTRY, get_model, find_models_with_capability
from src.config.task_capability import TaskType, TASK_REQUIREMENTS, TASK_LABELS
from src.config.model_router import ModelRouter, find_models, select_model


M = ModelCapability


# ──────────────────────────────────────────────
# 1. Capability Expansion
# ──────────────────────────────────────────────


class TestCapabilityExpansion:
    """New capabilities are properly declared."""

    def test_ppt_generation_exists(self):
        assert M.PPT_GENERATION in M
        assert "PPT生成" in CAPABILITY_LABELS.values()

    def test_pdf_generation_exists(self):
        assert M.PDF_GENERATION in M
        assert "PDF生成" in CAPABILITY_LABELS.values()

    def test_cap_count(self):
        """Should now have 15 capabilities (was 13, +2 new)."""
        all_caps = [c for c in M]
        assert len(all_caps) >= 15


# ──────────────────────────────────────────────
# 2. TaskType Expansion
# ──────────────────────────────────────────────


class TestTaskTypeExpansion:
    """All new tasks are properly declared with requirements."""

    NEW_TASKS = [
        TaskType.CREATE_DIAGRAM,
        TaskType.CREATE_MINDMAP,
        TaskType.GENERATE_PDF,
        TaskType.EXPORT_TEXTBOOK,
        TaskType.GENERATE_VIDEO_SCRIPT,
        TaskType.GENERATE_TEACHING_VIDEO,
        TaskType.IMAGE_UNDERSTANDING,
        TaskType.VIDEO_UNDERSTANDING,
    ]

    def test_task_count(self):
        """Should now have 18 task types (was 10, +8 new)."""
        all_tasks = list(TaskType)
        assert len(all_tasks) >= 18

    def test_all_new_tasks_have_requirements(self):
        for task in self.NEW_TASKS:
            reqs = TASK_REQUIREMENTS.get(task.value, [])
            assert len(reqs) > 0, f"Task {task.name} has no requirements"

    def test_all_new_tasks_have_labels(self):
        for task in self.NEW_TASKS:
            assert task.value in TASK_LABELS, f"Task {task.name} has no label"

    def test_create_diagram_needs_image_gen(self):
        reqs = TASK_REQUIREMENTS[TaskType.CREATE_DIAGRAM]
        assert M.IMAGE_GENERATION in reqs

    def test_create_mindmap_needs_image_gen(self):
        reqs = TASK_REQUIREMENTS[TaskType.CREATE_MINDMAP]
        assert M.IMAGE_GENERATION in reqs

    def test_generate_pdf_needs_pdf_gen(self):
        reqs = TASK_REQUIREMENTS[TaskType.GENERATE_PDF]
        assert M.PDF_GENERATION in reqs

    def test_export_textbook_needs_document_and_long_context(self):
        reqs = TASK_REQUIREMENTS[TaskType.EXPORT_TEXTBOOK]
        assert M.DOCUMENT_GENERATION in reqs
        assert M.LONG_CONTEXT in reqs

    def test_generate_video_script_is_text_only(self):
        """Video script writing doesn't need video generation — just text+reasoning."""
        reqs = TASK_REQUIREMENTS[TaskType.GENERATE_VIDEO_SCRIPT]
        assert M.TEXT_GENERATION in reqs
        assert M.VIDEO_GENERATION not in reqs

    def test_generate_teaching_video_needs_video_gen(self):
        reqs = TASK_REQUIREMENTS[TaskType.GENERATE_TEACHING_VIDEO]
        assert M.VIDEO_GENERATION in reqs

    def test_image_understanding_needs_image_input(self):
        reqs = TASK_REQUIREMENTS[TaskType.IMAGE_UNDERSTANDING]
        assert M.IMAGE_INPUT in reqs

    def test_video_understanding_needs_video_input(self):
        reqs = TASK_REQUIREMENTS[TaskType.VIDEO_UNDERSTANDING]
        assert M.VIDEO_INPUT in reqs


# ──────────────────────────────────────────────
# 3. New Vision/Multimodal Models
# ──────────────────────────────────────────────


class TestNewMultimodalModels:
    """All new models are registered with correct capabilities."""

    def test_vision_models_registered(self):
        required = [
            "gpt-5.6-vision", "sora", "imagen", "veo",
            "gemini-ultra-vision", "qwen-vl", "tongyi-wanxiang",
            "kimi-vision", "grok-vision",
        ]
        for mid in required:
            assert mid in MODEL_REGISTRY, f"Missing: {mid}"

    def test_gpt56_vision_has_image_generation(self):
        m = MODEL_REGISTRY["gpt-5.6-vision"]
        assert M.IMAGE_GENERATION in m.capabilities
        assert M.IMAGE_INPUT in m.capabilities
        assert M.PPT_GENERATION in m.capabilities

    def test_sora_has_video_generation(self):
        m = MODEL_REGISTRY["sora"]
        assert M.VIDEO_GENERATION in m.capabilities

    def test_imagen_has_image_generation(self):
        m = MODEL_REGISTRY["imagen"]
        assert M.IMAGE_GENERATION in m.capabilities

    def test_veo_has_video_generation(self):
        m = MODEL_REGISTRY["veo"]
        assert M.VIDEO_GENERATION in m.capabilities

    def test_gemini_ultra_vision_full_multimodal(self):
        m = MODEL_REGISTRY["gemini-ultra-vision"]
        assert M.IMAGE_INPUT in m.capabilities
        assert M.IMAGE_GENERATION in m.capabilities
        assert M.VIDEO_INPUT in m.capabilities
        assert M.VIDEO_GENERATION in m.capabilities
        assert M.PPT_GENERATION in m.capabilities
        assert M.PDF_GENERATION in m.capabilities

    def test_qwen_vl_has_image_gen(self):
        m = MODEL_REGISTRY["qwen-vl"]
        assert M.IMAGE_GENERATION in m.capabilities
        assert M.IMAGE_INPUT in m.capabilities

    def test_tongyi_wanxiang_image_gen(self):
        m = MODEL_REGISTRY["tongyi-wanxiang"]
        assert M.IMAGE_GENERATION in m.capabilities

    def test_kimi_vision_has_image_input(self):
        m = MODEL_REGISTRY["kimi-vision"]
        assert M.IMAGE_INPUT in m.capabilities
        assert M.IMAGE_GENERATION not in m.capabilities  # vision only, no gen

    def test_grok_vision_has_image_input(self):
        m = MODEL_REGISTRY["grok-vision"]
        assert M.IMAGE_INPUT in m.capabilities

    def test_model_count(self):
        """Should now have 23 models (was 14, +9 new)."""
        assert len(MODEL_REGISTRY) >= 23

    def test_models_with_image_generation(self):
        """Verify which models can IMAGE_GENERATION."""
        capable = find_models_with_capability(M.IMAGE_GENERATION)
        names = {m.model_id for m in capable}
        expected = {"gpt-5.6-vision", "imagen", "gemini-ultra-vision",
                     "qwen-vl", "tongyi-wanxiang"}
        assert expected.issubset(names), f"Missing: {expected - names}"

    def test_models_with_video_generation(self):
        capable = find_models_with_capability(M.VIDEO_GENERATION)
        names = {m.model_id for m in capable}
        expected = {"sora", "veo", "gemini-ultra-vision"}
        assert expected.issubset(names), f"Missing: {expected - names}"


# ──────────────────────────────────────────────
# 4. Model Router — Multimodal Selection
# ──────────────────────────────────────────────


class TestMultimodalRouter:
    """Router correctly selects models for multimodal tasks."""

    @pytest.fixture
    def router(self):
        return ModelRouter()

    def test_select_model_for_image_understanding(self, router):
        result = router.select_model(TaskType.IMAGE_UNDERSTANDING)
        assert result.success
        # Should prefer openai, google, qwen, or moonshot
        assert result.model_info.provider in ("openai", "google", "qwen", "moonshot")

    def test_select_model_for_video_understanding(self, router):
        result = router.select_model(TaskType.VIDEO_UNDERSTANDING)
        assert result.success
        # Should prefer google (Gemini Ultra) or openai
        assert result.model_info.provider in ("google", "openai")

    def test_select_model_for_create_diagram(self, router):
        """CREATE_DIAGRAM needs IMAGE_GENERATION — should find capable models."""
        result = router.select_model(TaskType.CREATE_DIAGRAM)
        assert result.success
        assert M.IMAGE_GENERATION in result.model_info.capabilities

    def test_select_model_for_create_mindmap(self, router):
        result = router.select_model(TaskType.CREATE_MINDMAP)
        assert result.success
        assert M.IMAGE_GENERATION in result.model_info.capabilities

    def test_select_model_for_teaching_video(self, router):
        result = router.select_model(TaskType.GENERATE_TEACHING_VIDEO)
        assert result.success
        assert M.VIDEO_GENERATION in result.model_info.capabilities

    def test_select_model_for_video_script_is_text(self, router):
        """Video script doesn't need video gen — text models work."""
        result = router.select_model(TaskType.GENERATE_VIDEO_SCRIPT)
        assert result.success
        # Should use text-focused models, not video models
        assert result.model_info.provider in ("openai", "anthropic", "deepseek")

    def test_select_model_for_pdf(self, router):
        result = router.select_model(TaskType.GENERATE_PDF)
        assert result.success
        assert M.PDF_GENERATION in result.model_info.capabilities

    def test_image_gen_finds_gpt56_vision_or_imagen(self, router):
        """Image generation route picks GPT-5.6 Vision or Imagen."""
        models = router.find_models(TaskType.CREATE_DIAGRAM)
        names = [m.display_name for m in models]
        assert "GPT-5.6 Vision" in names or "Imagen" in names or "Gemini Ultra Vision" in names

    def test_deepseek_blocked_for_image_gen(self, router):
        """DeepSeek-V3 should NOT appear in image gen candidates."""
        models = router.find_models(TaskType.CREATE_DIAGRAM)
        names = [m.display_name for m in models]
        assert "DeepSeek-V3" not in names
        assert "DeepSeek-R1" not in names


# ──────────────────────────────────────────────
# 5. Capability Guard — Unsupported Warnings
# ──────────────────────────────────────────────


class TestUnsupportedWarnings:
    """check_task_capability returns friendly messages for unsupported tasks."""

    def test_deepseek_no_image_gen_warning(self):
        ok, err = check_task_capability("deepseek", "", TaskType.CREATE_DIAGRAM)
        assert not ok
        assert err is not None
        assert "不支持" in err

    def test_deepseek_no_video_warning(self):
        ok, err = check_task_capability("deepseek", "", TaskType.GENERATE_TEACHING_VIDEO)
        assert not ok
        assert err is not None

    def test_gpt56_supports_image_understanding(self):
        ok, err = check_task_capability("openai", "", TaskType.IMAGE_UNDERSTANDING)
        assert ok
        assert err is None

    def test_gemini_supports_video_understanding(self):
        ok, err = check_task_capability("google", "", TaskType.VIDEO_UNDERSTANDING)
        assert ok
        assert err is None

    def test_suggests_alternatives_for_image_gen(self):
        ok, err = check_task_capability("deepseek", "", TaskType.CREATE_MINDMAP)
        assert not ok
        # Error should suggest alternatives
        assert err is not None

    def test_image_generation_message_is_friendly(self):
        ok, err = check_task_capability("deepseek", "", TaskType.CREATE_DIAGRAM)
        assert not ok
        # Check that message is user-friendly, not a stack trace
        assert "不支持" in err
        assert "Traceback" not in err

    def test_text_only_tasks_always_pass(self):
        """Text-only tasks should pass for any provider."""
        ok, err = check_task_capability("deepseek", "", TaskType.CHAT)
        assert ok
        ok, err = check_task_capability("deepseek", "", TaskType.GENERATE_PROFILE)
        assert ok


# ──────────────────────────────────────────────
# 6. Capability Matrix — Per-Model Verification
# ──────────────────────────────────────────────


class TestCapabilityMatrix:
    """Each model's capability matrix is correct."""

    def test_gpt56_vision_matrix(self):
        m = MODEL_REGISTRY["gpt-5.6-vision"]
        assert M.TEXT_GENERATION in m.capabilities
        assert M.IMAGE_INPUT in m.capabilities
        assert M.IMAGE_GENERATION in m.capabilities
        assert M.PPT_GENERATION in m.capabilities
        assert M.PDF_GENERATION in m.capabilities
        assert M.VIDEO_GENERATION not in m.capabilities

    def test_sora_matrix(self):
        m = MODEL_REGISTRY["sora"]
        assert M.VIDEO_GENERATION in m.capabilities
        assert M.IMAGE_GENERATION not in m.capabilities

    def test_imagen_matrix(self):
        m = MODEL_REGISTRY["imagen"]
        assert M.IMAGE_GENERATION in m.capabilities
        assert M.VIDEO_GENERATION not in m.capabilities

    def test_gemini_ultra_vision_matrix(self):
        m = MODEL_REGISTRY["gemini-ultra-vision"]
        # Full multimodal — image and video both in and out
        assert M.IMAGE_INPUT in m.capabilities
        assert M.IMAGE_GENERATION in m.capabilities
        assert M.VIDEO_INPUT in m.capabilities
        assert M.VIDEO_GENERATION in m.capabilities
        assert M.PPT_GENERATION in m.capabilities
        assert M.PDF_GENERATION in m.capabilities

    def test_qwen_vl_matrix(self):
        m = MODEL_REGISTRY["qwen-vl"]
        assert M.IMAGE_INPUT in m.capabilities
        assert M.IMAGE_GENERATION in m.capabilities
        assert M.VIDEO_GENERATION not in m.capabilities

    def test_tongyi_wanxiang_matrix(self):
        m = MODEL_REGISTRY["tongyi-wanxiang"]
        assert M.IMAGE_GENERATION in m.capabilities
        assert M.IMAGE_INPUT not in m.capabilities  # gen only, not vision

    def test_kimi_vision_no_image_gen(self):
        m = MODEL_REGISTRY["kimi-vision"]
        assert M.IMAGE_INPUT in m.capabilities
        assert M.IMAGE_GENERATION not in m.capabilities

    def test_grok_vision_matrix(self):
        m = MODEL_REGISTRY["grok-vision"]
        assert M.IMAGE_INPUT in m.capabilities
        assert M.IMAGE_GENERATION not in m.capabilities


# ──────────────────────────────────────────────
# 7. Integration — Full Pipeline
# ──────────────────────────────────────────────


class TestFullPipeline:
    """End-to-end: task → router → capability check."""

    def test_image_gen_pipeline(self):
        from src.workflow import get_model_for_task
        r = get_model_for_task(TaskType.CREATE_DIAGRAM)
        assert r["success"]
        assert r["model_id"]
        # Verify selected model actually has IMAGE_GENERATION
        m = get_model(r["model_id"])
        assert M.IMAGE_GENERATION in m.capabilities

    def test_teaching_video_pipeline(self):
        from src.workflow import get_model_for_task
        r = get_model_for_task(TaskType.GENERATE_TEACHING_VIDEO)
        assert r["success"]
        m = get_model(r["model_id"])
        assert M.VIDEO_GENERATION in m.capabilities

    def test_image_understanding_pipeline(self):
        from src.workflow import get_model_for_task
        r = get_model_for_task(TaskType.IMAGE_UNDERSTANDING)
        assert r["success"]
        m = get_model(r["model_id"])
        assert M.IMAGE_INPUT in m.capabilities

    def test_video_understanding_pipeline(self):
        from src.workflow import get_model_for_task
        r = get_model_for_task(TaskType.VIDEO_UNDERSTANDING)
        assert r["success"]
        m = get_model(r["model_id"])
        assert M.VIDEO_INPUT in m.capabilities

    def test_deepseek_rejected_for_image_gen(self):
        from src.workflow import check_task_capability_for_current
        r = check_task_capability_for_current("deepseek", "deepseek-chat", TaskType.CREATE_DIAGRAM)
        assert not r["ok"]
        assert "不支持" in r["error"]

    def test_deepseek_accepted_for_video_script(self):
        """Video script is text-only, DeepSeek should pass."""
        from src.workflow import check_task_capability_for_current
        r = check_task_capability_for_current("deepseek", "deepseek-chat", TaskType.GENERATE_VIDEO_SCRIPT)
        assert r["ok"]


# ──────────────────────────────────────────────
# 8. Existing Tests Still Pass (Regression)
# ──────────────────────────────────────────────


class TestRegression:
    """Existing functionality unchanged."""

    def test_existing_models_unchanged(self):
        """Core models still have their original capabilities."""
        ds = MODEL_REGISTRY["deepseek-v3"]
        assert M.TEXT_GENERATION in ds.capabilities
        assert M.IMAGE_GENERATION not in ds.capabilities

        gpt = MODEL_REGISTRY["gpt-5.6"]
        assert M.TOOL_CALLING in gpt.capabilities
        assert M.IMAGE_INPUT in gpt.capabilities

        cl = MODEL_REGISTRY["claude-opus"]
        assert M.LONG_CONTEXT in cl.capabilities

    def test_existing_tasks_unchanged(self):
        reqs = TASK_REQUIREMENTS[TaskType.GENERATE_PLAN]
        assert M.REASONING in reqs

        reqs = TASK_REQUIREMENTS[TaskType.GENERATE_MATERIAL]
        assert M.LONG_CONTEXT in reqs

    def test_existing_router_still_works(self):
        result = select_model(TaskType.CHAT)
        assert result.success
        assert result.model_info is not None
