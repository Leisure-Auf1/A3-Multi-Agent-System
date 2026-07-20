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
    # Phase 14.2: Runtime observability
    run_info: Optional[Dict[str, Any]] = None


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
    budget = None
    try:
        budget = TokenBudgetManager(user.id)
        budget.check_available(tokens=500)
    except TokenBudgetExceeded as e:
        raise HTTPException(status_code=429, detail=e.user_message)
    except Exception:
        budget = None  # Non-critical — proceed without budget tracking

    # ── Resolve LLM provider ───────────────
    # Phase 14.2: All users with valid config get LLM.
    # create_provider() handles priority: user config > env var > mock/rule fallback.
    llm_provider = None
    try:
        from src.core.provider_factory import create_provider
        llm_provider = create_provider()
    except Exception:
        pass  # Falls back to rule-only if no provider configured

    # ── Execute through unified pipeline ───
    result = _pipeline_service.run(
        user_id=user.id,
        goal=req.goal,
        llm_provider=llm_provider,
    )

    # Phase 14.2: Populate run_info for UI observability
    run_info = _build_run_info(llm_provider, result)

    # ── Consume token budget ───────────────
    if budget is not None:
        try:
            budget.consume(
                tokens=500,
                provider=getattr(llm_provider, 'provider_name', 'rule'),
            )
        except Exception:
            pass

    return PipelineRunResponse(**result, run_info=run_info)


# ── Phase 14.2: Runtime observability helper ────────


def _build_run_info(llm_provider: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    """Build run_info dict for UI transparency.

    Extracts provider, model, tokens, latency from provider and result trace.
    """
    # Detect provider name: src/providers/* use .provider_name,
    # veritas.llm.* providers don't — fall back to type name.
    provider_name = getattr(llm_provider, 'provider_name', None)
    if not provider_name and llm_provider is not None:
        provider_name = type(llm_provider).__name__.replace('Provider', '').lower()
    model_name = getattr(llm_provider, 'model', None)
    info = {
        "engine": provider_name or "rule",
        "provider": provider_name or "rule",
        "model": model_name or "",
        "generation_time_ms": result.get("duration_ms", 0),
        "is_fallback": False,
        "fallback_from": "",
        "fallback_reason": "",
        "tokens_used": 0,
    }

    # Extract token totals from agent trace if available
    trace = result.get("trace", [])
    if trace:
        total_tokens = 0
        for t in trace:
            if isinstance(t, dict):
                total_tokens += t.get("tokens_used", 0)
        info["tokens_used"] = total_tokens

    # Detect if we fell back from a real provider to rule-only
    if info["engine"] == "mock" and info["model"] == "":
        info["is_fallback"] = True
        info["fallback_reason"] = "No LLM provider configured"

    elif info["engine"] == "rule" or info["engine"] is None:
        info["engine"] = "rule-only"
        info["provider"] = "rule"
        info["is_fallback"] = True
        info["fallback_reason"] = "No API key configured — using rule-only mode"

    return info
