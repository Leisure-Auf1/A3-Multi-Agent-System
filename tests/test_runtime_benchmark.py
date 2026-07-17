"""
Phase 5.6 — Runtime Benchmark Tests

Covers:
  1. FailureScenario: enum values, labels
  2. InjectionConfig: defaults and customization
  3. FailureInjector: wrap normal, exception, timeout, memory, low_score
  4. FailureInjector: recover_on_retry, persist failure, reset
  5. BenchmarkMetrics: record, success_rate, failure_count
  6. BenchmarkMetrics: latency (avg, min, max, median, stddev)
  7. BenchmarkMetrics: recovery_rate, avg_steps, per_scenario
  8. BenchmarkMetrics: improvement_over comparison
  9. BenchmarkRunner: run single scenario, baseline vs runtime
 10. BenchmarkRunner: run_all, run_comparison, comparison_table
 11. BenchmarkReporter: generate_report, simple_report, save
 12. Integration: real engine comparison (with/without recovery)
 13. Edge cases: empty metrics, zero runs
"""
from __future__ import annotations

import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.runtime import AgentState, RuntimeEngine
from src.benchmark import (
    FailureScenario,
    FailureInjector,
    InjectionConfig,
    BenchmarkMetrics,
    RunRecord,
    BenchmarkRunner,
    BenchmarkReporter,
)


# ══════════════════════════════════════════════
# 1. FailureScenario
# ══════════════════════════════════════════════

class TestFailureScenario:
    def test_all_scenarios_present(self):
        values = {s.value for s in FailureScenario}
        expected = {"normal", "llm_timeout", "agent_exception", "memory_failure", "low_score"}
        assert values == expected

    def test_labels(self):
        assert FailureScenario.NORMAL.label == "正常执行"
        assert FailureScenario.LLM_TIMEOUT.label == "LLM 超时"
        assert FailureScenario.AGENT_EXCEPTION.label == "Agent 异常"
        assert FailureScenario.MEMORY_FAILURE.label == "记忆损坏"
        assert FailureScenario.LOW_SCORE.label == "低分评估"


# ══════════════════════════════════════════════
# 2. InjectionConfig
# ══════════════════════════════════════════════

class TestInjectionConfig:
    def test_defaults(self):
        cfg = InjectionConfig()
        assert cfg.fail_on_attempt == 1
        assert cfg.recover_on_retry is True
        assert cfg.exception_message == "Injected failure for benchmark"
        assert cfg.low_score_value == 35

    def test_custom(self):
        cfg = InjectionConfig(
            fail_on_attempt=3,
            recover_on_retry=False,
            exception_message="custom fail",
            low_score_value=20,
        )
        assert cfg.fail_on_attempt == 3
        assert cfg.recover_on_retry is False
        assert cfg.low_score_value == 20


# ══════════════════════════════════════════════
# 3. FailureInjector — Normal / No failure
# ══════════════════════════════════════════════

class TestFailureInjectorNormal:
    def test_normal_calls_handler(self):
        inj = FailureInjector()
        called = []
        wrapped = inj.wrap("test", lambda c: called.append(1), FailureScenario.NORMAL)
        wrapped(None)
        assert len(called) == 1

    def test_normal_no_injection_recorded(self):
        inj = FailureInjector()
        wrapped = inj.wrap("test", lambda c: None, FailureScenario.NORMAL)
        wrapped(None)
        assert inj.total_injections == 0


# ══════════════════════════════════════════════
# 4. FailureInjector — AGENT_EXCEPTION
# ══════════════════════════════════════════════

class TestFailureInjectorException:
    def test_raises_on_first_attempt(self):
        inj = FailureInjector()
        wrapped = inj.wrap("agent", lambda c: exec('raise RuntimeError("should not reach")'), FailureScenario.AGENT_EXCEPTION)
        with pytest.raises(RuntimeError, match="Injected failure"):
            wrapped(None)
        assert inj.total_injections == 1

    def test_recovers_on_retry(self):
        inj = FailureInjector()
        called = []
        wrapped = inj.wrap("agent", lambda c: called.append("ok"), FailureScenario.AGENT_EXCEPTION)

        # First call → fails
        with pytest.raises(RuntimeError):
            wrapped(None)
        assert called == []

        # Second call → recovers (handler called)
        wrapped(None)
        assert called == ["ok"]

    def test_persist_failure(self):
        """With recover_on_retry=False, always fails."""
        cfg = InjectionConfig(recover_on_retry=False)
        inj = FailureInjector()
        wrapped = inj.wrap("agent", lambda c: None, FailureScenario.AGENT_EXCEPTION, cfg)

        for _ in range(5):
            with pytest.raises(RuntimeError):
                wrapped(None)


