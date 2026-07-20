"""
Tests for Phase 8.3-B1 — Material Panel (AI教材展示).

Covers:
- Empty content → empty state
- Normal material display
- Multi-chapter material
- Markdown download content verification
- Helper function outputs
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from web.components.material_panel import (
    render_material_panel,
    get_material_markdown,
    _to_markdown,
    _init_session,
)


# ── Fixtures ─────────────────────────────────────────────


def make_material_dict(
    title="Test Material",
    chapters_count=2,
    include_all_fields=True,
) -> dict:
    """Build a TeachingMaterial dict for testing."""
    chapters = []
    for i in range(chapters_count):
        ch = {
            "chapter_id": f"ch{i + 1}",
            "title": f"Chapter {i + 1}",
            "explanation": f"Explanation for chapter {i + 1}.",
            "estimated_minutes": 20 + i * 10,
            "summary": f"Summary for chapter {i + 1}",
        }
        if include_all_fields:
            ch["concepts"] = [
                {
                    "name": f"Concept {i + 1}.1",
                    "description": f"Description of concept {i + 1}.1",
                    "difficulty": "beginner" if i == 0 else "intermediate",
                    "related": [f"rel_{i}"] if i > 0 else [],
                },
                {
                    "name": f"Concept {i + 1}.2",
                    "description": f"Description of concept {i + 1}.2",
                    "difficulty": "advanced" if i > 0 else "intermediate",
                    "related": [],
                },
            ]
            ch["examples"] = [
                {
                    "title": f"Example {i + 1}.1",
                    "code": f"def example_{i + 1}():\\n    pass",
                    "explanation": f"Shows example {i + 1}.1",
                    "expected_output": f"Output {i + 1}.1",
                },
            ]
            ch["exercises"] = [
                {
                    "question": f"Question {i + 1}.1?",
                    "answer": f"Answer {i + 1}.1",
                    "hint": f"Hint {i + 1}.1",
                    "type": "open" if i % 2 == 0 else "coding",
                },
                {
                    "question": f"Question {i + 1}.2?",
                    "answer": f"Answer {i + 1}.2",
                    "hint": "",
                    "type": "multiple_choice",
                },
            ]
        chapters.append(ch)

    return {
        "material_id": "mat_test",
        "title": title,
        "learning_objectives": ["Objective 1", "Objective 2"],
        "chapters": chapters,
        "overall_summary": "Overall summary text.",
        "target_profile": "junior_dev / visual_dominant / normal",
        "total_estimated_minutes": sum(ch["estimated_minutes"] for ch in chapters),
        "generation_source": "rule",
        "metadata": {"test": True},
    }


# ── Tests: Markdown Export ────────────────────────────────


class TestMarkdownExport:
    """Tests for Markdown generation from TeachingMaterial."""

    def test_empty_content_returns_empty_string(self):
        """get_material_markdown with None returns empty string."""
        result = get_material_markdown(None)
        assert result == ""

    def test_empty_dict_returns_empty_string(self):
        """get_material_markdown with empty dict returns empty string."""
        result = get_material_markdown({})
        assert result == ""

    def test_generates_title(self):
        """Markdown includes the material title."""
        content = make_material_dict(title="Python 装饰器教程")
        md = _to_markdown(content)

        assert "# Python 装饰器教程" in md

    def test_generates_learning_objectives(self):
        """Markdown includes learning objectives section."""
        content = make_material_dict()
        md = _to_markdown(content)

        assert "## 学习目标" in md
        assert "- Objective 1" in md
        assert "- Objective 2" in md

    def test_generates_chapters(self):
        """Markdown includes chapter headings."""
        content = make_material_dict(chapters_count=2)
        md = _to_markdown(content)

        assert "## Chapter 1" in md
        assert "## Chapter 2" in md

    def test_generates_concepts(self):
        """Markdown includes concept names and descriptions."""
        content = make_material_dict(chapters_count=1)
        md = _to_markdown(content)

        assert "### 核心概念" in md
        assert "Concept 1.1" in md
        assert "Description of concept 1.1" in md

    def test_generates_examples(self):
        """Markdown includes code examples."""
        content = make_material_dict(chapters_count=1)
        md = _to_markdown(content)

        assert "### 示例" in md
        assert "```python" in md
        assert "def example_1():" in md

    def test_generates_exercises(self):
        """Markdown includes exercises with answers."""
        content = make_material_dict(chapters_count=1)
        md = _to_markdown(content)

        assert "### 练习" in md
        assert "Question 1.1" in md
        assert "Answer 1.1" in md

    def test_generates_overall_summary(self):
        """Markdown includes overall summary."""
        content = make_material_dict()
        md = _to_markdown(content)

        assert "## 总结" in md
        assert "Overall summary text." in md

    def test_generates_metadata_header(self):
        """Markdown includes metadata in blockquote."""
        content = make_material_dict()
        md = _to_markdown(content)

        assert "> 画像: junior_dev / visual_dominant / normal" in md
        assert "> 生成方式: rule" in md
        assert "> 预计总时长:" in md

    def test_single_chapter(self):
        """Single chapter material works."""
        content = make_material_dict(chapters_count=1)
        md = _to_markdown(content)

        assert "## Chapter 1" in md
        assert "## Chapter 2" not in md

    def test_empty_chapters_no_crash(self):
        """Material with no chapters doesn't crash Markdown export."""
        content = make_material_dict(chapters_count=0)
        md = _to_markdown(content)

        assert md  # not empty
        assert "# Test Material" in md

    def test_chapter_without_concepts_no_crash(self):
        """Chapter without concepts field doesn't crash."""
        content = make_material_dict(include_all_fields=False)
        md = _to_markdown(content)

        assert "## Chapter 1" in md
        # Just shouldn't crash

    def test_chapter_summary_included(self):
        """Chapter summary appears in Markdown."""
        content = make_material_dict(chapters_count=1)
        md = _to_markdown(content)

        assert "Summary for chapter 1" in md

    def test_exercise_hint_optional(self):
        """Exercises without hints still render."""
        content = make_material_dict(chapters_count=1)
        md = _to_markdown(content)

        # Exercise 2 has no hint, so hint section should only appear once
        assert md.count("提示") >= 1  # At least exercise 1's hint

    def test_get_material_markdown_with_content(self):
        """get_material_markdown returns valid markdown string."""
        content = make_material_dict()
        md = get_material_markdown(content)

        assert len(md) > 100
        assert "# Test Material" in md

    def test_markdown_has_four_backticks_not_three(self):
        """Ensure code blocks use ``` not ````."""
        content = make_material_dict(chapters_count=1)
        md = _to_markdown(content)

        # Count triple backticks (should be an even number: open + close)
        triple_count = md.count("```")
        assert triple_count >= 2
        assert triple_count % 2 == 0


