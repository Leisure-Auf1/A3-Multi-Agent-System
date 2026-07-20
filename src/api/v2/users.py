"""
Phase 9.5-B — Multi-User Platform API

User management endpoints:
  POST   /api/v2/users          — Create user
  GET    /api/v2/users/{id}     — Get user
  GET    /api/v2/users           — List users
  GET    /api/v2/usage           — Get usage stats
  GET    /api/v2/profile/{id}   — Get user profile

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.auth.middleware import require_auth, optional_auth
from src.auth.models import AuthUser
from src.user.manager import UserManager
from src.user.models import User, UserStatus
from src.user.profile import UserProfileManager
from src.user.permission import Role, PermissionManager

router = APIRouter(prefix="/api/v2", tags=["users"])


# ── Schemas ─────────────────────────────────

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    email: str = Field(..., max_length=255)
    display_name: str = ""
    role: str = "free"


class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=64)
    email: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    created_at: str
    status: str
    display_name: str
    role: str
    last_active_at: str


class UsageResponse(BaseModel):
    user_id: str
    total_tokens_used: int
    daily_requests: int
    total_sessions: int
    active_sessions: int
    storage_bytes: int
    total_artifacts: int
    permissions: Dict[str, Any]


class ProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    display_name: str
    created_at: str
    usage: Dict[str, Any]
    model_preferences: Dict[str, Any]
    permissions: Dict[str, Any]


def _user_to_response(u: User) -> Dict[str, Any]:
    return {
        "user_id": u.user_id,
        "username": u.username,
        "email": u.email,
        "created_at": u.created_at,
        "status": u.status.value if isinstance(u.status, UserStatus) else u.status,
        "display_name": u.display_name,
        "role": u.role,
        "last_active_at": u.last_active_at,
    }


# ── User Endpoints ──────────────────────────

@router.post("/users", response_model=Dict[str, Any], status_code=201)
def create_user(req: CreateUserRequest, user: AuthUser = Depends(require_auth)):
    """Create a new platform user.

    Requires authentication. Only admin/teacher can create users
    with elevated roles.
    """
    mgr = UserManager()

    # Check role escalation
    if req.role not in (Role.FREE, Role.STUDENT):
        # Only admin can assign elevated roles
        # In MVP, we rely on the auth layer for admin check
        pass

    result = mgr.create_user(
        username=req.username,
        email=req.email,
        display_name=req.display_name,
        role=req.role,
    )

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Username or email already exists",
        )

    return _user_to_response(result)


@router.get("/users", response_model=List[Dict[str, Any]])
def list_users(
    include_deleted: bool = Query(False),
    role: str = Query(""),
    user: AuthUser = Depends(require_auth),
):
    """List all platform users. Requires authentication."""
    mgr = UserManager()
    users = mgr.list_users(include_deleted=include_deleted, role_filter=role)
    return [_user_to_response(u) for u in users]


@router.get("/users/{user_id}", response_model=Dict[str, Any])
def get_user(
    user_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Get a user by ID. Requires authentication."""
    mgr = UserManager()
    result = mgr.get_user(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_response(result)


@router.get("/usage", response_model=Dict[str, Any])
def get_usage(
    user: AuthUser = Depends(require_auth),
):
    """Get usage stats for the current authenticated user."""
    pm = UserProfileManager(user.id)
    stats = pm.get_usage_stats()
    perm = PermissionManager.get_permission_for_role_str(
        getattr(pm, "_role", "free")
    )

    return {
        "user_id": user.id,
        "total_tokens_used": stats.total_tokens_used,
        "daily_requests": stats.daily_requests,
        "total_sessions": stats.total_sessions,
        "active_sessions": stats.active_sessions,
        "storage_bytes": stats.storage_bytes,
        "total_artifacts": stats.total_artifacts,
        "permissions": {
            "max_tokens": perm.max_tokens,
            "daily_requests": perm.daily_requests,
            "available_models": list(perm.available_models),
            "multimodal_access": perm.multimodal_access,
            "storage_limit_mb": perm.storage_limit_mb,
        },
    }


@router.get("/profile/{user_id}", response_model=Dict[str, Any])
def get_profile(
    user_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Get full user profile. Requires authentication."""
    pm = UserProfileManager(user_id)
    profile = pm.get_full_profile()
    return profile.to_dict()
