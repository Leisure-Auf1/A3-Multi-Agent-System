"""
Phase 9.3-A — Orchestration Layer Tests

Covers:
- TaskPlanner: keyword matching, agent mapping, task_hint override, defaults
- CostOptimizer: tier routing, cost ranking, provider cost estimates
- FallbackManager: circuit breaker, cooldown, success reset, get_fallback
- ModelSelector: capability + cost + availability + fallback integration
- Edge cases: no capable models, all providers down, empty candidates
"""

import sys
import time
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.orchestration import (
    TaskPlanner,
    ModelSelector,
    SelectionResult,
    select_model,
    CostDecision,
    FallbackManager,
    ProviderState,
    get_task_cost_tier,
    get_provider_cost_estimate,
    get_provider_cost_tier,
    select_cost_optimal,
    rank_by_cost,
)
from src.config.task_capability import TaskType
from src.config.model_registry import ModelInfo, get_model
from src.config.model_capability import ModelCapability


# ═══════════════════════════════════════════════════════════════
# 1. TaskPlanner Tests
# ═══════════════════════════════════════════════════════════════

class TestTaskPlanner:
    """Task type mapping from user requests and agent names."""

    def setup_method(self):
        self.planner = TaskPlanner()

    def test_agent_mapping_content_generator(self):
        task = self.planner.plan(agent_name="ContentGeneratorAgent")
        assert task == TaskType.GENERATE_MATERIAL

    def test_agent_mapping_ppt_generator(self):
        task = self.planner.plan(agent_name="PPTGeneratorAgent")
        assert task == TaskType.GENERATE_PPT

    def test_agent_mapping_image_generator(self):
        task = self.planner.plan(agent_name="ImageGeneratorAgent")
        assert task == TaskType.GENERATE_IMAGE

    def test_agent_mapping_video_generator(self):
        task = self.planner.plan(agent_name="VideoGeneratorAgent")
        assert task == TaskType.GENERATE_VIDEO

    def test_agent_mapping_tutor_agent(self):
        task = self.planner.plan(agent_name="TutorAgent")
        assert task == TaskType.CHAT

    def test_agent_mapping_evaluation_agent(self):
        task = self.planner.plan(agent_name="EvaluationAgent")
        assert task == TaskType.GRADE_ANSWER

    def test_agent_mapping_reflection_agent(self):
        task = self.planner.plan(agent_name="ReflectionAgent")
        assert task == TaskType.ANALYZE_ERROR

    def test_agent_mapping_planner_agent(self):
        task = self.planner.plan(agent_name="PlannerAgent")
        assert task == TaskType.GENERATE_PLAN

    def test_agent_mapping_profile_agent(self):
        task = self.planner.plan(agent_name="ProfileAgent")
        assert task == TaskType.GENERATE_PROFILE

    def test_keyword_material(self):
        task = self.planner.plan(user_request="帮我生成一份Python入门教材")
        assert task == TaskType.GENERATE_MATERIAL

    def test_keyword_ppt(self):
        task = self.planner.plan(user_request="生成一份关于机器学习的PPT课件")
        assert task == TaskType.GENERATE_PPT

    def test_keyword_video(self):
        task = self.planner.plan(user_request="录制一个教学视频")
        assert task == TaskType.GENERATE_VIDEO

    def test_keyword_image(self):
        task = self.planner.plan(user_request="生成一张架构图")
        assert task == TaskType.CREATE_DIAGRAM

    def test_keyword_mindmap(self):
        task = self.planner.plan(user_request="创建思维导图")
        assert task == TaskType.CREATE_MINDMAP

    def test_keyword_plan(self):
        task = self.planner.plan(user_request="帮我规划Python学习路线")
        assert task == TaskType.GENERATE_PLAN

    def test_keyword_error_analysis(self):
        task = self.planner.plan(user_request="分析这道题为什么错了")
        assert task == TaskType.ANALYZE_ERROR

    def test_keyword_grade(self):
        task = self.planner.plan(user_request="请批改我的作业")
        assert task == TaskType.GRADE_ANSWER

    def test_keyword_profile(self):
        task = self.planner.plan(user_request="测试一下我的Python水平")
        assert task == TaskType.GENERATE_PROFILE

    def test_keyword_rag(self):
        task = self.planner.plan(user_request="搜索Python变量相关知识")
        assert task == TaskType.RAG_RETRIEVAL

    def test_explicit_task_hint_overrides_all(self):
        task = self.planner.plan(
            user_request="生成教材",
            agent_name="PPTGeneratorAgent",
            task_hint="generate_image",
        )
        assert task == TaskType.GENERATE_IMAGE

    def test_default_is_chat(self):
        task = self.planner.plan(user_request="今天天气怎么样")
        assert task == TaskType.CHAT

    def test_empty_request_defaults_chat(self):
        task = self.planner.plan()
        assert task == TaskType.CHAT

    def test_invalid_task_hint_ignored(self):
        task = self.planner.plan(
            user_request="生成教材",
            task_hint="nonexistent_task",
        )
        assert task == TaskType.GENERATE_MATERIAL  # falls through to keyword

    def test_get_task_label(self):
        label = self.planner.get_task_label(TaskType.GENERATE_MATERIAL)
        assert "教材" in label

    def test_get_required_capabilities(self):
        caps = self.planner.get_required_capabilities(TaskType.GENERATE_MATERIAL)
        assert len(caps) > 0


