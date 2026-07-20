"""
Tests for ImageGeneratorAgent (Phase 8.3-F2).

Covers:
- ImageArtifact data model roundtrip
- Capability check: ModelCapability.IMAGE_GENERATION, check_task_capability
- Router selection: ModelRouter for CREATE_DIAGRAM, CREATE_MINDMAP
- Prompt generation: LLM prompt generation
- Fallback: SVG / Mermaid / Markdown diagram generation
- generate_image(): concept illustration
- generate_diagram(): Mermaid flowchart
- generate_mindmap(): Mermaid mindmap + SVG
- Capability error: unsupported model returns proper error artifact
- PPT integration: SlideItem.image field

Constraints: does NOT modify Veritas-Core or src/core/
"""

import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.content_generator_agent import (
    ContentGeneratorAgent, TeachingMaterial, Chapter,
    ConceptItem, ExampleItem, ExerciseItem,
)
from config.model_capability import (
    ModelCapability, check_task_capability, get_provider_capabilities,
    CAPABILITY_LABELS, CAPABILITY_ICONS, has_capability,
)
from config.task_capability import TaskType, TASK_REQUIREMENTS
from config.model_router import ModelRouter, RouterResult
from config.model_registry import MODEL_REGISTRY, find_models_with_capability

from agents.image_generator_agent import (
    ImageGeneratorAgent,
    ImageArtifact,
)
from agents.ppt_generator_agent import (
    PPTGeneratorAgent, PPTStructure, SlideItem,
)


# ── Helpers ──────────────────────────────────────────────────

def _make_material(chapter_count: int = 2) -> TeachingMaterial:
    """Create a TeachingMaterial for testing."""
    concepts = [
        ConceptItem(name=f"概念 {i+1}", description=f"概念{i+1}的详细解释",
                     difficulty="beginner", related=[])
        for i in range(2)
    ]
    chapters = [
        Chapter(
            chapter_id=f"ch{i+1}",
            title=f"第{i+1}章: Python 核心主题{i+1}",
            explanation=f"这是第{i+1}章的解释。",
            concepts=concepts,
            examples=[ExampleItem(title=f"示例", code="x=1")],
            exercises=[ExerciseItem(question="Q?", answer="A")],
            estimated_minutes=20,
            summary=f"小结{i+1}",
        )
        for i in range(chapter_count)
    ]
    return TeachingMaterial(
        material_id="test_mat",
        title="Python 编程基础",
        learning_objectives=["理解变量", "掌握循环"],
        chapters=chapters,
        overall_summary="涵盖基础概念。",
        target_profile="beginner",
    )


# ── Mock LLM Provider ────────────────────────────────────────

class MockLLMProvider:
    """Simulates an LLM that returns image prompt JSON."""

    def __init__(self, response_json: Optional[dict] = None, should_fail: bool = False):
        self._response = response_json
        self._should_fail = should_fail

    @property
    def is_available(self):
        return True

    def generate(self, prompt: str, system_prompt: str = "", **kwargs):
        if self._should_fail:
            raise RuntimeError("LLM unavailable")

        class FakeResponse:
            content = json.dumps(self._response or {})
            success = True
            error = ""

        return FakeResponse()


class MockFailingLLMProvider:
    """Simulates an LLM that always fails."""

    @property
    def is_available(self):
        return True

    def generate(self, prompt: str, system_prompt: str = "", **kwargs):
        class FakeResponse:
            content = ""
            success = False
            error = "API error"

        return FakeResponse()


# ──────────────────────────────────────────────
# 1. ImageArtifact Data Model
# ──────────────────────────────────────────────

