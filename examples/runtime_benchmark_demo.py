#!/usr/bin/env python3
"""
Phase 5.6 — Runtime Benchmark Demo

Demonstrates the benchmark framework comparing baseline (no recovery)
vs Runtime (with recovery) across all failure scenarios.

Usage:
    python examples/runtime_benchmark_demo.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from veritas.benchmark import (
    FailureScenario,
    BenchmarkRunner,
    BenchmarkReporter,
)


def main():
    print("=" * 60)
    print("  Veritas Runtime Benchmark Demo")
    print("=" * 60)
    print()

    runner = BenchmarkRunner(iterations=10)
    reporter = BenchmarkReporter()

    # ── Individual scenario comparison ────────
    scenarios = [
        FailureScenario.NORMAL,
        FailureScenario.LLM_TIMEOUT,
        FailureScenario.AGENT_EXCEPTION,
        FailureScenario.MEMORY_FAILURE,
        FailureScenario.LOW_SCORE,
    ]

    results = {}
    for scenario in scenarios:
        print(f"Running: {scenario.value}...")
        result = runner.run_comparison(scenario)
        results[scenario.value] = result

        imp = result["improvement"]
        print(f"  Baseline SR: {imp['baseline_success_rate']:.1f}%")
        print(f"  Runtime SR:  {imp['runtime_success_rate']:.1f}%")
        print(f"  Improvement: +{imp['success_rate_improvement']:.1f}%")
        print(f"  Recovery:    {imp['recovery_rate_pct']:.1f}%")
        print()

    # ── Full report ───────────────────────────
    print("-" * 60)
    print("  Generating Markdown Report...")
    print("-" * 60)

    report = reporter.generate_report(results, extra={
        "version": "Phase 5.6",
        "iterations": "10 per scenario",
        "engine": "RuntimeEngine + PolicyEngine + RecoveryManager",
    })

    report_path = os.path.join(
        os.path.dirname(__file__), "..", "benchmark_report.md"
    )
    reporter.save(report_path, report)
    print(f"\nReport saved to: {report_path}")
    print()

    # ── Summary table ─────────────────────────
    print("=" * 60)
    print("  Comparison Table")
    print("=" * 60)
    print()
    print(runner.comparison_table())


if __name__ == "__main__":
    main()
