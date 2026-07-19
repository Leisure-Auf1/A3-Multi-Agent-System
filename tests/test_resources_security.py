"""
PR #2.1 — Resource Security Tests

Verify the /resources/student/{id} endpoint requires auth + enforces ownership.
"""
from __future__ import annotations

import sys, os, uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.api.server import app
    return TestClient(app)


def _register_and_auth(client, prefix="X") -> dict:
    """Helper: register a user and return auth headers + user_id."""
    email = f"res_{prefix}_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/api/v2/auth/register", json={
        "email": email, "password": "testpass", "display_name": f"Res{prefix}"})
    resp = client.post("/api/v2/auth/login", json={
        "email": email, "password": "testpass"})
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['token']}"},
        "user_id": data["user_id"],
    }


class TestResourceStudentAuth:
    """Verify /resources/student/{id} requires authentication."""

    def test_no_token_returns_401(self, client):
        """Unauthenticated access → 401."""
        resp = client.get("/api/v2/resources/student/test-id")
        assert resp.status_code == 401

    def test_wrong_user_returns_403(self, client):
        """User A accessing User B's resources → 403."""
        user_a = _register_and_auth(client, "A")
        user_b = _register_and_auth(client, "B")

        # User A tries to access User B's resources
        resp = client.get(
            f"/api/v2/resources/student/{user_b['user_id']}",
            headers=user_a["headers"])
        assert resp.status_code == 403

    def test_own_resources_returns_200(self, client):
        """User accessing own resources → 200 (may be empty)."""
        user = _register_and_auth(client, "C")
        resp = client.get(
            f"/api/v2/resources/student/{user['user_id']}",
            headers=user["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
