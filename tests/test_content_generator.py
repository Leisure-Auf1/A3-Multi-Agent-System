"""
Tests for ContentGeneratorAgent (Phase 8.3-A).

Covers:
- Fallback rule-based generation
- LLM provider call
- Empty provider (rule fallback)
- Schema completeness (all required fields present)
- Workflow integration
- Data model roundtrip serialization
"""

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.agent_router import DynamicProfile
from agents.content_generator_agent import (
    ContentGeneratorAgent,
    TeachingMaterial,
    Chapter,
    ConceptItem,
    ExampleItem,
    ExerciseItem,
)
from agents.planner_agent import PlannerAgent, LearningPlan, PlanNode
from agents.profile_agent import ProfileAgent


# ── Mock LLM Provider ────────────────────────────────────────


class MockLLMProvider:
    """Simulates an LLM that returns teaching material JSON."""

    def __init__(self, response_json: Optional[dict] = None, should_fail: bool = False):
        self._response = response_json
        self._should_fail = should_fail
        self.model = "mock-model"

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


# ── Helpers ──────────────────────────────────────────────────


def _make_profile(kb="junior_dev", cog="visual_dominant", pace="normal"):
    """Create a DynamicProfile for testing."""
    return DynamicProfile(
        knowledge_base=kb,
        cognitive_style=cog,
        error_prone_bias="magic_syntax_blind",
        learning_pace=pace,
        interaction_preference="code_sandbox",
        frustration_threshold="medium",
    )


def _make_plan(node_count=3):
    """Create a LearningPlan for testing."""
    nodes = []
    for i in range(node_count):
        nodes.append(PlanNode(
            node_id=f"topic_{i + 1}",
            title=f"Topic {i + 1}",
            core_concept=f"Core concept {i + 1}",
            depth=1 + (i % 3),
            estimated_minutes=15 + i * 5,
            required_concepts=[],
            exercise_count=3,
            teaching_strategy="standard",
            notes=f"Notes for topic {i + 1}",
        ))
    return LearningPlan(
        plan_id="test_plan",
        profile_summary="junior_dev / visual_dominant / normal",
        nodes=nodes,
        total_minutes=60,
        strategy_rationale="Test strategy",
    )


# ── Data Model Tests ─────────────────────────────────────────


class TestDataModels(unittest.TestCase):
    """Test serialization roundtrip for all data models."""

    def test_concept_item_roundtrip(self):
        c = ConceptItem(
            name="closures",
            description="函数闭包",
            difficulty="intermediate",
            related=["functions", "scope"],
        )
        d = c.to_dict()
        c2 = ConceptItem.from_dict(d)
        self.assertEqual(c2.name, "closures")
        self.assertEqual(c2.description, "函数闭包")
        self.assertEqual(c2.difficulty, "intermediate")
        self.assertEqual(c2.related, ["functions", "scope"])

    def test_example_item_roundtrip(self):
        e = ExampleItem(
            title="Basic closure",
            code="def outer(): ...",
            explanation="Shows closure",
            expected_output="result",
        )
        d = e.to_dict()
        e2 = ExampleItem.from_dict(d)
        self.assertEqual(e2.title, "Basic closure")
        self.assertEqual(e2.code, "def outer(): ...")

    def test_exercise_item_roundtrip(self):
        ex = ExerciseItem(
            question="What is a closure?",
            answer="A function with captured vars",
            hint="Think scope",
            type="open",
        )
        d = ex.to_dict()
        ex2 = ExerciseItem.from_dict(d)
        self.assertEqual(ex2.question, "What is a closure?")
        self.assertEqual(ex2.type, "open")

    def test_chapter_roundtrip(self):
        ch = Chapter(
            chapter_id="ch1",
            title="Chapter 1",
            explanation="Some explanation",
            concepts=[
                ConceptItem(name="c1", description="d1"),
            ],
            examples=[
                ExampleItem(title="e1", code="..."),
            ],
            exercises=[
                ExerciseItem(question="q1", answer="a1"),
            ],
            estimated_minutes=30,
            summary="Summary text",
        )
        d = ch.to_dict()
        ch2 = Chapter.from_dict(d)
        self.assertEqual(ch2.chapter_id, "ch1")
        self.assertEqual(len(ch2.concepts), 1)
        self.assertEqual(len(ch2.examples), 1)
        self.assertEqual(len(ch2.exercises), 1)

    def test_teaching_material_roundtrip(self):
        tm = TeachingMaterial(
            material_id="mat_001",
            title="Test Material",
            learning_objectives=["obj1", "obj2"],
            chapters=[
                Chapter(chapter_id="ch1", title="Ch1"),
                Chapter(chapter_id="ch2", title="Ch2"),
            ],
            overall_summary="Summary",
            target_profile="junior_dev",
            total_estimated_minutes=60,
            generation_source="rule",
        )
        d = tm.to_dict()
        tm2 = TeachingMaterial.from_dict(d)
        self.assertEqual(tm2.material_id, "mat_001")
        self.assertEqual(len(tm2.chapters), 2)
        self.assertEqual(tm2.generation_source, "rule")

    def test_teaching_material_to_json(self):
        tm = TeachingMaterial(
            material_id="mat_001",
            title="Test",
        )
        j = tm.to_json()
        self.assertIn("mat_001", j)
        data = json.loads(j)
        self.assertEqual(data["title"], "Test")

    def test_default_values(self):
        """Verify all data models have sensible defaults."""
        tm = TeachingMaterial(material_id="m", title="t")
        self.assertEqual(tm.learning_objectives, [])
        self.assertEqual(tm.chapters, [])
        self.assertEqual(tm.total_estimated_minutes, 0)
        self.assertEqual(tm.generation_source, "rule")

        ch = Chapter(chapter_id="c", title="t")
        self.assertEqual(ch.explanation, "")
        self.assertEqual(ch.concepts, [])
        self.assertEqual(ch.examples, [])
        self.assertEqual(ch.exercises, [])
        self.assertEqual(ch.estimated_minutes, 20)


