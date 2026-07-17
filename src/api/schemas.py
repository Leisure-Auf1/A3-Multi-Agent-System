"""
Phase 4.2.5 — API Schemas (Pydantic models)

Request/Response models for the API layer.
Reuses WorkflowResult shape for response consistency.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────────
# Request
# ──────────────────────────────────────────────

class LearningPlanRequest(BaseModel):
    """POST /api/v1/learning/plan 请求体"""

    goal: str = Field(
        ...,
        min_length=1,
        description="学习目标 (自然语言)",
        examples=["我想学习 Python Agent 开发"],
    )
    student_id: str = Field(
        default="api_user",
        description="学生 ID",
    )
    provider: str = Field(
        default="mock",
        description="LLM provider: mock | spark | rule | none",
        pattern="^(mock|spark|rule|none)$",
    )
    profile: Optional[Dict[str, str]] = Field(
        default=None,
        description="预置画像 (6维, 不传则从 goal 自动提取)",
    )
    knowledge_gaps: Optional[List[str]] = Field(
        default=None,
        description="知识缺口列表",
    )


# ──────────────────────────────────────────────
# Response (mirrors WorkflowResult.to_dict())
# ──────────────────────────────────────────────

class LearningPlanResponse(BaseModel):
    """POST /api/v1/learning/plan 响应体"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "session_id": "a3_session_1721000000",
                "profile": {
                    "profile": {"knowledge_base": "mid_level"},
                    "source": "llm",
                    "confidence": 0.9,
                },
                "learning_plan": {
                    "nodes": [],
                    "total_minutes": 120,
                    "metadata": {"planning_mode": "llm"},
                },
                "resources": [],
                "evaluation": {"score": 85, "passed": True},
                "reflection": {"success": True, "source": "llm"},
                "trace": [],
                "memory_saved": True,
                "total_duration_ms": 245.3,
                "errors": [],
            }
        }
    )

    success: bool
    session_id: str = ""
    profile: Optional[Dict[str, Any]] = None
    learning_plan: Optional[Dict[str, Any]] = None
    resources: Optional[List[Dict[str, Any]]] = None
    evaluation: Optional[Dict[str, Any]] = None
    reflection: Optional[Dict[str, Any]] = None
    trace: Optional[List[Dict[str, Any]]] = None
    memory_saved: bool = False
    total_duration_ms: float = 0.0
    errors: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """GET /health 响应体"""

    status: str = "ok"
