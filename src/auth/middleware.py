"""
Phase 9.1 — Auth Middleware

FastAPI dependency for extracting current user from request.
"""
from __future__ import annotations

from fastapi import Header, HTTPException, Depends
from typing import Optional

from .auth_manager import get_current_user
from .models import AuthUser


async def require_auth(
    authorization: Optional[str] = Header(None),
) -> AuthUser:
    """FastAPI dependency: extract user from Bearer token.

    Usage:
        @router.get("/me")
        def me(user: AuthUser = Depends(require_auth)):
            return user.to_dict()
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    user = get_current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


async def optional_auth(
    authorization: Optional[str] = Header(None),
) -> Optional[AuthUser]:
    """FastAPI dependency: extract user if token present, else None."""
    if not authorization:
        return None

    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    return get_current_user(token) if token else None