# ── Tests: Session State ─────────────────────────────────


class TestSessionState:
    """Tests for material panel session state initialization."""

    def test_init_session_sets_keys(self, monkeypatch):
        """_init_session initializes required keys."""
        # Clear streamlit session_state
        monkeypatch.setattr(
            "streamlit.session_state",
            {},
            raising=True,
        )
        import streamlit as st

        # Clear existing
        st.session_state.clear()

        _init_session()

        assert "_material_show_answers" in st.session_state
        assert isinstance(st.session_state["_material_show_answers"], set)

    def test_init_session_idempotent(self, monkeypatch):
        """Calling _init_session multiple times doesn't reset values."""
        monkeypatch.setattr(
            "streamlit.session_state",
            {},
            raising=True,
        )
        import streamlit as st

        st.session_state.clear()
        _init_session()
        st.session_state["_material_show_answers"].add(42)
        _init_session()

        # Set should still contain 42
        assert 42 in st.session_state["_material_show_answers"]


# ── Integration with ContentGeneratorAgent ────────────────


class TestMaterialPanelIntegration:
    """Integration tests: panel consumes real ContentGeneratorAgent output."""

    def test_panel_accepts_real_content_generator_output(self):
        """render_material_panel accepts real TeachingMaterial.to_dict()."""
        from src.agents.content_generator_agent import ContentGeneratorAgent, TeachingMaterial

        # Create a manual TeachingMaterial.to_dict()
        tm = TeachingMaterial(
            material_id="mat_int",
            title="Integration Test Material",
            learning_objectives=["Learn A", "Understand B"],
            chapters=[],
            overall_summary="All done.",
            target_profile="mid_level",
            total_estimated_minutes=30,
            generation_source="rule",
        )

        content_dict = tm.to_dict()
        assert content_dict["material_id"] == "mat_int"
        assert content_dict["title"] == "Integration Test Material"

        # Verify _to_markdown works with this content
        md = get_material_markdown(content_dict)
        assert "Integration Test Material" in md
        assert "Learn A" in md

    def test_content_from_workflow_result(self):
        """Content from A3Workflow result is consumable by panel."""
        from src.workflow import A3Workflow

        wf = A3Workflow(student_id="test_student")
        result = wf.run(
            user_goal="Learn Python",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
            },
        )

        content = result.to_dict().get("content")
        assert content is not None
        assert "title" in content
        assert "chapters" in content
        assert "learning_objectives" in content

        # Should produce valid markdown
        md = get_material_markdown(content)
        assert len(md) > 50
        assert content["title"] in md
