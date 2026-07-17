"""
Phase 5.7 — Runtime Decision Explainability Tests

Covers:
  1. DecisionReason: creation, properties, to_dict, auto_description
  2. DecisionCategory: enum values, is_recovery, is_termination
  3. DecisionTrace: creation, to_dict, to_summary
  4. DecisionChain: linking, length, all_recovered, to_dict
  5. ExplanationRecorder: RuntimeHook integration, trace capture
  6. ExplanationRecorder: decision reason building (all action types)
  7. ExplanationRecorder: query methods (by_action, by_category, recovery_traces)
  8. ExplanationRecorder: explainability_score, decision_diversity
  9. ExplanationRecorder: to_dict, to_summary, reset
 10. Engine integration: recorder + policy engine
 11. Engine integration: recorder + recovery
 12. ExplainabilityMetrics: recording, aggregation
 13. Benchmark integration: explainability in benchmark pipeline
 14. Edge cases: empty recorder, no policy engine, backward compat
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock

from veritas.runtime import (
    AgentState,
    StateTransition,
    TransitionTable,
    RuntimeEngine,
    RuntimeContext,
    RuntimePolicyEngine,
    RuntimeDecision,
)
from veritas.runtime.recovery import RecoveryManager, RecoveryConfig
from veritas.runtime.explain import (
    DecisionTrace,
    DecisionReason,
    DecisionCategory,
    DecisionChain,
    ExplanationRecorder,
)
from veritas.benchmark import ExplainabilityMetrics


# ══════════════════════════════════════════════
# 1. DecisionReason
# ══════════════════════════════════════════════

class TestDecisionReason:
    def test_create(self):
        r = DecisionReason(
            rule_id="exception_retry",
            category=DecisionCategory.FAILURE_RECOVERY,
            priority=2,
            evidence={"failure": "EXCEPTION"},
            description="Retry after exception",
        )
        assert r.rule_id == "exception_retry"
        assert r.category == DecisionCategory.FAILURE_RECOVERY
        assert r.priority == 2

    def test_is_recovery(self):
        r = DecisionReason(category=DecisionCategory.FAILURE_RECOVERY)
        assert r.is_recovery is True
        r2 = DecisionReason(category=DecisionCategory.NORMAL_FLOW)
        assert r2.is_recovery is False

    def test_is_termination(self):
        r = DecisionReason(category=DecisionCategory.LOOP_GUARD)
        assert r.is_termination is True
        r2 = DecisionReason(category=DecisionCategory.ESCALATION)
        assert r2.is_termination is True
        r3 = DecisionReason(category=DecisionCategory.NORMAL_FLOW)
        assert r3.is_termination is False

    def test_to_dict(self):
        r = DecisionReason(
            rule_id="test", category=DecisionCategory.QUALITY_GATE,
            priority=3, evidence={"score": 45},
        )
        d = r.to_dict()
        assert d["rule_id"] == "test"
        assert d["category"] == "quality_gate"
        assert d["evidence"]["score"] == 45

    def test_auto_description(self):
        r = DecisionReason(rule_id="foo", category=DecisionCategory.LOOP_GUARD)
        d = r.to_dict()
        assert "foo" in d["description"]


# ══════════════════════════════════════════════
# 2. DecisionCategory
# ══════════════════════════════════════════════

class TestDecisionCategory:
    def test_all_categories(self):
        values = {c.value for c in DecisionCategory}
        expected = {"normal_flow", "failure_recovery", "quality_gate",
                     "health_check", "loop_guard", "memory_issue", "escalation"}
        assert values == expected

    def test_from_value(self):
        assert DecisionCategory("failure_recovery") == DecisionCategory.FAILURE_RECOVERY
        assert DecisionCategory("normal_flow") == DecisionCategory.NORMAL_FLOW


# ══════════════════════════════════════════════
# 3. DecisionTrace
# ══════════════════════════════════════════════

class TestDecisionTrace:
    def test_create_minimal(self):
        t = DecisionTrace(action="CONTINUE")
        assert t.action == "CONTINUE"
        assert t.confidence == 1.0
        assert t.timestamp != ""

    def test_create_full(self):
        reason = DecisionReason(rule_id="r1", category=DecisionCategory.HEALTH_CHECK, priority=5)
        t = DecisionTrace(
            action="TERMINATE",
            from_state=AgentState.EVALUATE,
            to_state=AgentState.DONE,
            reason=reason,
            confidence=0.95,
            context={"health_score": 30},
            recovery_attempted=False,
            trace_id="tr1",
        )
        assert t.from_state == AgentState.EVALUATE
        assert t.to_state == AgentState.DONE
        assert t.reason is not None
        assert t.reason.rule_id == "r1"

    def test_to_dict(self):
        t = DecisionTrace(
            action="RETRY",
            from_state=AgentState.PROFILE,
            to_state=AgentState.PROFILE,
            reason=DecisionReason(rule_id="r", category=DecisionCategory.FAILURE_RECOVERY),
            recovery_attempted=True,
            recovery_success=True,
        )
        d = t.to_dict()
        assert d["action"] == "RETRY"
        assert d["from_state"] == "PROFILE"
        assert d["to_state"] == "PROFILE"
        assert d["recovery_attempted"] is True
        assert d["recovery_success"] is True
        assert d["reason"] is not None

    def test_to_summary(self):
        t = DecisionTrace(
            action="RETRY",
            from_state=AgentState.PROFILE,
            to_state=AgentState.PROFILE,
            reason=DecisionReason(rule_id="exception_retry"),
            recovery_attempted=True,
            recovery_success=True,
        )
        s = t.to_summary()
        assert "RETRY" in s
        assert "PROFILE→PROFILE" in s
        assert "exception_retry" in s
        assert "recovered" in s


# ══════════════════════════════════════════════
# 4. DecisionChain
# ══════════════════════════════════════════════

class TestDecisionChain:
    def test_empty_chain(self):
        c = DecisionChain(chain_id="c1")
        assert c.length == 0
        assert c.final_action is None

    def test_add_traces(self):
        c = DecisionChain(chain_id="c1")
        c.add(DecisionTrace(action="RETRY"))
        c.add(DecisionTrace(action="CONTINUE"))
        assert c.length == 2
        assert c.final_action == "CONTINUE"

    def test_all_recovered(self):
        c = DecisionChain(chain_id="c1")
        c.add(DecisionTrace(action="RETRY", recovery_attempted=True, recovery_success=True))
        c.add(DecisionTrace(action="CONTINUE"))
        assert c.all_recovered is True

    def test_not_all_recovered(self):
        c = DecisionChain(chain_id="c1")
        c.add(DecisionTrace(action="RETRY", recovery_attempted=True, recovery_success=False))
        assert c.all_recovered is False

    def test_to_dict(self):
        c = DecisionChain(chain_id="c1")
        c.add(DecisionTrace(action="RETRY", recovery_attempted=True, recovery_success=True))
        d = c.to_dict()
        assert d["chain_id"] == "c1"
        assert d["length"] == 1
        assert d["all_recovered"] is True


# ══════════════════════════════════════════════
# 5. ExplanationRecorder — Basic
# ══════════════════════════════════════════════

class TestExplanationRecorderBasic:
    def test_create(self):
        r = ExplanationRecorder()
        assert len(r.traces) == 0
        assert len(r.chains) == 0

    def test_is_runtime_hook(self):
        from veritas.runtime import RuntimeHook
        r = ExplanationRecorder()
        assert isinstance(r, RuntimeHook)

    def test_empty_explainability_score(self):
        r = ExplanationRecorder()
        # No decisions → perfectly explainable
        assert r.explainability_score() == 1.0

    def test_empty_decision_diversity(self):
        r = ExplanationRecorder()
        assert r.decision_diversity() == 0.0

    def test_reset(self):
        r = ExplanationRecorder()
        r._traces.append(DecisionTrace(action="CONTINUE"))
        r.reset()
        assert len(r.traces) == 0


# ══════════════════════════════════════════════
# 6. ExplanationRecorder — Query Methods
# ══════════════════════════════════════════════

class TestExplanationRecorderQuery:
    @pytest.fixture
    def recorder(self):
        r = ExplanationRecorder()
        r._traces = [
            DecisionTrace(action="CONTINUE", reason=DecisionReason(category=DecisionCategory.NORMAL_FLOW)),
            DecisionTrace(action="RETRY", reason=DecisionReason(category=DecisionCategory.FAILURE_RECOVERY)),
            DecisionTrace(action="RETRY", reason=DecisionReason(category=DecisionCategory.FAILURE_RECOVERY)),
            DecisionTrace(action="TERMINATE", reason=DecisionReason(category=DecisionCategory.LOOP_GUARD)),
        ]
        return r

    def test_traces_by_action(self, recorder):
        assert len(recorder.traces_by_action("RETRY")) == 2
        assert len(recorder.traces_by_action("TERMINATE")) == 1
        assert len(recorder.traces_by_action("REFLECT")) == 0

    def test_traces_by_category(self, recorder):
        assert len(recorder.traces_by_category(DecisionCategory.FAILURE_RECOVERY)) == 2
        assert len(recorder.traces_by_category(DecisionCategory.NORMAL_FLOW)) == 1

    def test_recovery_traces(self, recorder):
        assert len(recorder.recovery_traces()) == 2

    def test_last_trace(self, recorder):
        assert recorder.last_trace().action == "TERMINATE"


# ══════════════════════════════════════════════
# 7. ExplanationRecorder — Explainability Metrics
# ══════════════════════════════════════════════

class TestExplanationRecorderMetrics:
    def test_explainability_score_with_data(self):
        r = ExplanationRecorder(auto_chain=False)
        r._traces = [
            DecisionTrace(
                action="RETRY",
                reason=DecisionReason(rule_id="exception_retry"),
                context={"errors": ["fail"]},
            ),
        ]
        score = r.explainability_score()
        assert score > 0.5  # has reason + context

    def test_explainability_score_perfect(self):
        r = ExplanationRecorder(auto_chain=False)
        r._traces = [
            DecisionTrace(
                action="CONTINUE",
                reason=DecisionReason(rule_id="normal_continue"),
                context={"transition_status": "success"},
            ),
            DecisionTrace(
                action="RETRY",
                reason=DecisionReason(rule_id="exception_retry"),
                context={"errors": ["fail"]},
            ),
        ]
        score = r.explainability_score()
        # All have reasons + context
        assert score > 0.7

    def test_explainability_score_no_reasons(self):
        r = ExplanationRecorder(auto_chain=False)
        r._traces = [
            DecisionTrace(action="CONTINUE"),  # no reason
            DecisionTrace(action="RETRY"),      # no reason
        ]
        score = r.explainability_score()
        assert score < 0.5  # missing reason component

    def test_decision_diversity(self):
        r = ExplanationRecorder()
        r._traces = [
            DecisionTrace(action="CONTINUE"),
            DecisionTrace(action="RETRY"),
            DecisionTrace(action="REFLECT"),
            DecisionTrace(action="TERMINATE"),
            DecisionTrace(action="META_REFLECT"),
        ]
        assert r.decision_diversity() == 1.0  # all 5 actions

    def test_recovery_success_rate(self):
        r = ExplanationRecorder()
        r._traces = [
            DecisionTrace(action="RETRY", reason=DecisionReason(category=DecisionCategory.FAILURE_RECOVERY), recovery_success=True),
            DecisionTrace(action="RETRY", reason=DecisionReason(category=DecisionCategory.FAILURE_RECOVERY), recovery_success=True),
            DecisionTrace(action="RETRY", reason=DecisionReason(category=DecisionCategory.FAILURE_RECOVERY), recovery_success=False),
        ]
        assert r.recovery_success_rate() == 2 / 3

    def test_recovery_success_rate_empty(self):
        r = ExplanationRecorder()
        assert r.recovery_success_rate() == 0.0


# ══════════════════════════════════════════════
# 8. ExplanationRecorder — Serialization
# ══════════════════════════════════════════════

class TestExplanationRecorderSerialization:
    def test_to_dict(self):
        r = ExplanationRecorder(auto_chain=False)
        r._traces = [
            DecisionTrace(
                action="RETRY",
                reason=DecisionReason(rule_id="exception_retry", category=DecisionCategory.FAILURE_RECOVERY),
            ),
        ]
        d = r.to_dict()
        assert d["total_decisions"] == 1
        assert "explainability_score" in d
        assert "decision_diversity" in d
        assert "by_action" in d
        assert "by_category" in d
        assert "traces" in d

    def test_to_summary(self):
        r = ExplanationRecorder(auto_chain=False)
        r._traces = [DecisionTrace(action="CONTINUE")]
        s = r.to_summary()
        assert s["total_decisions"] == 1
        assert "explainability_score" in s
        assert "decision_diversity" in s


# ══════════════════════════════════════════════
# 9. Engine Integration — Recorder Hook
# ══════════════════════════════════════════════

class TestEngineWithRecorder:
    def test_recorder_with_policy_engine(self):
        """Recorder hook captures decisions from policy engine."""
        recorder = ExplanationRecorder()
        policy = RuntimePolicyEngine()
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="rec1", policy_engine=policy)
        engine._table = table
        engine.add_hook(recorder)
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert len(recorder.traces) > 0
        assert recorder.last_trace() is not None
        summary = recorder.to_summary()
        assert summary["total_decisions"] >= 1

    def test_recorder_with_recovery(self):
        """Recorder captures decisions during recovery scenarios."""
        recorder = ExplanationRecorder()
        policy = RuntimePolicyEngine()
        recovery = RecoveryManager(RecoveryConfig(max_retries=2))
        attempts = []

        def flaky(c):
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("transient")

        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(
            session_id="rec2", policy_engine=policy, recovery_manager=recovery,
        )
        engine._table = table
        engine.add_hook(recorder)
        engine.register_handler(AgentState.PROFILE, flaky)
        engine.run()

        assert len(recorder.traces) >= 2  # at least pre-transition + post
        # Should have decisions recorded
        assert recorder.last_trace() is not None

    def test_recorder_chains(self):
        """Chains should be created for related decisions."""
        recorder = ExplanationRecorder(auto_chain=True)
        policy = RuntimePolicyEngine()
        recovery = RecoveryManager(RecoveryConfig(max_retries=2))
        attempts = []

        def flaky(c):
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("transient")

        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(
            session_id="rec3", policy_engine=policy, recovery_manager=recovery,
        )
        engine._table = table
        engine.add_hook(recorder)
        engine.register_handler(AgentState.PROFILE, flaky)
        engine.run()

        assert len(recorder.chains) >= 1

    def test_recorder_without_policy(self):
        """Without policy engine, recorder captures nothing — backward compat."""
        recorder = ExplanationRecorder()
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="rec4")
        engine._table = table
        engine.add_hook(recorder)
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert len(recorder.traces) == 0  # no policy → no decisions


# ══════════════════════════════════════════════
# 10. ExplainabilityMetrics
# ══════════════════════════════════════════════

class TestExplainabilityMetrics:
    def test_empty(self):
        m = ExplainabilityMetrics()
        assert m.total_runs == 0
        assert m.avg_explainability() == 0.0

    def test_record_from_recorder(self):
        m = ExplainabilityMetrics()
        recorder = ExplanationRecorder(auto_chain=False)
        recorder._traces = [
            DecisionTrace(
                action="CONTINUE",
                reason=DecisionReason(rule_id="normal_continue"),
                context={"status": "success"},
            ),
        ]
        m.record_from_recorder(recorder)
        assert m.total_runs == 1
        assert m.avg_explainability() > 0.5

    def test_record_raw(self):
        m = ExplainabilityMetrics()
        m.record_raw(0.8, 0.6, 0.9)
        m.record_raw(0.9, 0.4, 1.0)
        assert m.total_runs == 2
        assert m.avg_explainability() == pytest.approx(0.85)

    def test_avg_decisions_per_run(self):
        m = ExplainabilityMetrics(label="test")
        r = ExplanationRecorder(auto_chain=False)
        r._traces = [DecisionTrace(action="c") for _ in range(3)]
        m.record_from_recorder(r)
        r2 = ExplanationRecorder(auto_chain=False)
        r2._traces = [DecisionTrace(action="c") for _ in range(5)]
        m.record_from_recorder(r2)
        assert m.avg_decisions_per_run() == 4.0

    def test_to_dict(self):
        m = ExplainabilityMetrics(label="exp")
        m.record_raw(0.85, 0.5, 1.0)
        d = m.to_dict()
        assert d["label"] == "exp"
        assert d["total_runs"] == 1
        assert "avg_explainability_score" in d

    def test_to_summary(self):
        m = ExplainabilityMetrics(label="s")
        m.record_raw(0.9, 0.7, 0.8)
        s = m.to_summary()
        assert s["runs"] == 1
        assert "90" in s["explainability"]  # 0.9 → 90%


# ══════════════════════════════════════════════
# 11. _build_reason — All Decision Types
# ══════════════════════════════════════════════

class TestBuildReason:
    @pytest.fixture
    def recorder(self):
        return ExplanationRecorder()

    def _make_decision(self, action, failure_type=None, **kwargs):
        meta = {}
        if failure_type:
            meta["failure"] = {"failure_type": failure_type, "detail": "test"}
        if kwargs:
            meta.update(kwargs)
        return RuntimeDecision(
            from_state=AgentState.PROFILE,
            to_state=AgentState.PLAN,
            action=action,
            reason="test",
            metadata=meta,
        )

    def _transition(self, status="success"):
        return StateTransition(
            from_state=AgentState.PROFILE,
            to_state=AgentState.PLAN,
            status=status,
        )

    def test_continue_reason(self, recorder):
        d = self._make_decision("CONTINUE")
        reason = recorder._build_reason(d, self._transition(), RuntimeContext())
        assert reason.rule_id == "normal_continue"
        assert reason.category == DecisionCategory.NORMAL_FLOW

    def test_retry_exception_reason(self, recorder):
        d = self._make_decision("RETRY", failure_type="EXCEPTION")
        reason = recorder._build_reason(d, self._transition("error"), RuntimeContext())
        assert reason.rule_id == "exception_retry"
        assert reason.category == DecisionCategory.FAILURE_RECOVERY

    def test_retry_timeout_reason(self, recorder):
        d = self._make_decision("RETRY", failure_type="TIMEOUT")
        reason = recorder._build_reason(d, self._transition(), RuntimeContext())
        assert reason.rule_id == "timeout_retry"
        assert reason.category == DecisionCategory.FAILURE_RECOVERY

    def test_reflect_reason(self, recorder):
        d = self._make_decision("REFLECT", failure_type="LOW_SCORE")
        reason = recorder._build_reason(d, self._transition(), RuntimeContext())
        assert reason.rule_id == "low_score_reflect"
        assert reason.category == DecisionCategory.QUALITY_GATE

    def test_meta_reflect_reason(self, recorder):
        d = self._make_decision("META_REFLECT", failure_type="LOW_SCORE")
        reason = recorder._build_reason(d, self._transition(), RuntimeContext())
        assert reason.rule_id == "low_score_meta_reflect"
        assert reason.category == DecisionCategory.QUALITY_GATE

    def test_terminate_repeated_reason(self, recorder):
        d = self._make_decision("TERMINATE", failure_type="REPEATED_TRANSITION")
        reason = recorder._build_reason(d, self._transition(), RuntimeContext())
        assert reason.rule_id == "repeated_terminate"
        assert reason.category == DecisionCategory.LOOP_GUARD

    def test_terminate_memory_reason(self, recorder):
        d = self._make_decision("TERMINATE", failure_type="MEMORY_FAILURE")
        reason = recorder._build_reason(d, self._transition(), RuntimeContext())
        assert reason.rule_id == "memory_terminate"
        assert reason.category == DecisionCategory.MEMORY_ISSUE


# ══════════════════════════════════════════════
# 12. Edge Cases
# ══════════════════════════════════════════════

class TestExplainEdgeCases:
    def test_recorder_without_engine_run(self):
        """Recorder doesn't crash without explicit engine."""
        r = ExplanationRecorder()
        assert r.to_dict()["total_decisions"] == 0

    def test_explainability_metrics_no_runs(self):
        m = ExplainabilityMetrics()
        assert m.avg_decisions_per_run() == 0.0

    def test_trace_with_none_states(self):
        t = DecisionTrace(action="CONTINUE")
        d = t.to_dict()
        assert d["from_state"] is None
        assert d["to_state"] is None

    def test_recovery_traces_no_recovery_category(self):
        r = ExplanationRecorder()
        r._traces = [
            DecisionTrace(action="CONTINUE", reason=DecisionReason(category=DecisionCategory.NORMAL_FLOW)),
        ]
        assert len(r.recovery_traces()) == 0
        assert r.recovery_success_rate() == 0.0

    def test_multiple_recorders_same_engine(self):
        """Two recorders on the same engine should both work."""
        r1 = ExplanationRecorder()
        r2 = ExplanationRecorder()
        policy = RuntimePolicyEngine()
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="multi", policy_engine=policy)
        engine._table = table
        engine.add_hook(r1)
        engine.add_hook(r2)
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert len(r1.traces) > 0
        assert len(r2.traces) > 0
