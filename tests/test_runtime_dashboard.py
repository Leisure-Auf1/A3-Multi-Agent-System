"""
Phase 5.0 — Runtime Dashboard Tests

Covers:
  1. RuntimeSnapshot capture from EventBus
  2. RuntimeBus singleton
  3. FastAPI runtime endpoints
  4. RuntimeSnapshot with real engine events
  5. Metrics integration with snapshot
"""

from __future__ import annotations

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from veritas.runtime import (
    AgentState,
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeMetrics,
    RuntimeSnapshot,
    RuntimeBus,
    RuntimeEngine,
    RuntimeObserver,
    TransitionTable,
)
from src.api.server import app

client = TestClient(app)


# ── Auth helper ──

def _register_and_login(email: str = "rt_dash@a3.local") -> dict:
    client.post("/api/v2/auth/register", json={
        "email": email, "password": "testpass", "display_name": "RT Dash Test",
    })
    resp = client.post("/api/v2/auth/login", json={
        "email": email, "password": "testpass",
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


_AUTH = None


def _auth() -> dict:
    global _AUTH
    if _AUTH is None:
        _AUTH = _register_and_login()
    return _AUTH


# ──────────────────────────────────────────────
# 1. RuntimeSnapshot
# ──────────────────────────────────────────────

class TestRuntimeSnapshot:
    def test_capture_empty_bus(self):
        bus = RuntimeEventBus()
        snapshot = RuntimeSnapshot.capture(bus)
        assert snapshot.current_state is None
        assert snapshot.recent_events == []
        assert snapshot.metrics == {}

    def test_capture_with_events(self):
        bus = RuntimeEventBus()
        bus.emit(RuntimeEvent(
            event_type="state_enter", state=AgentState.EVALUATE,
            metadata={"score": 88},
        ))
        bus.emit(RuntimeEvent(
            event_type="transition", state=AgentState.REFLECT,
            status="success",
        ))

        snapshot = RuntimeSnapshot.capture(bus)
        assert snapshot.current_state == "REFLECT"
        assert len(snapshot.recent_events) == 2
        assert len(snapshot.timeline) == 2

    def test_capture_evaluation_score(self):
        bus = RuntimeEventBus()
        bus.emit(RuntimeEvent(
            event_type="evaluation", state=AgentState.EVALUATE,
            metadata={"score": 73},
        ))
        bus.emit(RuntimeEvent(
            event_type="evaluation", state=AgentState.EVALUATE,
            metadata={"score": 91},
        ))

        snapshot = RuntimeSnapshot.capture(bus)
        # Last evaluation score wins
        assert snapshot.evaluation_score == 91

    def test_capture_errors(self):
        bus = RuntimeEventBus()
        bus.emit(RuntimeEvent(
            event_type="transition", state=AgentState.PROFILE,
            status="error", metadata={"error": "ProfileAgent failed"},
        ))

        snapshot = RuntimeSnapshot.capture(bus)
        assert snapshot.has_errors is True
        assert "ProfileAgent" in (snapshot.last_error or "")

    def test_capture_with_metrics(self):
        bus = RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)

        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 85}))
        bus.emit(RuntimeEvent(event_type="done", metadata={"total_duration_ms": 250}))

        snapshot = RuntimeSnapshot.capture(bus, metrics)
        assert snapshot.metrics.get("avg_score") == 85.0
        assert snapshot.metrics.get("total_runs") == 1

    def test_to_dict(self):
        bus = RuntimeEventBus()
        bus.emit(RuntimeEvent(event_type="state_enter", state=AgentState.PROFILE))
        snapshot = RuntimeSnapshot.capture(bus)
        d = snapshot.to_dict()
        assert "captured_at" in d
        assert d["current_state"] == "PROFILE"
        assert "metrics" in d
        assert "recent_events" in d

    def test_max_recent(self):
        bus = RuntimeEventBus()
        for i in range(30):
            bus.emit(RuntimeEvent(event_type="transition", state=AgentState.PROFILE))
        snapshot = RuntimeSnapshot.capture(bus, max_recent=10)
        assert len(snapshot.recent_events) == 10


# ──────────────────────────────────────────────
# 2. RuntimeBus singleton
# ──────────────────────────────────────────────

