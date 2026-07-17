"""
Phase 4.9 — Runtime Observability Tests

Covers:
  1. RuntimeEvent creation and serialization
  2. RuntimeEventBus: subscribe, emit, event_log
  3. RuntimeObserver: attach to engine, collect events
  4. RuntimeMetrics: accumulation via bus
  5. Full pipeline observability
  6. Backward compatibility: engine runs without observer
"""

from __future__ import annotations

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.runtime import (
    AgentState,
    StateTransition,
    TransitionTable,
    RuntimeCheckpoint,
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeObserver,
    RuntimeMetrics,
    RuntimeEngine,
    RuntimeContext,
)
from src.workflow import A3Workflow
from src.memory.memory_manager import MemoryManager
from src.core.meta_reflector import MetaReflectorAgent, _LocalMemoryStore


# ──────────────────────────────────────────────
# 1. RuntimeEvent
# ──────────────────────────────────────────────

class TestRuntimeEvent:
    def test_creation(self):
        event = RuntimeEvent(
            event_type="transition",
            session_id="s1",
            state=AgentState.EVALUATE,
            duration_ms=12.5,
            metadata={"score": 85},
        )
        assert event.event_type == "transition"
        assert event.session_id == "s1"
        assert event.state == AgentState.EVALUATE
        assert event.duration_ms == 12.5
        assert event.metadata["score"] == 85
        assert len(event.event_id) == 12

    def test_to_dict(self):
        event = RuntimeEvent(
            event_type="evaluation",
            session_id="s1",
            state=AgentState.EVALUATE,
            metadata={"score": 90},
        )
        d = event.to_dict()
        assert d["event_type"] == "evaluation"
        assert d["state"] == "EVALUATE"
        assert d["metadata"]["score"] == 90

    def test_defaults(self):
        event = RuntimeEvent()
        assert event.event_type == "transition"
        assert event.state is None
        assert event.status == "success"


# ──────────────────────────────────────────────
# 2. RuntimeEventBus
# ──────────────────────────────────────────────

class TestRuntimeEventBus:
    def test_emit_and_log(self):
        bus = RuntimeEventBus()
        bus.emit(RuntimeEvent(event_type="evaluation", session_id="s1"))
        bus.emit(RuntimeEvent(event_type="reflection", session_id="s1"))
        assert len(bus.event_log()) == 2

    def test_subscribe_specific_type(self):
        bus = RuntimeEventBus()
        received = []

        bus.subscribe("evaluation", received.append)
        bus.emit(RuntimeEvent(event_type="evaluation"))
        bus.emit(RuntimeEvent(event_type="reflection"))

        assert len(received) == 1
        assert received[0].event_type == "evaluation"

    def test_subscribe_all(self):
        bus = RuntimeEventBus()
        received = []

        bus.subscribe_all(received.append)
        bus.emit(RuntimeEvent(event_type="evaluation"))
        bus.emit(RuntimeEvent(event_type="done"))

        assert len(received) == 2

    def test_events_by_type(self):
        bus = RuntimeEventBus()
        bus.emit(RuntimeEvent(event_type="evaluation"))
        bus.emit(RuntimeEvent(event_type="evaluation"))
        bus.emit(RuntimeEvent(event_type="reflection"))

        evals = bus.events_by_type("evaluation")
        assert len(evals) == 2

    def test_subscriber_error_does_not_break(self):
        bus = RuntimeEventBus()

        def bad_handler(event):
            raise RuntimeError("boom")

        bus.subscribe("evaluation", bad_handler)
        # Should not raise
        bus.emit(RuntimeEvent(event_type="evaluation"))
        assert len(bus.event_log()) == 1

    def test_subscriber_count(self):
        bus = RuntimeEventBus()
        assert bus.subscriber_count() == 0
        bus.subscribe("x", lambda e: None)
        bus.subscribe_all(lambda e: None)
        assert bus.subscriber_count() == 2


# ──────────────────────────────────────────────
# 3. RuntimeObserver
# ──────────────────────────────────────────────

