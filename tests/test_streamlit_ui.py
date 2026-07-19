"""
PR #3 — Streamlit UI Tests

Tests for API client, auth logic, cross-user isolation, and architecture constraints.
"""
from __future__ import annotations

import sys, os, json, uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


# ══════════════════════════════════════════════════
# Architecture Constraint: No src/ imports in web/
# ══════════════════════════════════════════════════

def test_no_src_imports_in_api_client():
    """web/utils/api.py must not import from src/."""
    with open("web/utils/api.py") as f:
        content = f.read()
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("from src.") or stripped.startswith("import src."):
            pytest.fail(f"Banned src/ import in web/utils/api.py: {stripped}")


def test_no_src_imports_in_auth_component():
    """web/components/auth.py must not import from src/."""
    with open("web/components/auth.py") as f:
        content = f.read()
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("from src.") or stripped.startswith("import src."):
            pytest.fail(
                f"Banned src/ import in web/components/auth.py: {stripped}")


def test_no_src_imports_in_chat_component():
    """web/components/chat.py must not import from src/."""
    with open("web/components/chat.py") as f:
        content = f.read()
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("from src.") or stripped.startswith("import src."):
            pytest.fail(
                f"Banned src/ import in web/components/chat.py: {stripped}")


def test_no_src_imports_in_app_v4():
    """web/app_v4.py must not import from src/."""
    with open("web/app_v4.py") as f:
        content = f.read()
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("from src.") or stripped.startswith("import src."):
            pytest.fail(f"Banned src/ import in web/app_v4.py: {stripped}")


# ══════════════════════════════════════════════════
# Shared fixtures
# ══════════════════════════════════════════════════

@pytest.fixture(scope="module")
def test_client():
    from src.api.server import app
    return TestClient(app)


@pytest.fixture
def api(test_client):
    from web.utils.api import A3APIClient
    a = A3APIClient()
    a._test_client = test_client
    return a


def _auth_headers(client):
    """Register + login, return (token, user_id)."""
    email = f"ui_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/api/v2/auth/register", json={
        "email": email, "password": "testpass", "display_name": "UI Test"})
    resp = client.post("/api/v2/auth/login", json={
        "email": email, "password": "testpass"})
    data = resp.json()
    return data["token"], data["user_id"]


# ══════════════════════════════════════════════════
# Auth Tests
# ══════════════════════════════════════════════════

class TestAPIClientAuth:

    def test_token_injection(self, api, test_client):
        """Token is set and used in subsequent requests."""
        token, user_id = _auth_headers(test_client)
        api.set_token(token)
        me = api.me()
        assert me is not None
        assert me.get("id") == user_id

    def test_guest_login_returns_valid_token(self, api):
        """Guest login returns a working token."""
        result = api.guest("Test Guest")
        assert result.token
        assert result.user_id
        assert result.display_name == "Test Guest"

    def test_login_wrong_password_raises(self, api):
        """Bad credentials raise A3APIError."""
        from web.utils.api import A3APIError
        with pytest.raises(A3APIError) as exc:
            api.login("nonexistent@test.com", "wrongpass")
        assert exc.value.status == 401

    def test_register_then_login(self, api, test_client):
        """Register creates account, login returns same user_id."""
        email = f"reg_{uuid.uuid4().hex[:6]}@test.com"
        reg = api.register(email, "testpass", "RegTest")
        assert reg.token
        assert reg.user_id

        log = api.login(email, "testpass")
        assert log.user_id == reg.user_id


# ══════════════════════════════════════════════════
# Chat Tests
# ══════════════════════════════════════════════════

class TestAPIClientChat:

    def _setup(self, api, test_client):
        token, _ = _auth_headers(test_client)
        api.set_token(token)

    def test_create_thread_and_send_message(self, api, test_client):
        """End-to-end chat: create thread, send message, read back."""
        self._setup(api, test_client)
        thread = api.create_thread("Test Chat")
        tid = thread["id"]
        resp = api.send_message("Hello, tutor!", thread_id=tid)
        assert resp["thread_id"] == tid
        assert len(resp["content"]) > 0
        msgs = api.get_messages(tid)
        assert len(msgs) >= 2

    def test_thread_list(self, api, test_client):
        """Thread list returns user's threads."""
        self._setup(api, test_client)
        api.create_thread("Thread A")
        api.create_thread("Thread B")
        threads = api.get_threads()
        assert len(threads) >= 2

    def test_rename_thread(self, api, test_client):
        """Rename thread works."""
        self._setup(api, test_client)
        thread = api.create_thread("Old Name")
        tid = thread["id"]
        api.rename_thread(tid, "New Name")
        threads = api.get_threads()
        names = [t["title"] for t in threads]
        assert "New Name" in names


# ══════════════════════════════════════════════════
# Cross-User Isolation (PR #2.1 verification)
# ══════════════════════════════════════════════════

class TestAPIClientCrossUserIsolation:

    def test_cannot_access_others_thread(self, api, test_client):
        """User A's thread is invisible to User B via API client."""
        from web.utils.api import A3APIError

        token_a, _ = _auth_headers(test_client)
        token_b = test_client.post("/api/v2/auth/guest",
                                   json={"display_name": "B"}).json()["token"]

        api.set_token(token_a)
        thread = api.create_thread("A's Secret")
        tid = thread["id"]
        api.send_message("Secret!", thread_id=tid)

        api.set_token(token_b)
        with pytest.raises(A3APIError) as exc:
            api.get_messages(tid)
        assert exc.value.status in (403, 404)

    def test_cannot_rename_others_thread(self, api, test_client):
        """User B cannot rename User A's thread."""
        from web.utils.api import A3APIError

        token_a, _ = _auth_headers(test_client)
        token_b = test_client.post("/api/v2/auth/guest",
                                   json={"display_name": "B"}).json()["token"]

        api.set_token(token_a)
        thread = api.create_thread("A's Thread")
        tid = thread["id"]

        api.set_token(token_b)
        with pytest.raises(A3APIError) as exc:
            api.rename_thread(tid, "Hacked")
        assert exc.value.status in (403, 404)
