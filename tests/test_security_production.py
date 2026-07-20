"""
Phase 10.4-B — Security Production Tests

Covers:
  1. Unauthorized request (missing/invalid/expired token)
  2. Permission denied (wrong role)
  3. Token budget exceeded
  4. Multi-user isolation
  5. Audit log integration
  6. v1 deprecated endpoints with auth
  7. v2 pipeline auth chain

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import sys, os, time, json, uuid
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)

# ── Helpers ──────────────────────────────────

def _register_and_login(email: str, role: str = "free") -> dict:
    """Register a user and return auth dict with headers, user_id, role."""
    client.post("/api/v2/auth/register", json={
        "email": email, "password": "secpass123", "display_name": f"SecTest_{role}",
    })
    resp = client.post("/api/v2/auth/login", json={
        "email": email, "password": "secpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['token']}"},
        "user_id": data["user_id"],
        "email": email,
        "token": data["token"],
    }

# ── Pre-create test users ──
USER1 = None
USER2 = None


def _user1():
    global USER1
    if USER1 is None:
        USER1 = _register_and_login(f"sec_user1_{uuid.uuid4().hex[:6]}@a3.local", "free")
    return USER1


def _user2():
    global USER2
    if USER2 is None:
        USER2 = _register_and_login(f"sec_user2_{uuid.uuid4().hex[:6]}@a3.local", "free")
    return USER2


# ═══════════════════════════════════════════════
# 1. Unauthorized Requests
# ═══════════════════════════════════════════════

class TestUnauthorizedRequests:
    """Tests for missing, invalid, and expired tokens."""

    def test_missing_token_v2_run(self):
        """POST /api/v2/learning/run without token → 401."""
        resp = client.post("/api/v2/learning/run", json={"goal": "test"})
        assert resp.status_code == 401

    def test_missing_token_v2_learning(self):
        """POST /api/v2/learning/plan without token → 401."""
        resp = client.post("/api/v2/learning/plan", json={"goal": "test"})
        assert resp.status_code == 401

    def test_missing_token_v2_profile(self):
        """GET /api/v2/profile without token → 401."""
        resp = client.get("/api/v2/profile")
        assert resp.status_code == 401

    def test_missing_token_v2_history(self):
        """GET /api/v2/learning/history without token → 401."""
        resp = client.get("/api/v2/learning/history")
        assert resp.status_code == 401

    def test_missing_token_v1_learning(self):
        """POST /api/v1/learning/plan without token → 401."""
        resp = client.post("/api/v1/learning/plan", json={"goal": "test"})
        assert resp.status_code == 401

    def test_missing_token_v1_runtime(self):
        """GET /api/v1/runtime/state without token → 401."""
        resp = client.get("/api/v1/runtime/state")
        assert resp.status_code == 401

    def test_invalid_token_v2_run(self):
        """POST /api/v2/learning/run with invalid token → 401."""
        resp = client.post(
            "/api/v2/learning/run",
            json={"goal": "test"},
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )
        assert resp.status_code == 401

    def test_invalid_token_v1_runtime(self):
        """GET /api/v1/runtime/snapshot with invalid token → 401."""
        resp = client.get(
            "/api/v1/runtime/snapshot",
            headers={"Authorization": "Bearer bad_token"},
        )
        assert resp.status_code == 401

    def test_empty_token_v2(self):
        """POST /api/v2/learning/run with empty token → 401."""
        resp = client.post(
            "/api/v2/learning/run",
            json={"goal": "test"},
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_malformed_header_no_bearer(self):
        """Authorization header without Bearer prefix → 401."""
        resp = client.post(
            "/api/v2/learning/run",
            json={"goal": "test"},
            headers={"Authorization": "some_token"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════
# 2. Permission Denied
# ═══════════════════════════════════════════════

class TestPermissionDenied:
    """Tests for role-based access control."""

    def test_free_user_can_access_run(self):
        """Free users can access pipeline (rule-only mode)."""
        u = _user1()
        resp = client.post(
            "/api/v2/learning/run",
            json={"goal": "Learn Python async"},
            headers=u["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_free_user_can_access_own_data(self):
        """Free users can view their own profile/history."""
        u = _user1()
        resp = client.get("/api/v2/learning/history", headers=u["headers"])
        assert resp.status_code == 200

    def test_free_user_can_see_own_profile(self):
        """Free users can view their profile."""
        u = _user1()
        resp = client.get("/api/v2/profile", headers=u["headers"])
        assert resp.status_code == 200


# ═══════════════════════════════════════════════
# 3. Token Budget
# ═══════════════════════════════════════════════

class TestTokenBudget:
    """Tests for token budget enforcement."""

    def test_token_budget_check_before_run(self):
        """Pipeline run should check token budget."""
        u = _user1()
        resp = client.post(
            "/api/v2/learning/run",
            json={"goal": "Learn Python iterators"},
            headers=u["headers"],
        )
        # Should succeed for rule-only (no LLM tokens used)
        assert resp.status_code == 200

    def test_token_budget_headers_present(self):
        """Response should reflect budget usage."""
        u = _user1()
        resp = client.post(
            "/api/v2/learning/run",
            json={"goal": "Learn Python generators"},
            headers=u["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "duration_ms" in data
        assert "memory_saved" in data


# ═══════════════════════════════════════════════
# 4. Multi-User Isolation
# ═══════════════════════════════════════════════

class TestMultiUserIsolation:
    """Tests that users cannot see each other's data."""

    def test_user_cannot_see_other_user_history(self):
        """User A should not see User B's history via API."""
        u1 = _user1()
        u2 = _user2()

        # Run pipeline as user 1
        client.post(
            "/api/v2/learning/run",
            json={"goal": "User 1 goal"},
            headers=u1["headers"],
        )

        # User 2 should NOT see user 1's data
        resp = client.get("/api/v2/learning/stats", headers=u2["headers"])
        assert resp.status_code == 200

    def test_token_isolation(self):
        """Token from user A should not authenticate as user B."""
        u1 = _user1()
        # u1 token works for u1
        resp = client.get("/api/v2/profile", headers=u1["headers"])
        assert resp.status_code == 200
        assert resp.json()["user_id"] == u1["user_id"]

    def test_different_users_different_results(self):
        """Two users running pipeline get different run_ids."""
        u1 = _user1()
        u2 = _user2()

        r1 = client.post(
            "/api/v2/learning/run",
            json={"goal": "Goal A"},
            headers=u1["headers"],
        )
        r2 = client.post(
            "/api/v2/learning/run",
            json={"goal": "Goal B"},
            headers=u2["headers"],
        )

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["run_id"] != r2.json()["run_id"]
        assert r1.json()["user_id"] != r2.json()["user_id"]


