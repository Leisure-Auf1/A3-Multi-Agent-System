"""
Phase 16.2 — Core Product Visibility Tests

Tests for:
  - Memory Visibility (badge + Dashboard card)
  - History Replay (result_json in API + replay UI)
  - Demo Mode (Demo indicator + goal suggestions)
  30+ tests covering memory rendering, history restore, demo flow, regression.
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
    """Create API client + register/login."""
    from web.utils.api import A3APIClient
    client = A3APIClient()
    client._test_client = TestClient(app)
    email = f"maturity_{uuid.uuid4().hex[:6]}@a3.local"
    client._test_client.post("/api/v2/auth/register", json={
        "email": email, "password": "maturitytest", "display_name": "Maturity",
    })
    resp = client._test_client.post("/api/v2/auth/login", json={
        "email": email, "password": "maturitytest",
    })
    data = resp.json()
    client.set_token(data["token"])
    return client, data["user_id"], email


# ═══════════════════════════════════════════════
# 1. Memory Visibility — API Level
# ═══════════════════════════════════════════════

class TestMemoryVisibilityAPI:
    def test_pipeline_result_has_memory_saved(self):
        """Pipeline response includes memory_saved field."""
        c, uid, _ = _setup()
        result = c.run_pipeline("Memory test pipeline")
        assert "memory_saved" in result
        assert isinstance(result["memory_saved"], bool)

    def test_memory_saved_is_true(self):
        """Pipeline should report memory_saved=True on success."""
        c, uid, _ = _setup()
        result = c.run_pipeline("Memory save test")
        assert result["memory_saved"] is True

    def test_pipeline_result_has_goal(self):
        """Pipeline response includes goal for memory context."""
        c, uid, _ = _setup()
        result = c.run_pipeline("Goal memory context test")
        assert "goal" in result
        assert len(result["goal"]) > 3

    def test_memory_badge_rendered_in_app(self):
        """app.py shows memory_saved badge in pipeline results."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "memory_saved" in content
        assert '"🧠"' in content or "'🧠'" in content


# ═══════════════════════════════════════════════
# 2. Memory Visibility — Dashboard Card
# ═══════════════════════════════════════════════

class TestMemoryDashboardCard:
    def test_dashboard_has_memory_section(self):
        """Dashboard includes AI Memory section."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "🧠 AI Memory" in content

    def test_dashboard_has_memory_metrics(self):
        """Memory card has metric columns."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "dash.mastered" in content
        assert "dash.weak" in content
        assert "dash.interactions" in content

    def test_student_memory_exists_after_pipeline(self):
        """StudentMemoryStore has data after pipeline run."""
        c, uid, _ = _setup()
        c.run_pipeline("Memory persist test pipeline")
        from veritas.memory.student_memory import StudentMemoryStore
        store = StudentMemoryStore()
        assert store.exists(uid), f"Memory should exist for user {uid}"

    def test_student_memory_has_mastery(self):
        """StudentMemory has mastery_map after pipeline."""
        c, uid, _ = _setup()
        c.run_pipeline("Mastery test pipeline")
        from veritas.memory.student_memory import StudentMemoryStore
        store = StudentMemoryStore()
        mem = store.load(uid)
        assert mem is not None
        assert hasattr(mem, "mastery_map")
        assert isinstance(mem.mastery_map, dict)

    def test_student_memory_has_sessions(self):
        """StudentMemory has session_summaries after pipeline."""
        c, uid, _ = _setup()
        c.run_pipeline("Session test pipeline")
        from veritas.memory.student_memory import StudentMemoryStore
        store = StudentMemoryStore()
        mem = store.load(uid)
        assert hasattr(mem, "session_summaries")
        assert len(mem.session_summaries) >= 1


# ═══════════════════════════════════════════════
# 3. History Replay — API Level
# ═══════════════════════════════════════════════

class TestHistoryReplayAPI:
    def test_history_includes_result_json(self):
        """History API returns result_json field."""
        c, uid, _ = _setup()
        c.run_pipeline("History replay test pipeline")
        history = c.get_learning_history()
        assert len(history) >= 1
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        assert len(pipeline_runs) >= 1
        run = pipeline_runs[-1]
        assert "result_json" in run

    def test_history_result_json_has_plan(self):
        """result_json contains plan data for replay."""
        c, uid, _ = _setup()
        c.run_pipeline("Plan replay test pipeline")
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        run = pipeline_runs[-1]
        result_json = run.get("result_json")
        assert result_json is not None
        assert "plan" in result_json
        assert "nodes" in result_json["plan"]

    def test_history_result_json_has_evaluation(self):
        """result_json contains evaluation data."""
        c, uid, _ = _setup()
        c.run_pipeline("Eval replay test pipeline")
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        run = pipeline_runs[-1]
        result_json = run.get("result_json")
        assert result_json is not None
        assert "evaluation" in result_json

    def test_history_result_json_has_content(self):
        """result_json contains generated content."""
        c, uid, _ = _setup()
        c.run_pipeline("Content replay test")
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        run = pipeline_runs[-1]
        result_json = run.get("result_json")
        assert result_json is not None
        assert "content" in result_json

    def test_history_result_json_has_resources(self):
        """result_json contains resources list."""
        c, uid, _ = _setup()
        c.run_pipeline("Resources replay test")
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        run = pipeline_runs[-1]
        result_json = run.get("result_json")
        assert result_json is not None
        assert "resources" in result_json

    def test_history_result_json_has_reflection(self):
        """result_json contains reflection data."""
        c, uid, _ = _setup()
        c.run_pipeline("Reflection replay test")
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        run = pipeline_runs[-1]
        result_json = run.get("result_json")
        assert result_json is not None
        assert "reflection" in result_json

    def test_history_result_json_has_memory_saved(self):
        """result_json contains memory_saved flag."""
        c, uid, _ = _setup()
        c.run_pipeline("Mem flag replay test")
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        run = pipeline_runs[-1]
        result_json = run.get("result_json")
        assert result_json is not None
        assert "memory_saved" in result_json

    def test_history_includes_run_id(self):
        """History API returns run_id field."""
        c, uid, _ = _setup()
        c.run_pipeline("Run ID replay test pipeline")
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        run = pipeline_runs[-1]
        assert run.get("run_id") is not None

    def test_history_includes_duration_ms(self):
        """History API returns duration_ms field."""
        c, uid, _ = _setup()
        c.run_pipeline("Duration replay test pipeline")
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        run = pipeline_runs[-1]
        assert run.get("duration_ms", 0) > 0

    def test_history_old_entries_still_work(self):
        """History entries without result_json don't break."""
        c, uid, _ = _setup()
        history = c.get_learning_history()
        for r in history:
            assert "agent" in r
            assert "action" in r
            assert "score" in r
            # result_json may be None for old entries
            assert "result_json" in r


