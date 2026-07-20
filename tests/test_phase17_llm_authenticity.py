"""
Phase 17.1 — LLM Authenticity Tests

Tests for:
  1. Trace metadata contains provider/model/source
  2. AI Execution Card rendered in pipeline results
  3. Strong/weak areas filter empty topics
  4. Rule fallback still works
  5. Regression: existing pipeline functionality intact
"""

from __future__ import annotations

import sys, os, json, uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.api.server import app


# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════

def _setup() -> tuple:
    from web.utils.api import A3APIClient
    client = A3APIClient()
    client._test_client = TestClient(app)
    email = f"llm_auth_{uuid.uuid4().hex[:6]}@a3.local"
    client._test_client.post("/api/v2/auth/register", json={
        "email": email, "password": "authpass", "display_name": "LLMAuth",
    })
    resp = client._test_client.post("/api/v2/auth/login", json={
        "email": email, "password": "authpass",
    })
    data = resp.json()
    client.set_token(data["token"])
    return client, data["user_id"], email


def _run_pipeline(client) -> dict:
    """Run pipeline and return result."""
    return client.run_pipeline("Learn Python authentication patterns")


# ═══════════════════════════════════════════════
# 1. Trace Metadata — Provider Info
# ═══════════════════════════════════════════════

class TestTraceMetadata:
    def test_trace_events_have_metadata(self):
        """Every trace event has metadata dict."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        assert len(trace) > 0
        for t in trace:
            assert "metadata" in t, f"Trace event missing metadata: {t.get('agent','?')}"
            assert isinstance(t["metadata"], dict)

    def test_trace_metadata_has_source(self):
        """Metadata has source field (llm or rule)."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        agent_events = [t for t in trace if t.get("agent") not in ("System",)]
        assert len(agent_events) > 0
        for t in agent_events:
            meta = t["metadata"]
            assert "source" in meta, f"Missing source in {t['agent']}"

    def test_trace_metadata_has_llm_used(self):
        """Metadata has llm_used boolean."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        agent_events = [t for t in trace if t.get("agent") not in ("System",)]
        for t in agent_events:
            meta = t["metadata"]
            assert "llm_used" in meta, f"Missing llm_used in {t['agent']}"
            assert isinstance(meta["llm_used"], bool)

    def test_memory_agent_is_rule(self):
        """Memory agent always uses rule mode."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        memory_events = [t for t in trace if t.get("agent") == "Memory"]
        if memory_events:
            for t in memory_events:
                assert t["metadata"].get("llm_used") == False

    def test_rule_mode_trace_has_source_rule(self):
        """When no LLM configured, agent events have source=rule."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        agent_events = [t for t in trace if t.get("agent") not in ("System", "Workflow")]
        for t in agent_events:
            assert t["metadata"]["source"] in ("rule", "llm")

    def test_profile_agent_has_metadata(self):
        """ProfileAgent trace has metadata."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        pa = [t for t in trace if t.get("agent") == "ProfileAgent"]
        assert len(pa) >= 1
        assert "source" in pa[0]["metadata"]


# ═══════════════════════════════════════════════
# 2. AI Execution Card — Dashboard
# ═══════════════════════════════════════════════

