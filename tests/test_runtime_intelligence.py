"""
Phase 5.2 — Runtime Intelligence Layer Tests

Covers:
  1. RuntimeAnalyzer: state analysis, metrics, health score, reports
  2. FailureDetector: exception, low_score, repeated, timeout, memory
  3. RuntimePolicyEngine: continue, retry, reflect, terminate decisions
  4. RuntimeDecision: model and decision log
  5. RuntimeEngine + policy integration
  6. Backward compatibility (no policy = old behavior)
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.runtime import (
    AgentState,
    StateTransition,
    TransitionTable,
    RuntimeAnalyzer,
    HealthReport,
    StateAnalysis,
    FailureDetector,
    FailureEvent,
    RuntimePolicyEngine,
    RuntimeDecision,
    DecisionLog,
    RuntimeEngine,
    RuntimeContext,
    RuntimeMetrics,
)


# ──────────────────────────────────────────────
# 1. RuntimeAnalyzer
# ──────────────────────────────────────────────

class TestRuntimeAnalyzer:
    def test_analyze_state_success(self):
        analyzer = RuntimeAnalyzer()
        ctx = RuntimeContext()
        analysis = analyzer.analyze_state(AgentState.PROFILE, ctx)
        assert analysis.state == "PROFILE"
        assert analysis.is_healthy is True

    def test_analyze_state_with_error(self):
        analyzer = RuntimeAnalyzer()
        ctx = RuntimeContext(
            errors=["ProfileAgent: extraction failed"],
        )
        analysis = analyzer.analyze_state(AgentState.PROFILE, ctx)
        assert analysis.error_count >= 1
        assert "extraction failed" in (analysis.last_error or "")

    def test_analyze_evaluation_state_low_score(self):
        analyzer = RuntimeAnalyzer()
        ctx = RuntimeContext(evaluation={"score": 45, "issues": ["bad"]})
        analysis = analyzer.analyze_state(AgentState.EVALUATE, ctx)
        assert analysis.error_count >= 1

    def test_analyze_states(self):
        analyzer = RuntimeAnalyzer()
        ctx = RuntimeContext()
        analyses = analyzer.analyze_states(ctx)
        assert len(analyses) >= 4

    def test_analyze_metrics(self):
        bus = __import__('src.runtime.events', fromlist=['RuntimeEventBus']).RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)
        from src.runtime.events import RuntimeEvent
        # Emit success transitions + evaluation
        bus.emit(RuntimeEvent(event_type="transition", status="success"))
        bus.emit(RuntimeEvent(event_type="transition", status="success"))
        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 90}))
        bus.emit(RuntimeEvent(event_type="done", metadata={"total_duration_ms": 200}))

        analyzer = RuntimeAnalyzer()
        result = analyzer.analyze_metrics(metrics)
        assert result["avg_score"] == 90.0
        assert result["is_degraded"] is False

    def test_health_score_healthy(self):
        bus = __import__('src.runtime.events', fromlist=['RuntimeEventBus']).RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)
        from src.runtime.events import RuntimeEvent
        for i in range(3):
            bus.emit(RuntimeEvent(event_type="transition", status="success"))
            bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 88}))
            bus.emit(RuntimeEvent(event_type="done", metadata={"total_duration_ms": 100}))

        analyzer = RuntimeAnalyzer()
        health = analyzer.health_score(metrics)
        assert health.score >= 70
        assert health.status == "healthy"

    def test_health_score_degraded(self):
        bus = __import__('src.runtime.events', fromlist=['RuntimeEventBus']).RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)
        from src.runtime.events import RuntimeEvent
        # Error-heavy
        bus.emit(RuntimeEvent(event_type="transition", status="error"))
        bus.emit(RuntimeEvent(event_type="transition", status="success"))
        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 50}))

        analyzer = RuntimeAnalyzer()
        health = analyzer.health_score(metrics)
        assert health.score < 80

    def test_generate_runtime_report(self):
        bus = __import__('src.runtime.events', fromlist=['RuntimeEventBus']).RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)
        from src.runtime.events import RuntimeEvent
        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 75}))

        analyzer = RuntimeAnalyzer()
        report = analyzer.generate_runtime_report(metrics)
        assert "health" in report
        assert "metrics" in report
        assert "states" in report


# ──────────────────────────────────────────────
# 2. FailureDetector
# ──────────────────────────────────────────────

class TestFailureDetector:
    def test_detect_exception(self):
        detector = FailureDetector()
        t = StateTransition(
            from_state=AgentState.PROFILE,
            to_state=AgentState.PROFILE,
            status="error",
            error="test failure",
        )
        failure = detector.detect_from_transition(t, RuntimeContext())
        assert failure is not None
        assert failure.failure_type == "EXCEPTION"

    def test_detect_low_score(self):
        detector = FailureDetector()
        t = StateTransition(
            from_state=AgentState.EXECUTE,
            to_state=AgentState.EVALUATE,
            status="success",
        )
        ctx = RuntimeContext(evaluation={"score": 35})
        failure = detector.detect_from_transition(t, ctx)
        assert failure is not None
        assert failure.failure_type == "LOW_SCORE"
        assert failure.severity == "CRITICAL"

    def test_detect_repeated(self):
        detector = FailureDetector()
        t = StateTransition(
            from_state=AgentState.PROFILE,
            to_state=AgentState.PROFILE,
            status="success",
        )
        ctx = RuntimeContext()
        # Simulate repeats
        for _ in range(3):
            failure = detector.detect_from_transition(t, ctx)
        assert failure is not None
        assert failure.failure_type == "REPEATED_TRANSITION"

    def test_no_failure_on_success(self):
        detector = FailureDetector()
        t = StateTransition(
            from_state=AgentState.INIT,
            to_state=AgentState.PROFILE,
            status="success",
        )
        failure = detector.detect_from_transition(t, RuntimeContext())
        assert failure is None

    def test_detect_from_context(self):
        detector = FailureDetector()
        ctx = RuntimeContext(
            errors=["PlannerAgent: plan error"],
            evaluation={"score": 55},
        )
        failures = detector.detect_from_context(ctx)
        assert len(failures) >= 2  # exception + low_score

    def test_failure_to_dict(self):
        fe = FailureEvent(
            failure_type="LOW_SCORE",
            state=AgentState.EVALUATE,
            detail="Score 30 too low",
            severity="HIGH",
        )
        d = fe.to_dict()
        assert d["failure_type"] == "LOW_SCORE"
        assert d["state"] == "EVALUATE"
        assert d["severity"] == "HIGH"


# ──────────────────────────────────────────────
# 3. RuntimeDecision
# ──────────────────────────────────────────────

class TestRuntimeDecision:
    def test_create_decision(self):
        d = RuntimeDecision(
            from_state=AgentState.EVALUATE,
            to_state=AgentState.REFLECT,
            action="REFLECT",
            reason="Low score detected",
            confidence=0.8,
        )
        assert d.action == "REFLECT"
        assert d.confidence == 0.8

    def test_to_dict(self):
        d = RuntimeDecision(
            from_state=AgentState.PROFILE,
            to_state=AgentState.PROFILE,
            action="RETRY",
            reason="Retry after exception",
            metadata={"retry_count": 1},
        )
        dd = d.to_dict()
        assert dd["action"] == "RETRY"
        assert dd["from_state"] == "PROFILE"
        assert dd["metadata"]["retry_count"] == 1

    def test_decision_log(self):
        log = DecisionLog()
        log.record(RuntimeDecision(action="CONTINUE", from_state=AgentState.INIT, to_state=AgentState.PROFILE))
        log.record(RuntimeDecision(action="REFLECT", from_state=AgentState.EVALUATE, to_state=AgentState.REFLECT))
        log.record(RuntimeDecision(action="CONTINUE", from_state=AgentState.REFLECT, to_state=AgentState.MEMORY_UPDATE))

        assert log.last().action == "CONTINUE"
        assert len(log.by_action("REFLECT")) == 1
        assert len(log.by_action("CONTINUE")) == 2

    def test_decision_log_summary(self):
        log = DecisionLog()
        log.record(RuntimeDecision(action="CONTINUE"))
        log.record(RuntimeDecision(action="RETRY"))
        log.record(RuntimeDecision(action="CONTINUE"))

        s = log.summary()
        assert s["total"] == 3
        assert s["actions"]["CONTINUE"] == 2
        assert s["actions"]["RETRY"] == 1


# ──────────────────────────────────────────────
# 4. RuntimePolicyEngine
# ──────────────────────────────────────────────

class TestRuntimePolicyEngine:
    def test_continue_on_success(self):
        policy = RuntimePolicyEngine()
        decision = policy.decide(
            AgentState.PROFILE, AgentState.PLAN,
            RuntimeContext(),
            StateTransition(from_state=AgentState.PROFILE, to_state=AgentState.PLAN, status="success"),
        )
        assert decision.action == "CONTINUE"

    def test_reflect_on_low_score(self):
        policy = RuntimePolicyEngine()
        ctx = RuntimeContext(evaluation={"score": 50})
        t = StateTransition(
            from_state=AgentState.EXECUTE,
            to_state=AgentState.EVALUATE,
            status="success",
        )
        decision = policy.decide(AgentState.EXECUTE, AgentState.EVALUATE, ctx, t)
        assert decision.action in ("REFLECT", "META_REFLECT")

    def test_retry_on_exception(self):
        policy = RuntimePolicyEngine()
        ctx = RuntimeContext()
        t = StateTransition(
            from_state=AgentState.PROFILE,
            to_state=AgentState.PROFILE,
            status="error",
            error="Something broke",
        )
        decision = policy.decide(AgentState.PROFILE, AgentState.PROFILE, ctx, t)
        assert decision.action == "RETRY"

    def test_decision_log_accumulates(self):
        policy = RuntimePolicyEngine()
        policy.decide(AgentState.PROFILE, AgentState.PLAN, RuntimeContext(),
                      StateTransition(from_state=AgentState.PROFILE, to_state=AgentState.PLAN, status="success"))
        policy.decide(AgentState.PLAN, AgentState.EXECUTE, RuntimeContext(),
                      StateTransition(from_state=AgentState.PLAN, to_state=AgentState.EXECUTE, status="success"))

        assert len(policy.decision_log.decisions) == 2

    def test_decide_pre_transition_no_override(self):
        policy = RuntimePolicyEngine()
        d = policy.decide_pre_transition(AgentState.INIT, AgentState.PROFILE, RuntimeContext())
        assert d.action == "CONTINUE"


# ──────────────────────────────────────────────
# 5. RuntimeEngine + Policy Integration
# ──────────────────────────────────────────────

class TestEngineWithPolicy:
    def test_engine_with_policy_continues_normally(self):
        """Policy engine on normal flow → same as without policy."""
        policy = RuntimePolicyEngine()
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="pol_test", policy_engine=policy)
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        ctx = engine.run()
        assert ctx is not None
        assert engine._checkpoint.state_count() >= 1

    def test_engine_with_policy_terminates_on_repeat(self):
        """Repeated errors → policy terminates."""
        policy = RuntimePolicyEngine()
        fails = []

        def failing_handler(ctx):
            fails.append(1)
            raise RuntimeError("always fail")

        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="term_test", policy_engine=policy)
        engine._table = table
        engine.register_handler(AgentState.PROFILE, failing_handler)
        ctx = engine.run()
        # Should have retried up to MAX_RETRIES then terminated
        assert len(fails) <= policy.MAX_RETRIES_PER_STATE + 1
        assert len(ctx.errors) >= 1

    def test_engine_without_policy_works(self):
        """Without policy_engine, old behavior preserved."""
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="no_pol")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        ctx = engine.run()
        assert engine._checkpoint.state_count() >= 1
        assert ctx.errors == []


# ──────────────────────────────────────────────
# 6. Backward Compatibility
# ──────────────────────────────────────────────

class TestBackwardCompat:
    def test_engine_default_constructor(self):
        """Default RuntimeEngine() still works."""
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine()
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        ctx = engine.run()
        assert engine._checkpoint.state_count() >= 1

    def test_analyzer_standalone(self):
        """Analyzer works without engine."""
        analyzer = RuntimeAnalyzer()
        bus = __import__('src.runtime.events', fromlist=['RuntimeEventBus']).RuntimeEventBus()
        metrics = RuntimeMetrics()
        metrics.attach(bus)
        health = analyzer.health_score(metrics)
        assert isinstance(health, HealthReport)

    def test_failure_detector_standalone(self):
        """FailureDetector works standalone."""
        detector = FailureDetector()
        assert detector.detect_from_transition(
            StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE, status="success"),
            RuntimeContext(),
        ) is None
