"""
PR #2.1 — Chat Security Tests

Cross-user chat isolation: verify that User A cannot access User B's threads.
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


def _register_and_auth(client, prefix="A") -> dict:
    """Helper: register a user and return auth headers + user info."""
    email = f"security_{prefix}_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/api/v2/auth/register", json={
        "email": email, "password": "testpass", "display_name": f"User{prefix}"})
    resp = client.post("/api/v2/auth/login", json={
        "email": email, "password": "testpass"})
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['token']}"},
        "user_id": data["user_id"],
        "email": email,
    }


class TestChatThreadIsolation:
    """Verify User A cannot read/rename User B's threads."""

    def test_user_cannot_read_others_thread_messages(self, client):
        """User A creates thread → User B attempts read → 404."""
        user_a = _register_and_auth(client, "A")
        user_b = _register_and_auth(client, "B")

        # User A creates a thread with a message
        resp = client.post("/api/v2/chat/message", json={
            "message": "Secret discussion", "topic": "python"
        }, headers=user_a["headers"])
        assert resp.status_code == 200
        thread_id = resp.json()["thread_id"]

        # User A can read own messages
        resp_a = client.get(
            f"/api/v2/chat/threads/{thread_id}/messages",
            headers=user_a["headers"])
        assert resp_a.status_code == 200
        assert len(resp_a.json()) >= 2

        # User B attempts to read → must fail
        resp_b = client.get(
            f"/api/v2/chat/threads/{thread_id}/messages",
            headers=user_b["headers"])
        assert resp_b.status_code in (403, 404)

    def test_user_cannot_rename_others_thread(self, client):
        """User A creates thread → User B attempts rename → 404."""
        user_a = _register_and_auth(client, "A")
        user_b = _register_and_auth(client, "B")

        resp = client.post("/api/v2/chat/threads", json={
            "title": "My Private Thread"
        }, headers=user_a["headers"])
        assert resp.status_code == 201
        thread_id = resp.json()["id"]

        # User B attempts rename → must fail
        resp_b = client.patch(
            f"/api/v2/chat/threads/{thread_id}", json={"title": "Hacked"},
            headers=user_b["headers"])
        assert resp_b.status_code in (403, 404)

        # Verify title unchanged for User A
        resp_a = client.get("/api/v2/chat/threads", headers=user_a["headers"])
        threads = resp_a.json()
        assert any(t["id"] == thread_id and t["title"] == "My Private Thread"
                   for t in threads)

    def test_thread_list_only_returns_owners_threads(self, client):
        """Each user only sees their own threads."""
        user_a = _register_and_auth(client, "A")
        user_b = _register_and_auth(client, "B")

        # Both users create a thread
        client.post("/api/v2/chat/threads", json={
            "title": "A's Thread"}, headers=user_a["headers"])
        client.post("/api/v2/chat/threads", json={
            "title": "B's Thread"}, headers=user_b["headers"])

        # User A sees only "A's Thread"
        a_threads = client.get("/api/v2/chat/threads",
                               headers=user_a["headers"]).json()
        a_titles = [t["title"] for t in a_threads]
        assert "A's Thread" in a_titles
        assert "B's Thread" not in a_titles

    def test_nonexistent_thread_returns_404(self, client):
        """Accessing a non-existent thread returns 404 for any user."""
        user = _register_and_auth(client, "X")
        fake_id = uuid.uuid4().hex[:16]
        resp = client.get(
            f"/api/v2/chat/threads/{fake_id}/messages",
            headers=user["headers"])
        assert resp.status_code == 404