# ── ContentGeneratorAgent Tests ──────────────────────────────


class TestContentGeneratorAgent(unittest.TestCase):
    """Tests for ContentGeneratorAgent core functionality."""

    def setUp(self):
        self.agent = ContentGeneratorAgent()
        self.profile = _make_profile()
        self.plan = _make_plan()

    # ── Fallback (rule-based) generation ──

    def test_fallback_generate_produces_valid_material(self):
        """Fallback generates a complete TeachingMaterial with all required fields."""
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertIsInstance(material, TeachingMaterial)
        self.assertEqual(material.generation_source, "rule")
        self.assertTrue(len(material.title) > 0)
        self.assertTrue(len(material.material_id) > 0)

    def test_fallback_generates_chapters_from_nodes(self):
        """Each plan node becomes a chapter."""
        material = self.agent.generate_material(self.profile, self.plan)

        node_count = len(self.plan.nodes)
        self.assertEqual(len(material.chapters), node_count)

    def test_fallback_chapters_have_required_fields(self):
        """Each chapter has all required sub-fields."""
        material = self.agent.generate_material(self.profile, self.plan)

        for ch in material.chapters:
            self.assertTrue(len(ch.chapter_id) > 0)
            self.assertTrue(len(ch.title) > 0)
            self.assertTrue(len(ch.explanation) > 0)
            self.assertTrue(len(ch.concepts) > 0)
            self.assertTrue(len(ch.examples) > 0)
            self.assertTrue(len(ch.exercises) > 0)
            self.assertTrue(ch.estimated_minutes > 0)
            self.assertTrue(len(ch.summary) > 0)

    def test_fallback_respects_cognitive_style(self):
        """Visual-dominant profile gets visual explanations."""
        profile_visual = _make_profile(cog="visual_dominant")
        material = self.agent.generate_material(profile_visual, self.plan)

        self.assertIn("可视化", material.chapters[0].explanation)

    def test_fallback_respects_deep_dive_pace(self):
        """deep_dive pace gets more exercises."""
        profile_deep = _make_profile(pace="deep_dive")
        material = self.agent.generate_material(profile_deep, self.plan)

        # deep_dive should have more exercises than fast_track
        self.assertGreater(len(material.chapters[0].exercises), 1)

    def test_fallback_empty_plan(self):
        """Empty plan produces minimal valid material."""
        empty_plan = LearningPlan(plan_id="empty", profile_summary="none")
        material = self.agent.generate_material(self.profile, empty_plan)

        self.assertIsInstance(material, TeachingMaterial)
        self.assertEqual(len(material.chapters), 0)

    def test_fallback_target_profile_set(self):
        """target_profile reflects the profile used."""
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertIn("junior_dev", material.target_profile)
        self.assertIn("visual_dominant", material.target_profile)

    # ── LLM provider tests ──

    def test_llm_provider_call_produces_llm_material(self):
        """When LLM provider is set and succeeds, source='llm'."""
        llm_response = {
            "title": "Python Closures Guide",
            "learning_objectives": ["Understand closures", "Use closures"],
            "chapters": [
                {
                    "chapter_id": "ch1",
                    "title": "Introduction to Closures",
                    "explanation": "A closure is a function...",
                    "concepts": [
                        {"name": "Closure", "description": "A closure captures variables", "difficulty": "beginner", "related": []}
                    ],
                    "examples": [
                        {"title": "Basic", "code": "def outer(): x=1", "explanation": "Shows closure", "expected_output": "1"}
                    ],
                    "exercises": [
                        {"question": "Create a closure", "answer": "def outer():...", "hint": "Use nested function", "type": "coding"}
                    ],
                    "estimated_minutes": 30,
                    "summary": "Key takeaways",
                }
            ],
            "overall_summary": "Great material",
        }

        self.agent.set_llm_provider(MockLLMProvider(llm_response))
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertEqual(material.generation_source, "llm")
        self.assertEqual(material.title, "Python Closures Guide")
        self.assertEqual(len(material.chapters), 1)
        self.assertEqual(len(material.learning_objectives), 2)

    def test_llm_failure_falls_back_to_rule(self):
        """When LLM fails, rule-based generation is used."""
        self.agent.set_llm_provider(MockFailingLLMProvider())
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertEqual(material.generation_source, "rule")
        self.assertTrue(len(material.chapters) > 0)

    def test_llm_exception_falls_back_to_rule(self):
        """When LLM raises exception, rule-based generation is used."""
        self.agent.set_llm_provider(MockLLMProvider(should_fail=True))
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertEqual(material.generation_source, "rule")

    def test_empty_provider_uses_rule(self):
        """When no provider is set, rule generation is used."""
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertEqual(material.generation_source, "rule")
        self.assertIsNotNone(material)

    def test_llm_provider_set_then_cleared(self):
        """Setting provider to None should still use rule."""
        self.agent.set_llm_provider(MockLLMProvider({"title": "T", "chapters": []}))
        self.agent.set_llm_provider(None)
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertEqual(material.generation_source, "rule")

    # ── Schema completeness ──

    def test_material_schema_has_all_top_level_fields(self):
        """TeachingMaterial.to_dict() contains all required fields."""
        material = self.agent.generate_material(self.profile, self.plan)
        d = material.to_dict()

        required_fields = {
            "material_id", "title", "learning_objectives", "chapters",
            "overall_summary", "target_profile", "total_estimated_minutes",
            "generation_source", "metadata",
        }
        for field in required_fields:
            self.assertIn(field, d, f"Missing field: {field}")

    def test_chapter_schema_has_all_fields(self):
        """Each chapter in to_dict() has all fields."""
        material = self.agent.fallback_generate(
            self.profile.to_dict(), self.plan.to_dict()
        )
        d = material.to_dict()

        for ch in d["chapters"]:
            required = {"chapter_id", "title", "explanation", "concepts",
                        "examples", "exercises", "estimated_minutes", "summary"}
            for field in required:
                self.assertIn(field, ch, f"Chapter missing field: {field}")

    def test_concept_schema_has_all_fields(self):
        """Concepts have name, description, difficulty, related."""
        material = self.agent.fallback_generate(
            self.profile.to_dict(), self.plan.to_dict()
        )
        for ch in material.chapters:
            for c in ch.concepts:
                d = c.to_dict()
                self.assertIn("name", d)
                self.assertIn("description", d)
                self.assertIn("difficulty", d)
                self.assertIn("related", d)

    def test_example_schema_has_all_fields(self):
        """Examples have title, code, explanation, expected_output."""
        material = self.agent.fallback_generate(
            self.profile.to_dict(), self.plan.to_dict()
        )
        for ch in material.chapters:
            for e in ch.examples:
                d = e.to_dict()
                self.assertIn("title", d)
                self.assertIn("code", d)
                self.assertIn("explanation", d)
                self.assertIn("expected_output", d)

    def test_exercise_schema_has_all_fields(self):
        """Exercises have question, answer, hint, type."""
        material = self.agent.fallback_generate(
            self.profile.to_dict(), self.plan.to_dict()
        )
        for ch in material.chapters:
            for ex in ch.exercises:
                d = ex.to_dict()
                self.assertIn("question", d)
                self.assertIn("answer", d)
                self.assertIn("hint", d)
                self.assertIn("type", d)

    # ── Profile with dict ──

    def test_generate_with_profile_dict(self):
        """generate_material works with dict profile input."""
        profile_dict = {
            "knowledge_base": "mid_level",
            "cognitive_style": "text_linear",
            "error_prone_bias": "variable_scoping",
            "learning_pace": "fast_track",
            "interaction_preference": "quiz_first",
            "frustration_threshold": "high",
        }
        material = self.agent.generate_material(profile_dict, self.plan)

        self.assertIsInstance(material, TeachingMaterial)
        self.assertEqual(material.generation_source, "rule")

    def test_generate_with_plan_dict(self):
        """generate_material works with dict plan input."""
        plan_dict = self.plan.to_dict()
        material = self.agent.generate_material(self.profile, plan_dict)

        self.assertIsInstance(material, TeachingMaterial)
        self.assertEqual(material.generation_source, "rule")

    # ── Learning objectives ──

    def test_learning_objectives_from_nodes(self):
        """Learning objectives are derived from plan nodes' core concepts."""
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertTrue(len(material.learning_objectives) > 0)
        for obj in material.learning_objectives:
            self.assertIn("理解", obj)

    # ── Overall summary ──

    def test_overall_summary_exists(self):
        """Overall summary is not empty."""
        material = self.agent.generate_material(self.profile, self.plan)

        self.assertTrue(len(material.overall_summary) > 0)

    # ── Edge cases ──

    def test_single_node_plan(self):
        """Plan with single node generates one chapter."""
        plan = _make_plan(node_count=1)
        material = self.agent.generate_material(self.profile, plan)

        self.assertEqual(len(material.chapters), 1)

    def test_many_nodes_plan(self):
        """Plan with many nodes generates many chapters."""
        plan = _make_plan(node_count=10)
        material = self.agent.generate_material(self.profile, plan)

        self.assertEqual(len(material.chapters), 10)

    def test_fallback_explicit_call(self):
        """fallback_generate works with dict inputs."""
        material = self.agent.fallback_generate(
            self.profile.to_dict(), self.plan.to_dict()
        )

        self.assertIsInstance(material, TeachingMaterial)
        self.assertEqual(material.generation_source, "rule")
        self.assertEqual(len(material.chapters), len(self.plan.nodes))

    def test_set_llm_provider_method(self):
        """set_llm_provider stores the provider."""
        mock = MockLLMProvider({"title": "T"})
        self.agent.set_llm_provider(mock)

        self.assertIs(self.agent._llm_provider, mock)