class TestRuntimeBus:
    def test_init_and_get(self):
        # Reset before test
        RuntimeBus.reset()
        RuntimeBus.init()

        bus = RuntimeBus.get_bus()
        metrics = RuntimeBus.get_metrics()
        assert isinstance(bus, RuntimeEventBus)
        assert isinstance(metrics, RuntimeMetrics)

    def test_singleton_returns_same_instance(self):
        RuntimeBus.init()
        bus1 = RuntimeBus.get_bus()
        bus2 = RuntimeBus.get_bus()
        assert bus1 is bus2

    def test_snapshot(self):
        RuntimeBus.reset()
        RuntimeBus.init()
        bus = RuntimeBus.get_bus()
        bus.emit(RuntimeEvent(event_type="state_enter", state=AgentState.EVALUATE))

        snapshot = RuntimeBus.snapshot()
        assert snapshot.current_state == "EVALUATE"

    def test_reset(self):
        RuntimeBus.init()
        bus = RuntimeBus.get_bus()
        bus.emit(RuntimeEvent(event_type="done"))

        RuntimeBus.reset()
        snap = RuntimeBus.snapshot()
        assert len(snap.recent_events) == 0
        assert snap.metrics.get("total_runs", 0) == 0


# ──────────────────────────────────────────────
# 3. FastAPI runtime endpoints
# ──────────────────────────────────────────────

class TestRuntimeAPI:
    def test_snapshot_endpoint(self):
        RuntimeBus.reset()
        RuntimeBus.init()
        bus = RuntimeBus.get_bus()
        bus.emit(RuntimeEvent(event_type="state_enter", state=AgentState.INIT))

        resp = client.get("/api/v1/runtime/snapshot", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()
        assert "current_state" in data
        assert "metrics" in data
        assert "recent_events" in data

    def test_metrics_endpoint(self):
        RuntimeBus.init()
        resp = client.get("/api/v1/runtime/metrics", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()
        assert "total_runs" in data
        assert "success_rate" in data

    def test_timeline_endpoint(self):
        RuntimeBus.reset()
        RuntimeBus.init()
        bus = RuntimeBus.get_bus()
        bus.emit(RuntimeEvent(event_type="state_enter", state=AgentState.PROFILE))

        resp = client.get("/api/v1/runtime/timeline", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_events_endpoint(self):
        RuntimeBus.reset()
        RuntimeBus.init()
        bus = RuntimeBus.get_bus()
        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 77}))

        resp = client.get("/api/v1/runtime/events?limit=5", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_state_endpoint(self):
        RuntimeBus.reset()
        RuntimeBus.init()
        bus = RuntimeBus.get_bus()
        bus.emit(RuntimeEvent(event_type="state_enter", state=AgentState.EVALUATE))

        resp = client.get("/api/v1/runtime/state", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()
        assert "current_state" in data
        assert data["current_state"] == "EVALUATE"

    def test_reset_endpoint(self):
        RuntimeBus.init()
        resp = client.post("/api/v1/runtime/reset", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "reset"

    def test_all_endpoints_respond(self):
        """Every runtime endpoint returns 200."""
        RuntimeBus.init()
        h = _auth()
        endpoints = [
            ("GET", "/api/v1/runtime/snapshot"),
            ("GET", "/api/v1/runtime/metrics"),
            ("GET", "/api/v1/runtime/timeline"),
            ("GET", "/api/v1/runtime/events"),
            ("GET", "/api/v1/runtime/state"),
            ("POST", "/api/v1/runtime/reset"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = client.get(path, headers=h)
            else:
                resp = client.post(path, headers=h)
            assert resp.status_code == 200, f"{method} {path} returned {resp.status_code}"

    def test_no_token_returns_401(self):
        """Unauthenticated runtime queries must return 401."""
        RuntimeBus.init()
        resp = client.get("/api/v1/runtime/state")
        assert resp.status_code == 401


# ──────────────────────────────────────────────
# 4. Snapshot with real engine events
# ──────────────────────────────────────────────

class TestSnapshotWithEngine:
    def test_snapshot_after_engine_run(self):
        """RuntimeEngine emits events → Bus → Snapshot captures them."""
        RuntimeBus.reset()
        RuntimeBus.init()

        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="snap_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        # Attach observer to push events into RuntimeBus
        observer = RuntimeObserver(bus=RuntimeBus.get_bus(), session_id="snap_test")
        engine.add_hook(observer)
        engine.run()

        snapshot = RuntimeBus.snapshot()
        assert snapshot.current_state == "DONE"
        assert len(snapshot.timeline) >= 2  # at least state_enter + transition

    def test_metrics_after_engine_run(self):
        """Metrics accumulate from engine events."""
        RuntimeBus.reset()
        RuntimeBus.init()

        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="metric_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        observer = RuntimeObserver(bus=RuntimeBus.get_bus(), session_id="metric_test")
        engine.add_hook(observer)
        engine.run()

        metrics = RuntimeBus.get_metrics().summary()
        assert metrics["total_runs"] >= 1
        assert metrics["total_transitions"] >= 1