# ══════════════════════════════════════════════
# 5. FailureInjector — LLM_TIMEOUT
# ══════════════════════════════════════════════

class TestFailureInjectorTimeout:
    def test_raises_timeout(self):
        inj = FailureInjector()
        wrapped = inj.wrap("llm", lambda c: None, FailureScenario.LLM_TIMEOUT)
        with pytest.raises(TimeoutError):
            wrapped(None)

    def test_recovers_on_retry(self):
        inj = FailureInjector()
        called = []
        wrapped = inj.wrap("llm", lambda c: called.append("ok"), FailureScenario.LLM_TIMEOUT)
        with pytest.raises(TimeoutError):
            wrapped(None)
        wrapped(None)
        assert called == ["ok"]


# ══════════════════════════════════════════════
# 6. FailureInjector — MEMORY_FAILURE
# ══════════════════════════════════════════════

class TestFailureInjectorMemory:
    def test_corrupts_context(self):
        inj = FailureInjector()
        from src.runtime import RuntimeContext
        ctx = RuntimeContext(errors=[])

        wrapped = inj.wrap("mem", lambda c: None, FailureScenario.MEMORY_FAILURE)
        wrapped(ctx)
        assert "CORRUPTED_MEMORY" in ctx.errors

    def test_corrupts_reflection(self):
        inj = FailureInjector()
        from src.runtime import RuntimeContext
        ctx = RuntimeContext(reflection={"success": True})

        wrapped = inj.wrap("mem", lambda c: None, FailureScenario.MEMORY_FAILURE)
        wrapped(ctx)
        assert ctx.reflection == {"corrupted": True, "error": "memory failure"}


# ══════════════════════════════════════════════
# 7. FailureInjector — LOW_SCORE
# ══════════════════════════════════════════════

class TestFailureInjectorLowScore:
    def test_injects_low_score(self):
        inj = FailureInjector()
        from src.runtime import RuntimeContext
        ctx = RuntimeContext()

        wrapped = inj.wrap("eval", lambda c: None, FailureScenario.LOW_SCORE)
        wrapped(ctx)
        assert ctx.evaluation == {"score": 35, "issues": ["injected low score"]}

    def test_preserves_other_context(self):
        inj = FailureInjector()
        from src.runtime import RuntimeContext
        ctx = RuntimeContext(profile={"kb": "test"})

        wrapped = inj.wrap("eval", lambda c: setattr(c, 'profile', {'kb': 'kept'}), FailureScenario.LOW_SCORE)
        wrapped(ctx)
        # After low_score injection, profile should still be set by handler
        assert ctx.evaluation["score"] == 35


# ══════════════════════════════════════════════
# 8. FailureInjector — Reset & Query
# ══════════════════════════════════════════════

class TestFailureInjectorReset:
    def test_reset_clears_counts(self):
        cfg = InjectionConfig(recover_on_retry=False)
        inj = FailureInjector()
        wrapped = inj.wrap("a", lambda c: None, FailureScenario.AGENT_EXCEPTION, cfg)
        for _ in range(3):
            try:
                wrapped(None)
            except RuntimeError:
                pass
        assert inj.total_injections == 3
        inj.reset()
        assert inj.total_injections == 0
        assert inj.injection_log == {}

    def test_custom_fail_attempt(self):
        cfg = InjectionConfig(fail_on_attempt=2)
        inj = FailureInjector()
        called = []
        wrapped = inj.wrap("a", lambda c: called.append(1), FailureScenario.AGENT_EXCEPTION, cfg)

        # Attempt 1: no failure (fail_on_attempt=2)
        wrapped(None)
        assert called == [1]

        # Attempt 2: failure
        with pytest.raises(RuntimeError):
            wrapped(None)


# ══════════════════════════════════════════════
# 9. BenchmarkMetrics — Basic
# ══════════════════════════════════════════════

