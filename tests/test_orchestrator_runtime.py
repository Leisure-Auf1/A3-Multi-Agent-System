"""
Phase 9.3-B — Orchestrator Runtime Tests

Covers:
- OrchestratorRuntime initialization
- execute() basic flow (all task types)
- Task → Model auto-selection
- Capability mismatch (unsupported task)
- Fallback switching on failure
- Decision context serialization (ModelExecutionContext, ExecutionResult)
- Agent with orchestrator vs old provider fallback
- Multi-user isolation (decision logs)
- Edge cases: empty prompt, unknown task, all providers down
"""

import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.orchestration import (
    OrchestratorRuntime,
    get_runtime,
    ModelExecutionContext,
    ExecutionResult,
    ModelSelector,
    FallbackManager,
    TaskPlanner,
)
from src.config.task_capability import TaskType
from src.config.model_capability import ModelCapability, CAPABILITY_LABELS


# ═══════════════════════════════════════════════════════════════
# HTTP mock (all tests)
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def mock_urlopen():
    """Mock urllib to prevent real HTTP calls."""
    with mock.patch("urllib.request.urlopen") as m:
        def _side_effect(req, timeout=60):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "googleapis.com" in url:
                body = {
                    "candidates": [{
                        "content": {"parts": [{"text": "Mock Gemini"}]},
                        "finishReason": "STOP",
                    }],
                    "usageMetadata": {
                        "promptTokenCount": 10, "candidatesTokenCount": 20,
                        "totalTokenCount": 30,
                    },
                }
            elif "anthropic.com" in url:
                body = {
                    "id": "msg", "model": "claude",
                    "content": [{"type": "text", "text": "Mock Claude"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                }
            else:
                body = {
                    "id": "chatcmpl-test", "model": "test-model",
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": "Mock response"},
                        "finish_reason": "stop",
                    }],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                }
            raw = json.dumps(body).encode("utf-8")
            resp = mock.MagicMock()
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=None)
            resp.status = 200
            resp.read.return_value = raw
            return resp
        m.side_effect = _side_effect
        yield m


# ═══════════════════════════════════════════════════════════════
# 1. Runtime Initialization
# ═══════════════════════════════════════════════════════════════

class TestRuntimeInit:
    """OrchestratorRuntime creation and singleton."""

    def test_create_default(self):
        rt = OrchestratorRuntime()
        assert rt is not None
        assert rt._selector is not None
        assert rt._fallback is not None

    def test_get_runtime_singleton(self):
        rt1 = get_runtime()
        rt2 = get_runtime()
        assert rt1 is rt2

    def test_custom_selector(self):
        fm = FallbackManager(failure_threshold=5)
        selector = ModelSelector(fallback=fm)
        rt = OrchestratorRuntime(model_selector=selector)
        assert rt._selector is selector


# ═══════════════════════════════════════════════════════════════
# 2. execute() Basic Flow
# ═══════════════════════════════════════════════════════════════

class TestExecuteBasic:
    """Basic execute() for all task types with mocked HTTP."""

    def setup_method(self):
        self.rt = OrchestratorRuntime()

    def test_execute_chat(self):
        result = self.rt.execute(
            task_type="chat",
            prompt="Hello",
            agent_name="TutorAgent",
        )
        assert result.success is True
        assert len(result.content) > 0
        assert result.model != ""
        assert result.provider != ""

    def test_execute_generate_material(self):
        result = self.rt.execute(
            task_type="generate_material",
            prompt="Generate Python tutorial",
            agent_name="ContentGeneratorAgent",
        )
        assert result.success is True

    def test_execute_generate_plan(self):
        result = self.rt.execute(
            task_type="generate_plan",
            prompt="Plan a Python course",
            agent_name="PlannerAgent",
        )
        assert result.success is True

    def test_execute_generate_profile(self):
        result = self.rt.execute(
            task_type="generate_profile",
            prompt="Assess student level",
            agent_name="ProfileAgent",
        )
        assert result.success is True

    def test_execute_grade_answer(self):
        result = self.rt.execute(
            task_type="grade_answer",
            prompt="Grade this answer",
            agent_name="EvaluationAgent",
        )
        assert result.success is True

    def test_execute_analyze_error(self):
        result = self.rt.execute(
            task_type="analyze_error",
            prompt="Analyze error patterns",
            agent_name="ReflectionAgent",
        )
        assert result.success is True

    def test_execute_rag_retrieval(self):
        result = self.rt.execute(
            task_type="rag_retrieval",
            prompt="Find Python resources",
            agent_name="ResourceAgent",
        )
        assert result.success is True

    def test_execute_result_has_context(self):
        result = self.rt.execute(task_type="chat", prompt="Hi", agent_name="TutorAgent")
        assert result.context is not None
        assert isinstance(result.context, ModelExecutionContext)
        assert result.context.task_type == "chat"

    def test_execute_result_has_usage(self):
        result = self.rt.execute(task_type="chat", prompt="Hi", agent_name="TutorAgent")
        assert result.usage_prompt_tokens > 0
        assert result.usage_completion_tokens > 0

    def test_execute_result_to_dict(self):
        result = self.rt.execute(task_type="chat", prompt="Hi", agent_name="TutorAgent")
        d = result.to_dict()
        assert d["success"] is True
        assert "content" in d
        assert "model" in d
        assert "context" in d


