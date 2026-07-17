"""
Phase 5.5 — Runtime Lifecycle & Session Management Tests

Covers:
  1. AgentLifecycle: enum values, properties, labels
  2. AgentLifecycleRecord: creation, transition, error/recovery tracking
  3. RuntimeSession: start/end, state tracking, serialization
  4. LifecycleManager: agent registration, transitions, error/recovery marking
  5. Hook Integration: on_run_start, before/after_transition, on_error, on_run_end
  6. Engine Integration: full engine run with lifecycle tracking
  7. Error scenarios: handler errors, recovery integration
  8. Backward compat: engine without lifecycle
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.runtime import (
    AgentState,
    StateTransition,
    TransitionTable,
    RuntimeEngine,
    RuntimeContext,
    RuntimePolicyEngine,
    RuntimeHook,
    FailureEvent,
)
from src.runtime.lifecycle import (
    AgentLifecycle,
    AgentLifecycleRecord,
    RuntimeSession,
    LifecycleManager,
    agent_name_for_state,
)
from src.runtime.recovery import RecoveryManager


# ══════════════════════════════════════════════
# 1. AgentLifecycle
# ══════════════════════════════════════════════

class TestAgentLifecycle:
    def test_all_states_present(self):
        values = {s.value for s in AgentLifecycle}
        expected = {"created", "ready", "running", "waiting", "failed", "recovering", "terminated"}
        assert values == expected

    def test_is_active(self):
        assert AgentLifecycle.CREATED.is_active is True
        assert AgentLifecycle.READY.is_active is True
        assert AgentLifecycle.RUNNING.is_active is True
        assert AgentLifecycle.FAILED.is_active is True
        assert AgentLifecycle.RECOVERING.is_active is True
        assert AgentLifecycle.TERMINATED.is_active is False

    def test_is_healthy(self):
        assert AgentLifecycle.READY.is_healthy is True
        assert AgentLifecycle.RUNNING.is_healthy is True
        assert AgentLifecycle.WAITING.is_healthy is True
        assert AgentLifecycle.FAILED.is_healthy is False
        assert AgentLifecycle.TERMINATED.is_healthy is False

    def test_labels(self):
        assert AgentLifecycle.CREATED.label == "已创建"
        assert AgentLifecycle.READY.label == "就绪"
        assert AgentLifecycle.RUNNING.label == "运行中"
        assert AgentLifecycle.FAILED.label == "失败"
        assert AgentLifecycle.TERMINATED.label == "已终止"


# ══════════════════════════════════════════════
# 2. AgentLifecycleRecord
# ══════════════════════════════════════════════

class TestAgentLifecycleRecord:
    def test_default_created(self):
        rec = AgentLifecycleRecord(agent_name="profile")
        assert rec.agent_name == "profile"
        assert rec.lifecycle == AgentLifecycle.CREATED
        assert rec.error_count == 0
        assert rec.recovery_count == 0

    def test_transition_tracks_history(self):
        rec = AgentLifecycleRecord(agent_name="profile")
        rec.transition(AgentLifecycle.READY, "registered")
        rec.transition(AgentLifecycle.RUNNING, "executing")
        assert rec.lifecycle == AgentLifecycle.RUNNING
        assert len(rec.history) == 2
        assert rec.history[0]["from"] == "created"
        assert rec.history[0]["to"] == "ready"
        assert rec.history[1]["from"] == "ready"
        assert rec.history[1]["to"] == "running"

    def test_started_at_set_on_first_running(self):
        rec = AgentLifecycleRecord(agent_name="plan")
        assert rec.started_at is None
        rec.transition(AgentLifecycle.RUNNING, "start")
        assert rec.started_at is not None

        # Second RUNNING should not overwrite started_at
        first_start = rec.started_at
        rec.transition(AgentLifecycle.FAILED, "error")
        rec.transition(AgentLifecycle.RUNNING, "retry")
        assert rec.started_at == first_start

    def test_finished_at_set_on_terminated(self):
        rec = AgentLifecycleRecord(agent_name="eval")
        assert rec.finished_at is None
        rec.transition(AgentLifecycle.TERMINATED, "done")
        assert rec.finished_at is not None

    def test_record_error(self):
        rec = AgentLifecycleRecord(agent_name="planner")
        rec.record_error("something broke")
        assert rec.error_count == 1
        assert rec.last_error == "something broke"
        rec.record_error("another error")
        assert rec.error_count == 2

    def test_record_recovery(self):
        rec = AgentLifecycleRecord(agent_name="reflector")
        rec.record_recovery()
        rec.record_recovery()
        assert rec.recovery_count == 2

    def test_to_dict(self):
        rec = AgentLifecycleRecord(agent_name="profile")
        rec.transition(AgentLifecycle.READY, "ready")
        rec.record_error("fail")
        d = rec.to_dict()
        assert d["agent_name"] == "profile"
        assert d["lifecycle"] == "ready"
        assert d["error_count"] == 1
        assert len(d["history"]) == 1


# ══════════════════════════════════════════════
# 3. RuntimeSession
# ══════════════════════════════════════════════

class TestRuntimeSession:
    def test_start(self):
        s = RuntimeSession()
        s.start("s1", "t1")
        assert s.session_id == "s1"
        assert s.task_id == "t1"
        assert s.start_time is not None
        assert s.current_state == "INIT"

    def test_start_auto_task_id(self):
        s = RuntimeSession()
        s.start("s2")
        assert s.task_id == "task_s2"

    def test_end(self):
        s = RuntimeSession()
        s.start("s3")
        s.end(1500.0)
        assert s.total_duration_ms == 1500.0
        assert s.end_time is not None

    def test_record_state(self):
        s = RuntimeSession()
        s.start("s4")
        t = StateTransition(
            from_state=AgentState.INIT,
            to_state=AgentState.PROFILE,
            status="success",
            duration_ms=50.0,
        )
        s.record_state(AgentState.PROFILE, t)
        assert len(s.state_history) == 1
        assert s.state_history[0]["state"] == "PROFILE"
        assert s.state_history[0]["status"] == "success"

    def test_timeline(self):
        s = RuntimeSession()
        s.start("s5")
        s.record_state(AgentState.PROFILE)
        s.record_state(AgentState.PLAN)
        s.record_state(AgentState.EXECUTE)
        assert s.timeline() == ["PROFILE", "PLAN", "EXECUTE"]

    def test_error_count(self):
        s = RuntimeSession()
        s.start("s6")
        t_ok = StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE, status="success")
        t_err = StateTransition(
            from_state=AgentState.PROFILE, to_state=AgentState.PLAN,
            status="error", error="fail",
        )
        s.record_state(AgentState.PROFILE, t_ok)
        s.record_state(AgentState.PLAN, t_err)
        assert s.error_count() == 1

    def test_record_decision_and_recovery(self):
        s = RuntimeSession()
        s.start("s7")
        s.record_decision({"action": "RETRY", "reason": "test"})
        s.record_recovery({"strategy": "retry", "success": True})
        assert s.decision_count() == 1
        assert s.recovery_count() == 1

    def test_to_dict(self):
        s = RuntimeSession()
        s.start("s8")
        s.record_state(AgentState.PROFILE)
        s.end(500.0)
        d = s.to_dict()
        assert d["session_id"] == "s8"
        assert d["total_duration_ms"] == 500.0
        assert d["timeline"] == ["PROFILE"]
        assert "state_history" in d
        assert "decisions" in d

    def test_to_summary_dict(self):
        s = RuntimeSession()
        s.start("s9")
        s.record_state(AgentState.EVALUATE)
        s.end(200.0)
        d = s.to_summary_dict()
        assert d["session_id"] == "s9"
        assert d["state_count"] == 1
        assert d["final_status"] == "unknown"

    def test_state_count(self):
        s = RuntimeSession()
        s.start("s10")
        for _ in range(5):
            s.record_state(AgentState.PROFILE)
        assert s.state_count() == 5

    def test_final_status(self):
        s = RuntimeSession()
        s.start("s11")
        s.final_status = "completed"
        s.end(100.0)
        d = s.to_dict()
        assert d["final_status"] == "completed"


# ══════════════════════════════════════════════
# 4. LifecycleManager — Registration & Transitions
# ══════════════════════════════════════════════

class TestLifecycleManager:
    @pytest.fixture
    def lm(self):
        return LifecycleManager()

    def test_register_agent(self, lm):
        rec = lm.register_agent("profile")
        assert rec.agent_name == "profile"
        assert rec.lifecycle == AgentLifecycle.READY

    def test_get_agent(self, lm):
        lm.register_agent("plan")
        assert lm.get_agent("plan") is not None
        assert lm.get_agent("nonexistent") is None

    def test_transition_agent_auto_registers(self, lm):
        rec = lm.transition_agent("evaluate", AgentLifecycle.RUNNING, "starting")
        assert rec is not None
        assert rec.agent_name == "evaluate"
        assert rec.lifecycle == AgentLifecycle.RUNNING

    def test_transition_agent_no_auto_register(self):
        lm = LifecycleManager(auto_register=False)
        rec = lm.transition_agent("unknown", AgentLifecycle.RUNNING)
        assert rec is None

    def test_mark_error(self, lm):
        rec = lm.register_agent("planner")
        lm.mark_error("planner", "crash!")
        assert rec.error_count == 1
        assert rec.last_error == "crash!"
        assert rec.lifecycle == AgentLifecycle.FAILED

    def test_mark_recovery(self, lm):
        rec = lm.register_agent("executor")
        lm.mark_recovery("executor")
        assert rec.recovery_count == 1
        assert rec.lifecycle == AgentLifecycle.RECOVERING

    def test_mark_recovered(self, lm):
        rec = lm.register_agent("reflector")
        lm.mark_error("reflector", "boom")
        assert rec.lifecycle == AgentLifecycle.FAILED
        lm.mark_recovered("reflector")
        assert rec.lifecycle == AgentLifecycle.READY

    def test_agent_states(self, lm):
        lm.register_agent("profile")
        lm.register_agent("plan")
        lm.transition_agent("profile", AgentLifecycle.RUNNING)
        states = lm.agent_states
        assert states["profile"] == "running"
        assert states["plan"] == "ready"

    def test_agent_summary(self, lm):
        lm.register_agent("profile")
        lm.mark_error("profile", "fail")
        lm.mark_recovery("profile")
        s = lm.agent_summary()
        assert s["total_agents"] == 1
        assert s["errors"]["profile"] == 1
        assert s["recoveries"]["profile"] == 1

    def test_to_dict(self, lm):
        lm.register_agent("profile")
        d = lm.to_dict()
        assert "session" in d
        assert "agents" in d
        assert "summary" in d
        assert d["summary"]["total_agents"] == 1

    def test_reset(self, lm):
        lm.register_agent("profile")
        assert lm.agent_summary()["total_agents"] == 1
        lm.reset()
        assert lm.agent_summary()["total_agents"] == 0


# ══════════════════════════════════════════════
# 5. LifecycleManager — Hook Integration
# ══════════════════════════════════════════════

class TestLifecycleHook:
    def test_on_run_start_registers_all_agents(self):
        lm = LifecycleManager()
        ctx = RuntimeContext(session_id="h1")
        lm.on_run_start(None, ctx)
        # Should have registered all non-terminal states
        assert lm.agent_summary()["total_agents"] == 8  # INIT through MEMORY_UPDATE

    def test_before_transition_sets_running(self):
        lm = LifecycleManager()
        lm.on_run_start(None, RuntimeContext(session_id="h2"))
        lm.before_transition(None, AgentState.INIT, AgentState.PROFILE, RuntimeContext())
        rec = lm.get_agent("profile")
        assert rec.lifecycle == AgentLifecycle.RUNNING

    def test_before_transition_skips_terminal(self):
        lm = LifecycleManager()
        lm.on_run_start(None, RuntimeContext(session_id="h3"))
        # DONE is terminal, should not be tracked
        lm.before_transition(None, AgentState.INIT, AgentState.DONE, RuntimeContext())
        # Agent should not have been created for DONE
        assert lm.get_agent("done") is None

    def test_after_transition_success(self):
        lm = LifecycleManager()
        ctx = RuntimeContext(session_id="h4")
        lm.on_run_start(None, ctx)
        lm.before_transition(None, AgentState.INIT, AgentState.PROFILE, ctx)
        t = StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE, status="success")
        lm.after_transition(None, AgentState.INIT, AgentState.PROFILE, ctx, t)
        rec = lm.get_agent("profile")
        assert rec.lifecycle == AgentLifecycle.READY

    def test_after_transition_error(self):
        lm = LifecycleManager()
        ctx = RuntimeContext(session_id="h5")
        lm.on_run_start(None, ctx)
        lm.before_transition(None, AgentState.INIT, AgentState.PROFILE, ctx)
        t = StateTransition(
            from_state=AgentState.INIT, to_state=AgentState.PROFILE,
            status="error", error="failed hard",
        )
        lm.after_transition(None, AgentState.INIT, AgentState.PROFILE, ctx, t)
        rec = lm.get_agent("profile")
        assert rec.lifecycle == AgentLifecycle.FAILED
        assert rec.error_count == 1

    def test_on_error_sets_failed(self):
        lm = LifecycleManager()
        lm.on_run_start(None, RuntimeContext(session_id="h6"))
        lm.on_error(None, AgentState.PLAN, RuntimeContext(), "plan crash")
        rec = lm.get_agent("plan")
        assert rec.lifecycle == AgentLifecycle.FAILED

    def test_on_run_end_terminates_all(self):
        lm = LifecycleManager()
        lm.on_run_start(None, RuntimeContext(session_id="h7"))
        lm.before_transition(None, AgentState.INIT, AgentState.PROFILE, RuntimeContext())
        lm.on_run_end(None, RuntimeContext(), 1000.0)

        for rec in lm._agents.values():
            assert rec.lifecycle == AgentLifecycle.TERMINATED

    def test_on_run_end_sets_session_status(self):
        lm = LifecycleManager()
        lm.on_run_start(None, RuntimeContext(session_id="h8"))
        lm.on_run_end(None, RuntimeContext(), 500.0)
        assert lm.session.final_status == "completed"  # no errors

    def test_on_run_end_error_status(self):
        lm = LifecycleManager()
        lm.on_run_start(None, RuntimeContext(session_id="h9"))
        lm.mark_error("profile", "fail")
        lm.on_run_end(None, RuntimeContext(), 500.0)
        assert lm.session.final_status == "error"


# ══════════════════════════════════════════════
# 6. Engine Integration
# ══════════════════════════════════════════════

class TestEngineLifecycleIntegration:
    def test_engine_with_lifecycle(self):
        lm = LifecycleManager()
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.PLAN,
            AgentState.PLAN: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="eng_life")
        engine._table = table
        engine.add_hook(lm)
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.register_handler(AgentState.PLAN, lambda c: None)
        ctx = engine.run()
        assert ctx is not None
        assert lm.session.final_status == "completed"
        assert len(lm.session.timeline()) >= 2

    def test_engine_with_error_lifecycle(self):
        lm = LifecycleManager()
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="eng_err")
        engine._table = table
        engine.add_hook(lm)
        engine.register_handler(AgentState.PROFILE, lambda c: exec('raise RuntimeError("fail")'))
        ctx = engine.run()
        assert lm.session.final_status == "error"
        rec = lm.get_agent("profile")
        assert rec.error_count >= 1

    def test_engine_without_lifecycle_backward_compat(self):
        """No lifecycle hook — engine works as before."""
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="no_lifecycle")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        ctx = engine.run()
        assert engine._checkpoint.state_count() >= 1

    def test_lifecycle_with_policy_and_recovery(self):
        """Full stack: policy + recovery + lifecycle."""
        lm = LifecycleManager()
        policy = RuntimePolicyEngine()
        recovery = RecoveryManager()

        attempts = []
        def flaky_handler(ctx):
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("transient")

        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(
            session_id="full_stack",
            policy_engine=policy,
            recovery_manager=recovery,
        )
        engine._table = table
        engine.add_hook(lm)
        engine.register_handler(AgentState.PROFILE, flaky_handler)
        ctx = engine.run()

        # Lifecycle should track recovery
        rec = lm.get_agent("profile")
        assert rec is not None
        # Should have been in FAILED at some point
        has_failed = any(h["to"] == "failed" for h in rec.history)
        assert has_failed or rec.error_count > 0

    def test_multiple_hooks_work_together(self):
        """LifecycleManager alongside other hooks."""
        lm = LifecycleManager()
        call_log = []

        class LogHook(RuntimeHook):
            def after_transition(self, engine, from_s, to_s, ctx, t):
                call_log.append(f"{from_s.name}→{to_s.name}")

        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="multi_hook")
        engine._table = table
        engine.add_hook(lm)
        engine.add_hook(LogHook())
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert len(call_log) >= 1
        assert lm.agent_summary()["total_agents"] >= 1


# ══════════════════════════════════════════════
# 7. Recovery → Lifecycle Integration
# ══════════════════════════════════════════════

class TestRecoveryLifecycle:
    def test_recovery_updates_lifecycle(self):
        lm = LifecycleManager()
        lm.register_agent("profile")
        lm.mark_error("profile", "transient")
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.FAILED

        lm.mark_recovery("profile")
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.RECOVERING
        assert lm.get_agent("profile").recovery_count == 1

        lm.mark_recovered("profile")
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.READY

    def test_full_failure_recovery_cycle(self):
        """Simulate: RUNNING → FAILED → RECOVERING → READY → RUNNING → READY → TERMINATED"""
        lm = LifecycleManager()
        ctx = RuntimeContext(session_id="cycle")
        lm.on_run_start(None, ctx)

        # Agent starts running
        lm.before_transition(None, AgentState.INIT, AgentState.PROFILE, ctx)
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.RUNNING

        # Failure
        lm.mark_error("profile", "something broke")
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.FAILED

        # Recovery
        lm.mark_recovery("profile")
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.RECOVERING
        lm.mark_recovered("profile")
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.READY

        # Retry succeeds
        lm.before_transition(None, AgentState.INIT, AgentState.PROFILE, ctx)
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.RUNNING
        lm.after_transition(None, AgentState.INIT, AgentState.PROFILE, ctx,
                            StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE, status="success"))

        # Run ends
        lm.on_run_end(None, ctx, 2000.0)
        assert lm.get_agent("profile").lifecycle == AgentLifecycle.TERMINATED


# ══════════════════════════════════════════════
# 8. Edge Cases
# ══════════════════════════════════════════════

class TestLifecycleEdgeCases:
    def test_agent_name_mapping(self):
        assert agent_name_for_state(AgentState.PROFILE) == "profile"
        assert agent_name_for_state(AgentState.META_REFLECT) == "meta_reflect"
        assert agent_name_for_state(AgentState.MEMORY_UPDATE) == "memory_update"

    def test_empty_session(self):
        s = RuntimeSession()
        assert s.timeline() == []
        assert s.state_count() == 0
        assert s.error_count() == 0

    def test_lifecycle_manager_without_session(self):
        lm = LifecycleManager()
        # Session is auto-created
        assert lm.session is not None
        assert lm.session.session_id == ""

    def test_reset_preserves_behavior(self):
        """After reset, lifecycle manager works fresh."""
        lm = LifecycleManager()
        lm.register_agent("a")
        lm.reset()
        lm.register_agent("b")
        assert lm.agent_summary()["total_agents"] == 1
        names = list(lm.agent_states.keys())
        assert "b" in names
        assert "a" not in names
