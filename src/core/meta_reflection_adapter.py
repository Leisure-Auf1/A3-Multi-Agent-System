"""
Phase 4.6 — MetaReflectionAdapter

Converts EvaluationResult + ReflectionResult → MetaReflector input format.
Decouples the workflow from MetaReflector's internal contract.

Usage:
    adapter = MetaReflectionAdapter()
    failure_context = adapter.build_failure_context(evaluation, reflection, student_id)
    concept = adapter.extract_concept(reflection, learning_plan)
    severity = adapter.determine_severity(evaluation)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class MetaReflectionAdapter:
    """Bridge between pipeline evaluation output and MetaReflector input."""

    THRESHOLD: int = 70

    # ── Public API ────────────────────────────

    def should_trigger(self, evaluation: Optional[Dict[str, Any]]) -> bool:
        """
        Determine if MetaReflector should be triggered.

        Conditions: score < 70 OR issues non-empty.
        """
        if not evaluation or not isinstance(evaluation, dict):
            return False
        score = evaluation.get("score", 100)
        issues = evaluation.get("issues", [])
        return score < self.THRESHOLD or (isinstance(issues, list) and len(issues) > 0)

    def build_failure_context(
        self,
        evaluation: Optional[Dict[str, Any]],
        reflection: Optional[Dict[str, Any]],
        student_id: str = "",
    ) -> Dict[str, Any]:
        """
        Convert evaluation + reflection into MetaReflector.reflect() failure_context.

        Expected keys by MetaReflector:
          - mistake: error/problem description
          - student_id: student identifier
          - scores: list of scores
          - attempts: number of attempts
          - profile_type: optional profile label
        """
        eval_data = evaluation or {}
        refl_data = reflection or {}

        # Mistake: issues from evaluation (preferred) or reflection improvements
        issues = eval_data.get("issues", [])
        if isinstance(issues, list) and issues:
            mistake = "; ".join(str(i) for i in issues[:3])
        else:
            improvements = refl_data.get("improvements", [])
            if isinstance(improvements, list) and improvements:
                mistake = "; ".join(str(i) for i in improvements[:3])
            else:
                mistake = f"Pipeline evaluation score {eval_data.get('score', 0)}"

        # Scores list
        scores = [eval_data.get("score", 0)]
        rg = eval_data.get("review_gate")
        if rg and isinstance(rg, dict):
            rg_score = rg.get("score")
            if rg_score is not None:
                scores.append(rg_score)

        return {
            "mistake": mistake,
            "student_id": student_id,
            "scores": scores,
            "attempts": 1,
            "profile_type": self._extract_profile_type(reflection),
        }

    def extract_concept(
        self,
        reflection: Optional[Dict[str, Any]] = None,
        learning_plan: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Extract a concept label from available context.

        Priority: reflection goal → plan node titles → empty string.
        """
        if reflection and isinstance(reflection, dict):
            goal = reflection.get("goal", "")
            if goal:
                return goal[:80]

        if learning_plan and isinstance(learning_plan, dict):
            nodes = learning_plan.get("nodes", [])
            if isinstance(nodes, list) and nodes:
                titles = [
                    n.get("title", "")
                    for n in nodes[:3]
                    if isinstance(n, dict) and n.get("title")
                ]
                if titles:
                    return ", ".join(titles[:2])

        return ""

    def determine_severity(
        self,
        evaluation: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Map evaluation score to severity level.

        Rules:
          score < 40  → CRITICAL
          score < 60  → HIGH
          score < 70  → MEDIUM
          issues only  → LOW
        """
        if not evaluation or not isinstance(evaluation, dict):
            return "MEDIUM"

        score = evaluation.get("score", 100)
        if score < 40:
            return "CRITICAL"
        if score < 60:
            return "HIGH"
        if score < self.THRESHOLD:
            return "MEDIUM"

        # Score passes but issues exist → LOW
        issues = evaluation.get("issues", [])
        if isinstance(issues, list) and issues:
            return "LOW"

        return "MEDIUM"

    # ── Internal helpers ──────────────────────

    def _extract_profile_type(
        self, reflection: Optional[Dict[str, Any]]
    ) -> str:
        """Extract a profile-type label from reflection or return empty."""
        if not reflection or not isinstance(reflection, dict):
            return ""
        # Check for embedded profile info if any (future-proof)
        return ""
