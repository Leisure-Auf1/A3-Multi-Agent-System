"""
Phase 10.2 / 10.3 — Unified Learning Pipeline API

POST /api/v2/learning/run

Routes through A3Workflow (battle-tested, 7 agent, EventBus, Memory).
Security: Auth → Permission → TokenBudget → Pipeline.

Architecture:
    API → Auth → Permission → LearningPipelineService → A3Workflow
              ↓ token budget check             ↓
         TokenBudgetManager            EventBus + Trace + Memory + Evaluation

Does NOT modify src/core/ or Veritas-Core.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.middleware import require_auth
from src.auth.models import AuthUser
from src.services.learning_pipeline import LearningPipelineService
from src.platform.token_budget import TokenBudgetManager
from src.platform.errors import TokenBudgetExceeded
from src.user.permission import PermissionManager, Role

router = APIRouter(prefix="/api/v2/learning", tags=["learning"])


# ── Schemas ──────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=2000)
    depth: str = "normal"


class PipelineRunResponse(BaseModel):
    run_id: str
    user_id: str
    goal: str
    profile: Dict[str, Any] = Field(default_factory=dict)
    plan: Dict[str, Any] = Field(default_factory=dict)
    resources: List[Dict[str, Any]] = Field(default_factory=list)
    content: Optional[Dict[str, Any]] = None
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    reflection: Optional[Dict[str, Any]] = None
    trace: Optional[List[Dict[str, Any]]] = None
    artifacts_saved: List[str] = Field(default_factory=list)
    memory_saved: bool = False
    duration_ms: float = 0.0
    status: str = "success"


# ── Service instance ─────────────────────────────────

_pipeline_service = LearningPipelineService()


# ── Route ────────────────────────────────────────────

@router.post("/run", response_model=PipelineRunResponse)
def run_learning_pipeline(
    req: PipelineRunRequest,
    user: AuthUser = Depends(require_auth),
):
    """Execute the complete learning pipeline through A3Workflow.

    Flow:
        ProfileAgent → PlannerAgent → ContentGeneratorAgent
        → ResourceAgent → ReviewGate → ReflectionAgent → Memory

    All results persist to workspace/{user_id}/artifacts/.
    Pipeline runs generate EventBus events + TraceCollector records.
    """
    # ── Security: Token Budget check ───────
    try:
        budget = TokenBudgetManager(user.id)
        budget.check_available(tokens=500)
    except TokenBudgetExceeded as e:
        raise HTTPException(status_code=429, detail=e.user_message)

    # ── Security: Role-based permission ────
    # Free users can run pipeline but with rule-only mode
    # Pro/Teacher/Admin users get LLM provider if configured
    from src.user.manager import UserManager
    um = UserManager()
    platform_user = um.get_user_by_email(user.email)
    role = platform_user.role if platform_user else "free"

    # ── Resolve LLM provider ───────────────
    llm_provider = None
    if role in (Role.PRO, Role.TEACHER, Role.ADMIN):
        try:
            from src.core.provider_factory import create_provider
            llm_provider = create_provider()
        except Exception:
            pass  # Fall back to rule-only

    # ── Execute through unified pipeline ───
    result = _pipeline_service.run(
        user_id=user.id,
        goal=req.goal,
        llm_provider=llm_provider,
    )

    # ── Consume token budget ───────────────
    try:
        budget.consume(
            tokens=500,
            provider=getattr(llm_provider, 'provider_name', 'rule'),
        )
    except Exception:
        pass

    return PipelineRunResponse(**result)
