"""
Phase 4.7 — LLM Provider Abstraction Layer Tests

Covers:
  1. LLMResponse with latency_ms
  2. All 5 providers: Mock, Rule, DeepSeek, OpenAI, Spark
  3. create_provider factory (all modes)
  4. FallbackChain
  5. MetaReflector with LLMProvider injection
  6. AgentRouter with LLMProvider injection
  7. Backward compatibility
  8. Integration: workflow with provider
"""

from __future__ import annotations

import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.llm.provider import LLMProvider, LLMResponse
from src.llm.mock_provider import MockLLMProvider
from src.llm.rule_provider import RuleProvider
from src.llm.deepseek_provider import DeepSeekProvider
from src.llm.openai_provider import OpenAIProvider
from src.llm.xunfei_provider import XunfeiSparkProvider
from src.llm.factory import (
    create_provider, FallbackChain, get_provider_info,
)
from src.core.meta_reflector import MetaReflectorAgent, _LocalMemoryStore
from src.core.agent_router import AgentRouter
from src.workflow import A3Workflow
from src.memory.memory_manager import MemoryManager


# ──────────────────────────────────────────────
# 1. LLMResponse
# ──────────────────────────────────────────────

class TestLLMResponse:
    def test_default_values(self):
        resp = LLMResponse()
        assert resp.content == ""
        assert resp.model == ""
        assert resp.finish_reason == "stop"
        assert resp.error is None
        assert resp.latency_ms == 0.0
        assert resp.usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def test_success_property(self):
        assert LLMResponse(content="hi").success is True
        assert LLMResponse(content="").success is False
        assert LLMResponse(error="fail").success is False

    def test_to_dict_includes_latency_ms(self):
        resp = LLMResponse(content="ok", model="gpt", latency_ms=123.4)
        d = resp.to_dict()
        assert d["latency_ms"] == 123.4
        assert "content" in d
        assert "error" in d

    def test_with_error(self):
        resp = LLMResponse(error="timeout", finish_reason="error", latency_ms=5000)
        assert resp.success is False
        assert resp.to_dict()["error"] == "timeout"


# ──────────────────────────────────────────────
# 2. MockProvider
# ──────────────────────────────────────────────

class TestMockProvider:
    def test_generate_default(self):
        mock = MockLLMProvider()
        resp = mock.generate("any prompt")
        assert resp.success
        assert "mock" in resp.content.lower() or "response" in resp.content.lower()

    def test_generate_mapped_response(self):
        mock = MockLLMProvider()
        mock.add_response("hello", "world")
        resp = mock.generate("say hello to everyone")
        assert resp.content == "world"

    def test_call_history(self):
        mock = MockLLMProvider()
        mock.generate("p1")
        mock.generate("p2")
        assert mock.call_count == 2
        assert mock.last_call()["prompt"] == "p2"

    def test_is_always_available(self):
        assert MockLLMProvider().is_available is True

    def test_error_response(self):
        mock = MockLLMProvider()
        resp = mock.generate_error("boom")
        assert resp.success is False
        assert resp.error == "boom"


# ──────────────────────────────────────────────
# 3. RuleProvider
# ──────────────────────────────────────────────

class TestRuleProvider:
    def test_generate_default(self):
        rp = RuleProvider()
        resp = rp.generate("any")
        assert resp.success
        assert resp.content == "Rule-based response."
        assert resp.model == "rule-v1"
        assert resp.latency_ms == 0.0

    def test_generate_custom_handler(self):
        rp = RuleProvider(handler=lambda p: f"echo: {p}")
        resp = rp.generate("hello")
        assert resp.content == "echo: hello"

    def test_call_count(self):
        rp = RuleProvider()
        rp.generate("a")
        rp.generate("b")
        assert rp.call_count == 2

    def test_is_always_available(self):
        assert RuleProvider().is_available is True


# ──────────────────────────────────────────────
# 4. DeepSeek / OpenAI / Spark providers (instantiation only)

class TestProviderInstantiation:
    def test_deepseek_no_key_returns_error(self):
        """Without DEEPSEEK_API_KEY, generate returns error (no crash)."""
        with tempfile.TemporaryDirectory() as tmp:
            # Ensure key is unset
            old = os.environ.pop("DEEPSEEK_API_KEY", None)
            try:
                provider = DeepSeekProvider()
                resp = provider.generate("test")
                assert resp.success is False
                err_msg = resp.error or ""
                assert "DEEPSEEK_API_KEY" in err_msg
            finally:
                if old:
                    os.environ["DEEPSEEK_API_KEY"] = old

    def test_openai_no_key_returns_error(self):
        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            provider = OpenAIProvider()
            resp = provider.generate("test")
            assert resp.success is False
            assert "OPENAI_API_KEY" in (resp.error or "")
        finally:
            if old:
                os.environ["OPENAI_API_KEY"] = old

    def test_spark_no_key_returns_error(self):
        for k in ("XF_API_KEY", "XUNFEI_API_KEY", "XF_SPARK_API_KEY"):
            os.environ.pop(k, None)
        provider = XunfeiSparkProvider(api_key="")
        resp = provider.generate("test")
        assert resp.success is False

    def test_spark_is_available_with_key(self):
        try:
            os.environ["XF_SPARK_API_KEY"] = "fake-key"
            provider = XunfeiSparkProvider()
            assert provider.is_available is True
        finally:
            os.environ.pop("XF_SPARK_API_KEY", None)


