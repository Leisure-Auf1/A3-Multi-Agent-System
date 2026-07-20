"""
Phase 10.2/10.3 — Product Runtime Tests (updated for A3Workflow consolidation)
"""

from __future__ import annotations

import json, os, sys, uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))
sys.path.insert(0, str(_project_root))
from src.api.server import app
from src.services.learning_pipeline import LearningPipelineService


def _ue(): return f"rt_{uuid.uuid4().hex[:8]}@test.com"

def _auth(c):
    e = _ue()
    r = c.post("/api/v2/auth/register", json={"email": e, "password": "test1234", "display_name": "T"})
    assert r.status_code == 201; d = r.json()
    return d["token"], d["user_id"], e

def _h(t): return {"Authorization": f"Bearer {t}"}


class TestUnifiedPipeline:
    def test_pipeline_run_200(self):
        c = TestClient(app); t, _, _ = _auth(c)
        assert c.post("/api/v2/learning/run", json={"goal": "Learn Python"}, headers=_h(t)).status_code == 200
    def test_pipeline_all_fields(self):
        c = TestClient(app); t, _, _ = _auth(c)
        d = c.post("/api/v2/learning/run", json={"goal": "Learn AI"}, headers=_h(t)).json()
        for k in ["run_id","user_id","profile","plan","resources","evaluation","trace","status"]:
            assert k in d
    def test_pipeline_has_nodes(self):
        c = TestClient(app); t, _, _ = _auth(c)
        d = c.post("/api/v2/learning/run", json={"goal": "Master decorators"}, headers=_h(t)).json()
        assert len(d["plan"]["nodes"]) > 0
    def test_pipeline_has_trace(self):
        c = TestClient(app); t, _, _ = _auth(c)
        d = c.post("/api/v2/learning/run", json={"goal": "Trace check"}, headers=_h(t)).json()
        assert len(d["trace"]) > 0
    def test_pipeline_needs_auth(self):
        assert TestClient(app).post("/api/v2/learning/run", json={"goal": "x"}).status_code in (401,403)
    def test_pipeline_empty_goal_rejected(self):
        c = TestClient(app); t, _, _ = _auth(c)
        assert c.post("/api/v2/learning/run", json={"goal": ""}, headers=_h(t)).status_code == 422


class TestService:
    def test_creates(self):
        assert LearningPipelineService() is not None
    def test_run_dict(self):
        r = LearningPipelineService().run(user_id="u", goal="Test")
        assert isinstance(r, dict)
    def test_all_keys(self):
        r = LearningPipelineService().run(user_id="u", goal="Test")
        for k in ["run_id","user_id","goal","profile","plan","resources","evaluation","trace","artifacts_saved","memory_saved"]:
            assert k in r
    def test_trace_in_result(self):
        r = LearningPipelineService().run(user_id="u", goal="Trace")
        assert len(r["trace"]) > 0
    def test_memory_saved(self):
        r = LearningPipelineService().run(user_id="u", goal="Memory")
        assert r["memory_saved"] is True
    def test_uses_a3workflow(self):
        import inspect
        assert "A3Workflow" in inspect.getsource(LearningPipelineService.run)
    def test_no_direct_agents(self):
        import inspect
        src = inspect.getsource(LearningPipelineService.run)
        assert "ProfileAgent()" not in src and "PlannerAgent()" not in src
    def test_plan_to_markdown(self):
        md = LearningPipelineService._plan_to_markdown("T", {"topic":"T","difficulty":"easy","total_estimated_hours":2,"nodes":[{"title":"Intro","concepts":["a"],"estimated_hours":1}]})
        assert "Intro" in md and "a" in md
    def test_cleanup(self):
        r = LearningPipelineService().run(user_id="clean", goal="Clean")
        for p in r["artifacts_saved"]:
            try: os.remove(p)
            except OSError: pass


class TestP0Fixes:
    def test_tutor_fallback_nonempty(self):
        from src.agents.tutor_agent import TutorAgent, TutorContext
        r = TutorAgent(llm_provider=None).explain("What is a decorator?", TutorContext(current_topic="Python"))
        assert len(r.content) > 0
    def test_chat_api_nonempty(self):
        c = TestClient(app); t, _, _ = _auth(c)
        d = c.post("/api/v2/chat/message", json={"message": "Python?", "topic": "py"}, headers=_h(t)).json()
        assert len(d["content"]) > 0
    def test_assess_profile_field_fix(self):
        from web.utils.api import A3APIClient
        api = A3APIClient(); api._test_client = TestClient(app)
        api.set_token(api.register(_ue(), "test1234", "Fix").token)
        assert "profile" in api.assess_profile("I am a beginner")


class TestNoRegression:
    def test_pipeline_in_openapi(self):
        assert "/api/v2/learning/run" in TestClient(app).get("/openapi.json").json()["paths"]
    def test_pipeline_router_exported(self):
        from src.api.v2 import pipeline_router; assert pipeline_router is not None
    def test_no_pipeline_executor_in_code(self):
        import inspect
        assert "PipelineExecutor" not in inspect.getsource(__import__('src.api.v2.pipeline', fromlist=['run_learning_pipeline']))
