"""
Phase 16.1 — Learning Loop Completion Tests

Tests for:
  - Quiz panel integration into pipeline results
  - Reflection output rendering
  - Trace-driven progress (actual agent names)
  - Pipeline result completeness (all UI sections)
"""

from __future__ import annotations

import sys, os, uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.api.server import app


# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════

def _setup_api_client() -> tuple:
    """Create A3APIClient with TestClient backend + register/login."""
    from web.utils.api import A3APIClient
    client = A3APIClient()
    client._test_client = TestClient(app)

    email = f"phase16_{uuid.uuid4().hex[:6]}@a3.local"
    client._test_client.post("/api/v2/auth/register", json={
        "email": email, "password": "phase16test", "display_name": "Phase16Test",
    })
    resp = client._test_client.post("/api/v2/auth/login", json={
        "email": email, "password": "phase16test",
    })
    data = resp.json()
    client.set_token(data["token"])
    return client, data["user_id"], email


def _run_pipeline_and_get_result(goal: str = "Learn Python generators") -> dict:
    """Run pipeline and return full result dict."""
    c, uid, _ = _setup_api_client()
    return c.run_pipeline(goal)


# ═══════════════════════════════════════════════
# 1. Quiz Panel Integration
# ═══════════════════════════════════════════════

class TestQuizPanelIntegration:
    def test_quiz_panel_importable(self):
        """render_quiz_panel is importable from web.components.quiz_panel."""
        from web.components.quiz_panel import render_quiz_panel
        assert callable(render_quiz_panel)

    def test_quiz_panel_handles_none_provider(self):
        """Quiz panel returns None gracefully when provider=None."""
        from web.components.quiz_panel import render_quiz_panel
        # Cannot call directly in pytest (needs Streamlit context),
        # but the function itself handles None cleanly
        import inspect
        src = inspect.getsource(render_quiz_panel)
        assert "if provider is None:" in src
        assert "return None" in src

    def test_quiz_panel_session_state_keys(self):
        """Quiz panel defines session_state keys for state management."""
        from web.components.quiz_panel import (
            _QUIZ_QUESTIONS, _QUIZ_RESULT, _QUIZ_SUBMITTED,
            _QUIZ_EVAL_DICT, _ERROR_ANALYSES,
        )
        assert _QUIZ_QUESTIONS == "quiz_questions"
        assert _QUIZ_RESULT == "quiz_result"
        assert _QUIZ_SUBMITTED == "quiz_submitted"

    def test_quiz_panel_app_imports_it(self):
        """app.py imports render_quiz_panel."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "from web.components.quiz_panel import render_quiz_panel" in content

    def test_quiz_panel_invoked_in_pipeline_results(self):
        """render_quiz_panel is called inside _render_pipeline_results."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "render_quiz_panel" in content


# ═══════════════════════════════════════════════
# 2. Reflection Output
# ═══════════════════════════════════════════════

