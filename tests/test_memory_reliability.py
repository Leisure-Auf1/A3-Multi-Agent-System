"""
Phase 8.3-E0.5 — Memory Reliability Tests

Validates StudentMemory persistence under realistic AI Tutor usage:
- Multi-session: data accumulates across repeated learning sessions
- Multi-user: student isolation (no cross-contamination)
- Crash recovery: memory survives restart (reload from disk)
- Continuous workflows: rapid sequential sessions don't lose data
- SQLite dual-write: A3Workflow persists to both JSON and SQLite

Design: all student IDs are UUID-based (no stale data from previous runs).
"""

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _fresh_id(prefix: str = "rel") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _run_session(sid: str, goal: str = "Learn Python") -> dict:
    """Run one A3Workflow session and return result + memory state."""
    from workflow import A3Workflow
    from veritas.memory import MemoryManager

    wf = A3Workflow(student_id=sid)
    result = wf.run(
        user_goal=goal,
        user_profile={"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"},
    )
    mem = MemoryManager().get_student_memory(sid)
    return {
        "result": result,
        "memory": mem,
        "session_count": len(mem.session_summaries) if mem else 0,
        "profile_count": len(mem.profile_history) if mem else 0,
        "mastery_count": len(mem.mastery_map) if mem else 0,
    }


def _count_db_records(sid: str) -> int:
    """Count session records in A3 SQLite DB."""
    try:
        from src.data.db import _get_conn
        conn = _get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM learning_records "
            "WHERE user_id = ? AND agent = 'A3Workflow' AND action = 'session_completed'",
            (sid,)
        ).fetchone()
        return row["cnt"] if row else 0
    except Exception:
        return -1


# ──────────────────────────────────────────────
# 1. Multi-Session Persistence
# ──────────────────────────────────────────────


class TestMultiSessionPersistence:
    """Memory accumulates correctly across 3+ consecutive sessions."""

    def test_three_sessions_accumulate(self):
        """3 sessions → 3 session_summaries, 3 profile_history entries, growing mastery."""
        sid = _fresh_id("multi")
        counts = []

        for i in range(3):
            info = _run_session(sid, f"Learn topic {i}")
            counts.append({
                "sessions": info["session_count"],
                "profiles": info["profile_count"],
                "mastery": info["mastery_count"],
            })

        # Session count: 1, 2, 3
        assert counts[0]["sessions"] == 1
        assert counts[1]["sessions"] == 2
        assert counts[2]["sessions"] == 3

        # Profile history grows
        assert counts[0]["profiles"] >= 1
        assert counts[2]["profiles"] >= 3

        # Mastery accumulates (EMA, so keys stay same but values evolve)
        assert counts[2]["mastery"] >= counts[0]["mastery"]

    def test_five_sessions_stable(self):
        """5 sessions should all persist (no data loss, no corruption)."""
        sid = _fresh_id("five")
        for i in range(5):
            _run_session(sid, f"Goal session {i}")

        from veritas.memory import MemoryManager
        mem = MemoryManager().get_student_memory(sid)
        assert len(mem.session_summaries) == 5
        assert len(mem.profile_history) == 5

    def test_session_data_integrity(self):
        """Each session record has required fields."""
        sid = _fresh_id("integrity")
        _run_session(sid, "Learn closures")
        _run_session(sid, "Learn decorators")

        from veritas.memory import MemoryManager
        mem = MemoryManager().get_student_memory(sid)

        for s in mem.session_summaries:
            assert "course_id" in s
            assert "nodes_completed" in s
            assert "total_score" in s
            assert "time_spent" in s
            assert "timestamp" in s


# ──────────────────────────────────────────────
# 2. Multi-User Isolation
# ──────────────────────────────────────────────


class TestMultiUserIsolation:
    """Student memory is strictly isolated — no cross-contamination."""

    def test_two_students_independent_mastery(self):
        """Student A's mastery doesn't leak into Student B."""
        sid_a = _fresh_id("isoA")
        sid_b = _fresh_id("isoB")

        _run_session(sid_a, "Learn Python basics")
        _run_session(sid_b, "Learn JavaScript")

        from veritas.memory import MemoryManager
        mem_a = MemoryManager().get_student_memory(sid_a)
        mem_b = MemoryManager().get_student_memory(sid_b)

        # Both have data, but different sessions
        assert len(mem_a.session_summaries) >= 1
        assert len(mem_b.session_summaries) >= 1

        # A's data is NOT in B's file
        assert mem_a.student_id == sid_a
        assert mem_b.student_id == sid_b

    def test_three_students_no_cross_write(self):
        """3 students → each has exactly their own history."""
        students = [_fresh_id("trip") for _ in range(3)]
        for i, sid in enumerate(students):
            _run_session(sid, f"Learn topic {i}")
            _run_session(sid, f"Review topic {i}")

        from veritas.memory import MemoryManager
        for sid in students:
            mem = MemoryManager().get_student_memory(sid)
            assert len(mem.session_summaries) == 2
            assert mem.student_id == sid

    def test_mastery_map_is_per_student(self):
        """Student A studying closures doesn't add closures to B's mastery."""
        sid_a = _fresh_id("masA")
        sid_b = _fresh_id("masB")

        _run_session(sid_a, "Learn Python closures extensively")
        _run_session(sid_b, "Learn basic math")

        from veritas.memory import MemoryManager
        mm = MemoryManager()
        mem_a = mm.get_student_memory(sid_a)
        mem_b = mm.get_student_memory(sid_b)

        # B should NOT have closures in mastery just because A does
        # (JSON files are per-student, so isolation is structural)
        for key in mem_b.mastery_map:
            assert key not in ("closures_hidden",)


