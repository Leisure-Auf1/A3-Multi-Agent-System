"""
Phase 9.4 — Learning Path API

POST   /api/v2/learning/plan     (PlannerAgent)
GET    /api/v2/learning/history
GET    /api/v2/learning/stats
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.auth.middleware import require_auth
from src.auth.models import AuthUser
from src.agents.planner_agent import PlannerAgent
from src.data.learning_records import get_history, get_stats

router = APIRouter(prefix="/api/v2/learning", tags=["learning"])


class LearningPlanRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=500)
    profile: Dict[str, Any] = Field(default_factory=dict)
    knowledge_gaps: List[str] = Field(default_factory=list)


class PlanNodeResponse(BaseModel):
    title: str
    concepts: List[str]
    order: int
    estimated_hours: float = 1.0
    resources: List[str] = Field(default_factory=list)


class LearningPlanResponse(BaseModel):
    topic: str
    nodes: List[PlanNodeResponse]
    total_estimated_hours: float
    difficulty: str


class LearningRecordResponse(BaseModel):
    id: str
    agent: str
    action: str
    course_id: str
    score: float
    created_at: str


class LearningStatsResponse(BaseModel):
    total_sessions: int
    avg_score: float
    total_duration_ms: int


@router.post("/plan", response_model=LearningPlanResponse)
def generate_learning_plan(
    req: LearningPlanRequest,
    user: AuthUser = Depends(require_auth),
):
    """Generate a personalized learning plan."""
    agent = PlannerAgent()
    plan = agent.plan(
        profile=req.profile,
        goal_text=req.goal,
    )

    nodes = []
    if hasattr(plan, 'nodes'):
        for n in plan.nodes:
            nodes.append(PlanNodeResponse(
                title=getattr(n, 'title', str(n)),
                concepts=getattr(n, 'concepts', []),
                order=getattr(n, 'order', 0),
                estimated_hours=getattr(n, 'estimated_hours', 1.0),
                resources=getattr(n, 'resources', []),
            ))

    return LearningPlanResponse(
        topic=getattr(plan, 'topic', req.goal),
        nodes=nodes,
        total_estimated_hours=getattr(plan, 'estimated_hours', len(nodes)),
        difficulty=getattr(plan, 'difficulty', 'beginner'),
    )


@router.get("/history", response_model=List[LearningRecordResponse])
def get_learning_history(user: AuthUser = Depends(require_auth)):
    return [
        LearningRecordResponse(
            id=r["id"], agent=r["agent"], action=r["action"],
            course_id=r.get("course_id", ""), score=r.get("score", 0.0),
            created_at=r["created_at"],
        )
        for r in get_history(user.id)
    ]


@router.get("/stats", response_model=LearningStatsResponse)
def get_learning_stats(user: AuthUser = Depends(require_auth)):
    return LearningStatsResponse(**get_stats(user.id))
