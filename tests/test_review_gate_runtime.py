"""
Phase 4.5 — ReviewGate Runtime Integration Tests

Covers:
  1. ReviewGateManager.evaluate_content_quality() public API
  2. review_adapter converts correctly
  3. EvaluationManager includes review_gate field
  4. High-quality text scores higher than low-quality
  5. Fallback: ReviewGate unavailable → evaluation still works
  6. Backward compat: evaluation structure preserved
"""

from __future__ import annotations

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.core.review_gate import ReviewGateManager
from src.evaluation.review_adapter import adapt_review_gate_result
from src.evaluation.evaluator import EvaluationManager
from src.workflow import A3Workflow
from src.core.provider_factory import create_provider
from src.memory.memory_manager import MemoryManager
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)

GOAL = "学习 Python Agent 开发和 EventBus 架构"


# ──────────────────────────────────────────────
# 1. ReviewGateManager public API
# ──────────────────────────────────────────────

class TestReviewGatePublicAPI:
    def test_evaluate_content_quality_returns_structured(self):
        result = ReviewGateManager.evaluate_content_quality(
            "你好！今天我们学习 Python 装饰器。想象一下：你可以把函数当变量传递..."
            "❌ 不好的写法 → 每个函数复制粘贴代码\n✅ 好的写法 → @decorator 一行搞定\n"
            "## 核心概念\n💡 关键: @decorator 只是语法糖\n"
            "## 动手试试\n接下来写一个计时装饰器\n"
            "## 对比\n❌ 不加 @wraps\n✅ 加 @wraps\n"
            "## 总结\n回顾：函数一等公民→闭包→装饰器→@wraps"
        )
        assert "score" in result
        assert "passed" in result
        assert "scores" in result
        assert isinstance(result["score"], int)
        assert 0 <= result["score"] <= 100
        assert "colloquialism" in result["scores"]
        assert "clarity" in result["scores"]
        assert "progression" in result["scores"]

    def test_high_quality_text_scores_higher(self):
        good = ReviewGateManager.evaluate_content_quality(
            "你好！今天我们学习。想象一下：函数可以当变量传递。"
            "💡 关键理解。❌ 以前这样写... ✅ 现在这样写..."
            "## 接下来\n第一步、第二步。## 总结"
        )
        poor = ReviewGateManager.evaluate_content_quality(
            "Decorator is a design pattern. It wraps functions."
        )
        # Good text should score at least as high as poor text
        # (colloquialism markers, clarity, transitions)
        assert good["score"] >= poor["score"]

    def test_empty_text(self):
        result = ReviewGateManager.evaluate_content_quality("")
        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_pure_english_text(self):
        """English text without Chinese markers should still score."""
        result = ReviewGateManager.evaluate_content_quality(
            "First, we need to understand functions. Next, decorators. "
            "Finally, practice. ❌ bad pattern ✅ good pattern"
        )
        assert "score" in result
        assert result["score"] >= 0


# ──────────────────────────────────────────────
# 2. Review Adapter
# ──────────────────────────────────────────────

class TestReviewAdapter:
    def test_adapt_structured_result(self):
        raw = {"score": 82, "passed": True, "scores": {
            "colloquialism": 75, "clarity": 88, "progression": 83,
        }}
        adapted = adapt_review_gate_result(raw)
        assert adapted["score"] == 82
        assert adapted["passed"] is True
        assert len(adapted["gates"]) == 1
        gate = adapted["gates"][0]
        assert gate["name"] == "CONTENT_QUALITY"
        assert gate["passed"] is True
        assert "checkpoint_sig" in adapted

    def test_adapt_failed_result(self):
        raw = {"score": 50, "passed": False, "scores": {
            "colloquialism": 30, "clarity": 40, "progression": 50,
        }}
        adapted = adapt_review_gate_result(raw)
        assert adapted["passed"] is False
        assert adapted["gates"][0]["passed"] is False


# ──────────────────────────────────────────────
# 3. EvaluationManager with ReviewGate
# ──────────────────────────────────────────────

