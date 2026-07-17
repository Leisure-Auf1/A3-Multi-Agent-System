"""
Phase 4.4 — Evaluation Pipeline Tests

Covers:
  1. EvaluationManager standalone: score, explanations, fallback
  2. A3Workflow.run() includes enhanced evaluation
  3. WorkflowResult.explanations property
  4. API response includes explanations
  5. Backward compat: old evaluation structure preserved
"""

from __future__ import annotations

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.evaluation.evaluator import EvaluationManager
from src.workflow import A3Workflow
from src.workflow.result import WorkflowResult
from src.core.provider_factory import create_provider
from src.memory.memory_manager import MemoryManager
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)

GOAL = "学习 Python Agent 开发和 EventBus 架构"


# ──────────────────────────────────────────────
# 1. EvaluationManager standalone
# ──────────────────────────────────────────────

class TestEvaluationManager:
    def test_score_is_in_range(self):
        em = EvaluationManager()
        result = em.evaluate(
            learning_plan={
                "nodes": [
                    {"node_id": "a", "title": "A", "depth": 2, "estimated_minutes": 30},
                    {"node_id": "b", "title": "B", "depth": 2, "estimated_minutes": 25},
                    {"node_id": "c", "title": "C", "depth": 3, "estimated_minutes": 35},
                ],
                "total_minutes": 90,
            },
            resources=[
                {"type": "documentation", "title": "Docs"},
                {"type": "exercise", "title": "Ex"},
            ],
        )
        assert 75 <= result["score"] <= 100
        assert isinstance(result["passed"], bool)

    def test_passed_above_threshold(self):
        em = EvaluationManager()
        # Good plan should pass
        result = em.evaluate(
            learning_plan={
                "nodes": [{"node_id": "a", "title": "A"} for _ in range(5)],
                "total_minutes": 120,
            },
            resources=[
                {"type": "doc"}, {"type": "video"}, {"type": "exercise"},
            ],
        )
        assert result["passed"] is True
        assert result["score"] >= 70

    def test_explanations_present(self):
        em = EvaluationManager()
        result = em.evaluate(
            learning_plan={
                "nodes": [
                    {"node_id": "x1", "title": "LLM基础"},
                    {"node_id": "x2", "title": "Agent通信"},
                ],
                "total_minutes": 60,
            },
            profile={"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"},
        )
        expl = result.get("explanations", [])
        assert len(expl) > 0
        # Each explanation has required fields
        required = {"agent", "action", "decision", "reason", "confidence"}
        for e in expl:
            assert required.issubset(e.keys()), f"Missing keys in {e}"

    def test_empty_plan_does_not_crash(self):
        em = EvaluationManager()
        result = em.evaluate()
        assert result["score"] == 75  # baseline
        assert result["passed"] is True

    def test_no_resources_lowers_score(self):
        em = EvaluationManager()
        result_no_res = em.evaluate(
            learning_plan={
                "nodes": [{"node_id": "a", "title": "A"}] * 3,
                "total_minutes": 100,
            },
            resources=[],
        )
        result_with_res = em.evaluate(
            learning_plan={
                "nodes": [{"node_id": "a", "title": "A"}] * 3,
                "total_minutes": 100,
            },
            resources=[
                {"type": "doc"}, {"type": "exercise"},
            ],
        )
        assert result_with_res["score"] >= result_no_res["score"]

    def test_llm_planning_mode_boosts_score(self):
        em = EvaluationManager()
        rule_result = em.evaluate(
            learning_plan={
                "nodes": [{"node_id": "a", "title": "A"}] * 3,
                "total_minutes": 100,
                "metadata": {"planning_mode": "rule"},
            },
        )
        llm_result = em.evaluate(
            learning_plan={
                "nodes": [{"node_id": "a", "title": "A"}] * 3,
                "total_minutes": 100,
                "metadata": {"planning_mode": "llm"},
            },
        )
        assert llm_result["score"] > rule_result["score"]

    def test_deep_profile_nesting(self):
        """Profile wrapped in {"profile": {...}} structure."""
        em = EvaluationManager()
        result = em.evaluate(
            learning_plan={
                "nodes": [{"node_id": "a", "title": "A"}] * 3,
                "total_minutes": 100,
            },
            profile={
                "profile": {"knowledge_base": "junior_dev"},
                "source": "rule",
                "confidence": 0.95,
            },
        )
        assert result["score"] >= 75
        assert len(result["explanations"]) > 0


