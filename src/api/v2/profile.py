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
    """Analyze student description and return profile assessment.

    Uses LLM provider if configured, falls back to rule-based extraction.
    """
    from fastapi.responses import JSONResponse
    from src.api.dependencies import get_llm_provider

    llm = get_llm_provider()
    agent = ProfileAgent()
    if llm is not None:
        agent.set_llm_provider(llm)
        result = agent.extract_with_provider(req.text)
    else:
        result = agent.extract(req.text)

    profile = result.to_dict() if hasattr(result, 'to_dict') else {}
    source = result.source if hasattr(result, 'source') else 'rule'
    save_profile(user.id, profile)
    resp = JSONResponse(content=ProfileResponse(
        user_id=user.id, profile=profile, source=source
    ).model_dump())
    return resp