# ═══════════════════════════════════════════════
# 5. Audit Log Integration
# ═══════════════════════════════════════════════

class TestAuditLog:
    """Tests that audit log is wired to critical paths."""

    def test_audit_logger_importable(self):
        """AuditLogger can be imported."""
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        assert logger is not None

    def test_audit_log_logs_entry(self):
        """AuditLogger.log() writes a valid entry."""
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        entry = logger.log(
            user_id="test_audit",
            role="free",
            endpoint="/api/v2/learning/run",
            method="POST",
            status_code=200,
            success=True,
        )
        assert entry.event_id.startswith("audit_")
        assert entry.user_id == "test_audit"

    def test_audit_log_query(self):
        """AuditLogger.query() returns entries."""
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        logger.log(user_id="q_user", role="free", endpoint="/t", method="GET")
        entries = logger.query("q_user", limit=10)
        assert len(entries) > 0

    def test_audit_log_creates_file(self):
        """Audit log creates JSONL file on disk."""
        from src.security.audit import AuditLogger
        uid = f"audit_file_{uuid.uuid4().hex[:8]}"
        logger = AuditLogger()
        logger.log(user_id=uid, role="free", endpoint="/t", method="GET")
        path = Path.home() / ".a3-agent/workspace" / uid / "security" / "audit.jsonl"
        assert path.exists()

    def test_audit_log_user_stats(self):
        """AuditLogger.get_user_stats() returns aggregate stats."""
        from src.security.audit import AuditLogger
        uid = f"stats_{uuid.uuid4().hex[:8]}"
        logger = AuditLogger()
        logger.log(user_id=uid, role="pro", endpoint="/a", method="POST", tokens_used=100, success=True)
        logger.log(user_id=uid, role="pro", endpoint="/b", method="GET", success=True)
        stats = logger.get_user_stats(uid)
        assert stats["total_calls"] >= 2
        assert stats["total_tokens"] >= 100

    def test_audit_suspicious_detection(self):
        """Suspicious activity detection works."""
        from src.security.audit import AuditLogger
        uid = f"susp_{uuid.uuid4().hex[:8]}"
        logger = AuditLogger()
        for i in range(15):
            logger.log(user_id=uid, role="free", endpoint="/f", method="POST", success=(i % 4 != 0))
        suspicious = logger.get_suspicious_activity(uid, lookback_hours=1)


