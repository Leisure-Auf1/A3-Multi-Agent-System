"""
Phase 11.2 — Release Candidate Smoke Tests

End-to-end smoke tests verifying the complete release pipeline:
startup → health → auth → pipeline → artifact generation.

Runs against in-process TestClient (zero external deps).
"""

from __future__ import annotations

import sys, os, json, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)


def _register_and_login(email: str) -> dict:
    """Register and login, return {headers, user_id, token}."""
    client.post("/api/v2/auth/register", json={
        "email": email, "password": "smoke_pass", "display_name": "SmokeTest",
    })
    resp = client.post("/api/v2/auth/login", json={
        "email": email, "password": "smoke_pass",
    })
    assert resp.status_code == 200
    d = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {d['token']}"},
        "user_id": d["user_id"],
        "token": d["token"],
    }


# ═══════════════════════════════════════════════
# 1. Startup
# ═══════════════════════════════════════════════

class TestStartup:
    def test_health_endpoint(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_app_title(self):
        assert app.title == "A3 Multi-Agent Learning System — API"

    def test_app_version(self):
        assert app.version == "2.0.0"


# ═══════════════════════════════════════════════
# 2. Auth
# ═══════════════════════════════════════════════

class TestAuthSmoke:
    def test_register_returns_token(self):
        email = f"smoke_reg_{uuid.uuid4().hex[:6]}@rc.local"
        resp = client.post("/api/v2/auth/register", json={
            "email": email, "password": "smoke1234", "display_name": "Smoke",
        })
        assert resp.status_code == 201
        assert "token" in resp.json()

    def test_login_returns_token(self):
        email = f"smoke_login_{uuid.uuid4().hex[:6]}@rc.local"
        client.post("/api/v2/auth/register", json={
            "email": email, "password": "smoke1234", "display_name": "S",
        })
        resp = client.post("/api/v2/auth/login", json={
            "email": email, "password": "smoke1234",
        })
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_me_endpoint(self):
        u = _register_and_login(f"smoke_me_{uuid.uuid4().hex[:6]}@rc.local")
        resp = client.get("/api/v2/auth/me", headers=u["headers"])
        assert resp.status_code == 200

    def test_unauthorized_blocked(self):
        resp = client.post("/api/v2/learning/run", json={"goal": "Test"})
        assert resp.status_code == 401

    def test_logout(self):
        u = _register_and_login(f"smoke_logout_{uuid.uuid4().hex[:6]}@rc.local")
        resp = client.post("/api/v2/auth/logout", headers=u["headers"])
        assert resp.status_code == 200


# ═══════════════════════════════════════════════
# 3. Pipeline
# ═══════════════════════════════════════════════

class TestPipelineSmoke:
    def test_run_pipeline_success(self):
        u = _register_and_login(f"smoke_run_{uuid.uuid4().hex[:6]}@rc.local")
        resp = client.post("/api/v2/learning/run", json={
            "goal": "Learn Python async/await patterns"
        }, headers=u["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "run_id" in data

    def test_run_pipeline_returns_trace(self):
        u = _register_and_login(f"smoke_trace_{uuid.uuid4().hex[:6]}@rc.local")
        resp = client.post("/api/v2/learning/run", json={
            "goal": "Understand distributed systems"
        }, headers=u["headers"])
        data = resp.json()
        assert "trace" in data
        assert isinstance(data["trace"], list)

    def test_run_pipeline_returns_artifacts(self):
        u = _register_and_login(f"smoke_art_{uuid.uuid4().hex[:6]}@rc.local")
        resp = client.post("/api/v2/learning/run", json={
            "goal": "Master Python decorators deeply"
        }, headers=u["headers"])
        data = resp.json()
        assert "artifacts_saved" in data
        assert isinstance(data["artifacts_saved"], list)

    def test_run_pipeline_memory_saved(self):
        u = _register_and_login(f"smoke_mem_{uuid.uuid4().hex[:6]}@rc.local")
        resp = client.post("/api/v2/learning/run", json={
            "goal": "Learn multi-agent architecture"
        }, headers=u["headers"])
        assert resp.json()["memory_saved"] is True

    def test_multiple_runs(self):
        u = _register_and_login(f"smoke_multi_{uuid.uuid4().hex[:6]}@rc.local")
        r1 = client.post("/api/v2/learning/run", json={
            "goal": "First pipeline run"
        }, headers=u["headers"])
        r2 = client.post("/api/v2/learning/run", json={
            "goal": "Second pipeline run"
        }, headers=u["headers"])
        assert r1.json()["run_id"] != r2.json()["run_id"]


# ═══════════════════════════════════════════════
# 4. Artifact Generation
# ═══════════════════════════════════════════════

class TestArtifactSmoke:
    def test_artifacts_on_disk(self):
        u = _register_and_login(f"smoke_disk_{uuid.uuid4().hex[:6]}@rc.local")
        resp = client.post("/api/v2/learning/run", json={
            "goal": "Learn Python typing system"
        }, headers=u["headers"])
        for path in resp.json()["artifacts_saved"]:
            assert os.path.exists(path), f"Artifact missing: {path}"

    def test_artifact_count(self):
        u = _register_and_login(f"smoke_cnt_{uuid.uuid4().hex[:6]}@rc.local")
        resp = client.post("/api/v2/learning/run", json={
            "goal": "Python generators and iterators"
        }, headers=u["headers"])
        # Should produce at least 3 artifacts: profile, plan JSON, plan MD, eval
        assert len(resp.json()["artifacts_saved"]) >= 3

    def test_workspace_browsable(self):
        u = _register_and_login(f"smoke_ws_{uuid.uuid4().hex[:6]}@rc.local")
        client.post("/api/v2/learning/run", json={
            "goal": "Workspace verification"
        }, headers=u["headers"])
        from src.workspace.manager import WorkspaceManager
        wm = WorkspaceManager()
        arts = wm.list_artifacts(u["user_id"])
        assert len(arts) > 0


# ═══════════════════════════════════════════════
# 5. History & Stats
# ═══════════════════════════════════════════════

class TestHistorySmoke:
    def test_history_accessible(self):
        u = _register_and_login(f"smoke_hist_{uuid.uuid4().hex[:6]}@rc.local")
        client.post("/api/v2/learning/run", json={
            "goal": "History test pipeline"
        }, headers=u["headers"])
        resp = client.get("/api/v2/learning/history", headers=u["headers"])
        assert resp.status_code == 200

    def test_stats_accessible(self):
        u = _register_and_login(f"smoke_stats_{uuid.uuid4().hex[:6]}@rc.local")
        client.post("/api/v2/learning/run", json={
            "goal": "Stats test pipeline"
        }, headers=u["headers"])
        resp = client.get("/api/v2/learning/stats", headers=u["headers"])
        assert resp.status_code == 200
        assert resp.json()["total_sessions"] >= 1


# ═══════════════════════════════════════════════
# 6. Version Verification
# ═══════════════════════════════════════════════

class TestVersionMetadata:
    def test_desktop_config_version(self):
        from desktop.config import APP_VERSION, APP_NAME
        assert APP_NAME == "A3-Agent"
        assert APP_VERSION == "1.0.0"

    def test_desktop_config_imports(self):
        from desktop.config import (
            API_PORT, UI_PORT, HEALTH_POLL_TIMEOUT,
            IS_WIN, USER_DATA_DIR, BUNDLE_ROOT,
            verify_bundle_integrity,
        )
        assert API_PORT == 8000
        assert UI_PORT == 8501
        assert HEALTH_POLL_TIMEOUT == 30.0
        ok, missing = verify_bundle_integrity()
        assert isinstance(ok, bool)

    def test_app_version_string(self):
        assert app.version == "2.0.0"  # API version, not product version


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
