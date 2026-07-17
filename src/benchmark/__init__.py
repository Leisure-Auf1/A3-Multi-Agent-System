"""
Phase 5.6 — Runtime Benchmark Layer

Benchmark framework for measuring and validating the Runtime Recovery Layer.
Provides failure injection, performance metrics, and comparison reporting.

Modules:
    scenarios  — FailureScenario + FailureInjector
    metrics    — BenchmarkMetrics (success rate, latency, recovery)
    runner     — BenchmarkRunner (scenario execution + comparison)
    reporter   — BenchmarkReporter (Markdown reports)

Usage:
    from src.benchmark import BenchmarkRunner, FailureScenario, BenchmarkReporter

    runner = BenchmarkRunner(iterations=10)
    results = runner.run_all()

    reporter = BenchmarkReporter()
    report = reporter.generate_report(results)
    print(report)
"""

from .scenarios import FailureScenario, FailureInjector, InjectionConfig
from .metrics import BenchmarkMetrics, RunRecord, ExplainabilityMetrics  # Phase 5.7
from .runner import BenchmarkRunner
from .reporter import BenchmarkReporter

__all__ = [
    "FailureScenario",
    "FailureInjector",
    "InjectionConfig",
    "BenchmarkMetrics",
    "RunRecord",
    "ExplainabilityMetrics",  # Phase 5.7
    "BenchmarkRunner",
    "BenchmarkReporter",
]