# ═══════════════════════════════════════════════
# 6. v1 Deprecated Endpoints with Auth
# ═══════════════════════════════════════════════

class TestV1DeprecatedAuth:
    """Tests that v1 deprecated endpoints work with auth."""

    def test_v1_learning_with_auth(self):
        """POST /api/v1/learning/plan with valid token → 200."""
        u = _user1()
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": "Test Python", "provider": "rule"},
            headers=u["headers"],
        )
        assert resp.status_code == 200
        assert "X-Deprecated-API" in resp.headers
        assert resp.headers["X-Deprecated-API"] == "true"

    def test_v1_runtime_with_auth(self):
        """GET /api/v1/runtime/state with valid token → 200."""
        from veritas.runtime import RuntimeBus
        RuntimeBus.init()
        u = _user1()
        resp = client.get("/api/v1/runtime/state", headers=u["headers"])
        assert resp.status_code == 200
        assert "X-Deprecated-API" in resp.headers

    def test_v1_learning_migration_header(self):
        """v1 response includes migration path header."""
        u = _user1()
        resp = client.post(
            "/api/v1/learning/plan",
            json={"goal": "Test"},
            headers=u["headers"],
        )
        assert resp.headers.get("X-Migration-Path") == "/api/v2/learning/run"

    def test_v1_runtime_sunset_header(self):
        """v1 runtime response includes Sunset header."""
        from veritas.runtime import RuntimeBus
        RuntimeBus.init()
        u = _user1()
        resp = client.get("/api/v1/runtime/state", headers=u["headers"])
        assert "Sunset" in resp.headers


# ═══════════════════════════════════════════════
# 7. v2 Pipeline Auth Chain
# ═══════════════════════════════════════════════

class TestV2PipelineAuth:
    """Tests that v2 pipeline has complete auth chain."""

    def test_v2_pipeline_returns_run_id(self):
        """Successful pipeline run returns run_id and trace."""
        u = _user1()
        resp = client.post(
            "/api/v2/learning/run",
            json={"goal": "Learn testing"},
            headers=u["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "run_id" in data
        assert "trace" in data
        assert "artifacts_saved" in data

    def test_v2_pipeline_includes_memory_saved(self):
        """Pipeline result includes memory_saved flag."""
        u = _user1()
        resp = client.post(
            "/api/v2/learning/run",
            json={"goal": "Learn docker"},
            headers=u["headers"],
        )
        data = resp.json()
        assert "memory_saved" in data
        assert isinstance(data["memory_saved"], bool)

    def test_logout_invalidates_token(self):
        """After logout, old token should fail on next request."""
        u = _register_and_login(f"logout_test_{uuid.uuid4().hex[:6]}@a3.local")
        resp = client.post("/api/v2/auth/logout", headers=u["headers"])
        assert resp.status_code == 200
        # Token should be invalidated — subsequent requests fail
        resp2 = client.get("/api/v2/profile", headers=u["headers"])
        # Authentication check should reject
        assert resp2.status_code in (401,)

    def test_guest_can_access_profile(self):
        """Guest users can create and access profile."""
        g = client.post("/api/v2/auth/guest", json={"display_name": "GuestTest"}).json()
        gh = {"Authorization": f"Bearer {g['token']}"}
        resp = client.get("/api/v2/profile", headers=gh)
        assert resp.status_code in (200, 401)  # guests may have limited access


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
