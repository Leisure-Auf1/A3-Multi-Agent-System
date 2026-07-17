"""
Phase 9.1 — Auth API Routes

POST /api/v2/auth/register
POST /api/v2/auth/login
POST /api/v2/auth/guest
POST /api/v2/auth/logout
GET  /api/v2/auth/me
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional

from src.auth import (
    AuthUser, AuthToken, RegisterRequest, LoginRequest,
    register, login, login_guest, logout,
)
from src.auth.middleware import require_auth

router = APIRouter(prefix="/api/v2/auth", tags=["auth"])


# ── Request/Response Schemas ──────────────────────────────

class RegisterBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=4, max_length=128)
    display_name: str = Field(default="", max_length=60)


class LoginBody(BaseModel):
    email: str
    password: str


class GuestBody(BaseModel):
    display_name: str = Field(default="Guest", max_length=60)


class TokenResponse(BaseModel):
    token: str
    user_id: str
    display_name: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: str = ""
    last_login_at: Optional[str] = None
    is_guest: bool = False


# ── Routes ────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def auth_register(body: RegisterBody) -> TokenResponse:
    """Register a new user account."""
    result = register(RegisterRequest(
        email=body.email,
        password=body.password,
        display_name=body.display_name,
    ))
    if result is None:
        raise HTTPException(status_code=409, detail="Email already registered")
    return TokenResponse(
        token=result.token,
        user_id=result.user_id,
        display_name=result.display_name,
    )


@router.post("/login", response_model=TokenResponse)
def auth_login(body: LoginBody) -> TokenResponse:
    """Login with email and password."""
    result = login(LoginRequest(email=body.email, password=body.password))
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(
        token=result.token,
        user_id=result.user_id,
        display_name=result.display_name,
    )


@router.post("/guest", response_model=TokenResponse)
def auth_guest(body: GuestBody = GuestBody()) -> TokenResponse:
    """Create a guest session (no registration required)."""
    result = login_guest(body.display_name)
    return TokenResponse(
        token=result.token,
        user_id=result.user_id,
        display_name=result.display_name,
    )


@router.post("/logout")
def auth_logout(
    authorization: str = Header(...),
    user: AuthUser = Depends(require_auth),
):
    """Logout (destroy session)."""
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    logout(token) if token else None
    return {"success": True}


@router.get("/me", response_model=UserResponse)
def auth_me(user: AuthUser = Depends(require_auth)) -> UserResponse:
    """Get current user info."""
    return UserResponse(**user.to_dict())
