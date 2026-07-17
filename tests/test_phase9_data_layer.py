"""
Phase 9.1 — Data Layer Tests

Tests for: db.py, auth/, data/stores, API routes.
"""
from __future__ import annotations

import os
import sys
import json
import uuid
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


# ── Helpers ───────────────────────────────────────────────

def _make_user():
    """Create a test user and return its id."""
    from src.data.db import create_user
    uid = uuid.uuid4().hex[:12]
    create_user(uid, f"{uid}@test.com", "hash123", "Test")
    return uid


# ── DB Tests ──────────────────────────────────────────────

class TestDatabase:
    def test_init_creates_tables(self):
        from src.data.db import init_db, _get_conn
        init_db()
        conn = _get_conn()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        assert "users" in table_names
        assert "learning_records" in table_names
        assert "chat_threads" in table_names
        assert "chat_messages" in table_names

    def test_create_and_get_user(self):
        from src.data.db import create_user, get_user_by_id, get_user_by_email
        uid = uuid.uuid4().hex[:12]
        user = create_user(uid, f"{uid}@test.com", "hash123", "Test User")
        assert user.id == uid
        row = get_user_by_id(uid)
        assert row is not None
        assert row["email"] == f"{uid}@test.com"

    def test_learning_records_crud(self):
        from src.data.db import (
            LearningRecord, create_learning_record,
            get_user_records, get_user_stats,
        )
        uid = _make_user()
        for i in range(3):
            rec = LearningRecord(
                id=uuid.uuid4().hex[:16], user_id=uid,
                agent="tutor", action="explain",
                course_id="python101",
                result_json=json.dumps({"topic": f"topic_{i}"}),
                score=80 + i * 5, duration_ms=1000 + i * 100,
            )
            create_learning_record(rec)
        records = get_user_records(uid)
        assert len(records) == 3
        stats = get_user_stats(uid)
        assert stats["total_sessions"] == 3
        assert stats["avg_score"] == pytest.approx(85.0)

    def test_chat_threads_crud(self):
        from src.data.db import create_thread, get_user_threads, update_thread_title
        uid = _make_user()
        t1 = create_thread(uuid.uuid4().hex[:16], uid, "Thread 1")
        t2 = create_thread(uuid.uuid4().hex[:16], uid, "Thread 2")
        threads = get_user_threads(uid)
        assert len(threads) == 2
        # Update title and verify
        update_thread_title(t1.id, "Updated")
        threads2 = get_user_threads(uid)
        titles = {t["title"] for t in threads2}
        assert "Updated" in titles
        assert "Thread 2" in titles

    def test_chat_messages_crud(self):
        from src.data.db import (
            create_thread, ChatMessage, create_message, get_thread_messages,
        )
        uid = _make_user()
        tid = uuid.uuid4().hex[:16]
        create_thread(tid, uid, "Test")
        create_message(ChatMessage(
            id=uuid.uuid4().hex[:16], thread_id=tid, role="user", content="Hello"))
        create_message(ChatMessage(
            id=uuid.uuid4().hex[:16], thread_id=tid, role="assistant", content="Hi"))
        msgs = get_thread_messages(tid)
        assert len(msgs) == 2


# ── Auth Tests ────────────────────────────────────────────

class TestAuthManager:
    def test_register_and_login(self):
        from src.auth import register, login, RegisterRequest, LoginRequest
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        result = register(RegisterRequest(
            email=email, password="testpass123", display_name="Tester"))
        assert result is not None
        assert result.token
        result2 = login(LoginRequest(email=email, password="testpass123"))
        assert result2 is not None

    def test_login_wrong_password(self):
        from src.auth import register, login, RegisterRequest, LoginRequest
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        register(RegisterRequest(email=email, password="correct", display_name="X"))
        result = login(LoginRequest(email=email, password="wrong"))
        assert result is None

    def test_register_duplicate_email(self):
        from src.auth import register, RegisterRequest
        email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
        r1 = register(RegisterRequest(email=email, password="pass1"))
        assert r1 is not None
        r2 = register(RegisterRequest(email=email, password="pass2"))
        assert r2 is None

    def test_guest_login(self):
        from src.auth import login_guest, get_current_user
        result = login_guest("Guest User")
        assert result.token
        user = get_current_user(result.token)
        assert user is not None
        assert user.is_guest

    def test_logout(self):
        from src.auth import login_guest, logout, get_current_user
        result = login_guest()
        assert get_current_user(result.token) is not None
        logout(result.token)
        assert get_current_user(result.token) is None

    def test_password_hashing(self):
        from src.auth.auth_manager import _make_hash, _verify_password
        h = _make_hash("mypassword")
        assert _verify_password("mypassword", h)
        assert not _verify_password("wrong", h)

    def test_short_password_rejected(self):
        from src.auth import register, RegisterRequest
        result = register(RegisterRequest(email="test@x.com", password="ab"))
        assert result is None

    def test_session_expiry(self):
        from src.auth.session import create_session, get_user_by_token, _sessions
        from src.auth.models import AuthUser
        import time
        user = AuthUser(id="test", email="", display_name="T", is_guest=True)
        token = create_session(user)
        assert get_user_by_token(token) is not None
        _sessions[token]["expires_at"] = time.time() - 1
        assert get_user_by_token(token) is None


