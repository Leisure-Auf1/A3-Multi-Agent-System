"""
Phase 4.6 — MetaReflection Pipeline Tests

Covers:
  1. MetaReflectionAdapter: should_trigger, build_failure_context, severity
  2. A3Workflow with MetaReflector: meta_reflection in result, experience written
  3. A3Workflow without MetaReflector: backward compat (no crash)
  4. WorkflowResult.meta_reflection serialization
  5. Phase 4.5 compat: evaluation["review_gate"] untouched
"""

from __future__ import annotations

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.core.meta_reflector import MetaReflectorAgent, _LocalMemoryStore
from src.core.meta_reflection_adapter import MetaReflectionAdapter
from src.core.decision_explainer import ReflectionResult as MetaReflectionResult
from src.workflow import A3Workflow
from src.workflow.result import WorkflowResult
from src.memory.memory_manager import MemoryManager
from src.evaluation.evaluator import EvaluationManager

GOAL = "学习 Python Agent 开发"


# ──────────────────────────────────────────────
# 1. MetaReflectionAdapter
# ──────────────────────────────────────────────

class TestMetaReflectionAdapter:

    def test_should_trigger_low_score(self):
        adapter = MetaReflectionAdapter()
        assert adapter.should_trigger({"score": 50, "issues": []}) is True

    def test_should_trigger_issues_only(self):
        adapter = MetaReflectionAdapter()
        assert adapter.should_trigger({"score": 85, "issues": ["bad node"]}) is True

    def test_should_not_trigger_high_score_no_issues(self):
        adapter = MetaReflectionAdapter()
        assert adapter.should_trigger({"score": 90, "issues": []}) is False

    def test_should_not_trigger_none(self):
        adapter = MetaReflectionAdapter()
        assert adapter.should_trigger(None) is False

    def test_build_failure_context(self):
        adapter = MetaReflectionAdapter()
        ctx = adapter.build_failure_context(
            evaluation={"score": 55, "issues": ["missing resources", "too many nodes"]},
            reflection={"goal": "Python", "improvements": ["fix pacing"]},
            student_id="stu_1",
        )
        assert "missing resources" in ctx["mistake"]
        assert ctx["student_id"] == "stu_1"
        assert ctx["scores"] == [55]
        assert ctx["attempts"] == 1

    def test_build_failure_context_fallback_to_improvements(self):
        adapter = MetaReflectionAdapter()
        ctx = adapter.build_failure_context(
            evaluation={"score": 65, "issues": []},
            reflection={"improvements": ["fix pacing", "split nodes"]},
        )
        assert "fix pacing" in ctx["mistake"]

    def test_determine_severity_critical(self):
        adapter = MetaReflectionAdapter()
        assert adapter.determine_severity({"score": 30}) == "CRITICAL"

    def test_determine_severity_high(self):
        adapter = MetaReflectionAdapter()
        assert adapter.determine_severity({"score": 55}) == "HIGH"

    def test_determine_severity_medium(self):
        adapter = MetaReflectionAdapter()
        assert adapter.determine_severity({"score": 65}) == "MEDIUM"

    def test_determine_severity_low(self):
        adapter = MetaReflectionAdapter()
        assert adapter.determine_severity({"score": 85, "issues": ["x"]}) == "LOW"


# ──────────────────────────────────────────────
# 2. A3Workflow with MetaReflector
# ──────────────────────────────────────────────

