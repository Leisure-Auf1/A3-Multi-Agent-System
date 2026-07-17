"""
Phase 5.1 — Runtime Store Tests

Covers:
  1. Session creation, update, query
  2. Checkpoint save/load
  3. Runtime cache (set, get, TTL, stats)
  4. Trace recording and query
  5. Runtime snapshot aggregation
  6. Session eviction at capacity
  7. Reset
"""

from __future__ import annotations

import sys, os, time, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from veritas.runtime import (
    AgentState,
    StateTransition,
    RuntimeStore,
    SessionRecord,
    TransitionTable,
    RuntimeEngine,
)


# ──────────────────────────────────────────────
# 1. Session Management
# ──────────────────────────────────────────────

class TestSessionManagement:
    def test_create_session(self):
        store = RuntimeStore()
        sid = store.create_session(user_goal="learn Python")
        assert sid.startswith("sess_")
        assert sid in store.list_sessions()

    def test_get_session(self):
        store = RuntimeStore()
        sid = store.create_session()
        session = store.get_session(sid)
        assert session is not None
        assert session.session_id == sid
        assert session.is_complete is False

    def test_update_state(self):
        store = RuntimeStore()
        sid = store.create_session()
        store.update_state(sid, state=AgentState.EVALUATE, transitions=3, score=82)

        session = store.get_session(sid)
        assert session.current_state == "EVALUATE"
        assert session.total_transitions == 3
        assert session.evaluation_score == 82

    def test_update_state_completed(self):
        store = RuntimeStore()
        sid = store.create_session()
        store.update_state(sid, completed=True, errors=2)

        session = store.get_session(sid)
        assert session.is_complete is True
        assert session.error_count == 2

    def test_update_state_nonexistent(self):
        store = RuntimeStore()
        # Should not crash
        store.update_state("nonexistent", state=AgentState.DONE)


# ──────────────────────────────────────────────
# 2. Checkpoint Storage
# ──────────────────────────────────────────────

class TestCheckpoint:
    def test_save_and_load_checkpoint(self):
        store = RuntimeStore()
        sid = store.create_session()

        t = StateTransition(
            from_state=AgentState.INIT,
            to_state=AgentState.PROFILE,
            status="success",
            duration_ms=12.0,
        )
        store.save_checkpoint(sid, state=AgentState.PROFILE, transitions=[t])

        cp = store.load_checkpoint(sid)
        assert cp is not None
        assert cp["state"] == "PROFILE"
        assert len(cp["transitions"]) == 1
        assert cp["transitions"][0]["status"] == "success"

    def test_load_nonexistent_checkpoint(self):
        store = RuntimeStore()
        assert store.load_checkpoint("nonexistent") is None

    def test_checkpoint_with_file_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(storage_dir=tmp)
            sid = store.create_session()
            store.save_checkpoint(sid, state=AgentState.DONE)

            # New store loading from same dir
            store2 = RuntimeStore(storage_dir=tmp)
            cp = store2.load_checkpoint(sid)
            assert cp is not None
            assert cp["state"] == "DONE"


# ──────────────────────────────────────────────
# 3. Runtime Cache
# ──────────────────────────────────────────────

class TestCache:
    def test_set_and_get(self):
        store = RuntimeStore()
        store.cache_set("key1", "value1")
        assert store.cache_get("key1") == "value1"

    def test_get_missing(self):
        store = RuntimeStore()
        assert store.cache_get("missing") is None

    def test_ttl_expiration(self):
        store = RuntimeStore()
        store.cache_set("key2", "val2", ttl_seconds=0.001)
        time.sleep(0.01)  # Wait for expiration
        assert store.cache_get("key2") is None

    def test_delete(self):
        store = RuntimeStore()
        store.cache_set("k", "v")
        assert store.cache_delete("k") is True
        assert store.cache_delete("k") is False

    def test_cache_stats(self):
        store = RuntimeStore()
        store.cache_set("a", 1)
        store.cache_get("a")  # hit
        store.cache_get("b")  # miss

        stats = store.cache_stats()
        assert stats["size"] >= 1
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert 0 < stats["hit_rate"] < 1


# ──────────────────────────────────────────────
# 4. Trace Index
# ──────────────────────────────────────────────

class TestTraceIndex:
    def test_record_and_query(self):
        store = RuntimeStore()
        sid = store.create_session()

        t1 = StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE, status="success")
        t2 = StateTransition(from_state=AgentState.PROFILE, to_state=AgentState.EVALUATE, status="error")

        store.trace_record(sid, t1)
        store.trace_record(sid, t2)

        # Query by state
        results = store.trace_query(state="PROFILE")
        assert len(results) == 1

        # Query by status
        errors = store.trace_query(status="error")
        assert len(errors) == 1
        assert errors[0]["to"] == "EVALUATE"

    def test_trace_query_limit(self):
        store = RuntimeStore()
        sid = store.create_session()
        for i in range(5):
            store.trace_record(sid,
                StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE, status="success"))

        results = store.trace_query(limit=3)
        assert len(results) == 3


# ──────────────────────────────────────────────
# 5. Runtime Snapshot
# ──────────────────────────────────────────────

class TestSnapshot:
    def test_get_runtime_snapshot(self):
        store = RuntimeStore()
        store.create_session(user_goal="goal1")
        store.create_session(user_goal="goal2")

        snap = store.get_runtime_snapshot()
        assert snap["active_count"] >= 2
        assert snap["completed_count"] == 0
        assert len(snap["sessions"]) >= 2
        assert "cache" in snap
        assert "total_traces" in snap

    def test_snapshot_with_completed(self):
        store = RuntimeStore()
        sid = store.create_session()
        store.update_state(sid, completed=True)

        snap = store.get_runtime_snapshot()
        assert snap["completed_count"] == 1


# ──────────────────────────────────────────────
# 6. Session Eviction
# ──────────────────────────────────────────────

class TestEviction:
    def test_max_sessions_evicts_oldest(self):
        store = RuntimeStore(max_sessions=3)
        s1 = store.create_session()
        s2 = store.create_session()
        s3 = store.create_session()
        s4 = store.create_session()  # should evict s1

        sessions = store.list_sessions()
        assert len(sessions) <= 3
        assert s1 not in sessions  # evicted


# ──────────────────────────────────────────────
# 7. Reset
# ──────────────────────────────────────────────

class TestReset:
    def test_reset_clears_all(self):
        store = RuntimeStore()
        store.create_session()
        store.cache_set("x", "y")
        store.reset()

        assert len(store.list_sessions()) == 0
        assert store.cache_get("x") is None