# ──────────────────────────────────────────────
# 2. Workflow integration
# ──────────────────────────────────────────────

def _make_workflow(provider_mode="rule"):
    tmp = tempfile.mkdtemp(prefix="a3_eval_test_")
    provider = create_provider(provider_mode) if provider_mode != "rule" else None
    return A3Workflow(
        memory_manager=MemoryManager(storage_root=tmp),
        student_id="eval_test",
        llm_provider=provider,
    )


class TestWorkflowEvaluation:
    def test_evaluation_has_explanations(self):
        wf = _make_workflow()
        result = wf.run(user_goal=GOAL)
        assert result.success
        assert result.evaluation is not None
        assert "score" in result.evaluation
        assert "passed" in result.evaluation
        assert "explanations" in result.evaluation

    def test_explanations_property_works(self):
        wf = _make_workflow()
        result = wf.run(user_goal=GOAL)
        expl = result.explanations
        assert expl is not None
        assert len(expl) > 0

    def test_llm_mode_explanations(self):
        """LLM mode should also include explanations."""
        wf = _make_workflow("mock")
        result = wf.run(user_goal=GOAL)
        assert result.success
        expl = result.explanations
        assert expl is not None
        assert len(expl) > 0

    def test_explanations_match_planning_mode(self):
        """Explanations contain PlannerAgent entries matching plan nodes."""
        wf = _make_workflow()
        result = wf.run(user_goal=GOAL)
        expl = result.explanations
        planner_explanations = [
            e for e in expl if e.get("agent") == "PlannerAgent"
        ]
        nodes = result.learning_plan.get("nodes", [])
        # At least one explanation per node
        assert len(planner_explanations) >= len(nodes)


# ──────────────────────────────────────────────
# 3. WorkflowResult.explanations property
# ──────────────────────────────────────────────

class TestWorkflowResultExplanations:
    def test_property_returns_none_when_no_evaluation(self):
        r = WorkflowResult()
        assert r.explanations is None

    def test_property_returns_none_when_no_explanations_key(self):
        r = WorkflowResult()
        r.evaluation = {"score": 80, "passed": True}
        assert r.explanations is None

    def test_property_returns_explanations(self):
        r = WorkflowResult()
        r.evaluation = {
            "score": 85,
            "passed": True,
            "explanations": [
                {"agent": "PlannerAgent", "decision": "test"}
            ],
        }
        assert r.explanations is not None
        assert len(r.explanations) == 1


# ──────────────────────────────────────────────
# 4. API response
# ──────────────────────────────────────────────

class TestAPIResponse:
    def test_api_evaluation_includes_explanations(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL, "provider": "rule"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "evaluation" in data
        eval_data = data["evaluation"]
        assert "explanations" in eval_data
        assert "score" in eval_data
        assert "passed" in eval_data

    def test_api_explanations_are_not_empty(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL, "provider": "mock"},
        )
        data = resp.json()
        expl = data["evaluation"].get("explanations", [])
        assert len(expl) > 0


# ──────────────────────────────────────────────
# 5. Backward compat
# ──────────────────────────────────────────────

class TestBackwardCompat:
    def test_old_evaluation_structure_preserved(self):
        """evaluation dict still has score, passed, issues."""
        wf = _make_workflow()
        result = wf.run(user_goal=GOAL)
        assert isinstance(result.evaluation["score"], int)
        assert isinstance(result.evaluation["passed"], bool)
        assert isinstance(result.evaluation["issues"], list)

    def test_simulate_review_still_works(self):
        """_simulate_review fallback still returns valid dict."""
        wf = _make_workflow()
        fb = wf._simulate_review(
            {"nodes": [{"node_id": "x"}] * 3},
            [{"type": "doc"}, {"type": "exercise"}],
        )
        assert "score" in fb
        assert "passed" in fb
        assert "issues" in fb

    def test_workflow_result_to_dict_still_works(self):
        wf = _make_workflow()
        result = wf.run(user_goal=GOAL)
        d = result.to_dict()
        assert "evaluation" in d
        assert "learning_plan" in d
        assert "trace" in d
        assert "plan" in d  # backward compat alias


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