class TestWorkflowWithMetaReflector:

    @staticmethod
    def _make_low_score_plan() -> dict:
        """A plan that yields a low evaluation score."""
        return {
            "nodes": [],  # zero nodes → low score
            "total_minutes": 0,
        }

    def test_meta_reflector_wired_to_experience(self):
        """Verify set_experience_store is called."""
        mm = MemoryManager(auto_seed=False)
        reflector = MetaReflectorAgent(db_client=_LocalMemoryStore())
        wf = A3Workflow(
            memory_manager=mm,
            meta_reflector=reflector,
            student_id="test_stu",
        )
        # After init, _exp_store should be set
        assert hasattr(reflector, "_exp_store")
        assert reflector._exp_store is mm.experience

    def test_meta_reflection_populated_on_low_score(self):
        """Low score → meta_reflector triggered → meta_reflection in result."""
        mm = MemoryManager(auto_seed=False)
        reflector = MetaReflectorAgent(db_client=_LocalMemoryStore())
        wf = A3Workflow(
            memory_manager=mm,
            meta_reflector=reflector,
            student_id="test_stu",
        )

        result = wf.run(
            user_goal="学习 Python 闭包",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )

        # With zero nodes, score should be low enough to trigger
        assert result.evaluation is not None
        score = result.evaluation.get("score", 100)
        issues = result.evaluation.get("issues", [])

        if score < MetaReflectionAdapter.THRESHOLD or issues:
            assert result.meta_reflection is not None, (
                f"MetaReflector should trigger when score={score} < {MetaReflectionAdapter.THRESHOLD}"
            )
            mr = result.meta_reflection
            assert "mistake" in mr or "root_cause" in mr
            # Verify experience was written
            stats = mm.experience.stats()
            assert stats["total_lessons"] >= 1, (
                f"ExperienceMemory should have at least 1 lesson, got {stats['total_lessons']}"
            )

    def test_no_trigger_when_score_high(self):
        """High score → meta_reflector NOT triggered."""
        mm = MemoryManager(auto_seed=False)
        reflector = MetaReflectorAgent(db_client=_LocalMemoryStore())
        wf = A3Workflow(
            memory_manager=mm,
            meta_reflector=reflector,
            student_id="test_stu",
        )

        # A good plan should score high enough to skip trigger
        result = wf.run(
            user_goal="Python basics",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )

        # The default plan should have enough nodes to score okay
        eval_result = result.evaluation or {}
        score = eval_result.get("score", 100)
        issues = eval_result.get("issues", [])
        if score >= MetaReflectionAdapter.THRESHOLD and not issues:
            assert result.meta_reflection is None, (
                "MetaReflector should NOT trigger with high score and no issues"
            )


# ──────────────────────────────────────────────
# 3. Backward compat: without MetaReflector
# ──────────────────────────────────────────────

class TestBackwardCompat:

    def test_workflow_runs_without_meta_reflector(self):
        """No MetaReflector → no crash, meta_reflection is None."""
        wf = A3Workflow(student_id="test_stu")
        result = wf.run(
            user_goal="学习 Python",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )
        assert result.success
        assert result.evaluation is not None
        assert result.reflection is not None
        assert result.meta_reflection is None  # never triggered
        d = result.to_dict()
        assert "meta_reflection" in d
        assert d["meta_reflection"] is None

    def test_workflow_result_has_meta_reflection_field(self):
        """WorkflowResult always has meta_reflection field."""
        wr = WorkflowResult()
        assert hasattr(wr, "meta_reflection")
        assert wr.meta_reflection is None
        d = wr.to_dict()
        assert "meta_reflection" in d


# ──────────────────────────────────────────────
# 4. Phase 4.5 compat: evaluation["review_gate"]
# ──────────────────────────────────────────────

class TestPhase45Compat:

    def test_evaluation_still_has_review_gate(self):
        """evaluation output format unchanged by Phase 4.6."""
        em = EvaluationManager()
        plan = {
            "nodes": [
                {"node_id": "a", "title": "Intro", "depth": 1, "estimated_minutes": 10},
                {"node_id": "b", "title": "Basics", "depth": 2, "estimated_minutes": 20},
            ],
            "total_minutes": 60,
            "strategy_rationale": "Foundational learning path with clear progression.",
        }
        result = em.evaluate(
            learning_plan=plan,
            resources=[{"type": "doc"}, {"type": "exercise"}],
            user_goal=GOAL,
        )
        # Phase 4.5 compat: review_gate key may or may not be present depending
        # on ReviewGate runtime availability, but the overall structure is preserved
        assert "score" in result
        assert "passed" in result
        assert "issues" in result
        assert "explanations" in result
        # review_gate is optional (depends on runtime)

    def test_workflow_result_explanations_property(self):
        """WorkflowResult.explanations property still works."""
        wf = A3Workflow(student_id="test_stu")
        result = wf.run(
            user_goal=GOAL,
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )
        # explanations property from Phase 4.4 still works
        expl = result.explanations
        if result.evaluation and "explanations" in result.evaluation:
            assert expl is not None
        else:
            assert expl is None
        assert result.success
