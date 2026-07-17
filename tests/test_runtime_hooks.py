"""
Phase 4.10 — Runtime Native Hooks Tests

Covers:
  1. RuntimeHook base class (no-op by default)
  2. Custom hook: before/after/error called in order
  3. RuntimeObserver via native hook (not monkey-patch)
  4. Parallel hook invocation
  5. Hook errors do not crash engine
  6. Backward compat: engine.add_hook + observer.attach_to_engine both work
  7. CompositeHook groups hooks
"""

from __future__ import annotations

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.runtime import (
    AgentState,
    RuntimeHook,
    CompositeHook,
    RuntimeEventBus,
    RuntimeObserver,
    RuntimeMetrics,
    RuntimeEngine,
    RuntimeContext,
    TransitionTable,
)
from src.workflow import A3Workflow


# ──────────────────────────────────────────────
# 1. RuntimeHook base
# ──────────────────────────────────────────────

class TestRuntimeHookBase:
    def test_default_noop(self):
        """Calling hook methods without override does not crash."""
        hook = RuntimeHook()
        hook.on_run_start(None, None)
        hook.on_run_end(None, None, 0.0)
        hook.before_transition(None, AgentState.INIT, AgentState.PROFILE, None)
        from src.runtime.transition import StateTransition
        hook.after_transition(None, AgentState.INIT, AgentState.PROFILE, None,
                              StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE))
        hook.on_error(None, AgentState.PROFILE, None, "test error")

    def test_custom_hook_collects_calls(self):
        """Custom hook records call order."""
        calls = []

        class TestHook(RuntimeHook):
            def before_transition(self, engine, from_state, to_state, ctx):
                calls.append(("before", to_state.name))

            def after_transition(self, engine, from_state, to_state, ctx, transition):
                calls.append(("after", to_state.name, transition.status))

            def on_error(self, engine, state, ctx, error):
                calls.append(("error", state.name))

        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="hook_test")
        engine._table = table

        hook = TestHook()
        engine.add_hook(hook)
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        engine.run()

        assert ("before", "PROFILE") in calls
        assert any(c[0] == "after" and c[1] == "PROFILE" for c in calls)


# ──────────────────────────────────────────────
# 2. Hook call order
# ──────────────────────────────────────────────

class TestHookCallOrder:
    def test_before_then_after(self):
        """before_transition called before after_transition."""
        order = []

        class OrderHook(RuntimeHook):
            def before_transition(self, engine, from_state, to_state, ctx):
                order.append("before")

            def after_transition(self, engine, from_state, to_state, ctx, transition):
                order.append("after")

        # Short chain: INIT→PROFILE→DONE (only 1 real transition)
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="order_test")
        engine._table = table
        engine.add_hook(OrderHook())
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert order[0] == "before"
        assert order[1] == "after"
        # INIT→PROFILE (handler) + PROFILE→DONE (skipped) → 4 calls total
        assert len(order) == 4

    def test_error_triggers_on_error_and_after(self):
        """Error handler notified, after_transition still called."""
        events = []

        class ErrHook(RuntimeHook):
            def on_error(self, engine, state, ctx, error):
                events.append(("error", error))

            def after_transition(self, engine, from_state, to_state, ctx, transition):
                events.append(("after", transition.status))

        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="err_test")
        engine._table = table
        engine.add_hook(ErrHook())
        engine.register_handler(AgentState.PROFILE, lambda c: _raise("BOOM"))
        engine.run()

        assert any(e[0] == "error" and "BOOM" in e[1] for e in events)
        assert any(e[0] == "after" and e[1] == "error" for e in events)

    def test_run_start_end(self):
        """on_run_start and on_run_end called."""
        events = []

        class RunHook(RuntimeHook):
            def on_run_start(self, engine, ctx):
                events.append("start")

            def on_run_end(self, engine, ctx, total_duration_ms):
                events.append(("end", total_duration_ms))

        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="run_test")
        engine._table = table
        engine.add_hook(RunHook())
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert "start" in events
        assert any(e[0] == "end" and e[1] > 0 for e in events)


def _raise(msg):
    raise ValueError(msg)


# ──────────────────────────────────────────────
# 3. RuntimeObserver via native hook
# ──────────────────────────────────────────────