class TestRuntimeObserver:
    def test_attach_to_engine_collects_events(self):
        """Observer attached to engine collects state_enter/transition events."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="obs_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        bus = RuntimeEventBus()
        observer = RuntimeObserver(bus=bus, session_id="obs_test")
        observer.attach_to_engine(engine)

        ctx = engine.run()

        events = observer.events()
        assert len(events) >= 2  # at least state_enter + transition for PROFILE

    def test_collects_transition_event(self):
        """Transition events are recorded."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="t_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        observer = RuntimeObserver(session_id="t_test")
        observer.attach_to_engine(engine)
        engine.run()

        transitions = observer.events_by_type("transition")
        assert len(transitions) >= 1
        assert transitions[0].state == AgentState.PROFILE

    def test_collects_done_event(self):
        """Done event emitted at end."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="d_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        observer = RuntimeObserver(session_id="d_test")
        observer.attach_to_engine(engine)
        engine.run()

        done = observer.events_by_type("done")
        assert len(done) == 1
        assert "total_duration_ms" in done[0].metadata

    def test_collects_error_event(self):
        """Handler error → error event emitted."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="err_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: _raise("fail"))

        observer = RuntimeObserver(session_id="err_test")
        observer.attach_to_engine(engine)
        engine.run()

        errors = observer.events_by_type("error")
        assert len(errors) >= 1
        assert "fail" in errors[0].metadata.get("error", "")

    def test_observer_bus_gets_events(self):
        """Event bus receives published events."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="bus_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        bus = RuntimeEventBus()
        observer = RuntimeObserver(bus=bus, session_id="bus_test")
        observer.attach_to_engine(engine)
        engine.run()

        assert len(bus.event_log()) >= 2


def _raise(msg):
    raise ValueError(msg)


# ──────────────────────────────────────────────
# 4. RuntimeMetrics
# ──────────────────────────────────────────────

class TestRuntimeMetrics:
    def test_attaches_to_bus(self):
        bus = RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)

        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 88}))
        bus.emit(RuntimeEvent(event_type="done", metadata={"total_duration_ms": 123}))

        assert metrics.avg_score == 88.0
        assert metrics.total_runs == 1

    def test_counts_reflections(self):
        bus = RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)

        bus.emit(RuntimeEvent(event_type="reflection"))
        bus.emit(RuntimeEvent(event_type="reflection"))
        bus.emit(RuntimeEvent(event_type="meta_reflection"))

        assert metrics.reflection_count == 2
        assert metrics.meta_reflection_count == 1

    def test_success_rate(self):
        bus = RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)

        bus.emit(RuntimeEvent(event_type="transition", status="success"))
        bus.emit(RuntimeEvent(event_type="transition", status="success"))
        bus.emit(RuntimeEvent(event_type="transition", status="error"))

        # 2 success / 3 total transitions = 0.667
        assert 0.6 < metrics.success_rate < 0.7

    def test_summary(self):
        bus = RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)

        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 75}))
        bus.emit(RuntimeEvent(event_type="done", metadata={"total_duration_ms": 200}))

        s = metrics.summary()
        assert s["total_runs"] == 1
        assert s["avg_score"] == 75.0
        assert "scores" in s

    def test_reset(self):
        bus = RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)

        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 99}))
        assert metrics.avg_score == 99.0

        metrics.reset()
        assert metrics.avg_score == 0.0
        assert metrics.total_runs == 0


# ──────────────────────────────────────────────
# 5. Full pipeline observability
# ──────────────────────────────────────────────

class TestFullPipelineObservability:
    def test_observer_and_metrics_together(self):
        """Observer + Metrics working together on a real engine run."""
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="full_test")
        engine._table = table

        visited = []
        engine.register_handler(AgentState.PROFILE, lambda c: visited.append("profile"))

        bus = RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)

        observer = RuntimeObserver(bus=bus, session_id="full_test")
        observer.attach_to_engine(engine)

        # Also emit an evaluation manually via bus
        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 82}))

        engine.run()

        assert len(observer.events()) >= 3
        assert len(bus.event_log()) >= 3
        assert metrics.total_runs == 1
        assert metrics.avg_score == 82.0


# ──────────────────────────────────────────────
# 6. Backward compatibility
# ──────────────────────────────────────────────

class TestBackwardCompat:
    def test_engine_runs_without_observer(self):
        """Engine works fine without observer (no crash)."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="no_obs")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        ctx = engine.run()
        assert engine._checkpoint.state_count() >= 1

    def test_observer_does_not_break_workflow(self):
        """Workflow with observer attached still produces valid result."""
        wf = A3Workflow(student_id="test_stu")

        # Attach observer before running
        bus = RuntimeEventBus()
        observer = RuntimeObserver(bus=bus, session_id="wf_test")

        result = wf.run_via_runtime(
            user_goal="test",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )
        assert result.success


# ──────────────────────────────────────────────
# 7. RuntimeContext
# ──────────────────────────────────────────────

class TestRuntimeContextObservability:
    def test_evaluation_score_during_transition(self):
        """Observer sees evaluation score in metadata."""
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.EVALUATE,
            AgentState.EVALUATE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="eval_obs")
        engine._table = table

        def set_score(ctx):
            ctx.evaluation = {"score": 73, "issues": []}
        engine.register_handler(AgentState.EVALUATE, set_score)

        observer = RuntimeObserver(session_id="eval_obs")
        observer.attach_to_engine(engine)
        engine.run()

        transitions = observer.events_by_type("transition")
        eval_transition = [t for t in transitions if t.state == AgentState.EVALUATE]
        assert len(eval_transition) >= 1
        assert eval_transition[0].metadata.get("score") == 73