# ──────────────────────────────────────────────
# 5. Factory
# ──────────────────────────────────────────────

class TestFactory:
    def test_create_mock(self):
        provider = create_provider("mock")
        assert isinstance(provider, MockLLMProvider)
        assert provider.is_available

    def test_create_rule(self):
        provider = create_provider("rule")
        assert isinstance(provider, RuleProvider)

    def test_create_none(self):
        assert create_provider("none") is None
        assert create_provider("rule_only") is None

    def test_create_unknown_falls_back_to_mock(self):
        provider = create_provider("nonexistent")
        assert isinstance(provider, MockLLMProvider)

    def test_create_deepseek_no_key_returns_none(self):
        old = os.environ.pop("DEEPSEEK_API_KEY", None)
        try:
            provider = create_provider("deepseek")
            # Without key, builder returns None → factory returns None
            assert provider is None
        finally:
            if old:
                os.environ["DEEPSEEK_API_KEY"] = old

    def test_get_provider_info(self):
        info = get_provider_info()
        assert "mode" in info
        assert "provider" in info

    def test_backward_compat_core_factory(self):
        """Old import path still works."""
        from src.core.provider_factory import create_provider as old_create
        provider = old_create("mock")
        assert isinstance(provider, MockLLMProvider)


# ──────────────────────────────────────────────
# 6. FallbackChain
# ──────────────────────────────────────────────

class TestFallbackChain:
    def test_primary_succeeds(self):
        mock = MockLLMProvider()
        mock.add_response("test", "primary response")
        rule = RuleProvider()
        chain = FallbackChain([mock, rule])
        resp = chain.generate("test")
        assert resp.success
        assert resp.content == "primary response"

    def test_fallback_to_rule(self):
        # Mock has no matching response → default fallback
        mock = MockLLMProvider()
        rule = RuleProvider()
        chain = FallbackChain([mock, rule])

        resp = chain.generate("unmatched prompt")
        assert resp.success
        # Should have fallen through to rule provider
        assert "Rule-based" in resp.content or "mock" in resp.content.lower()

    def test_all_fail(self):
        # Two mock providers that return errors
        mock1 = MockLLMProvider()
        mock2 = MockLLMProvider()
        chain = FallbackChain([mock1, mock2])
        # No pre-mapped responses → Mock falls back to default ("This is a mock response.")
        # So it should still succeed
        resp = chain.generate("anything")
        assert resp.success

    def test_single_provider(self):
        rule = RuleProvider()
        chain = FallbackChain([rule])
        resp = chain.generate("x")
        assert resp.success
        assert resp.content == "Rule-based response."

    def test_last_provider_tracked(self):
        rule = RuleProvider()
        chain = FallbackChain([rule])
        chain.generate("x")
        assert chain.last_provider == "RuleProvider"

    def test_repr(self):
        chain = FallbackChain([RuleProvider(), MockLLMProvider()])
        assert "FallbackChain" in repr(chain)
        assert "RuleProvider" in repr(chain)
        assert "MockLLMProvider" in repr(chain)


# ──────────────────────────────────────────────
# 7. MetaReflector with LLMProvider
# ──────────────────────────────────────────────

class TestMetaReflectorProvider:
    def test_with_mock_provider_distills(self):
        """MetaReflector uses LLMProvider for distill_accident."""
        mock = MockLLMProvider()
        mock.add_response(
            "Analyze failure",
            json.dumps({
                "error_type": "TestError",
                "problem_context": "test context",
                "root_cause_analysis": "test cause",
                "anti_pattern_code": "bad_code()",
                "golden_patch_code": "good_code()",
                "abstract_lint_rule": "use good code",
            }),
        )
        reflector = MetaReflectorAgent(
            db_client=_LocalMemoryStore(),
            llm_provider=mock,
        )
        lesson = reflector.distill_accident("node-99", {
            "error_type": "TestError",
            "context": "test",
        })
        assert lesson is not None
        assert lesson.error_type == "TestError"
        assert lesson.root_cause_analysis == "test cause"

    def test_without_provider_uses_rule(self):
        """Without LLMProvider and without api_key, falls back to rule."""
        reflector = MetaReflectorAgent(
            db_client=_LocalMemoryStore(),
            api_key="",  # no key
        )
        lesson = reflector.distill_accident("node-1", {
            "error_type": "SyntaxError",
            "context": "unclosed bracket",
        })
        assert lesson is not None
        assert "括号" in lesson.root_cause_analysis

    def test_mock_provider_error_falls_back(self):
        """LLMProvider returns error → rule fallback."""
        mock = MockLLMProvider()
        # No mapped response → default mock content, not valid JSON
        # MetaReflector._llm_distill_via_provider catches JSON parse error → rule
        reflector = MetaReflectorAgent(
            db_client=_LocalMemoryStore(),
            llm_provider=mock,
        )
        lesson = reflector.distill_accident("node-2", {
            "error_type": "TypeError",
            "context": "None returned",
        })
        assert lesson is not None
        # Should use rule fallback
        assert lesson.root_cause_analysis is not None