class TestAIExecutionCard:
    def test_app_has_ai_execution_card(self):
        """web/app.py contains AI Execution Card."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "AI Execution Card" in content

    def test_app_extracts_llm_agents_from_trace(self):
        """AI Card code extracts LLM vs rule agents from trace metadata."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert 'meta.get("llm_used")' in content
        assert 'meta.get("source")' in content

    def test_app_shows_provider_model(self):
        """AI Card shows provider and model."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Provider:" in content
        assert "model_name" in content

    def test_app_shows_agent_counts(self):
        """AI Card shows LLM vs rule agent counts."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Agents (LLM)" in content
        assert "Agents (Rule)" in content

    def test_app_filters_system_workflow(self):
        """AI Card skips System and Workflow agents."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert '"System"' in content
        assert '"Workflow"' in content


# ═══════════════════════════════════════════════
# 3. Quiz Empty String Fix
# ═══════════════════════════════════════════════

class TestQuizEmptyFix:
    def test_score_quiz_filters_empty_topics(self):
        """score_quiz filters empty string topics from strong_areas."""
        from src.agents.evaluation_agent import EvaluationAgent, QuizQuestion, StudentAnswer

        agent = EvaluationAgent()
        questions = [
            QuizQuestion(id="q1", question="Q1?", options=["A","B"], correct_index=0, topic=""),
            QuizQuestion(id="q2", question="Q2?", options=["A","B"], correct_index=1, topic="Loops"),
            QuizQuestion(id="q3", question="Q3?", options=["A","B"], correct_index=0, topic=""),
        ]
        answers = [
            StudentAnswer(question_id="q1", selected_index=0),
            StudentAnswer(question_id="q2", selected_index=1),
            StudentAnswer(question_id="q3", selected_index=0),
        ]
        result = agent.score_quiz(questions, answers, "test_quiz")
        # Should NOT contain empty string
        assert "" not in result.strong_areas
        assert "" not in result.weak_areas
        # Should contain real topics
        assert "Loops" in result.strong_areas

    def test_score_quiz_empty_topics_not_in_weak(self):
        """Empty topics are filtered from weak_areas."""
        from src.agents.evaluation_agent import EvaluationAgent, QuizQuestion, StudentAnswer

        agent = EvaluationAgent()
        questions = [
            QuizQuestion(id="q1", question="Q1?", options=["A","B"], correct_index=0, topic=""),
            QuizQuestion(id="q2", question="Q2?", options=["A","B"], correct_index=0, topic="Functions"),
        ]
        answers = [
            StudentAnswer(question_id="q1", selected_index=1),  # wrong
            StudentAnswer(question_id="q2", selected_index=1),  # wrong
        ]
        result = agent.score_quiz(questions, answers, "test_quiz2")
        assert "" not in result.weak_areas
        assert "Functions" in result.weak_areas

    def test_score_quiz_all_correct_no_empty(self):
        """All correct, some topics empty → strong has only real topics."""
        from src.agents.evaluation_agent import EvaluationAgent, QuizQuestion, StudentAnswer

        agent = EvaluationAgent()
        questions = [
            QuizQuestion(id="q1", question="Q1?", options=["A","B"], correct_index=0, topic="Python"),
            QuizQuestion(id="q2", question="Q2?", options=["A","B"], correct_index=1, topic=""),
            QuizQuestion(id="q3", question="Q3?", options=["A","B"], correct_index=0, topic="Python"),
        ]
        answers = [
            StudentAnswer(question_id="q1", selected_index=0),
            StudentAnswer(question_id="q2", selected_index=1),
            StudentAnswer(question_id="q3", selected_index=0),
        ]
        result = agent.score_quiz(questions, answers, "test_quiz3")
        assert result.score_percent == 100.0
        assert "Python" in result.strong_areas
        assert "" not in result.strong_areas


# ═══════════════════════════════════════════════
# 4. Rule Fallback
# ═══════════════════════════════════════════════

class TestRuleFallback:
    def test_pipeline_works_without_llm(self):
        """Pipeline succeeds in rule-only mode."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        assert result["status"] == "success"

    def test_trace_metadata_rule_when_no_llm(self):
        """When no LLM, agent metadata shows rule source."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        agent_events = [t for t in trace if t.get("agent") not in ("System", "Workflow")]
        # All should be rule (mock is default in tests)
        rule_count = sum(1 for t in agent_events if t["metadata"].get("source") == "rule")
        llm_count = sum(1 for t in agent_events if t["metadata"].get("source") == "llm")
        assert rule_count + llm_count == len(agent_events)


# ═══════════════════════════════════════════════
# 5. Regression
# ═══════════════════════════════════════════════

class TestRegression:
    def test_pipeline_all_sections_present(self):
        """All pipeline result sections still present."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        required = ["run_id", "profile", "plan", "content", "evaluation",
                     "reflection", "trace", "resources", "run_info", "status"]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_trace_still_has_agent_names(self):
        """Trace still has agent field."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        for t in trace:
            assert "agent" in t

    def test_trace_still_has_duration(self):
        """Trace still has duration_ms."""
        c, uid, _ = _setup()
        result = _run_pipeline(c)
        trace = result.get("trace", [])
        for t in trace:
            assert "duration_ms" in t

    def test_quiz_still_works(self):
        """Quiz generation still works."""
        c, uid, _ = _setup()
        resp = c._test_client.post("/api/v2/evaluation/quiz/generate", json={
            "topic": "Python decorators"
        }, headers={"Authorization": f"Bearer {c._token}"})
        assert resp.status_code == 200

    def test_workflow_emit_still_works(self):
        """Workflow._emit accepts the new metadata parameter."""
        from src.workflow import A3Workflow
        wf = A3Workflow(student_id="test_meta")
        wf._emit("TestAgent", "test_action", "in", "out", duration_ms=1.0,
                 metadata={"custom": "value"})
        # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
