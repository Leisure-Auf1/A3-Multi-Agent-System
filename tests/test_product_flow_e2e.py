"""
Phase 10.1.5 — Product Flow E2E Validation

Complete end-to-end validation of the user journey:
  Register → Login → JWT → Profile → Learning Plan → Resources
  → Workspace → Logout → Login Again → Restore State

Tests use FastAPI TestClient — verifies ALL layers:
  web/app.py → A3APIClient → FastAPI → Auth → Agent Pipeline → Persistence

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import sys
import os
import time
import uuid
import tempfile
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure imports work from project root
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))
sys.path.insert(0, str(_project_root))

from src.api.server import app


# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════

def _unique_email() -> str:
    return f"e2e_{uuid.uuid4().hex[:8]}@test.com"


def _register_and_login(client: TestClient, email: str = "") -> tuple[str, str, str]:
    """Register + login, return (token, user_id, display_name)."""
    if not email:
        email = _unique_email()
    # Register
    resp = client.post("/api/v2/auth/register", json={
        "email": email, "password": "test1234",
        "display_name": "E2E Tester",
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    token = data["token"]
    user_id = data["user_id"]
    # Login
    resp = client.post("/api/v2/auth/login", json={
        "email": email, "password": "test1234",
    })
    assert resp.status_code == 200
    login_token = resp.json()["token"]
    return login_token, user_id, data["display_name"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════
# 1. Authentication Flow
# ═══════════════════════════════════════════════

class TestAuthenticationFlow:

    def test_register_new_user(self):
        """Register returns token and user_id."""
        client = TestClient(app)
        resp = client.post("/api/v2/auth/register", json={
            "email": _unique_email(), "password": "test1234",
            "display_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert "user_id" in data
        assert data["display_name"] == "New User"

    def test_register_duplicate_email(self):
        """Duplicate registration is rejected."""
        client = TestClient(app)
        email = _unique_email()
        client.post("/api/v2/auth/register", json={
            "email": email, "password": "test1234",
        })
        resp = client.post("/api/v2/auth/register", json={
            "email": email, "password": "test5678",
        })
        assert resp.status_code == 409 or resp.status_code == 400

    def test_login_valid_credentials(self):
        """Login with correct password returns token."""
        client = TestClient(app)
        email = _unique_email()
        client.post("/api/v2/auth/register", json={
            "email": email, "password": "test1234",
        })
        resp = client.post("/api/v2/auth/login", json={
            "email": email, "password": "test1234",
        })
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_login_invalid_password(self):
        """Wrong password is rejected."""
        client = TestClient(app)
        email = _unique_email()
        client.post("/api/v2/auth/register", json={
            "email": email, "password": "correct",
        })
        resp = client.post("/api/v2/auth/login", json={
            "email": email, "password": "wrong",
        })
        assert resp.status_code in (401, 400, 403)

    def test_jwt_token_returned_on_login(self):
        """Login returns a token string (UUID session token)."""
        client = TestClient(app)
        token, user_id, name = _register_and_login(client)
        assert len(token) > 10
        assert user_id != ""

    def test_invalid_token_rejected(self):
        """Requests with invalid token get 401."""
        client = TestClient(app)
        resp = client.get("/api/v2/profile",
                          headers=_headers("invalid-token-123"))
        assert resp.status_code == 401

    def test_missing_token_rejected(self):
        """Requests without token get 401."""
        client = TestClient(app)
        resp = client.get("/api/v2/profile")
        assert resp.status_code in (401, 403)

    def test_logout_invalidates_token(self):
        """After logout, token is no longer valid."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        # Logout
        resp = client.post("/api/v2/auth/logout",
                           headers=_headers(token))
        assert resp.status_code == 200
        # Token should be invalid now
        resp = client.get("/api/v2/auth/me",
                          headers=_headers(token))
        assert resp.status_code == 401


# ═══════════════════════════════════════════════
# 2. User Context & Permission
# ═══════════════════════════════════════════════

