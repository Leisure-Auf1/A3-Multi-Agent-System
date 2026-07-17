"""
Phase 4.4 / 4.5 — EvaluationManager

Unified evaluation entry point that assembles:
  1. Rule-based quality scoring (plan structure + resource coverage)
  2. ReviewGate content quality scoring (colloquialism/clarity/progression)
  3. DecisionExplainer adapter (why each decision was made)
  4. Fallback-safe: exceptions return fallback score dict

Usage:
    evaluator = EvaluationManager()
    result = evaluator.evaluate(
        learning_plan=plan_dict,
        resources=resource_list,
        profile=profile_dict,
        user_goal="学习 Python Agent 开发",
        student_id="api_user",
    )
    # → {score, passed, issues, explanations[], review_gate}
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class EvaluationManager:
    """
    Unified evaluation: quality score + ReviewGate + decision explanations.

    Phase 4.5 — Integrates ReviewGate content quality scoring
    via ReviewGateManager.evaluate_content_quality() public API.
    """

    PASS_THRESHOLD: int = 70

    def evaluate(
        self,
        learning_plan: Optional[Dict[str, Any]] = None,
        resources: Optional[List[Dict[str, Any]]] = None,
        profile: Optional[Dict[str, Any]] = None,
        user_goal: str = "",
        student_id: str = "",
    ) -> Dict[str, Any]:
        """
        Produce a structured evaluation result.

        Args:
            learning_plan: PlannerAgent output (with nodes, total_minutes, metadata)
            resources: ResourceAgent output (list of resource dicts)
            profile: ProfileAgent output (dict with profile/confidence/source)
            user_goal: Original learning goal text
            student_id: Student identifier

        Returns:
            {score, passed, issues[], explanations[], review_gate?}
        """
        plan = learning_plan or {}
        res = resources or []
        prof = self._extract_profile_inner(profile or {})

        # 1. Quality scoring (rule-based baseline)
        score = self._compute_quality_score(plan, res, prof)

        # 2. Phase 4.5 — ReviewGate content quality scoring
        review_gate = None
        try:
            review_gate = self._run_review_gate(plan, user_goal)
            if review_gate:
                # 取规则评分和 ReviewGate 评分的较高值
                score = max(score, review_gate.get("score", score))
        except Exception:
            pass  # ReviewGate 不可用时静默跳过

        # 3. Decision explanations
        explanations = self._build_explanations(plan, prof, user_goal)

        # 4. Issues
        issues: List[str] = []
        if not plan.get("nodes"):
            issues.append("No learning nodes generated")
        if not res:
            issues.append("No resources recommended")

        result = {
            "score": score,
            "passed": score >= self.PASS_THRESHOLD,
            "issues": issues,
            "explanations": explanations,
        }
        if review_gate is not None:
            result["review_gate"] = review_gate
        return result

    # ── Quality Scoring ───────────────────────

    def _compute_quality_score(
        self,
        plan: Dict[str, Any],
        resources: List[Dict[str, Any]],
        profile: Dict[str, str],
    ) -> int:
        """Rule-based quality score (0-100)."""
        score = 75  # Baseline

        # Plan structure
        nodes = plan.get("nodes", [])
        if len(nodes) >= 3:
            score += 5
        total_minutes = plan.get("total_minutes", 0)
        if 40 <= total_minutes <= 180:
            score += 5

        # Resource coverage
        if resources:
            if len(resources) >= 2:
                score += 5
            types = {r.get("type", "") for r in resources}
            if len(types) >= 2:
                score += 5

        # Profile enrichment (LLM mode indicates richer planning)
        metadata = plan.get("metadata", {})
        if metadata.get("planning_mode") == "llm":
            score += 5

        return min(score, 100)

    def _extract_profile_inner(
        self, profile_dict: Dict[str, Any]
    ) -> Dict[str, str]:
        """Extract inner profile dict from various shapes."""
        if "profile" in profile_dict:
            inner = profile_dict["profile"]
            if isinstance(inner, dict):
                return {k: str(v) for k, v in inner.items()}
        dim_keys = {
            "knowledge_base", "cognitive_style", "error_prone_bias",
            "learning_pace", "interaction_preference", "frustration_threshold",
        }
        return {k: str(v) for k, v in profile_dict.items() if k in dim_keys}

    # ── Phase 4.5 — ReviewGate Integration ────

    def _run_review_gate(
        self,
        plan: Dict[str, Any],
        user_goal: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Apply ReviewGate content quality scoring to plan content.

        Materializes plan content (rationale + node notes) as text,
        then calls ReviewGateManager.evaluate_content_quality().
        Returns None if ReviewGate is unavailable.
        """
        content = self._materialize_plan_content(plan, user_goal)
        if not content.strip():
            return None

        from src.core.review_gate import ReviewGateManager
        from src.evaluation.review_adapter import adapt_review_gate_result

        review_result = ReviewGateManager.evaluate_content_quality(content)
        return adapt_review_gate_result(review_result)

    def _materialize_plan_content(
        self,
        plan: Dict[str, Any],
        user_goal: str = "",
    ) -> str:
        """
        Convert plan dict into text for ReviewGate scoring.

        Combines: strategy_rationale + node notes + user_goal.
        """
        parts: List[str] = []

        if user_goal:
            parts.append(f"学习目标: {user_goal}")

        rationale = plan.get("strategy_rationale", "")
        if rationale:
            parts.append(rationale)

        nodes = plan.get("nodes", [])
        for node in nodes[:10]:  # Cap to avoid excessive text
            title = node.get("title", "")
            concept = node.get("core_concept", "")
            notes = node.get("notes", "")
            parts.append(f"## {title}")
            if concept:
                parts.append(f"核心概念: {concept}")
            if notes:
                parts.append(f"教学提示: {notes}")

        return "\n\n".join(parts)

    # ── Decision Explanations ─────────────────

    def _build_explanations(
        self,
        plan: Dict[str, Any],
        profile: Dict[str, str],
        user_goal: str = "",
    ) -> List[Dict[str, Any]]:
        """Generate per-node decision explanations using DecisionExplainer."""
        try:
            return self._build_with_explainer(plan, profile)
        except Exception:
            return self._fallback_explanations(plan, profile)

    def _build_with_explainer(
        self,
        plan: Dict[str, Any],
        profile: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Use DecisionExplainer for rich explanations."""
        from src.core.decision_explainer import DecisionExplainer

        explainer = DecisionExplainer()
        explanations: List[Dict[str, Any]] = []

        # Profile dimension explanations
        profile_explanations = explainer.explain_profile_extraction(
            profile_dict=profile,
            student_text="",
        )
        for exp in profile_explanations:
            explanations.append(exp.to_dict())

        # Plan node explanations
        nodes = plan.get("nodes", [])
        for node in nodes:
            node_id = node.get("node_id", "")
            title = node.get("title", "")
            exp = explainer.explain_plan_decision(
                mastery_map={},
                node_id=node_id,
                node_title=title,
                action="normal",
            )
            explanations.append(exp.to_dict())

        return explanations

    def _fallback_explanations(
        self,
        plan: Dict[str, Any],
        profile: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Simple fallback explanations when DecisionExplainer unavailable."""
        explanations: List[Dict[str, Any]] = []

        for dim, val in profile.items():
            if val:
                explanations.append({
                    "agent": "ProfileAgent",
                    "action": f"detect_{dim}",
                    "decision": f"{dim} = {val}",
                    "reason": f"从输入分析推理为 {val}",
                    "confidence": 0.85,
                    "evidence": [],
                    "alternative": "",
                    "timestamp": "",
                })

        nodes = plan.get("nodes", [])
        for node in nodes[:8]:
            explanations.append({
                "agent": "PlannerAgent",
                "action": f"include_{node.get('node_id', '?')}",
                "decision": f"保留「{node.get('title', '?')}」",
                "reason": "标准路径规划",
                "confidence": 0.80,
                "evidence": [],
                "alternative": "",
                "timestamp": "",
            })

        return explanations
