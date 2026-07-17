"""
Phase 5.6 — Benchmark Metrics

Computes quantitative metrics from benchmark runs:
  - Success rate
  - Recovery rate
  - Latency (average, min, max, variance)
  - Step counts

Usage:
    metrics = BenchmarkMetrics()
    metrics.record(success=True, latency_ms=45, recovered=True, steps=5)
    print(metrics.success_rate())  # 1.0
    print(metrics.to_dict())
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import statistics


@dataclass
class RunRecord:
    """A single benchmark run result."""
    success: bool
    latency_ms: float
    recovered: bool = False
    steps: int = 0
    scenario: str = ""
    error: str = ""


class BenchmarkMetrics:
    """
    Accumulates and analyzes benchmark run records.

    Tracks per-scenario metrics for comparison.
    """

    def __init__(self, label: str = ""):
        self.label = label
        self._records: List[RunRecord] = []
        self._by_scenario: Dict[str, List[RunRecord]] = {}

    # ── Record ────────────────────────────────

    def record(
        self,
        success: bool,
        latency_ms: float,
        recovered: bool = False,
        steps: int = 0,
        scenario: str = "",
        error: str = "",
    ) -> None:
        """Record a single benchmark run."""
        rec = RunRecord(
            success=success,
            latency_ms=latency_ms,
            recovered=recovered,
            steps=steps,
            scenario=scenario,
            error=error,
        )
        self._records.append(rec)
        if scenario:
            self._by_scenario.setdefault(scenario, []).append(rec)

    # ── Aggregates ────────────────────────────

    @property
    def total_runs(self) -> int:
        return len(self._records)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self._records if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self._records if not r.success)

    @property
    def recovery_count(self) -> int:
        return sum(1 for r in self._records if r.recovered)

    def success_rate(self) -> float:
        """Success rate as 0.0–1.0."""
        if not self._records:
            return 0.0
        return self.success_count / self.total_runs

    def success_rate_pct(self) -> float:
        """Success rate as 0–100%."""
        return self.success_rate() * 100

    def recovery_rate(self) -> float:
        """Recovery success rate: recovered / (recovered + failed)."""
        denom = self.recovery_count + self.failure_count
        if denom == 0:
            return 0.0
        return self.recovery_count / denom

    def recovery_rate_pct(self) -> float:
        return self.recovery_rate() * 100

    # ── Latency ───────────────────────────────

    @property
    def latencies(self) -> List[float]:
        return [r.latency_ms for r in self._records]

    def avg_latency_ms(self) -> float:
        if not self._records:
            return 0.0
        return statistics.mean(self.latencies)

    def min_latency_ms(self) -> float:
        if not self._records:
            return 0.0
        return min(self.latencies)

    def max_latency_ms(self) -> float:
        if not self._records:
            return 0.0
        return max(self.latencies)

    def median_latency_ms(self) -> float:
        if not self._records:
            return 0.0
        return statistics.median(self.latencies)

    def latency_variance(self) -> float:
        """Variance of latency values."""
        if len(self._records) < 2:
            return 0.0
        return statistics.variance(self.latencies)

    def latency_stddev(self) -> float:
        """Standard deviation of latency."""
        if len(self._records) < 2:
            return 0.0
        return statistics.stdev(self.latencies)

    # ── Steps ─────────────────────────────────

    def avg_steps(self) -> float:
        steps = [r.steps for r in self._records if r.steps > 0]
        if not steps:
            return 0.0
        return statistics.mean(steps)

    # ── Per-Scenario ──────────────────────────

    def scenario_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get per-scenario breakdown."""
        result = {}
        for name, records in self._by_scenario.items():
            success = sum(1 for r in records if r.success)
            total = len(records)
            result[name] = {
                "runs": total,
                "success_count": success,
                "failure_count": total - success,
                "success_rate": success / total if total > 0 else 0.0,
                "avg_latency_ms": statistics.mean([r.latency_ms for r in records]) if records else 0.0,
            }
        return result

    # ── Comparison ────────────────────────────

    def improvement_over(self, baseline: "BenchmarkMetrics") -> Dict[str, Any]:
        """
        Compare this metrics against a baseline.

        Returns percentage improvements for key dimensions.
        """
        base_sr = baseline.success_rate_pct()
        curr_sr = self.success_rate_pct()

        base_lat = baseline.avg_latency_ms()
        curr_lat = self.avg_latency_ms()

        sr_improvement = curr_sr - base_sr

        latency_overhead = 0.0
        if base_lat > 0:
            latency_overhead = ((curr_lat - base_lat) / base_lat) * 100

        return {
            "baseline_success_rate": round(base_sr, 1),
            "runtime_success_rate": round(curr_sr, 1),
            "success_rate_improvement": round(sr_improvement, 1),
            "baseline_avg_latency_ms": round(base_lat, 2),
            "runtime_avg_latency_ms": round(curr_lat, 2),
            "latency_overhead_pct": round(latency_overhead, 2),
            "baseline_failures": baseline.failure_count,
            "runtime_failures": self.failure_count,
            "runtime_recoveries": self.recovery_count,
            "recovery_rate_pct": round(self.recovery_rate_pct(), 1),
        }

    # ── Serialization ─────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Export all metrics."""
        return {
            "label": self.label,
            "total_runs": self.total_runs,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "recovery_count": self.recovery_count,
            "success_rate_pct": round(self.success_rate_pct(), 1),
            "recovery_rate_pct": round(self.recovery_rate_pct(), 1),
            "avg_latency_ms": round(self.avg_latency_ms(), 2),
            "min_latency_ms": round(self.min_latency_ms(), 2),
            "max_latency_ms": round(self.max_latency_ms(), 2),
            "median_latency_ms": round(self.median_latency_ms(), 2),
            "latency_stddev": round(self.latency_stddev(), 2),
            "avg_steps": round(self.avg_steps(), 1),
            "per_scenario": self.scenario_metrics(),
        }

    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "label": self.label,
            "runs": self.total_runs,
            "success_rate": f"{self.success_rate_pct():.1f}%",
            "recovery_rate": f"{self.recovery_rate_pct():.1f}%",
            "avg_latency": f"{self.avg_latency_ms():.1f}ms",
        }