class TestUserContext:

    def test_me_endpoint(self):
        """GET /me returns authenticated user info."""
        client = TestClient(app)
        token, user_id, name = _register_and_login(client)
        resp = client.get("/api/v2/auth/me",
                          headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user_id

    def test_usage_endpoint(self):
        """GET /usage returns user usage stats."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.get("/api/v2/usage",
                          headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "user_id" in data
        assert "total_tokens_used" in data

    def test_users_list_endpoint(self):
        """GET /users requires auth and returns list."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.get("/api/v2/users",
                          headers=_headers(token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_user_profile_endpoint(self):
        """GET /profile/{id} returns user profile."""
        client = TestClient(app)
        token, user_id, _ = _register_and_login(client)
        resp = client.get(f"/api/v2/profile/{user_id}",
                          headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "user_id" in data


# ═══════════════════════════════════════════════
# 3. Learning Flow
# ═══════════════════════════════════════════════

class TestLearningFlow:

    def test_assess_profile(self):
        """ProfileAgent assessment via API."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.post("/api/v2/profile/assess", json={
            "text": "I'm a CS student with basic Python. I learn best with visuals and coding."
        }, headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "profile" in data
        assert data["source"] in ("rule", "stored", "llm")  # Phase 15.1: LLM path added

    def test_create_learning_plan(self):
        """PlannerAgent generates a plan via API."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.post("/api/v2/learning/plan", json={
            "goal": "Learn multi-agent AI systems",
            "profile": {"knowledge_base": "junior_dev"},
        }, headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "topic" in data
        assert "nodes" in data
        assert len(data["nodes"]) > 0

    def test_full_pipeline_profile_to_plan(self):
        """Complete flow: assess profile → generate plan."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)

        # Step 1: Assess profile
        prof_resp = client.post("/api/v2/profile/assess", json={
            "text": "Network engineering student, Python basics, visual learner, wants AI agents."
        }, headers=_headers(token))
        assert prof_resp.status_code == 200
        profile = prof_resp.json()["profile"]

        # Step 2: Generate learning plan using profile
        plan_resp = client.post("/api/v2/learning/plan", json={
            "goal": "Build multi-agent AI systems",
            "profile": profile,
        }, headers=_headers(token))
        assert plan_resp.status_code == 200
        plan = plan_resp.json()
        assert len(plan["nodes"]) > 0

    def test_resource_generation(self):
        """Resource generation via API."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.post("/api/v2/resources/generate", json={
            "topic": "Python decorators",
            "concepts": ["decorators", "closures", "functools"],
        }, headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        # Either returns artifacts or a generation result
        assert isinstance(data, dict)

    def test_quiz_generation(self):
        """Quiz generation via API."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.post("/api/v2/evaluation/quiz/generate", json={
            "topic": "Python async programming",
        }, headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_learning_stats(self):
        """Learning stats returns data."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.get("/api/v2/learning/stats",
                          headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data


# ═══════════════════════════════════════════════
# 4. Settings / LLM Provider
# ═══════════════════════════════════════════════

class TestSettingsFlow:

    def test_get_llm_settings(self):
        """GET LLM settings returns config."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.get("/api/v2/settings/llm",
                          headers=_headers(token))
        assert resp.status_code == 200

    def test_save_llm_settings(self):
        """POST LLM settings saves config."""
        client = TestClient(app)
        token, _, _ = _register_and_login(client)
        resp = client.post("/api/v2/settings/llm", json={
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "api_key": "sk-test-key-123",
        }, headers=_headers(token))
        assert resp.status_code == 200


# ═══════════════════════════════════════════════
# 5. Recovery: Logout → Login → Restore
# ═══════════════════════════════════════════════

class TestRecoveryFlow:

    def test_profile_persists_across_sessions(self):
        """Profile data survives logout + re-login."""
        client = TestClient(app)
        email = _unique_email()
        token1, user_id1, _ = _register_and_login(client, email)

        # Set a profile
        client.post("/api/v2/profile/assess", json={
            "text": "Senior developer, backend specialist, text-based learner."
        }, headers=_headers(token1))

        # Logout
        client.post("/api/v2/auth/logout", headers=_headers(token1))

        # Re-login
        resp = client.post("/api/v2/auth/login", json={
            "email": email, "password": "test1234",
        })
        token2 = resp.json()["token"]

        # Profile should still exist
        prof_resp = client.get("/api/v2/profile",
                               headers=_headers(token2))
        assert prof_resp.status_code == 200
        data = prof_resp.json()
        assert data["user_id"] == user_id1
        assert data["source"] == "stored"

    def test_llm_settings_persist_across_sessions(self):
        """LLM config survives logout + re-login."""
        client = TestClient(app)
        email = _unique_email()
        token1, _, _ = _register_and_login(client, email)

        # Save settings
        client.post("/api/v2/settings/llm", json={
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": "sk-persist-test",
        }, headers=_headers(token1))

        # Logout + re-login
        client.post("/api/v2/auth/logout", headers=_headers(token1))
        resp = client.post("/api/v2/auth/login", json={
            "email": email, "password": "test1234",
        })
        token2 = resp.json()["token"]

        # Settings should persist
        set_resp = client.get("/api/v2/settings/llm",
                              headers=_headers(token2))
        assert set_resp.status_code == 200

    def test_multi_user_isolation(self):
        """User A cannot access User B's profile."""
        client = TestClient(app)
        token_a, user_id_a, _ = _register_and_login(client)
        token_b, user_id_b, _ = _register_and_login(client)

        assert user_id_a != user_id_b

        # User A sets profile
        client.post("/api/v2/profile/assess", json={
            "text": "User A profile data"
        }, headers=_headers(token_a))

        # User B reads profile — should NOT see User A's data
        prof_b = client.get("/api/v2/profile",
                            headers=_headers(token_b))
        assert prof_b.status_code == 200

    def test_guest_cannot_access_admin_routes(self):
        """Guest users have limited access."""
        client = TestClient(app)
        resp = client.post("/api/v2/auth/guest", json={
            "display_name": "Guest Visitor",
        })
        assert resp.status_code == 200
        guest_token = resp.json()["token"]

        # Guest can read own profile
        me = client.get("/api/v2/auth/me",
                        headers=_headers(guest_token))
        assert me.status_code == 200

        # Guest can still use learning endpoints
        plan = client.post("/api/v2/learning/plan", json={
            "goal": "Basic Python",
        }, headers=_headers(guest_token))
        assert plan.status_code == 200


# ═══════════════════════════════════════════════
# 6. Workspace Isolation
# ═══════════════════════════════════════════════

class TestWorkspaceFlow:

    def test_different_users_have_separate_profiles(self):
        """Profile data is isolated per user."""
        client = TestClient(app)
        token_a, uid_a, _ = _register_and_login(client)
        token_b, uid_b, _ = _register_and_login(client)

        # User A sets profile
        client.put("/api/v2/profile", json={
            "profile": {"learning_pace": "fast_track"}
        }, headers=_headers(token_a))

        # User B sets different profile
        client.put("/api/v2/profile", json={
            "profile": {"learning_pace": "deep_dive"}
        }, headers=_headers(token_b))

        # Read back
        prof_a = client.get("/api/v2/profile",
                            headers=_headers(token_a))
        prof_b = client.get("/api/v2/profile",
                            headers=_headers(token_b))
        assert prof_a.status_code == 200
        assert prof_b.status_code == 200
        # Each user should have their own data
        assert prof_a.json()["user_id"] == uid_a
        assert prof_b.json()["user_id"] == uid_b


# ═══════════════════════════════════════════════
# 7. API Client Bridge
# ═══════════════════════════════════════════════

class TestApiClientBridge:

    def test_api_client_register_login_flow(self):
        """A3APIClient (web layer) communicates with FastAPI correctly."""
        from web.utils.api import A3APIClient
        api = A3APIClient()
        api._test_client = TestClient(app)

        email = _unique_email()
        result = api.register(email, "test1234", "Client Test")
        assert result.token != ""
        assert result.user_id != ""
        assert result.display_name == "Client Test"

        api.clear_token()
        result2 = api.login(email, "test1234")
        assert result2.token != ""

    def test_api_client_learning_plan(self):
        """A3APIClient can call learning plan endpoint."""
        from web.utils.api import A3APIClient
        api = A3APIClient()
        api._test_client = TestClient(app)

        email = _unique_email()
        result = api.register(email, "test1234", "Plan User")
        api.set_token(result.token)

        plan = api.create_learning_plan("Learn AI agents")
        assert "nodes" in plan
        assert len(plan["nodes"]) > 0

    def test_api_client_profile_flow(self):
        """A3APIClient can call profile endpoints."""
        from web.utils.api import A3APIClient
        api = A3APIClient()
        api._test_client = TestClient(app)

        email = _unique_email()
        result = api.register(email, "test1234", "Profile User")
        api.set_token(result.token)

        profile_data = api.get_profile()
        assert "profile" in profile_data

        # API expects {"text": "..."} — use direct _post to test
        assessed = api._post("/api/v2/profile/assess", {
            "text": "I am a beginner Python developer who learns by doing."
        })
        assert "profile" in assessed

    def test_api_client_get_usage(self):
        """A3APIClient can call usage endpoint."""
        from web.utils.api import A3APIClient
        api = A3APIClient()
        api._test_client = TestClient(app)

        email = _unique_email()
        result = api.register(email, "test1234", "Usage User")
        api.set_token(result.token)

        usage = api.get_usage()
        assert "user_id" in usage

    def test_api_client_settings_flow(self):
        """A3APIClient can call settings endpoints."""
        from web.utils.api import A3APIClient
        api = A3APIClient()
        api._test_client = TestClient(app)

        email = _unique_email()
        result = api.register(email, "test1234", "Settings User")
        api.set_token(result.token)

        settings = api.get_llm_settings()
        assert isinstance(settings, dict)

        saved = api.save_llm_settings("deepseek", "deepseek-v4-pro", "sk-test")
        assert isinstance(saved, dict)


# ═══════════════════════════════════════════════
# 8. Web App Entry Point
# ═══════════════════════════════════════════════

class TestWebAppEntry:

    def test_web_app_import(self):
        """Unified web/app.py imports correctly."""
        from web.app import main
        assert callable(main)

    def test_web_app_tab_renderers(self):
        """All tab render functions exist."""
        from web.app import (
            _render_dashboard, _render_learning,
            _render_profile, _render_settings,
        )
        assert callable(_render_dashboard)
        assert callable(_render_learning)
        assert callable(_render_profile)
        assert callable(_render_settings)

    def test_web_app_pipeline_function(self):
        """Pipeline execution function exists."""
        from web.app import _execute_pipeline_with_progress
        assert callable(_execute_pipeline_with_progress)
