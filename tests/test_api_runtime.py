"""
Phase 4.2.5 — API Runtime Integration Tests

Tests the FastAPI service layer against the A3Workflow pipeline.
Uses httpx.TestClient (built into FastAPI) — zero extra deps.

Test matrix:
  1. GET  /health                          → 200
  2. POST /api/v1/learning/plan (mock)     → 200, profile/trace present
  3. POST /api/v1/learning/plan (rule)     → 200, source=rule
  4. POST /api/v1/learning/plan (empty)    → 422
  5. POST /api/v1/learning/plan (bad provider) → 422
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)

GOAL = "学习 Python Agent 开发"


# ──────────────────────────────────────────────
# 1. Health Check
# ──────────────────────────────────────────────

class TestHealthCheck:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ──────────────────────────────────────────────
# 2. Mock Provider — Full Pipeline
# ──────────────────────────────────────────────

class TestMockProvider:
    def test_full_pipeline_with_mock(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={
                "goal": GOAL,
                "provider": "mock",
                "student_id": "api_test_001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["profile"] is not None
        assert data["profile"]["source"] == "llm"
        assert data["learning_plan"] is not None
        assert data["learning_plan"]["metadata"]["planning_mode"] == "llm"
        assert data["reflection"]["source"] == "llm"
        assert data["trace"] is not None
        assert len(data["trace"]) >= 5
        assert data["memory_saved"] is True
        assert data["total_duration_ms"] > 0

    def test_mock_profile_mid_level(self):
        """Mock seed returns mid_level, not default junior_dev."""
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL, "provider": "mock"},
        )
        data = resp.json()
        assert data["profile"]["profile"]["knowledge_base"] == "mid_level"

    def test_trace_contains_agent_entries(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL, "provider": "mock"},
        )
        agents_in_trace = {t["agent"] for t in resp.json()["trace"]}
        assert "ProfileAgent" in agents_in_trace
        assert "PlannerAgent" in agents_in_trace
        assert "ReflectionAgent" in agents_in_trace


# ──────────────────────────────────────────────
# 3. Rule Provider — Fallback
# ──────────────────────────────────────────────

class TestRuleProvider:
    def test_rule_mode(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={
                "goal": GOAL,
                "provider": "rule",
                "student_id": "api_test_rule",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["profile"]["source"] == "rule"
        assert data["learning_plan"]["metadata"]["planning_mode"] == "rule"
        assert data["reflection"]["source"] == "rule"

    def test_rule_none_mode(self):
        """'none' also maps to rule."""
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL, "provider": "none"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ──────────────────────────────────────────────
# 4. Validation
# ──────────────────────────────────────────────

class TestValidation:
    def test_empty_goal_rejected(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": "", "provider": "mock"},
        )
        assert resp.status_code == 422

    def test_missing_goal_rejected(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={"provider": "mock"},
        )
        assert resp.status_code == 422

    def test_bad_provider_rejected(self):
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL, "provider": "openai"},
        )
        assert resp.status_code == 422

    def test_provider_defaults_to_mock(self):
        """When provider is omitted, default 'mock' should work."""
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": GOAL},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Default is mock → profile source should be llm
        assert data["profile"]["source"] == "llm"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