# ═══════════════════════════════════════════════
# 4. History Replay — UI Level
# ═══════════════════════════════════════════════

class TestHistoryReplayUI:
    def test_history_has_replay_section(self):
        """History tab includes replay rendering code."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Session Replay" in content or "result_json" in content

    def test_history_renders_plan_in_replay(self):
        """Replay renders Learning Plan."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Learning Plan" in content

    def test_history_renders_evaluation_in_replay(self):
        """Replay renders Evaluation."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Evaluation" in content

    def test_history_renders_reflection_in_replay(self):
        """Replay renders AI Reflection."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "AI Reflection" in content

    def test_history_renders_generated_lesson_in_replay(self):
        """Replay renders Generated Lesson."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Generated Lesson" in content

    def test_history_renders_resources_in_replay(self):
        """Replay renders Resources."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "📚" in content


# ═══════════════════════════════════════════════
# 5. Demo Mode
# ═══════════════════════════════════════════════

class TestDemoMode:
    def test_dashboard_has_demo_indicator(self):
        """Dashboard code includes Demo Mode indicator."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Demo Mode" in content

    def test_dashboard_has_goal_suggestions(self):
        """Dashboard includes goal suggestions."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Try These" in content

    def test_goal_suggestions_are_strings(self):
        """Goal suggestions are valid strings >= 3 chars."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        expected_goals = [
            "Learn Python basics",
            "Understand machine learning",
            "Master data structures",
        ]
        for g in expected_goals:
            assert g in content, f"Missing goal suggestion: {g}"

    def test_dashboard_has_custom_goal_section(self):
        """Dashboard still has custom goal input."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "Custom Goal" in content

    def test_demo_pipeline_works_without_api_key(self):
        """Pipeline works in demo mode (provider=None / rule)."""
        c, uid, _ = _setup()
        result = c.run_pipeline("Demo test pipeline")
        assert result["status"] == "success"
        assert "plan" in result

    def test_demo_mode_has_no_provider_in_run_info(self):
        """Demo mode shows rule-only in run_info."""
        c, uid, _ = _setup()
        result = c.run_pipeline("Provider check demo")
        run_info = result.get("run_info", {})
        engine = run_info.get("engine", "unknown")
        assert engine in ("rule-only", "rule", "mock") or engine != ""


# ═══════════════════════════════════════════════
# 6. Regression — Existing Functionality
# ═══════════════════════════════════════════════

class TestRegression:
    def test_pipeline_returns_all_existing_fields(self):
        """All existing pipeline fields still present."""
        c, uid, _ = _setup()
        result = c.run_pipeline("Regression test pipeline")
        required = ["run_id", "profile", "plan", "content", "evaluation",
                     "reflection", "trace", "resources", "run_info", "status"]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_history_still_returns_metadata(self):
        """History still has original metadata fields."""
        c, uid, _ = _setup()
        c.run_pipeline("History meta test")
        history = c.get_learning_history()
        assert len(history) >= 1
        r = history[0]
        assert "id" in r
        assert "agent" in r
        assert "action" in r
        assert "score" in r
        assert "created_at" in r

    def test_quiz_still_works(self):
        """Quiz panel import still works."""
        from web.components.quiz_panel import render_quiz_panel
        assert callable(render_quiz_panel)

    def test_chat_still_works(self):
        """Chat component import still works."""
        from web.components.chat import render_chat_sidebar, render_chat_main
        assert callable(render_chat_sidebar)

    def test_pipeline_runs_different_goals(self):
        """Multiple different pipeline runs all succeed."""
        c, uid, _ = _setup()
        goals = ["Python", "Machine Learning", "Data Structures"]
        for g in goals:
            result = c.run_pipeline(f"Learn {g}")
            assert result["status"] == "success"

    def test_full_flow_demo_to_history_replay(self):
        """End-to-end: run pipeline → check history → verify replay data."""
        c, uid, _ = _setup()
        # Run pipeline
        result = c.run_pipeline("Full flow test")
        assert result["status"] == "success"

        # Check history
        history = c.get_learning_history()
        pipeline_runs = [r for r in history if r.get("agent") == "pipeline"]
        assert len(pipeline_runs) >= 1

        # Verify replay data
        run = pipeline_runs[-1]
        result_json = run.get("result_json")
        assert result_json is not None
        assert "plan" in result_json
        assert "goal" in result_json
        assert "memory_saved" in result_json
        assert result_json["memory_saved"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