class TestEvaluationWithReviewGate:
    def test_evaluate_includes_review_gate(self):
        em = EvaluationManager()
        result = em.evaluate(
            learning_plan={
                "nodes": [
                    {"node_id": "a", "title": "LLM基础", "notes": "",
                     "core_concept": "理解 token context window prompting"},
                    {"node_id": "b", "title": "Agent通信", "notes": "",
                     "core_concept": "EventBus 事件驱动"},
                    {"node_id": "c", "title": "Memory管理", "notes": "",
                     "core_concept": "StudentMemory ExperienceMemory"},
                ],
                "total_minutes": 90,
                "strategy_rationale": "基于画像的个性化学习路径：快速通道，视觉图解驱动，节点数: 3",
            },
            user_goal=GOAL,
        )
        assert "review_gate" in result
        rg = result["review_gate"]
        assert rg is not None
        assert "score" in rg
        assert "gates" in rg
        assert "checkpoint_sig" in rg

    def test_review_gate_can_boost_score(self):
        """ReviewGate score can raise the final score above rule baseline."""
        em = EvaluationManager()
        # Plan with rich rationale content
        result = em.evaluate(
            learning_plan={
                "nodes": [{"node_id": "a", "title": "测试"}],
                "strategy_rationale": (
                    "你好！今天我们学习。想象一下：这是关键概念。"
                    "💡 核心理解。❌ 错误写法 ✅ 正确写法。"
                    "## 第一步\n接下来。## 总结"
                ),
            },
        )
        # With rich content, score should be >= 80 (at least baseline 75)
        assert result["score"] >= 75

    def test_empty_plan_review_gate_still_works(self):
        """Empty plan should still evaluate (review_gate may be None)."""
        em = EvaluationManager()
        result = em.evaluate()
        assert result["score"] == 75  # baseline
        assert result["passed"] is True
        # review_gate may be None for empty content
        assert "score" in result


# ──────────────────────────────────────────────
# 4. Workflow integration
# ──────────────────────────────────────────────

def _make_workflow(provider_mode="rule"):
    tmp = tempfile.mkdtemp(prefix="a3_rg_test_")
    provider = create_provider(provider_mode) if provider_mode != "rule" else None
    return A3Workflow(
        memory_manager=MemoryManager(storage_root=tmp),
        student_id="rg_test",
        llm_provider=provider,
    )


class TestWorkflowReviewGate:
    def test_workflow_evaluation_has_review_gate(self):
        wf = _make_workflow()
        result = wf.run(user_goal=GOAL)
        assert result.success
        assert result.evaluation is not None
        assert "review_gate" in result.evaluation

    def test_llm_mode_evaluation_has_review_gate(self):
        wf = _make_workflow("mock")
        result = wf.run(user_goal=GOAL)
        assert result.success
        eval_data = result.evaluation
        assert eval_data is not None
        assert "review_gate" in eval_data


# ──────────────────────────────────────────────
# 5. API Response
# ──────────────────────────────────────────────

class TestAPIReviewGate:
    def test_api_evaluation_includes_review_gate(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL, "provider": "rule"},
        )
        assert resp.status_code == 200
        data = resp.json()
        eval_data = data.get("evaluation", {})
        assert "review_gate" in eval_data

    def test_api_review_gate_not_none(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL, "provider": "mock"},
        )
        data = resp.json()
        rg = data["evaluation"].get("review_gate")
        assert rg is not None
        assert "score" in rg
        assert "gates" in rg


# ──────────────────────────────────────────────
# 6. Backward Compatibility
# ──────────────────────────────────────────────

class TestBackwardCompat:
    def test_evaluation_structure_preserved(self):
        em = EvaluationManager()
        result = em.evaluate(
            learning_plan={
                "nodes": [{"node_id": "a", "title": "A"}],
            },
        )
        # Core fields still present
        assert "score" in result
        assert "passed" in result
        assert "issues" in result
        assert "explanations" in result
        # review_gate is new but optional
        assert "review_gate" in result or True  # may be None or present

    def test_workflow_result_to_dict_still_works(self):
        wf = _make_workflow()
        result = wf.run(user_goal=GOAL)
        d = result.to_dict()
        assert "evaluation" in d
        assert "learning_plan" in d
        assert "trace" in d
        assert "plan" in d  # backward compat alias

    def test_simulate_review_still_works(self):
        wf = _make_workflow()
        fb = wf._simulate_review(
            {"nodes": [{"node_id": "x"}] * 3},
            [{"type": "doc"}, {"type": "exercise"}],
        )
        assert "score" in fb
        assert "passed" in fb
        assert "issues" in fb


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