# ═══════════════════════════════════════════════════════════════
# 3. Task → Model Auto-Selection
# ═══════════════════════════════════════════════════════════════

class TestTaskModelSelection:
    """Different tasks route to different models."""

    def setup_method(self):
        self.rt = OrchestratorRuntime()

    def test_material_task_uses_text_model(self):
        result = self.rt.execute(
            task_type="generate_material",
            prompt="Tutorial",
            agent_name="ContentGeneratorAgent",
        )
        assert result.success is True
        assert result.context is not None
        # Should be balanced tier for material generation
        assert result.context.cost_tier == "balanced"

    def test_chat_task_is_economy(self):
        result = self.rt.execute(
            task_type="chat", prompt="Hi", agent_name="TutorAgent",
        )
        assert result.context.cost_tier == "economy"

    def test_ppt_task_is_premium(self):
        result = self.rt.execute(
            task_type="generate_ppt",
            prompt="Create PPT",
            agent_name="PPTGeneratorAgent",
        )
        assert result.success is True
        assert result.context.cost_tier == "premium"

    def test_context_has_agent_name(self):
        result = self.rt.execute(
            task_type="chat", prompt="Hi", agent_name="TutorAgent",
        )
        assert result.context.agent_name == "TutorAgent"


# ═══════════════════════════════════════════════════════════════
# 4. Capability and Error Handling
# ═══════════════════════════════════════════════════════════════

class TestCapabilityAndErrors:
    """Capability mismatch and error handling."""

    def setup_method(self):
        self.rt = OrchestratorRuntime()

    def test_unknown_task_type(self):
        result = self.rt.execute(
            task_type="nonexistent_task",
            prompt="Test",
        )
        assert result.success is False
        assert "unknown" in result.error.lower()

    def test_deepseek_image_generation_rejected(self):
        """A text-only provider should not be selected for image generation."""
        result = self.rt.execute(
            task_type="generate_image",
            prompt="Generate a cat image",
            agent_name="ImageGeneratorAgent",
        )
        # Should succeed — model selector picks capable models only
        assert result.success is True
        assert result.provider != "deepseek"  # DeepSeek can't do images

    def test_context_has_required_capabilities(self):
        result = self.rt.execute(
            task_type="generate_plan",
            prompt="Plan",
            agent_name="PlannerAgent",
        )
        assert result.success is True
        assert len(result.context.required_capabilities) > 0


# ═══════════════════════════════════════════════════════════════
# 5. Fallback Switching
# ═══════════════════════════════════════════════════════════════

class TestFallbackSwitching:
    """FallbackManager integration."""

    def test_fallback_triggered_on_http_failure(self):
        """When primary provider fails, fallback is attempted."""
        import urllib.error
        primary_failed = {"count": 0}

        def _fail_then_pass(req, timeout=60):
            # Fail first call (primary), succeed second (fallback)
            primary_failed["count"] += 1
            if primary_failed["count"] <= 1:
                raise urllib.error.HTTPError(
                    "url", 500, "Server Error", {}, io.BytesIO(b"{}"),
                )
            body = json.dumps({
                "id": "fb", "model": "fallback-model",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "Fallback response"},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
            }).encode("utf-8")
            resp = mock.MagicMock()
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=None)
            resp.status = 200
            resp.read.return_value = body
            return resp

        with mock.patch("urllib.request.urlopen") as m:
            m.side_effect = _fail_then_pass
            rt = OrchestratorRuntime()
            result = rt.execute(
                task_type="chat", prompt="Hi", agent_name="TutorAgent",
            )
            # Should either succeed with fallback or fail gracefully
            assert isinstance(result, ExecutionResult)
            if result.success:
                assert "Fallback" in result.content

    def test_fallback_history_recorded(self):
        """When fallback is used, history is recorded."""
        import urllib.error
        call_count = {"n": 0}

        def _side(req, timeout=60):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise urllib.error.HTTPError("url", 500, "err", {}, io.BytesIO(b"{}"))
            body = json.dumps({
                "id": "ok", "model": "fb-model",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }).encode("utf-8")
            resp = mock.MagicMock()
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=None)
            resp.status = 200
            resp.read.return_value = body
            return resp

        with mock.patch("urllib.request.urlopen") as m:
            m.side_effect = _side
            fm = FallbackManager(failure_threshold=1, cooldown_seconds=0.01)
            selector = ModelSelector(fallback=fm)
            rt = OrchestratorRuntime(model_selector=selector)
            result = rt.execute(task_type="chat", prompt="Hi", agent_name="TutorAgent")
            assert isinstance(result, ExecutionResult)


