"""
Phase 5.6 — Benchmark Runner

Executes benchmark scenarios against the RuntimeEngine and collects
metrics. Compares baseline (no recovery) vs runtime (with recovery)
performance.

Usage:
    runner = BenchmarkRunner(iterations=20)

    # Baseline (no recovery)
    baseline = runner.run(engine_no_recovery, FailureScenario.AGENT_EXCEPTION)

    # Runtime (with recovery)
    runtime = runner.run(engine_with_recovery, FailureScenario.AGENT_EXCEPTION)

    comparison = runtime.improvement_over(baseline)
"""

from __future__ import annotations
import time
from typing import Any, Callable, Dict, List, Optional

from .scenarios import FailureScenario, FailureInjector, InjectionConfig
from .metrics import BenchmarkMetrics
from ..runtime import (
    AgentState,
    RuntimeEngine,
    RuntimeContext,
    RuntimePolicyEngine,
    TransitionTable,
)
from ..runtime.recovery import RecoveryManager, RecoveryConfig


class BenchmarkRunner:
    """
    Runs benchmark scenarios and collects performance metrics.

    Compares baseline (no recovery) vs runtime (with recovery) execution.

    Usage:
        runner = BenchmarkRunner(iterations=10)

        # Run a single scenario
        metrics = runner.run_scenario(
            scenario=FailureScenario.AGENT_EXCEPTION,
            with_recovery=True,
        )

        # Run all scenarios and compare
        results = runner.run_all()
    """

    def __init__(self, iterations: int = 10, warmup: int = 1):
        self.iterations = max(1, iterations)
        self.warmup = max(0, warmup)
        self._injector = FailureInjector()
        self._last_baseline: Optional[BenchmarkMetrics] = None
        self._last_runtime: Optional[BenchmarkMetrics] = None
        self._all_results: Dict[str, Dict[str, Any]] = {}

    # ── Main API ──────────────────────────────

    def run_scenario(
        self,
        scenario: FailureScenario,
        with_recovery: bool = True,
        label: str = "",
    ) -> BenchmarkMetrics:
        """
        Run a single scenario for `iterations` times.

        Args:
            scenario: Which failure to inject.
            with_recovery: Whether to use RecoveryManager.
            label: Custom metric label.

        Returns:
            BenchmarkMetrics with accumulated results.
        """
        label = label or f"{scenario.value}_{'runtime' if with_recovery else 'baseline'}"
        metrics = BenchmarkMetrics(label=label)

        # Warmup runs (discarded)
        for _ in range(self.warmup):
            self._single_run(scenario, with_recovery)

        # Measured runs
        for _ in range(self.iterations):
            self._injector.reset()
            t0 = time.time()

            success, error, steps, recovered = self._single_run(
                scenario, with_recovery,
            )

            latency_ms = (time.time() - t0) * 1000
            metrics.record(
                success=success,
                latency_ms=latency_ms,
                recovered=recovered,
                steps=steps,
                scenario=scenario.value,
                error=error,
            )

        return metrics

    def run_all(self) -> Dict[str, Any]:
        """
        Run all failure scenarios and compare baseline vs runtime.

        Returns a dict mapping scenario name → comparison data.
        """
        results = {}

        scenarios = [
            FailureScenario.NORMAL,
            FailureScenario.LLM_TIMEOUT,
            FailureScenario.AGENT_EXCEPTION,
            FailureScenario.MEMORY_FAILURE,
            FailureScenario.LOW_SCORE,
        ]

        for scenario in scenarios:
            baseline = self.run_scenario(scenario, with_recovery=False)
            runtime = self.run_scenario(scenario, with_recovery=True)
            comparison = runtime.improvement_over(baseline)

            results[scenario.value] = {
                "baseline": baseline.to_summary(),
                "runtime": runtime.to_summary(),
                "comparison": comparison,
            }

        self._last_baseline, self._last_runtime = self._aggregate_all(results)
        self._all_results = results
        return results

    def run_comparison(
        self,
        scenario: FailureScenario,
    ) -> Dict[str, Any]:
        """
        Run a single scenario and return baseline vs runtime comparison.

        Returns:
            Dict with baseline, runtime, and improvement keys.
        """
        baseline = self.run_scenario(scenario, with_recovery=False)
        runtime = self.run_scenario(scenario, with_recovery=True)
        return {
            "scenario": scenario.value,
            "label": scenario.label,
            "baseline": baseline.to_summary(),
            "runtime": runtime.to_summary(),
            "improvement": runtime.improvement_over(baseline),
        }

    # ── Internal ──────────────────────────────

    def _single_run(
        self,
        scenario: FailureScenario,
        with_recovery: bool,
    ) -> tuple:
        """
        Execute one benchmark run.

        Returns: (success, error, steps, recovered)
        """
        session_id = f"bm_{scenario.value}_{int(time.time() * 1000) % 100000}"
        recovery = RecoveryManager(RecoveryConfig(max_retries=2)) if with_recovery else None
        policy = RuntimePolicyEngine() if with_recovery else None  # baseline: no policy retry

        engine = RuntimeEngine(
            session_id=session_id,
            policy_engine=policy,
            recovery_manager=recovery,
        )

        # Short pipeline: INIT → PROFILE → DONE
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine._table = table

        # Create handler with or without injection
        def original_handler(ctx):
            if scenario == FailureScenario.NORMAL:
                ctx.profile = {"knowledge_base": "test"}
            elif scenario == FailureScenario.LOW_SCORE:
                ctx.profile = {"knowledge_base": "test"}
                ctx.evaluation = {"score": 35, "issues": ["low score"]}

        handler = self._injector.wrap(
            agent_name="profile",
            handler=original_handler,
            scenario=scenario,
        )

        engine.register_handler(AgentState.PROFILE, handler)

        try:
            engine.run()
            # Success if no errors or if recovery recovered them
            has_errors = engine._checkpoint.error_count() > 0
            if not has_errors:
                success = True
                error = ""
            else:
                # Check if recovery handled the errors
                recovered = recovery and any(r.success for r in recovery.history)
                success = recovered
                error = ""
                if not recovered:
                    timeline = engine._checkpoint.timeline()
                    for t in timeline:
                        if t.error:
                            error = t.error
                            break
        except Exception as e:
            success = False
            error = str(e)[:200]

        steps = engine._checkpoint.state_count()

        # Check if recovery was used
        recovered = False
        if recovery and len(recovery.history) > 0:
            recovered = any(r.success for r in recovery.history)

        # If injection happened but we still succeeded, that's recovery success
        if self._injector.total_injections > 0 and success:
            recovered = True

        return success, error, steps, recovered

    def _aggregate_all(
        self,
        results: Dict[str, Any],
    ) -> tuple:
        """Aggregate all scenario results into combined metrics."""
        baseline = BenchmarkMetrics(label="Overall Baseline")
        runtime = BenchmarkMetrics(label="Overall Runtime")

        for scenario_name, data in results.items():
            comp = data["comparison"]
            # Use the individual scenario metrics from the runner
            bl_m = self.run_scenario(
                FailureScenario(scenario_name), with_recovery=False,
            )
            rt_m = self.run_scenario(
                FailureScenario(scenario_name), with_recovery=True,
            )

        return baseline, runtime

    # ── Query ─────────────────────────────────

    def comparison_table(self) -> str:
        """Generate a text comparison table of all scenarios."""
        if not self._all_results:
            return "No results yet. Call run_all() first."

        lines = [
            f"{'Scenario':<25} {'Baseline SR':>12} {'Runtime SR':>12} {'Improvement':>12} {'Recovery':>12}",
            "-" * 73,
        ]
        for name, data in self._all_results.items():
            c = data["comparison"]
            bl_sr = f"{c['baseline_success_rate']:.1f}%"
            rt_sr = f"{c['runtime_success_rate']:.1f}%"
            imp = f"+{c['success_rate_improvement']:.1f}%"
            rec = f"{c['recovery_rate_pct']:.1f}%"
            lines.append(f"{name:<25} {bl_sr:>12} {rt_sr:>12} {imp:>12} {rec:>12}")

        return "\n".join(lines)

    @property
    def injection_log(self) -> dict:
        return self._injector.injection_log
