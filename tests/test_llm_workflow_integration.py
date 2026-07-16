"""
Phase 4.2 — LLM Runtime Integration Tests

验证:
  1. Rule 模式 (provider=None) 完整可用 — 向后兼容
  2. LLM 模式 (MockProvider) 全链路 mode=llm
  3. Provider 失败时自动 rule fallback (管道不中断)
  4. Agent 公共 API 未被破坏 (extract/plan/recommend/reflect)
  5. Trace 事件携带真实 duration_ms 与 mode 标记
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.workflow import A3Workflow
from src.core.provider_factory import create_provider
from src.core.agent_router import DynamicProfile
from src.llm.provider import LLMProvider, LLMResponse
from src.llm.mock_provider import MockLLMProvider
from src.memory.memory_manager import MemoryManager
from src.agents.profile_agent import ProfileAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.resource_agent import ResourceAgent
from src.agents.reflection_agent import ReflectionAgent


GOAL = "我想学习Python Agent开发"


class FailingProvider(LLMProvider):
    """始终抛异常的 provider — 用于验证 fallback."""

    def __init__(self):
        super().__init__(api_key="x", model="failing-model")

    def generate(self, prompt, system_prompt="", temperature=0.7,
                 max_tokens=2048, **kwargs) -> LLMResponse:
        raise RuntimeError("simulated provider outage")


class GarbageProvider(LLMProvider):
    """返回不可解析输出的 provider — 用于验证 JSON 解析 fallback."""

    def __init__(self):
        super().__init__(api_key="x", model="garbage-model")

    def generate(self, prompt, system_prompt="", temperature=0.7,
                 max_tokens=2048, **kwargs) -> LLMResponse:
        return LLMResponse(content="NOT JSON AT ALL {{{", model=self.model)


def _make_workflow(provider=None):
    """Workflow with isolated memory storage (no repo residue)."""
    tmp = tempfile.mkdtemp(prefix="a3_llm_test_")
    return A3Workflow(
        memory_manager=MemoryManager(storage_root=tmp),
        student_id="llm_integration_test",
        llm_provider=provider,
    )


# ──────────────────────────────────────────────
# 1. Rule 模式向后兼容
# ──────────────────────────────────────────────

class TestRuleModeBackwardCompat:
    def test_run_without_provider(self):
        result = _make_workflow(provider=None).run(user_goal=GOAL)
        assert result.success
        assert result.profile.get("source") == "rule"
        assert result.learning_plan["metadata"]["planning_mode"] == "rule"
        assert result.reflection.get("source") == "rule"
        assert result.memory_saved
        assert len(result.trace) >= 5

    def test_default_constructor_unchanged(self):
        """不传 llm_provider 时行为与 Phase 4 一致."""
        wf = _make_workflow()
        assert wf.llm_provider is None
        result = wf.run(user_goal=GOAL)
        assert result.success
        assert result.evaluation and "score" in result.evaluation


# ──────────────────────────────────────────────
# 2. LLM 模式 (MockProvider)
# ──────────────────────────────────────────────

class TestLLMMode:
    def test_full_pipeline_llm_mode(self):
        result = _make_workflow(provider=create_provider("mock")).run(user_goal=GOAL)
        assert result.success
        # 三个 LLM 接线点全部走 llm 路径
        assert result.profile.get("source") == "llm"
        assert result.learning_plan["metadata"]["planning_mode"] == "llm"
        assert result.reflection.get("source") == "llm"
        # 结构保持完整
        assert result.learning_plan.get("nodes")
        assert result.resources
        assert result.evaluation.get("passed") is not None
        assert result.memory_saved

    def test_llm_profile_differs_from_rule_default(self):
        """Mock 种子返回 mid_level, 区别于规则默认 junior_dev."""
        result = _make_workflow(provider=create_provider("mock")).run(user_goal=GOAL)
        assert result.profile["profile"]["knowledge_base"] == "mid_level"

    def test_trace_carries_mode_markers(self):
        result = _make_workflow(provider=create_provider("mock")).run(user_goal=GOAL)
        outputs = {t["agent"]: t["output"] for t in result.trace}
        assert "(mode=llm)" in outputs["ProfileAgent"]
        assert "(mode=llm)" in outputs["PlannerAgent"]
        assert "(mode=llm)" in outputs["ReflectionAgent"]

    def test_planner_llm_rationale_applied(self):
        result = _make_workflow(provider=create_provider("mock")).run(user_goal=GOAL)
        assert "画像" in result.learning_plan["strategy_rationale"]
        assert result.learning_plan["metadata"].get("llm_model") == "mock-model-v1"


# ──────────────────────────────────────────────
# 3. Provider 失败 → rule fallback
# ──────────────────────────────────────────────

class TestProviderFallback:
    def test_raising_provider_falls_back_to_rule(self):
        result = _make_workflow(provider=FailingProvider()).run(user_goal=GOAL)
        assert result.success  # 管道不中断
        assert result.profile.get("source") == "rule"
        assert result.learning_plan["metadata"]["planning_mode"] == "rule"
        assert result.reflection.get("source") == "rule"

    def test_garbage_output_falls_back_to_rule(self):
        result = _make_workflow(provider=GarbageProvider()).run(user_goal=GOAL)
        assert result.success
        assert result.profile.get("source") == "rule"
        assert result.learning_plan["metadata"]["planning_mode"] == "rule"
        assert result.reflection.get("source") == "rule"


# ──────────────────────────────────────────────
# 4. Agent 公共 API 未破坏
# ──────────────────────────────────────────────

class TestPublicAPIUnchanged:
    def test_profile_agent_extract(self):
        r = ProfileAgent().extract("零基础，喜欢看图学习")
        assert r.source == "rule"
        assert r.profile.knowledge_base == "junior_dev"

    def test_planner_agent_plan(self):
        profile = DynamicProfile()
        plan = PlannerAgent().plan(profile=profile, goal_text=GOAL)
        assert plan.nodes
        assert plan.metadata["planning_mode"] == "rule"

    def test_resource_agent_recommend(self):
        r = ResourceAgent().recommend(profile={"knowledge_base": "junior_dev"}, goal=GOAL)
        assert r.resources

    def test_reflection_agent_reflect(self):
        r = ReflectionAgent().reflect(goal=GOAL, feedback={"score": 88})
        assert r.success
        assert r.source == "rule"
        assert r.summary

    def test_reflection_result_dict_has_legacy_keys(self):
        d = ReflectionAgent().reflect(goal=GOAL).to_dict()
        for key in ("success", "goal", "score", "achievements",
                    "improvements", "summary", "generated_at"):
            assert key in d


# ──────────────────────────────────────────────
# 5. Trace 真实耗时
# ──────────────────────────────────────────────

class TestTraceDuration:
    def test_duration_ms_present(self):
        result = _make_workflow(provider=create_provider("mock")).run(user_goal=GOAL)
        agent_events = [t for t in result.trace
                        if t["agent"] not in ("System", "Workflow")]
        assert agent_events
        for ev in agent_events:
            assert isinstance(ev["duration_ms"], (int, float))
            assert ev["duration_ms"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