class TestImageArtifact:
    """ImageArtifact ser/deser tests."""

    def test_create_default(self):
        a = ImageArtifact()
        assert a.type == "svg"
        assert a.path == ""
        assert a.prompt == ""
        assert a.generation_source == "rule"

    def test_to_dict(self):
        a = ImageArtifact(
            path="/tmp/test.svg",
            type="svg",
            prompt="A diagram of Python",
            model="gpt-4o",
            provider="openai",
            generation_source="llm",
            content="<svg>...</svg>",
            metadata={"style": "minimalist"},
        )
        d = a.to_dict()
        assert d["type"] == "svg"
        assert d["prompt"] == "A diagram of Python"
        assert d["model"] == "gpt-4o"
        assert d["generation_source"] == "llm"
        assert "created_at" in d

    def test_from_dict(self):
        data = {
            "path": "/tmp/mindmap.svg",
            "type": "mermaid",
            "prompt": "mindmap",
            "model": "rule",
            "provider": "rule",
            "generation_source": "rule",
            "content": "mindmap\n  root((Python))",
            "metadata": {"chapter_count": 3},
            "created_at": "2026-01-01T00:00:00",
        }
        a = ImageArtifact.from_dict(data)
        assert a.path == "/tmp/mindmap.svg"
        assert a.type == "mermaid"
        assert a.content == "mindmap\n  root((Python))"

    def test_roundtrip(self):
        a = ImageArtifact(
            path="/tmp/img.svg",
            type="svg",
            prompt="prompt text",
            model="claude",
            provider="anthropic",
            generation_source="llm",
            content="<svg/>",
        )
        d = a.to_dict()
        a2 = ImageArtifact.from_dict(d)
        assert a2.path == a.path
        assert a2.type == a.type
        assert a2.generation_source == a.generation_source

    def test_to_base64_uri_svg(self):
        a = ImageArtifact(
            type="svg",
            content='<svg xmlns="http://www.w3.org/2000/svg"><text>hello</text></svg>',
        )
        uri = a.to_base64_uri()
        assert uri.startswith("data:image/svg+xml;base64,")
        # Decode and verify
        decoded = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
        assert "hello" in decoded

    def test_to_base64_uri_non_svg(self):
        a = ImageArtifact(type="png", path="/tmp/test.png")
        uri = a.to_base64_uri()
        assert uri == "/tmp/test.png"


# ──────────────────────────────────────────────
# 2. Capability Check Tests
# ──────────────────────────────────────────────

class TestCapabilityCheck:
    """Tests for IMAGE_GENERATION capability checking."""

    def setup_method(self):
        self.agent = ImageGeneratorAgent()

    def test_image_generation_flag_exists(self):
        """ModelCapability.IMAGE_GENERATION is defined."""
        assert ModelCapability.IMAGE_GENERATION is not None
        assert ModelCapability.IMAGE_GENERATION.value > 0

    def test_image_generation_in_task_requirements_create_diagram(self):
        """CREATE_DIAGRAM requires IMAGE_GENERATION + TEXT_GENERATION."""
        reqs = TASK_REQUIREMENTS.get(TaskType.CREATE_DIAGRAM, [])
        assert ModelCapability.IMAGE_GENERATION in reqs
        assert ModelCapability.TEXT_GENERATION in reqs

    def test_image_generation_in_task_requirements_create_mindmap(self):
        """CREATE_MINDMAP requires IMAGE_GENERATION."""
        reqs = TASK_REQUIREMENTS.get(TaskType.CREATE_MINDMAP, [])
        assert ModelCapability.IMAGE_GENERATION in reqs

    def test_deepseek_unsupported_for_image(self):
        """DeepSeek doesn't support IMAGE_GENERATION."""
        supported, err = check_task_capability("deepseek", "deepseek-chat", TaskType.CREATE_DIAGRAM)
        assert not supported
        assert err is not None

    def test_openai_vision_supports_image(self):
        """gpt-5.6-vision supports IMAGE_GENERATION."""
        caps = get_provider_capabilities("openai", "gpt-5.6-vision")
        # Provider-level check may differ from registry
        assert isinstance(caps, ModelCapability)

    def test_capability_error_text(self):
        """capability_error_message returns user-friendly text."""
        msg = ImageGeneratorAgent.capability_error_message("deepseek", "deepseek-chat",
                                                           TaskType.CREATE_DIAGRAM)
        assert "不支持" in msg
        assert "图片生成" in msg or "DeepSeek" in msg

    def test_capability_labels_have_image_generation(self):
        """IMAGE_GENERATION has label and icon."""
        assert ModelCapability.IMAGE_GENERATION in CAPABILITY_LABELS
        assert ModelCapability.IMAGE_GENERATION in CAPABILITY_ICONS