# ── Student Store Tests ───────────────────────────────────

class TestStudentStore:
    def test_save_and_load(self):
        from src.data.student_store import save_profile, get_profile
        uid = _make_user()
        data = {"name": "Alice", "level": "beginner", "interests": ["python"]}
        save_profile(uid, data)
        loaded = get_profile(uid)
        assert loaded is not None
        assert loaded["name"] == "Alice"

    def test_update_and_delete(self):
        from src.data.student_store import save_profile, get_profile, delete_profile
        uid = _make_user()
        save_profile(uid, {"name": "A", "level": "beginner"})
        save_profile(uid, {"name": "A", "level": "advanced"})
        assert get_profile(uid)["level"] == "advanced"
        delete_profile(uid)
        assert get_profile(uid) is None


# ── Learning Records Tests ────────────────────────────────

class TestLearningRecords:
    def test_record_action(self):
        from src.data.learning_records import record_agent_action, get_history
        uid = _make_user()
        record_agent_action(uid, "tutor", "explain",
                            result={"topic": "loops"}, score=85)
        history = get_history(uid)
        assert len(history) >= 1

    def test_stats(self):
        from src.data.learning_records import record_agent_action, get_stats
        uid = _make_user()
        for score in [70, 80, 90]:
            record_agent_action(uid, "eval", "quiz", score=score)
        stats = get_stats(uid)
        assert stats["total_sessions"] == 3
        assert stats["avg_score"] == pytest.approx(80.0)


# ── Thread Store Tests ────────────────────────────────────

class TestThreadStore:
    def test_create_and_list(self):
        from src.data.thread_store import new_thread, list_threads
        uid = _make_user()
        new_thread(uid, "Chat 1")
        new_thread(uid, "Chat 2")
        assert len(list_threads(uid)) == 2

    def test_add_and_get_messages(self):
        from src.data.thread_store import new_thread, add_message, get_messages
        uid = _make_user()
        t = new_thread(uid, "Test")
        add_message(t["id"], "user", "Hello")
        add_message(t["id"], "assistant", "Hi there!")
        msgs = get_messages(t["id"])
        assert len(msgs) == 2
        assert msgs[1]["content"] == "Hi there!"

    def test_rename_thread(self):
        from src.data.thread_store import new_thread, rename_thread, list_threads
        uid = _make_user()
        t = new_thread(uid, "Old")
        rename_thread(t["id"], "New")
        assert list_threads(uid)[0]["title"] == "New"


# ── KB Manager Tests ──────────────────────────────────────

class TestKBManager:
    def test_list_courses(self):
        from src.data.kb_manager import list_courses
        courses = list_courses()
        assert isinstance(courses, list)
        assert len(courses) > 0

    def test_get_resources_is_dict(self):
        from src.data.kb_manager import get_course_resources
        resources = get_course_resources("artificial_intelligence_multi_agent_course")
        assert isinstance(resources, dict)
        assert len(resources) > 0

    def test_get_exercises_is_dict(self):
        from src.data.kb_manager import get_course_exercises
        exercises = get_course_exercises("artificial_intelligence_multi_agent_course")
        assert isinstance(exercises, dict)

    def test_search_finds_results(self):
        from src.data.kb_manager import search_courses
        results = search_courses("agent")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_course_meta(self):
        from src.data.kb_manager import get_course_meta
        meta = get_course_meta("artificial_intelligence_multi_agent_course")
        assert "course_id" in meta
        assert "course_name" in meta


# ── Auth API Tests ────────────────────────────────────────

class TestAuthAPI:
    @pytest.fixture
    def client(self):
        from src.api.server import app
        return TestClient(app)

    def test_register(self, client):
        email = f"api_{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v2/auth/register", json={
            "email": email, "password": "testpass123", "display_name": "API"})
        assert resp.status_code == 201
        assert "token" in resp.json()

    def test_login(self, client):
        email = f"api_{uuid.uuid4().hex[:8]}@test.com"
        client.post("/api/v2/auth/register", json={
            "email": email, "password": "testpass", "display_name": "A"})
        resp = client.post("/api/v2/auth/login", json={
            "email": email, "password": "testpass"})
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v2/auth/login", json={
            "email": "no@test.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_guest(self, client):
        resp = client.post("/api/v2/auth/guest", json={"display_name": "Guest"})
        assert resp.status_code == 200

    def test_me_authenticated(self, client):
        resp = client.post("/api/v2/auth/guest", json={"display_name": "Me"})
        token = resp.json()["token"]
        resp2 = client.get("/api/v2/auth/me",
                           headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 200
        assert resp2.json()["display_name"] == "Me"

    def test_me_unauthorized(self, client):
        resp = client.get("/api/v2/auth/me")
        assert resp.status_code == 401

    def test_logout(self, client):
        resp = client.post("/api/v2/auth/guest")
        token = resp.json()["token"]
        resp2 = client.post("/api/v2/auth/logout",
                            headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 200
        resp3 = client.get("/api/v2/auth/me",
                           headers={"Authorization": f"Bearer {token}"})
        assert resp3.status_code == 401
