"""
Phase 9.4 — Student Profile API

GET    /api/v2/profile
PUT    /api/v2/profile
POST   /api/v2/profile/assess   (ProfileAgent analysis)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from src.auth.middleware import require_auth
from src.auth.models import AuthUser
from src.agents.profile_agent import ProfileAgent
from src.data.student_store import save_profile, get_profile

router = APIRouter(prefix="/api/v2/profile", tags=["profile"])


# ── Schemas ────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    profile: Dict[str, Any] = Field(default_factory=dict)


class ProfileAssessRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=2000)


class ProfileResponse(BaseModel):
    user_id: str
    profile: Dict[str, Any]
    source: str = "stored"  # stored | rule | llm


# ── Routes ─────────────────────────────────────────────────

@router.get("", response_model=ProfileResponse)
def get_student_profile(user: AuthUser = Depends(require_auth)):
    """Get the current user's student profile."""
    stored = get_profile(user.id)
    if stored:
        return ProfileResponse(user_id=user.id, profile=stored, source="stored")
    # Return empty profile with defaults
    return ProfileResponse(
        user_id=user.id,
        profile=ProfileAgent.DEFAULTS,
        source="stored",
    )


@router.put("", response_model=ProfileResponse)
def update_student_profile(
    req: ProfileUpdate,
    user: AuthUser = Depends(require_auth),
):
    """Update the student profile."""
    save_profile(user.id, req.profile)
    return ProfileResponse(user_id=user.id, profile=req.profile, source="stored")


@router.post("/assess", response_model=ProfileResponse)
def assess_student_profile(
    req: ProfileAssessRequest,
    user: AuthUser = Depends(require_auth),
):
    """⚠️ LEGACY — Direct agent call. Migrate to POST /api/v2/learning/run.

    Analyze student description and return profile assessment.
    """
    from fastapi.responses import JSONResponse
    agent = ProfileAgent()
    result = agent.extract(req.text)
    profile = result.to_dict() if hasattr(result, 'to_dict') else {}
    # Auto-save the assessed profile
    save_profile(user.id, profile)
    resp = JSONResponse(content=ProfileResponse(
        user_id=user.id, profile=profile, source="rule"
    ).model_dump())
    resp.headers["X-Deprecated-API"] = "true"
    resp.headers["X-Migration-Path"] = "/api/v2/learning/run"
    return resp