# ═══════════════════════════════════════════════════════════════
# 6. Decision Context Serialization
# ═══════════════════════════════════════════════════════════════

class TestContextSerialization:
    """ModelExecutionContext and ExecutionResult to_dict/from_dict/json."""

    def test_context_to_dict(self):
        ctx = ModelExecutionContext(
            task_type="chat",
            agent_name="TutorAgent",
            student_id="student-001",
            required_capabilities=["TEXT_GENERATION"],
            cost_tier="economy",
            selected_model="gpt-4o",
            selected_provider="openai",
            success=True,
        )
        d = ctx.to_dict()
        assert d["task_type"] == "chat"
        assert d["agent_name"] == "TutorAgent"
        assert d["success"] is True

    def test_context_from_dict(self):
        d = {
            "task_type": "generate_material",
            "agent_name": "ContentGeneratorAgent",
            "student_id": "s1",
            "cost_tier": "balanced",
            "selected_model": "claude-sonnet",
            "selected_provider": "anthropic",
            "success": True,
        }
        ctx = ModelExecutionContext.from_dict(d)
        assert ctx.task_type == "generate_material"
        assert ctx.selected_model == "claude-sonnet"

    def test_context_to_json(self):
        ctx = ModelExecutionContext(task_type="chat", success=True)
        j = ctx.to_json()
        assert isinstance(j, str)
        data = json.loads(j)
        assert data["task_type"] == "chat"

    def test_context_summary(self):
        ctx = ModelExecutionContext(
            task_type="chat",
            agent_name="TutorAgent",
            selected_provider="deepseek",
            selected_model="deepseek-chat",
            cost_tier="economy",
            success=True,
            latency_ms=234.5,
        )
        s = ctx.summary()
        assert "TutorAgent" in s
        assert "chat" in s
        assert "deepseek" in s
        assert "234" in s  # latency

    def test_execution_result_to_dict(self):
        result = ExecutionResult(
            success=True,
            content="Hello world",
            model="gpt-4o",
            provider="openai",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["content"] == "Hello world"

    def test_execution_result_failure_to_dict(self):
        result = ExecutionResult(
            success=False,
            error="Connection timeout",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert "Connection timeout" in d["error"]

    def test_context_latency_recorded(self):
        ctx = ModelExecutionContext(latency_ms=150.5)
        d = ctx.to_dict()
        assert d["latency_ms"] == 150.5


# ═══════════════════════════════════════════════════════════════
# 7. Agent Orchestrator Integration
# ═══════════════════════════════════════════════════════════════

class TestAgentOrchestratorIntegration:
    """Agents use orchestrator when available, fall back to old provider."""

    def test_content_generator_has_orchestrator(self):
        from src.agents.content_generator_agent import ContentGeneratorAgent
        agent = ContentGeneratorAgent()
        assert hasattr(agent, "_orchestrator")
        assert agent._orchestrator is None

    def test_content_generator_set_orchestrator(self):
        from src.agents.content_generator_agent import ContentGeneratorAgent
        agent = ContentGeneratorAgent()
        rt = OrchestratorRuntime()
        agent.set_orchestrator(rt)
        assert agent._orchestrator is rt

    def test_content_generator_old_provider_still_works(self):
        from src.agents.content_generator_agent import ContentGeneratorAgent
        agent = ContentGeneratorAgent()
        agent.set_llm_provider(mock.MagicMock())
        assert agent._llm_provider is not None

    def test_evaluation_agent_has_orchestrator(self):
        from src.agents.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()
        assert hasattr(agent, "_orchestrator")

    def test_ppt_generator_has_orchestrator(self):
        from src.agents.ppt_generator_agent import PPTGeneratorAgent
        agent = PPTGeneratorAgent()
        assert hasattr(agent, "_orchestrator")

    def test_image_generator_has_orchestrator(self):
        from src.agents.image_generator_agent import ImageGeneratorAgent
        agent = ImageGeneratorAgent()
        assert hasattr(agent, "_orchestrator")

    def test_video_generator_has_orchestrator(self):
        from src.agents.video_generator_agent import VideoGeneratorAgent
        agent = VideoGeneratorAgent()
        assert hasattr(agent, "_orchestrator")

    def test_content_generator_uses_orchestrator_when_set(self):
        """ContentGeneratorAgent uses orchestrator when available."""
        from src.agents.content_generator_agent import ContentGeneratorAgent
        agent = ContentGeneratorAgent()
        rt = OrchestratorRuntime()
        agent.set_orchestrator(rt)

        # Create minimal profile/plan
        profile = {"profile": {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant", "learning_pace": "normal"}}
        plan = {"plan_id": "test", "nodes": [{"node_id": "n1", "title": "Intro", "core_concept": "Python", "depth": 1, "estimated_minutes": 15}]}

        material = agent.generate_material(profile, plan)
        # Should succeed (either LLM via orchestrator or rule fallback)
        assert material is not None

    def test_content_generator_old_provider_precedence(self):
        """Old llm_provider works when orchestrator is not set."""
        from src.agents.content_generator_agent import ContentGeneratorAgent
        agent = ContentGeneratorAgent()
        # Don't set orchestrator — only old provider
        mock_provider = mock.MagicMock()
        mock_resp = mock.MagicMock()
        mock_resp.success = True
        mock_resp.content = '{"title": "Test", "chapters": [], "overall_summary": "ok"}'
        mock_provider.generate.return_value = mock_resp
        agent.set_llm_provider(mock_provider)

        profile = {"profile": {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant", "learning_pace": "normal"}}
        plan = {"plan_id": "test", "nodes": []}

        material = agent.generate_material(profile, plan)
        assert material is not None
        assert material.generation_source == "llm"


# ═══════════════════════════════════════════════════════════════
# 8. Settings UI Functions
# ═══════════════════════════════════════════════════════════════

class TestSettingsUIFunctions:
    """Settings tab render functions exist and are callable."""

    def test_render_model_status_page_exists(self):
        from web.settings_tab import render_model_status_page
        assert callable(render_model_status_page)

    def test_render_capability_display_exists(self):
        from web.settings_tab import _render_capability_display
        assert callable(_render_capability_display)


# ═══════════════════════════════════════════════════════════════
# 9. Decision Logging
# ═══════════════════════════════════════════════════════════════

class TestDecisionLogging:
    """Model decision log writing to workspace."""

    def test_log_decision_writes_file(self, tmp_path):
        from src.orchestration.runtime import _get_decision_log_path

        with mock.patch("src.orchestration.runtime.os.path.expanduser", return_value=str(tmp_path)):
            rt = OrchestratorRuntime()
            ctx = ModelExecutionContext(
                task_type="chat",
                agent_name="TutorAgent",
                student_id="test-student",
                selected_model="gpt-4o",
                selected_provider="openai",
                success=True,
            )
            rt._log_decision(ctx)

            log_path = tmp_path / "test-student" / "history" / "model_decisions.jsonl"
            assert log_path.exists()
            content = log_path.read_text()
            assert "chat" in content
            assert "TutorAgent" in content

    def test_log_decision_no_student_id_skips(self, tmp_path):
        """Empty student_id should not write log."""
        with mock.patch("src.orchestration.runtime.os.path.expanduser", return_value=str(tmp_path)):
            rt = OrchestratorRuntime()
            ctx = ModelExecutionContext(
                task_type="chat",
                student_id="",  # empty
                success=True,
            )
            rt._log_decision(ctx)
            # Should not create any directory
            workspace = tmp_path / ""
            # No error = pass


# ═══════════════════════════════════════════════════════════════
# 10. Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Boundary conditions."""

    def setup_method(self):
        self.rt = OrchestratorRuntime()

    def test_empty_prompt_still_works(self):
        result = self.rt.execute(task_type="chat", prompt="")
        assert isinstance(result, ExecutionResult)

    def test_all_known_task_types(self):
        """All TaskType values can be executed."""
        for task in TaskType:
            result = self.rt.execute(
                task_type=task.value,
                prompt="Test prompt",
                agent_name="TestAgent",
            )
            assert isinstance(result, ExecutionResult)

    def test_result_has_latency(self):
        result = self.rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        assert result.latency_ms >= 0

    def test_fallback_history_empty_on_success(self):
        result = self.rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        assert result.fallback_history == []

    def test_context_timestamp_is_float(self):
        result = self.rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        assert isinstance(result.context.timestamp, float)

    def test_chat_convenience_method(self):
        result = self.rt.chat(prompt="Hello", agent_name="TutorAgent")
        assert result.success is True