# ══════════════════════════════════════════════
# Phase 5.7 — Explainability Metrics
# ══════════════════════════════════════════════


class ExplainabilityMetrics:
    """
    Tracks explainability of runtime decisions across benchmark runs.

    Measures how transparent and auditable the decision-making is:
      - What fraction of decisions have structured reasons
      - Decision diversity (variety of actions taken)
      - Recovery decision coverage
      - Chain completeness
    """

    def __init__(self, label: str = ""):
        self.label = label
        self._scores: List[float] = []
        self._diversities: List[float] = []
        self._recovery_rates: List[float] = []
        self._total_decisions: int = 0
        self._total_runs: int = 0

    def record_from_recorder(self, recorder: Any) -> None:
        """
        Record explainability metrics from an ExplanationRecorder.

        Args:
            recorder: ExplanationRecorder after engine.run() completed.
        """
        summary = recorder.to_summary()
        self._scores.append(summary["explainability_score"])
        self._diversities.append(summary["decision_diversity"])
        self._recovery_rates.append(summary["recovery_success_rate"])
        self._total_decisions += summary["total_decisions"]
        self._total_runs += 1

    def record_raw(self, explain_score: float, diversity: float, recovery_rate: float) -> None:
        """Record explainability metrics directly."""
        self._scores.append(explain_score)
        self._diversities.append(diversity)
        self._recovery_rates.append(recovery_rate)
        self._total_runs += 1

    # ── Aggregates ────────────────────────────

    def avg_explainability(self) -> float:
        if not self._scores:
            return 0.0
        return sum(self._scores) / len(self._scores)

    def avg_diversity(self) -> float:
        if not self._diversities:
            return 0.0
        return sum(self._diversities) / len(self._diversities)

    def avg_recovery_rate(self) -> float:
        if not self._recovery_rates:
            return 0.0
        return sum(self._recovery_rates) / len(self._recovery_rates)

    @property
    def total_decisions(self) -> int:
        return self._total_decisions

    @property
    def total_runs(self) -> int:
        return self._total_runs

    def avg_decisions_per_run(self) -> float:
        if not self._total_runs:
            return 0.0
        return self._total_decisions / self._total_runs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "total_runs": self.total_runs,
            "total_decisions": self.total_decisions,
            "avg_decisions_per_run": round(self.avg_decisions_per_run(), 1),
            "avg_explainability_score": round(self.avg_explainability(), 3),
            "avg_decision_diversity": round(self.avg_diversity(), 3),
            "avg_recovery_explainability": round(self.avg_recovery_rate(), 3),
        }

    def to_summary(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "runs": self.total_runs,
            "decisions": self.total_decisions,
            "explainability": f"{self.avg_explainability():.1%}",
            "diversity": f"{self.avg_diversity():.1%}",
            "recovery_rate": f"{self.avg_recovery_rate():.1%}",
        }