# ── Workflow Integration Tests ───────────────────────────────


class TestWorkflowIntegration(unittest.TestCase):
    """Tests that ContentGeneratorAgent is correctly wired into A3Workflow."""

    def setUp(self):
        from workflow import A3Workflow
        self.agent = ContentGeneratorAgent()
        self.profile = _make_profile()
        self.plan = _make_plan()

    def test_a3workflow_runs_content_generator(self):
        """A3Workflow.run() produces result.content."""
        from workflow import A3Workflow

        wf = A3Workflow(student_id="test_student")
        result = wf.run(
            user_goal="Learn Python decorators",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )

        self.assertIsNotNone(result.content)
        self.assertIn("chapters", result.content)
        self.assertIn("title", result.content)
        self.assertIn("generation_source", result.content)
        self.assertIn("learning_objectives", result.content)

    def test_a3workflow_content_fallback_rule(self):
        """Without LLM provider, content uses rule generation."""
        from workflow import A3Workflow

        wf = A3Workflow(student_id="test_student")
        result = wf.run(
            user_goal="Learn Python",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "text_linear",
            },
        )

        self.assertEqual(result.content.get("generation_source"), "rule")

    def test_a3workflow_content_chapters_match_plan(self):
        """Content chapter count matches plan node count."""
        from workflow import A3Workflow

        wf = A3Workflow(student_id="test_student")
        result = wf.run(
            user_goal="Learn Python",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
            },
        )

        plan_nodes = result.learning_plan.get("nodes", [])
        content_chapters = result.content.get("chapters", [])

        self.assertEqual(len(content_chapters), len(plan_nodes))

    def test_content_in_result_serialization(self):
        """WorkflowResult.to_dict() includes content."""
        from workflow import A3Workflow

        wf = A3Workflow(student_id="test_student")
        result = wf.run(
            user_goal="Learn Python",
            user_profile={"knowledge_base": "junior_dev"},
        )

        d = result.to_dict()
        self.assertIn("content", d)
        self.assertIsNotNone(d["content"])

    def test_workflow_with_llm_provider(self):
        """A3Workflow with llm_provider wires it to ContentGeneratorAgent."""
        from workflow import A3Workflow

        llm_response = {
            "title": "LLM Generated Material",
            "learning_objectives": ["obj1"],
            "chapters": [
                {
                    "chapter_id": "ch1",
                    "title": "Ch1",
                    "explanation": "exp",
                    "concepts": [],
                    "examples": [],
                    "exercises": [],
                    "estimated_minutes": 20,
                    "summary": "sum",
                }
            ],
            "overall_summary": "Good",
        }
        mock_provider = MockLLMProvider(llm_response)

        wf = A3Workflow(
            student_id="test_student",
            llm_provider=mock_provider,
        )
        result = wf.run(
            user_goal="Learn Python",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
            },
        )

        self.assertEqual(result.content.get("generation_source"), "llm")
        self.assertEqual(result.content.get("title"), "LLM Generated Material")


if __name__ == "__main__":
    unittest.main()