class TestObserverViaNativeHook:
    def test_observer_collects_events_via_add_hook(self):
        """Observer registered via add_hook collects events."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="obs_native")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        observer = RuntimeObserver(session_id="obs_native")
        engine.add_hook(observer)  # Phase 4.10 native
        engine.run()

        events = observer.events()
        assert len(events) >= 2  # state_enter + transition

    def test_observer_collects_transition_event(self):
        """Transition events contain state info."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="trans_native")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        observer = RuntimeObserver(session_id="trans_native")
        engine.add_hook(observer)
        engine.run()

        transitions = observer.events_by_type("transition")
        assert len(transitions) >= 1
        assert transitions[0].state == AgentState.PROFILE

    def test_observer_collects_done_event(self):
        """Done event with duration."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="done_native")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        observer = RuntimeObserver(session_id="done_native")
        engine.add_hook(observer)
        engine.run()

        done = observer.events_by_type("done")
        assert len(done) == 1
        assert "total_duration_ms" in done[0].metadata

    def test_observer_collects_error_event(self):
        """Error events via native hook."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="err_native")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: _raise("fail_native"))

        observer = RuntimeObserver(session_id="err_native")
        engine.add_hook(observer)
        engine.run()

        errors = observer.events_by_type("error")
        assert len(errors) >= 1
        assert "fail_native" in errors[0].metadata.get("error", "")


# ──────────────────────────────────────────────
# 4. Legacy compat: attach_to_engine still works
# ──────────────────────────────────────────────

class TestLegacyCompat:
    def test_attach_to_engine_still_works(self):
        """Phase 4.9 API: observer.attach_to_engine() delegates to add_hook()."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="legacy")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        observer = RuntimeObserver(session_id="legacy")
        observer.attach_to_engine(engine)  # Phase 4.9 API
        engine.run()

        assert len(observer.events()) >= 2

    def test_observer_events_by_type_still_works(self):
        """events_by_type query unchanged."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="query_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)

        bus = RuntimeEventBus()
        observer = RuntimeObserver(bus=bus, session_id="query_test")
        engine.add_hook(observer)
        engine.run()

        state_enters = observer.events_by_type("state_enter")
        assert len(state_enters) >= 1


# ──────────────────────────────────────────────
# 5. Parallel hooks
# ──────────────────────────────────────────────

class TestParallelHooks:
    def test_multiple_hooks(self):
        """Multiple hooks all receive callbacks."""
        results_a = []
        results_b = []

        class HookA(RuntimeHook):
            def after_transition(self, engine, from_state, to_state, ctx, transition):
                results_a.append(to_state.name)

        class HookB(RuntimeHook):
            def after_transition(self, engine, from_state, to_state, ctx, transition):
                results_b.append(to_state.name)

        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="multi")
        engine._table = table
        engine.add_hook(HookA())
        engine.add_hook(HookB())
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert "PROFILE" in results_a
        assert "PROFILE" in results_b

    def test_hook_error_does_not_crash_engine(self):
        """A failing hook does not prevent other hooks or the engine."""

        class BadHook(RuntimeHook):
            def after_transition(self, engine, from_state, to_state, ctx, transition):
                raise RuntimeError("hook crash")

        good_calls = []

        class GoodHook(RuntimeHook):
            def after_transition(self, engine, from_state, to_state, ctx, transition):
                good_calls.append("ok")

        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="bad_hook")
        engine._table = table
        engine.add_hook(BadHook())
        engine.add_hook(GoodHook())
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        ctx = engine.run()

        assert "ok" in good_calls  # Good hook still called
        assert len(ctx.errors) == 0  # No engine-level errors


# ──────────────────────────────────────────────
# 6. CompositeHook
# ──────────────────────────────────────────────

class TestCompositeHook:
    def test_composite_groups_hooks(self):
        calls = []

        class HookX(RuntimeHook):
            def before_transition(self, engine, from_state, to_state, ctx): calls.append("X")

        class HookY(RuntimeHook):
            def before_transition(self, engine, from_state, to_state, ctx): calls.append("Y")

        composite = CompositeHook([HookX(), HookY()])

        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="composite")
        engine._table = table
        engine.add_hook(composite)
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert "X" in calls
        assert "Y" in calls


# ──────────────────────────────────────────────
# 7. Backward compat: engine without hooks
# ──────────────────────────────────────────────

class TestNoHooksCompat:
    def test_engine_runs_without_hooks(self):
        """Engine works without any hooks registered."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="no_hooks")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        ctx = engine.run()
        assert engine._checkpoint.state_count() >= 1

    def test_workflow_backward_compat(self):
        """Workflow still produces valid results."""
        wf = A3Workflow(student_id="test_stu")
        result = wf.run(
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