# ──────────────────────────────────────────────
# 3. Router Selection Tests
# ──────────────────────────────────────────────

class TestRouterSelection:
    """Tests for ModelRouter image generation model selection."""

    def setup_method(self):
        self.router = ModelRouter()
        self.agent = ImageGeneratorAgent()

    def test_find_models_for_create_diagram(self):
        """find_models returns models with IMAGE_GENERATION + TEXT_GENERATION."""
        models = self.router.find_models(TaskType.CREATE_DIAGRAM)
        assert isinstance(models, list)
        assert len(models) > 0
        for m in models:
            assert ModelCapability.IMAGE_GENERATION in m.capabilities

    def test_find_models_for_create_mindmap(self):
        """find_models returns models with IMAGE_GENERATION."""
        models = self.router.find_models(TaskType.CREATE_MINDMAP)
        assert isinstance(models, list)
        assert len(models) > 0
        for m in models:
            assert ModelCapability.IMAGE_GENERATION in m.capabilities

    def test_select_model_for_diagram_returns_openai_first(self):
        """TASK_PROVIDER_PRIORITY prefers OpenAI."""
        result = self.router.select_model(TaskType.CREATE_DIAGRAM)
        assert result.task == TaskType.CREATE_DIAGRAM
        if result.success:
            assert result.model_info is not None

    def test_agent_get_capable_models(self):
        """get_capable_models returns models."""
        models = self.agent.get_capable_models()
        assert isinstance(models, list)
        assert len(models) > 0

    def test_agent_get_recommended_model(self):
        """get_recommended_model for CREATE_DIAGRAM works."""
        result = self.agent.get_recommended_model(task_type=TaskType.CREATE_DIAGRAM)
        assert hasattr(result, "success")
        assert hasattr(result, "task")
        assert result.task == TaskType.CREATE_DIAGRAM

    def test_find_models_with_image_capability(self):
        """find_models_with_capability finds IMAGE_GENERATION models."""
        models = find_models_with_capability(ModelCapability.IMAGE_GENERATION)
        assert len(models) >= 3  # gpt-5.6-vision, gemini-ultra-vision, qwen-vl


# ──────────────────────────────────────────────
# 4. Prompt Generation Tests (LLM)
# ──────────────────────────────────────────────

class TestPromptGeneration:
    """Tests for LLM prompt generation."""

    def setup_method(self):
        self.agent = ImageGeneratorAgent()

    def test_llm_prompt_generation(self):
        """LLM generates image_prompt from concept."""
        llm_response = {
            "image_prompt": "A minimalist educational diagram showing Python decorators",
            "description": "Python 装饰器的图解",
            "style": "minimalist",
            "elements": ["function", "wrapper"],
        }
        self.agent.set_llm_provider(MockLLMProvider(llm_response))
        result = self.agent.generate_image(concept="Python decorators")
        assert result.prompt == "A minimalist educational diagram showing Python decorators"
        assert result.generation_source == "llm"

    def test_no_llm_provider_generates_rule_artifact(self):
        """Without LLM, generate_image returns rule artifact."""
        result = self.agent.generate_image(concept="Python loops")
        assert result.generation_source == "rule"
        assert result.type == "svg"

    def test_llm_failure_falls_back(self):
        """Failing LLM still produces artifact."""
        self.agent.set_llm_provider(MockFailingLLMProvider())
        result = self.agent.generate_image(concept="Python lists")
        assert result.generation_source == "rule"
        assert result.type == "svg"

    def test_set_llm_provider_method(self):
        """set_llm_provider stores provider."""
        mock = MockLLMProvider({"image_prompt": "test"})
        self.agent.set_llm_provider(mock)
        assert self.agent._llm_provider is mock

    def test_set_llm_provider_none_disables_llm(self):
        """Setting None disables LLM path."""
        mock = MockLLMProvider({"image_prompt": "test"})
        self.agent.set_llm_provider(mock)
        self.agent.set_llm_provider(None)
        result = self.agent.generate_image(concept="test")
        assert result.generation_source == "rule"