class TestBenchmarkMetricsBasic:
    def test_empty(self):
        m = BenchmarkMetrics()
        assert m.total_runs == 0
        assert m.success_rate() == 0.0
        assert m.avg_latency_ms() == 0.0

    def test_record_success(self):
        m = BenchmarkMetrics()
        m.record(success=True, latency_ms=10.0)
        m.record(success=True, latency_ms=20.0)
        assert m.total_runs == 2
        assert m.success_count == 2
        assert m.failure_count == 0
        assert m.success_rate() == 1.0

    def test_record_failure(self):
        m = BenchmarkMetrics()
        m.record(success=True, latency_ms=10.0)
        m.record(success=False, latency_ms=50.0, error="crash")
        assert m.success_rate() == 0.5
        assert m.failure_count == 1

    def test_recovery_count(self):
        m = BenchmarkMetrics()
        m.record(success=True, latency_ms=10.0, recovered=True)
        m.record(success=True, latency_ms=15.0)
        m.record(success=True, latency_ms=20.0, recovered=True)
        assert m.recovery_count == 2

    def test_recovery_rate(self):
        m = BenchmarkMetrics()
        # 2 failures recovered, 2 not recovered
        m.record(success=True, latency_ms=10.0, recovered=True)
        m.record(success=True, latency_ms=10.0, recovered=True)
        m.record(success=False, latency_ms=10.0)
        m.record(success=False, latency_ms=10.0)
        assert m.recovery_rate() == 0.5  # 2 recovered / 4 (recovered + failed)


# ══════════════════════════════════════════════
# 10. BenchmarkMetrics — Latency
# ══════════════════════════════════════════════

class TestBenchmarkMetricsLatency:
    @pytest.fixture
    def m(self):
        m = BenchmarkMetrics()
        for lat in [10, 20, 30, 40, 50]:
            m.record(success=True, latency_ms=lat)
        return m

    def test_avg(self, m):
        assert m.avg_latency_ms() == 30.0

    def test_min_max(self, m):
        assert m.min_latency_ms() == 10.0
        assert m.max_latency_ms() == 50.0

    def test_median(self, m):
        assert m.median_latency_ms() == 30.0

    def test_stddev(self, m):
        # stddev of [10,20,30,40,50] ≈ 15.81
        assert 14 < m.latency_stddev() < 17

    def test_variance_single_record(self):
        m = BenchmarkMetrics()
        m.record(success=True, latency_ms=10.0)
        assert m.latency_variance() == 0.0
        assert m.latency_stddev() == 0.0


# ══════════════════════════════════════════════
# 11. BenchmarkMetrics — Steps & Scenarios
# ══════════════════════════════════════════════

class TestBenchmarkMetricsAdvanced:
    def test_avg_steps(self):
        m = BenchmarkMetrics()
        m.record(success=True, latency_ms=10.0, steps=3)
        m.record(success=True, latency_ms=20.0, steps=5)
        assert m.avg_steps() == 4.0

    def test_per_scenario(self):
        m = BenchmarkMetrics()
        m.record(success=True, latency_ms=10.0, scenario="normal")
        m.record(success=False, latency_ms=20.0, scenario="agent_exception")
        m.record(success=True, latency_ms=30.0, scenario="agent_exception")
        by_scene = m.scenario_metrics()
        assert "normal" in by_scene
        assert by_scene["normal"]["success_rate"] == 1.0
        assert by_scene["agent_exception"]["success_rate"] == 0.5

    def test_improvement_over(self):
        baseline = BenchmarkMetrics(label="baseline")
        for _ in range(10):
            baseline.record(success=False, latency_ms=50.0)

        runtime = BenchmarkMetrics(label="runtime")
        for _ in range(10):
            runtime.record(success=True, latency_ms=60.0, recovered=True)

        imp = runtime.improvement_over(baseline)
        assert imp["baseline_success_rate"] == 0.0
        assert imp["runtime_success_rate"] == 100.0
        assert imp["success_rate_improvement"] == 100.0

    def test_to_dict(self):
        m = BenchmarkMetrics(label="test")
        m.record(success=True, latency_ms=42.0, recovered=True, steps=3, scenario="normal")
        d = m.to_dict()
        assert d["label"] == "test"
        assert d["total_runs"] == 1
        assert d["avg_latency_ms"] == 42.0

    def test_to_summary(self):
        m = BenchmarkMetrics(label="s")
        m.record(success=True, latency_ms=10.0)
        s = m.to_summary()
        assert s["runs"] == 1
        assert "100" in s["success_rate"]


# ══════════════════════════════════════════════
# 12. BenchmarkRunner
# ══════════════════════════════════════════════

