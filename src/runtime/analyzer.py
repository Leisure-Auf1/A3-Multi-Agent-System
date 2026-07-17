"""
Phase 5.2 — Runtime Analyzer

Analyzes runtime state, metrics, and context to produce:
  - State analysis (which states succeeded/failed)
  - Metric summaries
  - Health score (0–100)
  - Runtime reports

Non-invasive — reads RuntimeContext + RuntimeMetrics only.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .state import AgentState
from .metrics import RuntimeMetrics


@dataclass
class StateAnalysis:
    """Analysis of a single state execution."""
    state: str
    success_count: int = 0
    error_count: int = 0
    avg_duration_ms: float = 0.0
    last_error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        return self.error_count == 0


@dataclass
class HealthReport:
    """Overall runtime health assessment."""
    score: int = 100  # 0–100
    status: str = "healthy"  # healthy | degraded | failing
    issues: List[str] = field(default_factory=list)
    state_analyses: List[StateAnalysis] = field(default_factory=list)
    recommendation: str = ""


class RuntimeAnalyzer:
    """
    Analyzes runtime execution state and metrics.

    Usage:
        analyzer = RuntimeAnalyzer()
        health = analyzer.health_score(metrics, ctx)
        report = analyzer.generate_runtime_report(metrics, ctx)
    """

    HEALTHY_THRESHOLD = 70
    DEGRADED_THRESHOLD = 40

    # ── State Analysis ────────────────────

    def analyze_state(
        self,
        state: AgentState,
        context: Any,  # RuntimeContext
    ) -> StateAnalysis:
        """Analyze a single state's execution trend."""
        analysis = StateAnalysis(state=state.name)

        evaluation = getattr(context, 'evaluation', None) or {}
        errors = getattr(context, 'errors', []) or []

        if state == AgentState.EVALUATE:
            score = evaluation.get("score", 100) if isinstance(evaluation, dict) else 100
            if score < 70:
                analysis.error_count += 1
                analysis.last_error = f"Low evaluation score: {score}"
            else:
                analysis.success_count += 1

        # Check context errors matching this state (case-insensitive)
        for err in errors:
            if state.name.lower() in str(err).lower():
                analysis.error_count += 1
                analysis.last_error = str(err)

        if analysis.error_count == 0 and analysis.last_error is None:
            analysis.success_count = 1

        return analysis

    def analyze_states(
        self,
        context: Any,  # RuntimeContext
    ) -> List[StateAnalysis]:
        """Analyze all key states from context."""
        states = [
            AgentState.PROFILE, AgentState.PLAN, AgentState.EXECUTE,
            AgentState.EVALUATE, AgentState.REFLECT, AgentState.META_REFLECT,
            AgentState.MEMORY_UPDATE,
        ]
        return [self.analyze_state(s, context) for s in states]

    # ── Metrics Analysis ──────────────────

    def analyze_metrics(
        self,
        metrics: RuntimeMetrics,
    ) -> Dict[str, Any]:
        """Produce a structured analysis of metrics."""
        summary = metrics.summary()
        return {
            "runs": summary["total_runs"],
            "success_rate": summary["success_rate"],
            "avg_score": summary["avg_score"],
            "avg_duration_ms": summary["avg_duration_ms"],
            "reflection_rate": (
                summary["reflection_count"] / max(summary["total_runs"], 1)
            ),
            "is_degraded": summary["success_rate"] < 0.7,
        }

    # ── Health Score ───────────────────────

    def health_score(
        self,
        metrics: RuntimeMetrics,
        context: Optional[Any] = None,
    ) -> HealthReport:
        """
        Calculate an aggregate health score 0–100.

        Factors:
          - Success rate (weight: 40)
          - Average evaluation score (weight: 30)
          - Error count (weight: 20)
          - Reflection rate (weight: 10)
        """
        summary = metrics.summary()
        issues: List[str] = []

        # Success rate component
        success_rate = summary["success_rate"]
        success_component = success_rate * 40

        # Average score component
        avg_score = summary["avg_score"]
        score_component = (avg_score / 100) * 30

        # Error penalty
        error_count = summary["error_count"]
        error_penalty = min(error_count * 5, 20)
        error_component = 20 - error_penalty
        if error_count > 2:
            issues.append(f"High error count: {error_count}")

        # Reflection rate (too high = unhealthy)
        ref_count = summary["reflection_count"]
        runs = max(summary["total_runs"], 1)
        ref_rate = ref_count / runs
        ref_component = (1.0 - min(ref_rate, 1.0)) * 10
        if ref_rate > 0.5:
            issues.append(f"Frequent reflections: {ref_count}/{runs}")

        score = round(success_component + score_component + error_component + ref_component)
        score = max(0, min(100, score))

        # Status
        if score >= self.HEALTHY_THRESHOLD:
            status = "healthy"
        elif score >= self.DEGRADED_THRESHOLD:
            status = "degraded"
        else:
            status = "failing"

        # Context-specific checks
        if context:
            errors = getattr(context, 'errors', []) or []
            if errors:
                issues.append(f"Context errors: {len(errors)}")

        state_analyses = self.analyze_states(context) if context else []

        return HealthReport(
            score=score,
            status=status,
            issues=issues,
            state_analyses=state_analyses,
            recommendation=self._recommendation(score, status, issues),
        )

    def generate_runtime_report(
        self,
        metrics: RuntimeMetrics,
        context: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive runtime report."""
        health = self.health_score(metrics, context)
        metric_analysis = self.analyze_metrics(metrics)

        return {
            "health": {
                "score": health.score,
                "status": health.status,
                "issues": health.issues,
                "recommendation": health.recommendation,
            },
            "metrics": metric_analysis,
            "states": [{
                "state": sa.state,
                "healthy": sa.is_healthy,
                "success": sa.success_count,
                "errors": sa.error_count,
                "last_error": sa.last_error,
            } for sa in health.state_analyses],
        }

    # ── Helpers ─────────────────────────────

    @staticmethod
    def _recommendation(score: int, status: str, issues: List[str]) -> str:
        if status == "healthy":
            return "System is operating normally. Continue monitoring."
        elif status == "degraded":
            return (
                "System performance is below optimal. "
                + ("Review: " + "; ".join(issues[:2]) if issues else "Check error logs.")
            )
        else:
            return (
                "System requires immediate attention. "
                + ("Critical issues: " + "; ".join(issues[:3]) if issues else "Investigate root cause.")
            )