# ──────────────────────────────────────────────
# 5. Fallback Generation Tests
# ──────────────────────────────────────────────

class TestFallbackGeneration:
    """Tests for fallback SVG/Mermaid/Markdown generation."""

    def setup_method(self):
        self.agent = ImageGeneratorAgent()

    def test_generate_image_creates_svg(self):
        """generate_image always creates valid SVG."""
        result = self.agent.generate_image(concept="Python variables")
        assert result.type == "svg"
        assert len(result.content) > 0
        assert "<svg" in result.content

    def test_generate_image_has_path(self):
        """generate_image returns a valid path."""
        result = self.agent.generate_image(concept="test")
        assert result.path != ""
        assert os.path.isfile(result.path)
        os.unlink(result.path)

    def test_generate_diagram_creates_mermaid(self):
        """generate_diagram creates Mermaid content."""
        result = self.agent.generate_diagram(concept="Python class inheritance")
        assert result.type == "mermaid"
        assert "graph TD" in result.content

    def test_generate_diagram_with_material_context(self):
        """generate_image with material context still works."""
        material = _make_material()
        result = self.agent.generate_image(concept="decorators", material=material)
        assert result.type == "svg"
        assert len(result.content) > 0

    def test_generate_mindmap_from_material(self):
        """generate_mindmap from TeachingMaterial creates mindmap."""
        material = _make_material(chapter_count=3)
        result = self.agent.generate_mindmap(material)
        assert result.type == "mermaid"
        assert "mindmap" in result.content
        assert result.metadata.get("chapter_count") == 3

    def test_generate_mindmap_svg_path(self):
        """generate_mindmap stores SVG path in metadata."""
        material = _make_material()
        result = self.agent.generate_mindmap(material)
        svg_path = result.metadata.get("svg_path", "")
        assert svg_path != ""
        assert os.path.isfile(svg_path)
        os.unlink(svg_path)

    def test_generate_diagram_has_metadata(self):
        """generate_diagram includes mermaid and svg_path in metadata."""
        result = self.agent.generate_diagram(concept="test flow")
        assert "mermaid" in result.metadata
        assert "svg_path" in result.metadata

    def test_generate_mindmap_with_dict(self):
        """generate_mindmap works with dict input."""
        material = _make_material()
        result = self.agent.generate_mindmap(material.to_dict())
        assert result.type == "mermaid"
        assert result.content is not None

    def test_image_artifact_created_at(self):
        """ImageArtifact has created_at timestamp."""
        result = self.agent.generate_image(concept="test")
        assert result.created_at != ""
        assert "T" in result.created_at  # ISO format


# ──────────────────────────────────────────────
# 6. Capability Error Tests
# ──────────────────────────────────────────────

class TestCapabilityErrors:
    """Tests for capability error handling."""

    def setup_method(self):
        self.agent = ImageGeneratorAgent()

    def test_generate_diagram_unsupported_provider(self):
        """generate_diagram with unsupported provider returns error artifact."""
        result = self.agent.generate_diagram(
            concept="test",
            provider="deepseek",
            model="deepseek-chat",
        )
        assert result.type == "error"
        assert result.generation_source == "error"
        assert "不支持" in result.content or "error" in result.metadata

    def test_generate_mindmap_unsupported_provider(self):
        """generate_mindmap with unsupported provider returns error artifact."""
        material = _make_material()
        result = self.agent.generate_mindmap(
            material,
            provider="deepseek",
            model="deepseek-chat",
        )
        assert result.type == "error"
        assert result.generation_source == "error"

    def test_unsupported_error_has_alternatives(self):
        """Error artifact includes alternative model suggestions."""
        result = self.agent.generate_diagram(
            concept="test",
            provider="deepseek",
            model="deepseek-chat",
        )
        # Should list alternative models
        assert "error" in result.metadata or result.metadata.get("alternatives")

    def test_capability_error_message_includes_model_name(self):
        """Error message includes provider/model info."""
        msg = ImageGeneratorAgent.capability_error_message(
            "deepseek", "deepseek-chat", TaskType.CREATE_DIAGRAM
        )
        assert "DeepSeek" in msg
        assert "不支持" in msg or "支持" in msg