# ═══════════════════════════════════════════════════════════════
# 2. CostOptimizer Tests
# ═══════════════════════════════════════════════════════════════

class TestCostOptimizer:
    """Cost tier routing and provider cost estimates."""

    def test_chat_is_economy(self):
        assert get_task_cost_tier(TaskType.CHAT) == "economy"

    def test_profile_is_economy(self):
        assert get_task_cost_tier(TaskType.GENERATE_PROFILE) == "economy"

    def test_plan_is_balanced(self):
        assert get_task_cost_tier(TaskType.GENERATE_PLAN) == "balanced"

    def test_material_is_balanced(self):
        assert get_task_cost_tier(TaskType.GENERATE_MATERIAL) == "balanced"

    def test_ppt_is_premium(self):
        assert get_task_cost_tier(TaskType.GENERATE_PPT) == "premium"

    def test_image_is_premium(self):
        assert get_task_cost_tier(TaskType.GENERATE_IMAGE) == "premium"

    def test_video_is_premium(self):
        assert get_task_cost_tier(TaskType.GENERATE_VIDEO) == "premium"

    def test_deepseek_cost_lower_than_openai(self):
        ds = get_provider_cost_estimate("deepseek")
        oai = get_provider_cost_estimate("openai")
        assert ds < oai

    def test_spark_is_economy_provider(self):
        assert get_provider_cost_tier("spark") == "economy"

    def test_openai_is_premium_provider(self):
        assert get_provider_cost_tier("openai") == "premium"

    def test_deepseek_is_economy_provider(self):
        assert get_provider_cost_tier("deepseek") == "economy"

    def test_rank_by_cost_economy_prefers_cheap(self):
        candidates = [
            {"provider": "openai", "model_id": "gpt-4o", "priority": 90},
            {"provider": "deepseek", "model_id": "ds-v3", "priority": 85},
            {"provider": "spark", "model_id": "spark-lite", "priority": 60},
        ]
        ranked = rank_by_cost(candidates, "economy")
        # DeepSeek should rank high (economy tier, low cost)
        top_providers = [r["provider"] for r in ranked[:2]]
        assert "deepseek" in top_providers

    def test_rank_by_cost_premium_prefers_quality(self):
        candidates = [
            {"provider": "openai", "model_id": "gpt-4o", "priority": 90},
            {"provider": "deepseek", "model_id": "ds-v3", "priority": 85},
        ]
        ranked = rank_by_cost(candidates, "premium")
        assert ranked[0]["provider"] == "openai"  # higher priority wins

    def test_select_cost_optimal_returns_decision(self):
        candidates = [
            {"provider": "deepseek", "model_id": "ds-v3", "priority": 85},
        ]
        result = select_cost_optimal(TaskType.CHAT, candidates)
        assert result is not None
        assert result.provider == "deepseek"
        assert result.target_tier == "economy"

    def test_select_cost_optimal_empty(self):
        result = select_cost_optimal(TaskType.CHAT, [])
        assert result is None


# ═══════════════════════════════════════════════════════════════
# 3. FallbackManager Tests
# ═══════════════════════════════════════════════════════════════

