"""
Phase 10.3 — Learning Pipeline Service

Thin API adapter wrapping the battle-tested A3Workflow.
No new runtime — delegates entirely to existing infrastructure.

Flow:
    API request → LearningPipelineService.run()
        → A3Workflow.run()
            → ProfileAgent → PlannerAgent → ContentGeneratorAgent
            → ResourceAgent → ReviewGate → ReflectionAgent → Memory
        → persist artifacts to workspace
        → return formatted result

Architecture: does NOT modify src/core/ or Veritas-Core.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from src.workflow import A3Workflow
from src.workspace.manager import WorkspaceManager
from src.data.learning_records import record_agent_action


class LearningPipelineService:
    """Unified learning pipeline service.

    Wraps A3Workflow — the single source of truth for agent orchestration.
    Handles pre/post processing: workspace persistence, API response formatting.

    Usage:
        service = LearningPipelineService()
        result = service.run(
            user_id="usr_1",
            goal="Learn multi-agent AI systems",
            llm_provider=None,  # None = rule-only
        )
    """

    def __init__(self):
        self._workspace = WorkspaceManager()

    def run(
        self,
        user_id: str,
        goal: str,
        llm_provider: Any = None,
        profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute complete learning pipeline through A3Workflow.

        Args:
            user_id: Authenticated user ID (from auth layer)
            goal: Learning goal text
            llm_provider: Optional LLM provider (None = rule-only)
            profile: Optional pre-existing profile

        Returns:
            Dict with run_id, profile, plan, resources, evaluation,
            reflection, artifacts, trace, memory_saved, duration_ms
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        start = time.time()

        # ── Execute through A3Workflow ──────
        workflow = A3Workflow(
            student_id=user_id,
            llm_provider=llm_provider,
        )

        wf_result = workflow.run(
            user_goal=goal,
            user_profile=profile,
            session_id=run_id,
        )

        duration_ms = round((time.time() - start) * 1000, 1)

        # ── Persist artifacts to workspace ──
        artifacts = self._persist_to_workspace(
            user_id, run_id, goal,
            wf_result.profile or {},
            wf_result.learning_plan or {},
            wf_result.resources or [],
            wf_result.evaluation or {},
        )

        # ── Record pipeline completion with full result for replay ──
        full_result = {
            "run_id": run_id,
            "goal": goal,
            "plan": wf_result.learning_plan or {},
            "content": wf_result.content,
            "resources": wf_result.resources or [],
            "evaluation": wf_result.evaluation or {},
            "reflection": wf_result.reflection,
            "trace": wf_result.trace,
            "memory_saved": wf_result.memory_saved,
            "duration_ms": duration_ms,
            "status": "success" if wf_result.success else ("partial" if wf_result.errors else "error"),
        }
        try:
            record_agent_action(
                user_id, "pipeline", "run_complete",
                course_id="pipeline",
                score=wf_result.evaluation.get("score", 0) if wf_result.evaluation else 0,
                duration_ms=int(duration_ms),
                result=full_result,
            )
        except Exception:
            pass

        # ── Format response ──────────────────
        return {
            "run_id": run_id,
            "user_id": user_id,
            "goal": goal,
            "profile": wf_result.profile,
            "plan": wf_result.learning_plan or {},
            "resources": wf_result.resources or [],
            "content": wf_result.content,
            "evaluation": wf_result.evaluation or {},
            "reflection": wf_result.reflection,
            "trace": wf_result.trace,
            "artifacts_saved": artifacts,
            "memory_saved": wf_result.memory_saved,
            "duration_ms": duration_ms,
            "status": "success" if wf_result.success else ("partial" if wf_result.errors else "error"),
        }

    def _persist_to_workspace(
        self,
        user_id: str, run_id: str, goal: str,
        profile: Dict[str, Any],
        plan: Dict[str, Any],
        resources: List[Dict[str, Any]],
        evaluation: Dict[str, Any],
    ) -> List[str]:
        """Save pipeline outputs to workspace filesystem."""
        saved: List[str] = []

        # Profile JSON
        p = self._workspace.save_artifact(
            user_id, "materials",
            f"profile_{run_id}.json",
            json.dumps(profile, ensure_ascii=False, indent=2),
        )
        saved.append(p)

        # Plan JSON + Markdown
        p = self._workspace.save_artifact(
            user_id, "materials",
            f"plan_{run_id}.json",
            json.dumps(plan, ensure_ascii=False, indent=2),
        )
        saved.append(p)

        md = self._plan_to_markdown(goal, plan)
        p = self._workspace.save_artifact(
            user_id, "materials",
            f"plan_{run_id}.md", md,
        )
        saved.append(p)

        # Resources
        if resources:
            p = self._workspace.save_artifact(
                user_id, "materials",
                f"resources_{run_id}.json",
                json.dumps(resources, ensure_ascii=False, indent=2),
            )
            saved.append(p)

        # Evaluation
        p = self._workspace.save_artifact(
            user_id, "materials",
            f"eval_{run_id}.json",
            json.dumps(evaluation, ensure_ascii=False, indent=2),
        )
        saved.append(p)

        return saved

    @staticmethod
    def _plan_to_markdown(goal: str, plan: Dict[str, Any]) -> str:
        lines = [
            f"# Learning Plan: {goal}",
            "",
            f"**Topic**: {plan.get('topic', goal)}",
            f"**Difficulty**: {plan.get('difficulty', 'N/A')}",
            f"**Estimated Hours**: {plan.get('total_estimated_hours', len(plan.get('nodes', [])))}h",
            "", "## Learning Path", "",
        ]
        for i, node in enumerate(plan.get("nodes", [])):
            lines.append(f"### {i+1}. {node.get('title', 'Untitled')}")
            concepts = node.get("concepts", [])
            if concepts:
                lines.append(f"**Concepts**: {', '.join(concepts)}")
            lines.append(f"**Duration**: ~{node.get('estimated_hours', 1)}h")
            lines.append("")
        return "\n".join(lines)
