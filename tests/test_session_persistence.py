"""
PR #2.1 — Session Persistence Tests

Verify SQLite-backed sessions survive server "restarts" and clean up properly.
"""
from __future__ import annotations

import sys, os, uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.auth.models import AuthUser
from src.data.db import _get_conn, create_user
from src.auth.session import create_session, get_user_by_token, destroy_session


def _make_db_user() -> str:
    """Create a real user in DB for FK compliance, return user_id."""
    uid = f"sp_{uuid.uuid4().hex[:12]}"
    create_user(uid, f"{uid}@test.local", "nohash", "SessionTest")
    return uid


@pytest.fixture(autouse=True)
def _clean_sessions():
    """Remove all sessions before each test for isolation."""
    conn = _get_conn()
    conn.execute("DELETE FROM sessions")
    conn.commit()
    yield
    conn.execute("DELETE FROM sessions")
    conn.commit()


class TestSessionPersistence:
    """Verify sessions persist in SQLite, survive simulated restarts, and expire."""

    def test_create_and_get_session(self):
        """Token created → retrievable."""
        uid = _make_db_user()
        user = AuthUser(
            id=uid, email=f"{uid}@test.local", display_name="SessionTest",
            is_guest=True)
        token = create_session(user)
        got = get_user_by_token(token)
        assert got is not None
        assert got.id == uid
        assert got.display_name == "SessionTest"

    def test_session_survives_storage_reload(self):
        """Session persists across simulated "restart" (no in-memory state)."""
        import importlib
        uid = _make_db_user()
        user = AuthUser(
            id=uid, email=f"{uid}@test.local", display_name="Survivor",
            is_guest=True)
        token = create_session(user)

        # "Restart": re-import session module (simulates fresh process)
        import src.auth.session
        importlib.reload(src.auth.session)

        # Token should still work — data lives in SQLite, not memory
        got = get_user_by_token(token)
        assert got is not None
        assert got.id == uid

    def test_destroy_session_invalidates_token(self):
        """After destroy_session, token no longer works."""
        uid = _make_db_user()
        user = AuthUser(
            id=uid, email=f"{uid}@test.local", display_name="Destroy",
            is_guest=True)
        token = create_session(user)
        assert get_user_by_token(token) is not None

        destroy_session(token)
        assert get_user_by_token(token) is None

    def test_expired_token_removed(self):
        """Expired token → None and removed from DB."""
        import time
        uid = _make_db_user()
        user = AuthUser(
            id=uid, email=f"{uid}@test.local", display_name="Expire",
            is_guest=True)
        token = create_session(user)

        # Artificially expire the session
        conn = _get_conn()
        conn.execute(
            "UPDATE sessions SET expires_at = ? WHERE token = ?",
            (time.time() - 1, token))
        conn.commit()

        # Token should be invalid now
        assert get_user_by_token(token) is None

        # Token row should be deleted from DB
        row = conn.execute(
            "SELECT token FROM sessions WHERE token = ?", (token,)).fetchone()
        assert row is None