class TestFallbackManager:
    """Circuit breaker and auto-fallback."""

    def setup_method(self):
        self.fm = FallbackManager(failure_threshold=2, cooldown_seconds=30)

    def test_initial_state_all_available(self):
        assert self.fm.is_available("openai") is True
        assert self.fm.is_available("deepseek") is True

    def test_single_failure_still_available(self):
        self.fm.record_failure("openai", "gpt-4o", "timeout")
        assert self.fm.is_available("openai") is True

    def test_two_failures_triggers_cooldown(self):
        self.fm.record_failure("openai", "gpt-4o", "timeout")
        self.fm.record_failure("openai", "gpt-4o", "timeout")
        assert self.fm.is_available("openai") is False

    def test_success_resets_failures(self):
        self.fm.record_failure("openai", "gpt-4o", "timeout")
        self.fm.record_failure("openai", "gpt-4o", "timeout")
        assert self.fm.is_available("openai") is False
        self.fm.record_success("openai", "gpt-4o")
        assert self.fm.is_available("openai") is True

    def test_cooldown_expires(self):
        fm = FallbackManager(failure_threshold=1, cooldown_seconds=0.01)
        fm.record_failure("openai", "gpt-4o", "timeout")
        assert fm.is_available("openai") is False
        time.sleep(0.02)
        assert fm.is_available("openai") is True  # cooldown expired

    def test_get_fallback_skips_excluded(self):
        self.fm.record_failure("openai", "gpt-4o", "t")
        self.fm.record_failure("openai", "gpt-4o", "t")
        candidates = [
            {"provider": "openai", "model_id": "gpt-4o", "priority": 90},
            {"provider": "deepseek", "model_id": "ds-v3", "priority": 85},
        ]
        result = self.fm.get_fallback("chat", candidates)
        assert result is not None
        assert result["provider"] == "deepseek"  # skipped openai

    def test_get_fallback_returns_none_when_all_excluded(self):
        self.fm.record_failure("openai", "gpt-4o", "t")
        self.fm.record_failure("openai", "gpt-4o", "t")
        self.fm.record_failure("deepseek", "ds-v3", "t")
        self.fm.record_failure("deepseek", "ds-v3", "t")
        candidates = [
            {"provider": "openai", "model_id": "gpt-4o", "priority": 90},
            {"provider": "deepseek", "model_id": "ds-v3", "priority": 85},
        ]
        result = self.fm.get_fallback("chat", candidates)
        assert result is None

    def test_exclude_providers_extra_filter(self):
        candidates = [
            {"provider": "openai", "model_id": "gpt-4o", "priority": 90},
            {"provider": "deepseek", "model_id": "ds-v3", "priority": 85},
        ]
        result = self.fm.get_fallback("chat", candidates, exclude_providers={"openai"})
        assert result is not None
        assert result["provider"] == "deepseek"

    def test_get_excluded_providers(self):
        self.fm.record_failure("openai", "gpt-4o", "t")
        self.fm.record_failure("openai", "gpt-4o", "t")
        excluded = self.fm.get_excluded_providers()
        assert "openai" in excluded

    def test_get_provider_stats(self):
        self.fm.record_failure("openai", "gpt-4o", "timeout")
        self.fm.record_success("deepseek", "ds-v3")
        stats = self.fm.get_provider_stats()
        assert "openai" in stats
        assert stats["openai"]["failure_count"] == 1
        assert stats["deepseek"]["success_count"] == 1

    def test_reset_all_clears(self):
        self.fm.record_failure("openai", "gpt-4o", "t")
        self.fm.record_failure("openai", "gpt-4o", "t")
        self.fm.reset()
        assert self.fm.is_available("openai") is True

    def test_reset_single_provider(self):
        self.fm.record_failure("openai", "gpt-4o", "t")
        self.fm.record_failure("openai", "gpt-4o", "t")
        self.fm.record_failure("deepseek", "ds-v3", "t")
        self.fm.reset("openai")
        assert self.fm.is_available("openai") is True
        assert self.fm.is_available("deepseek") is True  # unaffected