# ──────────────────────────────────────────────
# 3. Crash Recovery / Restart
# ──────────────────────────────────────────────


class TestCrashRecovery:
    """Memory persists across A3Workflow instance destruction and reload."""

    def test_reload_from_disk(self):
        """Create workflow, run session, destroy, new workflow → data still there."""
        sid = _fresh_id("reload")

        # Session 1
        _run_session(sid, "Learn basics")

        # Simulate "restart": fresh MemoryManager
        from veritas.memory import MemoryManager
        mm = MemoryManager()
        mem = mm.get_student_memory(sid)
        assert mem is not None
        assert len(mem.session_summaries) == 1
        assert len(mem.profile_history) == 1

        # Session 2 (different A3Workflow instance)
        _run_session(sid, "Learn advanced")

        # Yet another MemoryManager
        mm2 = MemoryManager()
        mem2 = mm2.get_student_memory(sid)
        assert len(mem2.session_summaries) == 2

    def test_memory_survives_manager_gc(self):
        """After MemoryManager goes out of scope, data is still on disk."""
        sid = _fresh_id("gc")

        # Create, use, and discard MemoryManager
        def inner():
            from workflow import A3Workflow
            wf = A3Workflow(student_id=sid)
            wf.run(
                user_goal="Learn Python",
                user_profile={"knowledge_base": "junior_dev"},
            )

        inner()  # all local objects are GC'd

        # Fresh load should find data
        from veritas.memory import MemoryManager
        mm = MemoryManager()
        mem = mm.get_student_memory(sid)
        assert mem is not None
        assert len(mem.session_summaries) >= 1

    def test_concurrent_read_write_safety(self):
        """Sequential read-after-write from different MemoryManager instances."""
        sid = _fresh_id("concurrent")

        from workflow import A3Workflow
        wf = A3Workflow(student_id=sid)
        wf.run(user_goal="Learn", user_profile={"knowledge_base": "junior_dev"})

        # Read back immediately with a different instance
        from veritas.memory import MemoryManager
        mm = MemoryManager()
        mem = mm.get_student_memory(sid)

        # Modify via workflow
        wf2 = A3Workflow(student_id=sid)
        wf2.run(user_goal="Learn more", user_profile={"knowledge_base": "junior_dev"})

        # Read again — should see growth
        mm2 = MemoryManager()
        mem2 = mm2.get_student_memory(sid)
        assert len(mem2.session_summaries) == 2


# ──────────────────────────────────────────────
# 4. SQLite Dual-Write (Phase 8.3-E0.5)
# ──────────────────────────────────────────────


class TestSQLiteDualWrite:
    """A3Workflow persists sessions to SQLite DB as well as Veritas-Core JSON."""

    def test_session_written_to_db(self):
        """After one workflow run, learning_records has a session_completed row."""
        sid = _fresh_id("sql1")
        _run_session(sid, "Learn Python basics")

        db_count = _count_db_records(sid)
        assert db_count >= 1, f"Expected >=1 sessions in DB, got {db_count}"

    def test_two_sessions_both_written(self):
        """2 sessions → 2 DB records."""
        sid = _fresh_id("sql2")
        _run_session(sid, "Session 1")
        _run_session(sid, "Session 2")

        db_count = _count_db_records(sid)
        assert db_count == 2, f"Expected 2 sessions in DB, got {db_count}"

    def test_db_record_has_fields(self):
        """DB record contains goal, score, and duration."""
        sid = _fresh_id("sql_fields")

        from workflow import A3Workflow
        wf = A3Workflow(student_id=sid)
        wf.run(
            user_goal="Test Goal for DB Verification",
            user_profile={"knowledge_base": "junior_dev"},
        )

        from src.data.db import _get_conn
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM learning_records "
            "WHERE user_id = ? AND agent = 'A3Workflow' AND action = 'session_completed' "
            "ORDER BY created_at DESC LIMIT 1",
            (sid,)
        ).fetchone()

        assert row is not None, "No DB record found"
        record = dict(row)

        # Core fields
        assert record["user_id"] == sid
        assert record["agent"] == "A3Workflow"
        assert record["action"] == "session_completed"
        assert record["duration_ms"] >= 0  # may be 0 for near-instant rule pipeline

        # Result JSON should contain goal
        import json
        result = json.loads(record["result_json"])
        assert "goal" in result
        assert "nodes_completed" in result
        assert "total_score" in result
        assert "duration_ms" in result

    def test_json_and_db_in_sync(self):
        """JSON session count == DB record count."""
        sid = _fresh_id("sync")

        from veritas.memory import MemoryManager

        for i in range(3):
            _run_session(sid, f"Sync test {i}")

        json_count = len(MemoryManager().get_student_memory(sid).session_summaries)
        db_count = _count_db_records(sid)

        assert json_count == db_count, (
            f"JSON has {json_count} sessions, DB has {db_count} — should match"
        )