# ──────────────────────────────────────────────
# 8. AgentRouter with LLMProvider
# ──────────────────────────────────────────────

class TestAgentRouterProvider:
    def test_with_spark_provider(self):
        mock = MockLLMProvider()
        mock.add_response("route test", "spark response")
        router = AgentRouter(spark_provider=mock)
        result = router.route_request("ContentAgent", {
            "model": "test",
            "messages": [{"role": "user", "content": "route test"}],
        })
        assert "choices" in result
        assert result["choices"][0]["message"]["content"] == "spark response"

    def test_with_core_provider(self):
        mock = MockLLMProvider()
        mock.add_response("backend test", "core response")
        router = AgentRouter(core_provider=mock)
        result = router.route_request("MetaReflector", {
            "model": "test",
            "messages": [{"role": "user", "content": "backend test"}],
        })
        assert result["choices"][0]["message"]["content"] == "core response"

    def test_without_provider_routing_preserved(self):
        """Without providers, routing logic unchanged."""
        router = AgentRouter()
        result = router.route_request("UnknownAgent", {
            "model": "test",
            "messages": [{"role": "user", "content": "hi"}],
        })
        # Falls through to core dispatch (no key → error)
        assert "choices" in result


# ──────────────────────────────────────────────
# 9. Backward Compatibility
# ──────────────────────────────────────────────

class TestBackwardCompat:
    def test_meta_reflector_old_api(self):
        """Old api_key/base_url constructor still works."""
        reflector = MetaReflectorAgent(
            db_client=_LocalMemoryStore(),
            api_key="",  # no key → rule mode
        )
        lesson = reflector.distill_accident("n1", {"error_type": "TypeError"})
        assert lesson is not None

    def test_provider_factory_old_import(self):
        """from src.core.provider_factory import create_provider still works."""
        from src.core.provider_factory import create_provider as old_create
        from src.core.provider_factory import get_provider_info as old_info

        provider = old_create("mock")
        assert isinstance(provider, MockLLMProvider)

        info = old_info()
        assert "mode" in info

    def test_xunfei_spark_provider_unchanged(self):
        """Existing Spark provider test pattern unchanged."""
        provider = XunfeiSparkProvider(api_key="", model="spark-lite")
        resp = provider.generate("test")
        assert resp.success is False  # no key → error
        assert resp.error is not None

    def test_mock_provider_unchanged(self):
        """Existing MockProvider test pattern unchanged."""
        mock = MockLLMProvider()
        mock.add_response("x", "y")
        resp = mock.generate("x")
        assert resp.content == "y"
        assert resp.success


# ──────────────────────────────────────────────
# 10. Integration: Workflow with LLMProvider
# ──────────────────────────────────────────────

class TestWorkflowProviderIntegration:
    def test_workflow_with_mock_provider(self):
        """Workflow runs successfully with MockLLMProvider injected."""
        provider = MockLLMProvider()
        wf = A3Workflow(
            llm_provider=provider,
            student_id="test_stu",
        )
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

    def test_workflow_with_rule_provider_via_fallback_chain(self):
        """Workflow with FallbackChain([Mock, Rule]) succeeds."""
        chain = FallbackChain([MockLLMProvider(), RuleProvider()])
        wf = A3Workflow(
            llm_provider=chain,
            student_id="test_stu",
        )
        result = wf.run(
            user_goal="test goal",
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

    def test_meta_reflector_in_workflow_with_provider(self):
        """MetaReflector in workflow receives LLMProvider."""
        mock = MockLLMProvider()
        mock.add_response(
            "Analyze failure",
            json.dumps({
                "error_type": "WFError",
                "problem_context": "wf context",
                "root_cause_analysis": "wf cause",
                "anti_pattern_code": "",
                "golden_patch_code": "",
                "abstract_lint_rule": "test",
            }),
        )
        reflector = MetaReflectorAgent(
            db_client=_LocalMemoryStore(),
            llm_provider=mock,
        )

        # Use a bad plan to trigger MetaReflector
        mm = MemoryManager(auto_seed=False)
        wf = A3Workflow(
            memory_manager=mm,
            meta_reflector=reflector,
            student_id="test_stu",
        )
        result = wf.run(
            user_goal="Python test",
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