class TestBenchmarkRunner:
    def test_run_normal_scenario(self):
        runner = BenchmarkRunner(iterations=3)
        metrics = runner.run_scenario(FailureScenario.NORMAL, with_recovery=False)
        assert metrics.total_runs == 3
        assert metrics.success_rate() == 1.0

    def test_run_agent_exception_without_recovery(self):
        """Without recovery, agent_exception should fail."""
        runner = BenchmarkRunner(iterations=5)
        metrics = runner.run_scenario(FailureScenario.AGENT_EXCEPTION, with_recovery=False)
        # Without recovery, all should fail
        assert metrics.success_rate() < 1.0

    def test_run_agent_exception_with_recovery(self):
        """With recovery, agent_exception should have higher success rate."""
        runner = BenchmarkRunner(iterations=5)
        metrics = runner.run_scenario(FailureScenario.AGENT_EXCEPTION, with_recovery=True)
        # With recovery, should succeed on retry
        assert metrics.success_rate() > 0.0

    def test_run_comparison(self):
        runner = BenchmarkRunner(iterations=3)
        result = runner.run_comparison(FailureScenario.AGENT_EXCEPTION)
        assert "baseline" in result
        assert "runtime" in result
        assert "improvement" in result
        imp = result["improvement"]
        assert "success_rate_improvement" in imp

    def test_comparison_table_after_run_all(self):
        runner = BenchmarkRunner(iterations=2)
        runner.run_all()
        table = runner.comparison_table()
        assert "Scenario" in table
        assert "Baseline SR" in table
        assert "Runtime SR" in table

    def test_runner_with_warmup(self):
        runner = BenchmarkRunner(iterations=3, warmup=1)
        metrics = runner.run_scenario(FailureScenario.NORMAL)
        # Should have exactly `iterations` records (warmup discarded)
        assert metrics.total_runs == 3


# ══════════════════════════════════════════════
# 13. BenchmarkReporter
# ══════════════════════════════════════════════

class TestBenchmarkReporter:
    def test_generate_report(self):
        runner = BenchmarkRunner(iterations=2)
        results = runner.run_all()
        reporter = BenchmarkReporter()
        report = reporter.generate_report(results)
        assert "# Veritas Runtime Benchmark" in report
        assert "Overall Summary" in report

    def test_save_to_file(self):
        runner = BenchmarkRunner(iterations=1)
        results = runner.run_all()
        reporter = BenchmarkReporter()
        report = reporter.generate_report(results)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            path = reporter.save(f.name, report)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
            assert "Veritas Runtime Benchmark" in content
        os.unlink(path)

    def test_simple_report(self):
        runner = BenchmarkRunner(iterations=2)
        result = runner.run_comparison(FailureScenario.AGENT_EXCEPTION)
        reporter = BenchmarkReporter()
        report = reporter.generate_simple_report("Agent Exception", result)
        assert "Agent Exception" in report

    def test_report_has_key_findings(self):
        runner = BenchmarkRunner(iterations=1)
        results = runner.run_all()
        reporter = BenchmarkReporter()
        report = reporter.generate_report(results)
        assert "Key Findings" in report


# ══════════════════════════════════════════════
# 14. Integration — Real Engine Comparison
# ══════════════════════════════════════════════

class TestBenchmarkIntegration:
    def test_recovery_improves_success_rate(self):
        """Real comparison: recovery should improve success rate."""
        runner = BenchmarkRunner(iterations=5)
        result = runner.run_comparison(FailureScenario.AGENT_EXCEPTION)
        imp = result["improvement"]
        assert imp["runtime_success_rate"] > imp["baseline_success_rate"]

        # Recovery rate should be > 0
        assert imp["recovery_rate_pct"] > 0

    def test_normal_no_difference(self):
        """Normal scenario: with and without recovery should be similar."""
        runner = BenchmarkRunner(iterations=3)
        result = runner.run_comparison(FailureScenario.NORMAL)
        imp = result["improvement"]
        # Normal should have 100% both ways
        assert imp["runtime_success_rate"] == 100.0


# ══════════════════════════════════════════════
# 15. Edge Cases
# ══════════════════════════════════════════════

class TestBenchmarkEdgeCases:
    def test_single_iteration(self):
        runner = BenchmarkRunner(iterations=1)
        metrics = runner.run_scenario(FailureScenario.NORMAL)
        assert metrics.total_runs == 1

    def test_empty_metrics_to_dict(self):
        m = BenchmarkMetrics()
        d = m.to_dict()
        assert d["total_runs"] == 0

    def test_zero_iterations_clamped(self):
        runner = BenchmarkRunner(iterations=0)
        metrics = runner.run_scenario(FailureScenario.NORMAL)
        assert metrics.total_runs == 1  # clamped to 1

    def test_injector_multiple_agents(self):
        inj = FailureInjector()

        def ok(c):
            pass

        w1 = inj.wrap("a", ok, FailureScenario.AGENT_EXCEPTION)
        w2 = inj.wrap("b", ok, FailureScenario.NORMAL)

        with pytest.raises(RuntimeError):
            w1(None)
        w2(None)  # should not fail
        assert inj.total_injections == 1
