"""
Phase 9.1 — Session & Conversation Layer Tests

Covers:
- Session / Message data models
- SessionManager: create_session, get_session, close_session, delete_session
- Multi-user isolation
- append_message, load_context (token budget, max messages)
- resume_session
- Disk persistence (JSONL)
- Session listing and summaries
- Artifact linking
- Edge cases: missing sessions, empty messages, concurrent access patterns
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from workspace.manager import WorkspaceManager
from session.manager import SessionManager, Session, Message


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_session_manager() -> SessionManager:
    tmpdir = tempfile.mkdtemp(prefix="a3_test_sm_")
    wm = WorkspaceManager(root=tmpdir)
    return SessionManager(workspace=wm), tmpdir


# ──────────────────────────────────────────────
# 1. Data Model Tests
# ──────────────────────────────────────────────

class TestDataModels:

    def test_message_defaults(self):
        m = Message(role="user", content="Hello")
        assert m.role == "user"
        assert m.content == "Hello"
        assert m.timestamp != ""
        assert m.metadata == {}

    def test_message_to_dict(self):
        m = Message(role="assistant", content="Hi there", metadata={"tokens": 5})
        d = m.to_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "Hi there"
        assert d["metadata"]["tokens"] == 5

    def test_message_from_dict(self):
        d = {"role": "system", "content": "You are a tutor.", "timestamp": "2026-01-01T00:00:00"}
        m = Message.from_dict(d)
        assert m.role == "system"
        assert m.content == "You are a tutor."

    def test_message_roundtrip(self):
        m = Message(role="user", content="Q", metadata={"source": "web"})
        d = m.to_dict()
        m2 = Message.from_dict(d)
        assert m2.role == "user"
        assert m2.metadata["source"] == "web"

    def test_session_defaults(self):
        session = Session(session_id="s1", student_id="u1")
        assert session.title == "New Session"
        assert session.is_active is True
        assert session.messages == []
        assert session.artifacts == []

    def test_session_message_count(self):
        session = Session(session_id="s1", student_id="u1")
        assert session.message_count == 0
        session.messages.append(Message(role="user", content="Q"))
        session.messages.append(Message(role="assistant", content="A"))
        assert session.message_count == 2

    def test_session_last_message(self):
        session = Session(session_id="s1", student_id="u1")
        assert session.last_message is None
        session.messages.append(Message(role="user", content="first"))
        session.messages.append(Message(role="assistant", content="last"))
        assert session.last_message.content == "last"

    def test_session_to_dict(self):
        session = Session(session_id="s1", student_id="u1", title="Python 101",
                          related_course="python_basics", artifacts=["img_001"])
        d = session.to_dict()
        assert d["session_id"] == "s1"
        assert d["title"] == "Python 101"
        assert d["is_active"] is True

    def test_session_from_dict(self):
        d = {"session_id": "s2", "student_id": "u2", "title": "Test",
             "is_active": False, "messages": [
                 {"role": "user", "content": "Q"}]}
        session = Session.from_dict(d)
        assert session.student_id == "u2"
        assert session.is_active is False
        assert len(session.messages) == 1

    def test_session_roundtrip(self):
        session = Session(session_id="s3", student_id="u3", title="Loop",
                          messages=[Message(role="user", content="hi")],
                          artifacts=["a1", "a2"])
        d = session.to_dict()
        s2 = Session.from_dict(d)
        assert s2.title == "Loop"
        assert len(s2.artifacts) == 2


# ──────────────────────────────────────────────
# 2. Session Lifecycle Tests
# ──────────────────────────────────────────────

class TestSessionLifecycle:

    def setup_method(self):
        self.sm, self.tmpdir = _make_session_manager()

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_session(self):
        session = self.sm.create_session("student_001", "Python Lesson 1")
        assert session.student_id == "student_001"
        assert session.title == "Python Lesson 1"
        assert session.is_active is True
        assert session.session_id.startswith("sess_")

    def test_create_session_with_course(self):
        session = self.sm.create_session(
            "student_001", "Advanced Python",
            related_course="python_advanced",
        )
        assert session.related_course == "python_advanced"

    def test_create_session_with_metadata(self):
        session = self.sm.create_session(
            "student_001", "Test",
            metadata={"goal": "learn decorators", "level": "intermediate"},
        )
        assert session.metadata["goal"] == "learn decorators"

    def test_get_session(self):
        session = self.sm.create_session("student_001", "Test")
        retrieved = self.sm.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_get_nonexistent_session(self):
        result = self.sm.get_session("nonexistent_id")
        assert result is None

    def test_close_session(self):
        session = self.sm.create_session("student_001", "To Close")
        assert session.is_active is True
        result = self.sm.close_session(session.session_id)
        assert result is True
        retrieved = self.sm.get_session(session.session_id)
        assert retrieved.is_active is False

    def test_close_nonexistent_session(self):
        result = self.sm.close_session("nonexistent")
        assert result is False

    def test_delete_session(self):
        session = self.sm.create_session("student_001", "To Delete")
        result = self.sm.delete_session(session.session_id)
        assert result is True
        assert self.sm.get_session(session.session_id) is None

    def test_create_multiple_sessions_same_student(self):
        s1 = self.sm.create_session("student_001", "Session A")
        s2 = self.sm.create_session("student_001", "Session B")
        assert s1.session_id != s2.session_id


# ──────────────────────────────────────────────
# 3. Multi-User Isolation Tests
# ──────────────────────────────────────────────

class TestMultiUserIsolation:

    def setup_method(self):
        self.sm, self.tmpdir = _make_session_manager()

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_different_users_have_separate_sessions(self):
        s_a = self.sm.create_session("user_a", "User A Session")
        s_b = self.sm.create_session("user_b", "User B Session")

        sessions_a = self.sm.list_sessions("user_a")
        sessions_b = self.sm.list_sessions("user_b")

        ids_a = [s.session_id for s in sessions_a]
        ids_b = [s.session_id for s in sessions_b]

        assert s_a.session_id in ids_a
        assert s_b.session_id in ids_b
        assert s_a.session_id not in ids_b
        assert s_b.session_id not in ids_a

    def test_user_a_cannot_access_user_b_messages(self):
        session_a = self.sm.create_session("user_a", "Private")
        session_b = self.sm.create_session("user_b", "Other")

        self.sm.append_message(session_a.session_id, "user", "secret msg")

        # User b should not see this
        context_b = self.sm.load_context(session_b.session_id)
        assert len(context_b) == 0


# ──────────────────────────────────────────────
# 4. Message Operations Tests
# ──────────────────────────────────────────────

class TestMessageOperations:

    def setup_method(self):
        self.sm, self.tmpdir = _make_session_manager()

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_append_message(self):
        session = self.sm.create_session("student_001", "Chat")
        msg = self.sm.append_message(session.session_id, "user", "What is Python?")
        assert msg is not None
        assert msg.role == "user"
        assert msg.content == "What is Python?"

    def test_append_message_nonexistent_session(self):
        msg = self.sm.append_message("bad_id", "user", "Hello")
        assert msg is None

    def test_append_multiple_messages(self):
        session = self.sm.create_session("student_001", "Multi")
        self.sm.append_message(session.session_id, "user", "Q1")
        self.sm.append_message(session.session_id, "assistant", "A1")
        self.sm.append_message(session.session_id, "user", "Q2")

        retrieved = self.sm.get_session(session.session_id)
        assert retrieved.message_count == 3

    def test_append_message_with_metadata(self):
        session = self.sm.create_session("student_001", "Meta")
        msg = self.sm.append_message(
            session.session_id, "assistant", "Answer",
            metadata={"tokens": 42, "model": "gpt-4o"},
        )
        assert msg.metadata["tokens"] == 42
        assert msg.metadata["model"] == "gpt-4o"

    def test_message_updates_session_timestamp(self):
        session = self.sm.create_session("student_001", "Time")
        original_updated = session.updated_at

        import time
        time.sleep(0.01)
        self.sm.append_message(session.session_id, "user", "Hello")

        retrieved = self.sm.get_session(session.session_id)
        assert retrieved.updated_at != original_updated

    def test_different_roles(self):
        session = self.sm.create_session("student_001", "Roles")
        for role in ["user", "assistant", "system"]:
            msg = self.sm.append_message(session.session_id, role, f"{role} message")
            assert msg.role == role


# ──────────────────────────────────────────────
# 5. Context Loading Tests
# ──────────────────────────────────────────────

class TestContextLoading:

    def setup_method(self):
        self.sm, self.tmpdir = _make_session_manager()

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_context_empty(self):
        session = self.sm.create_session("student_001", "Empty")
        context = self.sm.load_context(session.session_id)
        assert context == []

    def test_load_context_returns_all(self):
        session = self.sm.create_session("student_001", "Full")
        self.sm.append_message(session.session_id, "user", "Q1")
        self.sm.append_message(session.session_id, "assistant", "A1")
        self.sm.append_message(session.session_id, "user", "Q2")

        context = self.sm.load_context(session.session_id)
        assert len(context) == 3
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"

    def test_load_context_max_messages(self):
        session = self.sm.create_session("student_001", "Limited")
        for i in range(10):
            self.sm.append_message(session.session_id, "user", f"Msg {i}")

        context = self.sm.load_context(session.session_id, max_messages=3)
        assert len(context) == 3
        assert context[-1]["content"] == "Msg 9"

    def test_load_context_max_tokens(self):
        session = self.sm.create_session("student_001", "TokenBudget")
        self.sm.append_message(session.session_id, "user", "Short")
        self.sm.append_message(session.session_id, "assistant", "A" * 500)  # ~125 tokens
        self.sm.append_message(session.session_id, "user", "After")

        context = self.sm.load_context(session.session_id, max_tokens=50)
        # Should only include the last ~50 tokens worth
        assert len(context) <= 3

    def test_load_context_nonexistent(self):
        context = self.sm.load_context("bad_session")
        assert context == []

    def test_load_full_context(self):
        session = self.sm.create_session("student_001", "All")
        for i in range(5):
            self.sm.append_message(session.session_id, "user", f"msg{i}")

        context = self.sm.load_full_context(session.session_id)
        assert len(context) == 5


# ──────────────────────────────────────────────
# 6. Resume Session Tests
# ──────────────────────────────────────────────

class TestResumeSession:

    def setup_method(self):
        self.sm, self.tmpdir = _make_session_manager()

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_resume_active_session(self):
        session = self.sm.create_session("student_001", "Ongoing")
        self.sm.append_message(session.session_id, "user", "Hello")

        resumed = self.sm.resume_session(session.session_id)
        assert resumed is not None
        assert resumed.is_active is True
        assert resumed.message_count == 1

    def test_resume_closed_session(self):
        session = self.sm.create_session("student_001", "Closed")
        self.sm.close_session(session.session_id)

        resumed = self.sm.resume_session(session.session_id)
        assert resumed is not None
        assert resumed.is_active is True  # Should be reactivated

    def test_resume_nonexistent_session(self):
        result = self.sm.resume_session("nonexistent")
        assert result is None


# ──────────────────────────────────────────────
# 7. Persistence Tests
# ──────────────────────────────────────────────

class TestPersistence:

    def test_session_survives_manager_reload(self):
        """Session data persists across SessionManager instances."""
        tmpdir = tempfile.mkdtemp(prefix="a3_test_persist_")

        try:
            # First manager
            wm1 = WorkspaceManager(root=tmpdir)
            sm1 = SessionManager(workspace=wm1)
            session = sm1.create_session("student_001", "Persistent Test")
            session_id = session.session_id
            sm1.append_message(session_id, "user", "Will this survive?")
            sm1.append_message(session_id, "assistant", "Yes it will.")

            # Second manager (simulates app restart)
            wm2 = WorkspaceManager(root=tmpdir)
            sm2 = SessionManager(workspace=wm2)
            loaded = sm2.get_session(session_id)

            assert loaded is not None
            assert loaded.title == "Persistent Test"
            assert loaded.message_count == 2
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_messages_persist_to_disk(self):
        tmpdir = tempfile.mkdtemp(prefix="a3_test_disk_")
        try:
            wm = WorkspaceManager(root=tmpdir)
            sm = SessionManager(workspace=wm)
            session = sm.create_session("student_001", "Disk")
            sm.append_message(session.session_id, "user", "disk test")

            # Verify file exists
            msg_file = os.path.join(
                tmpdir, "student_001", "history", "sessions",
                f"{session.session_id}_messages.jsonl"
            )
            assert os.path.isfile(msg_file)

            with open(msg_file, "r") as f:
                lines = f.readlines()
            assert len(lines) >= 1
            assert "disk test" in lines[0]
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# ──────────────────────────────────────────────
# 8. Session Listing Tests
# ──────────────────────────────────────────────

class TestSessionListing:

    def setup_method(self):
        self.sm, self.tmpdir = _make_session_manager()

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_list_sessions(self):
        self.sm.create_session("student_001", "Session 1")
        self.sm.create_session("student_001", "Session 2")

        sessions = self.sm.list_sessions("student_001")
        assert len(sessions) == 2

    def test_list_sessions_empty(self):
        sessions = self.sm.list_sessions("new_student")
        assert sessions == []

    def test_list_sessions_active_only(self):
        s1 = self.sm.create_session("student_001", "Active")
        s2 = self.sm.create_session("student_001", "Inactive")
        self.sm.close_session(s2.session_id)

        active = self.sm.list_sessions("student_001", active_only=True)
        assert len(active) == 1
        assert active[0].session_id == s1.session_id

    def test_get_sessions_summary(self):
        self.sm.create_session("student_001", "Summary Test")
        summaries = self.sm.get_sessions_summary("student_001")
        assert len(summaries) == 1
        assert "session_id" in summaries[0]
        assert "title" in summaries[0]
        assert "message_count" in summaries[0]


# ──────────────────────────────────────────────
# 9. Artifact Linking Tests
# ──────────────────────────────────────────────

class TestArtifactLinking:

    def setup_method(self):
        self.sm, self.tmpdir = _make_session_manager()

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_link_artifact(self):
        session = self.sm.create_session("student_001", "With Artifacts")
        result = self.sm.link_artifact(session.session_id, "img_001")
        assert result is True

        retrieved = self.sm.get_session(session.session_id)
        assert "img_001" in retrieved.artifacts

    def test_link_artifact_duplicate(self):
        session = self.sm.create_session("student_001", "Dup")
        self.sm.link_artifact(session.session_id, "a1")
        self.sm.link_artifact(session.session_id, "a1")  # duplicate

        retrieved = self.sm.get_session(session.session_id)
        assert retrieved.artifacts.count("a1") == 1  # No duplicates

    def test_link_artifact_nonexistent_session(self):
        result = self.sm.link_artifact("bad_id", "a1")
        assert result is False


# ──────────────────────────────────────────────
# 10. Edge Cases
# ──────────────────────────────────────────────

class TestEdgeCases:

    def setup_method(self):
        self.sm, self.tmpdir = _make_session_manager()

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_long_message_content(self):
        session = self.sm.create_session("student_001", "Long")
        long_text = "A" * 10000
        msg = self.sm.append_message(session.session_id, "user", long_text)
        assert msg is not None
        assert len(msg.content) == 10000

    def test_unicode_content(self):
        session = self.sm.create_session("student_001", "Unicode")
        msg = self.sm.append_message(session.session_id, "user",
                                      "你好世界 🌍 Python 编程 🐍")
        assert "你好世界" in msg.content
        assert "🌍" in msg.content

    def test_empty_message_content(self):
        session = self.sm.create_session("student_001", "Empty")
        msg = self.sm.append_message(session.session_id, "user", "")
        assert msg is not None
        assert msg.content == ""