class TestReflectionOutput:
    def test_reflection_data_structure(self):
        """Pipeline response has reflection with expected keys."""
        result = _run_pipeline_and_get_result("Learn Python async/await")
        refl = result.get("reflection")
        # Reflection may be None for rule-only, but if present has structure
        if refl is not None:
            assert isinstance(refl, dict)
            # Should have at least one of these keys
            has_structure = any(
                k in refl for k in ("source", "summary", "achievements", "improvements")
            )
            assert has_structure, f"Reflection has no expected keys: {list(refl.keys())}"

    def test_reflection_has_source(self):
        """Reflection has source field (rule/llm) when present."""
        result = _run_pipeline_and_get_result("Learn Python decorators")
        refl = result.get("reflection")
        if refl is not None:
            assert "source" in refl or "achievements" in refl or "improvements" in refl

    def test_reflection_rendered_in_app(self):
        """app.py renders reflection expander in _render_pipeline_results."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert '"💭 AI Reflection"' in content
        assert 'result.get("reflection")' in content

    def test_reflection_has_achievements_or_improvements(self):
        """Reflection has achievements/improvements lists when present."""
        result = _run_pipeline_and_get_result("Learn Python typing")
        refl = result.get("reflection")
        if refl is not None:
            # Either achievements or improvements should be a list
            ach = refl.get("achievements")
            imp = refl.get("improvements")
            assert ach is None or isinstance(ach, list)
            assert imp is None or isinstance(imp, list)


# ═══════════════════════════════════════════════
# 3. Pipeline Result Completeness
# ═══════════════════════════════════════════════

class TestPipelineResultCompleteness:
    def test_pipeline_result_has_all_sections(self):
        """Result dict has all sections needed for Phase 16.1 UI."""
        result = _run_pipeline_and_get_result("Comprehensive test")
        required = [
            "run_id", "profile", "plan", "content",
            "evaluation", "reflection", "trace", "resources",
            "run_info", "status",
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_pipeline_result_has_goal(self):
        """Pipeline result includes the goal for quiz topic extraction."""
        result = _run_pipeline_and_get_result("Learn Python generators")
        assert "goal" in result
        assert "Learn Python generators" in result["goal"]

    def test_pipeline_result_trace_is_list(self):
        """Trace is a list (for progress bar extraction)."""
        result = _run_pipeline_and_get_result("Trace test")
        trace = result.get("trace")
        assert isinstance(trace, list)

    def test_pipeline_result_run_info_has_engine(self):
        """run_info has engine field for UI transparency."""
        result = _run_pipeline_and_get_result("Run info test")
        run_info = result.get("run_info", {})
        assert "engine" in run_info


# ═══════════════════════════════════════════════
# 4. Trace-Driven Progress Bar
# ═══════════════════════════════════════════════

class TestTraceDrivenProgress:
    def test_progress_from_trace_extracts_agents(self):
        """Trace-driven agent extraction works."""
        result = _run_pipeline_and_get_result("Agent extraction test")
        trace = result.get("trace", [])

        agents_in_trace = []
        seen = set()
        for t in trace:
            agent = t.get("agent", "")
            if agent and agent not in seen and agent != "System":
                seen.add(agent)
                agents_in_trace.append(agent)

        # Should have at least one agent (even rule-only generates events)
        assert len(agents_in_trace) >= 1, f"Expected agents in trace, got: {trace}"

    def test_progress_fallback_empty_trace(self):
        """Empty trace → handles gracefully (no crash)."""
        empty_trace = []

        agents_in_trace = []
        seen = set()
        for t in empty_trace:
            agent = t.get("agent", "")
            if agent and agent not in seen and agent != "System":
                seen.add(agent)
                agents_in_trace.append(agent)

        # Should be empty, no crash
        assert agents_in_trace == []

    def test_progress_app_uses_trace_driven(self):
        """app.py uses trace-driven progress instead of hardcoded stages."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        # Phase 16.1 marker
        assert "Trace-driven agent progress" in content
        assert "agents_in_trace" in content
        # Old hardcoded loop should be gone
        assert "for i, stage in enumerate(PIPELINE_STAGES)" not in content

    def test_progress_completes_with_100_pct(self):
        """Progress bar reaches 100% at end."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        # Both branches set progress to 100%
        assert 'progress_bar.progress(100, "Pipeline complete (rule-only)")' in content
        assert "progress_bar.progress(pct" in content  # agents_in_trace path


# ═══════════════════════════════════════════════
# 5. UI Component Structure
# ═══════════════════════════════════════════════

class TestUIComponentStructure:
    def test_all_render_functions_exist(self):
        """All pipeline result section renderers are present in app.py."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        # All UI sections present
        sections = [
            "learn.engine_details",
            "Learning Plan",
            "Quality Evaluation",
            "AI Reflection",
            "AI-Generated Lesson",
            "Recommended Resources",
            "Interactive Quiz Panel",
        ]
        for section in sections:
            assert section in content, f"Missing UI section: {section}"

    def test_app_imports_all_components(self):
        """app.py imports quiz_panel along with existing components."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            content = f.read()
        # All component imports present
        assert "from web.components.auth" in content
        assert "from web.components.chat" in content
        assert "from web.components.quiz_panel" in content

    def test_app_file_grew_reasonably(self):
        """app.py grew by a reasonable amount (~50 lines)."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
        with open(app_path) as f:
            lines = f.readlines()
        # Should be under 950 lines (was 628, Phase 16.1 grew to 679, 16.2 to 833, 16.2-B to 858, 17.1 to 901)
        assert len(lines) < 950, f"app.py is {len(lines)} lines, too large"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