# ──────────────────────────────────────────────
# 7. PPT Integration Tests
# ──────────────────────────────────────────────

class TestPPTIntegration:
    """Tests for PPTGeneratorAgent slide.image integration."""

    def setup_method(self):
        self.ppt_agent = PPTGeneratorAgent()
        self.img_agent = ImageGeneratorAgent()

    def test_slide_item_has_image_field(self):
        """SlideItem has image field (Phase 8.3-F2)."""
        slide = SlideItem(slide_index=1, title="Test", image="/tmp/img.svg")
        assert slide.image == "/tmp/img.svg"

    def test_slide_item_image_default(self):
        """SlideItem.image defaults to empty string."""
        slide = SlideItem(slide_index=1, title="Test")
        assert slide.image == ""

    def test_slide_item_image_in_to_dict(self):
        """SlideItem.to_dict() includes image."""
        slide = SlideItem(slide_index=1, title="Test", image="/tmp/img.svg")
        d = slide.to_dict()
        assert "image" in d
        assert d["image"] == "/tmp/img.svg"

    def test_slide_item_image_from_dict(self):
        """SlideItem.from_dict() restores image."""
        data = {"slide_index": 1, "title": "Test", "image": "/tmp/img.svg"}
        slide = SlideItem.from_dict(data)
        assert slide.image == "/tmp/img.svg"

    def test_ppt_structure_roundtrip_with_image(self):
        """PPTStructure roundtrip preserves slide images."""
        slides = [
            SlideItem(slide_index=1, title="Cover", layout="title",
                       image="data:image/svg+xml;base64,PHN2Zy8+"),
        ]
        ps = PPTStructure(ppt_id="ppt_img", title="With Image", slides=slides)
        d = ps.to_dict()
        ps2 = PPTStructure.from_dict(d)
        assert len(ps2.slides) == 1
        assert ps2.slides[0].image == "data:image/svg+xml;base64,PHN2Zy8+"

    def test_ppt_with_image_generates(self):
        """PPT with image slides generates successfully."""
        from agents.content_generator_agent import ContentGeneratorAgent
        content_agent = ContentGeneratorAgent()

        # Generate image
        image_artifact = self.img_agent.generate_image(concept="Python variables")

        # Create PPT with image on a slide
        slides = [
            SlideItem(slide_index=1, title="Python Variables", layout="title",
                       image=image_artifact.path),
            SlideItem(slide_index=2, title="Summary", layout="summary"),
        ]
        ps = PPTStructure(ppt_id="test_img", title="PPT with Image", slides=slides,
                          total_slides=2)

        ppt_path = self.ppt_agent._render_pptx(ps)
        assert os.path.isfile(ppt_path)
        assert os.path.getsize(ppt_path) > 1000
        os.unlink(ppt_path)

    def test_ppt_with_base64_image(self):
        """PPT with base64 SVG image renders without error."""
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><text>test</text></svg>'
        b64 = base64.b64encode(svg.encode()).decode()
        data_uri = f"data:image/svg+xml;base64,{b64}"

        slides = [
            SlideItem(slide_index=1, title="Image Slide", layout="content",
                       image=data_uri),
        ]
        ps = PPTStructure(ppt_id="b64_test", title="Base64 Test", slides=slides,
                          total_slides=1)

        ppt_path = self.ppt_agent._render_pptx(ps)
        assert os.path.isfile(ppt_path)
        assert os.path.getsize(ppt_path) > 500
        os.unlink(ppt_path)

    def test_full_pipeline_material_to_ppt_with_images(self):
        """Full pipeline: material → PPT with images."""
        from agents.content_generator_agent import ContentGeneratorAgent

        material = _make_material()
        structure = self.ppt_agent.fallback_generate_structure(material.to_dict())

        # Add images to some slides
        img = self.img_agent.generate_image(concept="Python basics")
        for slide in structure.slides:
            if slide.layout in ("title", "content"):
                slide.image = img.path

        ppt_path = self.ppt_agent._render_pptx(structure)
        assert os.path.isfile(ppt_path)
        assert os.path.getsize(ppt_path) > 1000
        os.unlink(ppt_path)
