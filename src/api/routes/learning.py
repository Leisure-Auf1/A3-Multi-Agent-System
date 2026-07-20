"""Phase 4.2.5 — API Routes: Learning Plan

⚠️ DEPRECATED — use POST /api/v2/learning/run instead.
This v1 endpoint is frozen and will be removed in a future release.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.api.schemas import LearningPlanRequest, LearningPlanResponse
from src.api.dependencies import get_workflow
from src.auth.middleware import require_auth
from src.auth.models import AuthUser

router = APIRouter(prefix="/api/v1/learning", tags=["learning"], deprecated=True)


@router.post(
    "/plan",
    summary="⚠️ DEPRECATED — 生成个性化学习计划",
    description=(
        "⚠️ DEPRECATED: 请迁移到 POST /api/v2/learning/run。\n\n"
        "提交学习目标，触发完整多 Agent 协作管道 "
        "(ProfileAgent → PlannerAgent → ResourceAgent → Review → ReflectionAgent → Memory)。"
    ),
)
def create_learning_plan(
    req: LearningPlanRequest,
    user: AuthUser = Depends(require_auth),
) -> JSONResponse:
    """
    POST /api/v1/learning/plan

    ⚠️ DEPRECATED — use POST /api/v2/learning/run instead.

    触发 A3Workflow.run() 完整 pipeline。
    Agent 层、Memory 层、EventBus 机制不做任何修改。
    """
    if not req.goal.strip():
        raise HTTPException(status_code=422, detail="goal 不能为空")

    try:
        workflow = get_workflow(
            provider_mode=req.provider,
            student_id=req.student_id,
        )

        result = workflow.run(
            user_goal=req.goal,
            user_profile=req.profile,
            knowledge_gaps=req.knowledge_gaps or [],
            session_id=f"api_{req.student_id}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {exc}",
        )

    result_dict = result.to_dict()

    response = JSONResponse(content=LearningPlanResponse(
        success=result.success,
        session_id=result.context.session_id,
        profile=result_dict.get("profile"),
        learning_plan=result_dict.get("learning_plan"),
        resources=result_dict.get("resources"),
        evaluation=result_dict.get("evaluation"),
        reflection=result_dict.get("reflection"),
        trace=result_dict.get("trace"),
        memory_saved=result.memory_saved,
        total_duration_ms=result.total_duration_ms,
        errors=result.errors,
    ).model_dump())
    response.headers["X-Deprecated-API"] = "true"
    response.headers["X-Migration-Path"] = "/api/v2/learning/run"
    response.headers["Sunset"] = "2026-09-01"
    return response