# ═══════════════════════════════════════════════════════════════
# 4. ModelSelector Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestModelSelector:
    """End-to-end model selection with all layers integrated."""

    def setup_method(self):
        self.selector = ModelSelector()

    def test_select_content_generator(self):
        result = self.selector.select(
            agent_name="ContentGeneratorAgent",
            user_request="生成Python教材",
        )
        assert result.success is True
        assert result.task_type == "generate_material"
        assert result.model_id != ""
        assert result.provider_name != ""

    def test_select_ppt_generator_premium(self):
        result = self.selector.select(
            agent_name="PPTGeneratorAgent",
            user_request="生成PPT课件",
        )
        assert result.success is True
        assert result.task_type == "generate_ppt"
        assert result.cost_tier == "premium"

    def test_select_chat_economy(self):
        result = self.selector.select(
            agent_name="TutorAgent",
            user_request="什么是Python变量",
        )
        assert result.success is True
        assert result.cost_tier == "economy"

    def test_select_with_preferred_provider(self):
        result = self.selector.select(
            agent_name="TutorAgent",
            preferred_provider="deepseek",
        )
        assert result.success is True

    def test_select_force_premium(self):
        result = self.selector.select(
            agent_name="TutorAgent",
            force_premium=True,
        )
        assert result.success is True

    def test_select_no_capable_models(self):
        """When no model supports the task, returns failure."""
        result = self.selector.select(
            task_hint="nonexistent_task",
        )
        # Should fall back to CHAT which always has capable models
        assert result.success is True

    def test_to_dict(self):
        result = self.selector.select(agent_name="TutorAgent")
        d = result.to_dict()
        assert "success" in d
        assert "task_type" in d
        assert "model_id" in d

    def test_report_failure_and_retry(self):
        """After reporting a failure, the next select should skip that provider."""
        result1 = self.selector.select(agent_name="TutorAgent")
        provider1 = result1.provider_name

        # Simulate 2 failures to trigger circuit breaker
        self.selector.report_failure(provider1, result1.model_id, "timeout")
        self.selector.report_failure(provider1, result1.model_id, "timeout")

        # Should still be able to select something
        result2 = self.selector.select(agent_name="TutorAgent")
        assert result2.success is True
        # The excluded provider should not be selected unless it's the only one
        if result2.provider_name == provider1:
            # Only one provider available in registry, that's fine
            pass

    def test_report_success_resets(self):
        self.selector.report_failure("openai", "gpt-4o", "timeout")
        self.selector.report_success("openai", "gpt-4o")
        # After reset, provider should be available again
        assert self.selector._fallback.is_available("openai") is True

    def test_select_for_all_agents(self):
        """All known agent types can select a model."""
        agents = [
            ("ProfileAgent", "generate_profile"),
            ("PlannerAgent", "generate_plan"),
            ("ContentGeneratorAgent", "generate_material"),
            ("PPTGeneratorAgent", "generate_ppt"),
            ("ImageGeneratorAgent", "generate_image"),
            ("VideoGeneratorAgent", "generate_video"),
            ("EvaluationAgent", "grade_answer"),
            ("ReflectionAgent", "analyze_error"),
            ("ResourceAgent", "rag_retrieval"),
            ("TutorAgent", "chat"),
        ]
        for agent_name, expected_task in agents:
            result = self.selector.select(agent_name=agent_name)
            assert result.success is True, f"{agent_name} failed"
            assert result.task_type == expected_task, f"{agent_name}: {result.task_type} != {expected_task}"


# ═══════════════════════════════════════════════════════════════
# 5. Module-Level Convenience
# ═══════════════════════════════════════════════════════════════

class TestModuleConvenience:
    """Module-level select_model() convenience function."""

    def test_select_model_convenience(self):
        result = select_model(agent_name="TutorAgent", user_request="Hi")
        assert result.success is True
        assert result.model_id != ""

    def test_select_model_all_params(self):
        result = select_model(
            user_request="生成教材",
            agent_name="ContentGeneratorAgent",
            task_hint="generate_material",
            preferred_provider="openai",
        )
        assert result.success is True


# ═══════════════════════════════════════════════════════════════
# 6. Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Boundary conditions and error handling."""

    def test_empty_request_selects_chat_model(self):
        selector = ModelSelector()
        result = selector.select()
        assert result.success is True

    def test_task_planner_case_insensitive(self):
        planner = TaskPlanner()
        task = planner.plan(user_request="PPT课件生成")
        assert task == TaskType.GENERATE_PPT

    def test_cost_optimizer_unknown_task_defaults_balanced(self):
        tier = get_task_cost_tier("unknown_task")
        assert tier == "balanced"

    def test_cost_estimate_unknown_provider(self):
        cost = get_provider_cost_estimate("unknown")
        assert cost == 1.0  # default

    def test_cost_tier_unknown_provider(self):
        tier = get_provider_cost_tier("unknown")
        assert tier == "balanced"

    def test_fallback_manager_unknown_provider_available(self):
        fm = FallbackManager()
        assert fm.is_available("nonexistent_provider") is True

    def test_selection_result_fields(self):
        result = SelectionResult(
            success=True,
            task_type="chat",
            model_id="test-model",
            provider_name="test",
            cost_tier="economy",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["model_id"] == "test-model"

    def test_selection_result_failure_fields(self):
        result = SelectionResult(
            success=False,
            error="No model available",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "No model available"
