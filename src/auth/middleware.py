"""
Phase 9.1 / 9.6-A — Auth Middleware

FastAPI dependencies for authentication and authorization.
Supports Bearer token extraction, role-based guards, and permission checks.

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Depends, Request
from typing import Optional, Callable, List

from .auth_manager import get_current_user
from .models import AuthUser
from ..user.permission import PermissionManager, Role


async def require_auth(
    authorization: str = Header(None),
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
    authorization: str = Header(None),
) -> Optional[AuthUser]:
    """FastAPI dependency: extract user if token present, else None."""
    if not authorization:
        return None

    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    return get_current_user(token) if token else None


# ── Role-Based Guards (Phase 9.6-A) ──────────

def _get_user_role(user: AuthUser) -> str:
    """Resolve a user's role from the platform UserManager."""
    try:
        from ..user.manager import UserManager
        mgr = UserManager()
        u = mgr.get_user_by_email(user.email)
        if u:
            return u.role
    except Exception:
        pass
    # Fallback for auth users not in platform registry
    if user.is_guest:
        return Role.FREE
    return Role.FREE


def require_role(*allowed_roles: str):
    """FastAPI dependency factory: require one of the given roles.

    Usage:
        @router.get("/admin")
        def admin_panel(user: AuthUser = Depends(require_role("admin"))):
            ...
    """
    async def _guard(user: AuthUser = Depends(require_auth)) -> AuthUser:
        role = _get_user_role(user)
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' not allowed. Required: {', '.join(allowed_roles)}",
            )
        return user
    return _guard


def require_pro():
    """FastAPI dependency: require PRO role or above."""
    return require_role(Role.PRO, Role.TEACHER, Role.ADMIN)


def require_teacher_or_admin():
    """FastAPI dependency: require TEACHER or ADMIN role."""
    return require_role(Role.TEACHER, Role.ADMIN)


def require_admin():
    """FastAPI dependency: require ADMIN role."""
    return require_role(Role.ADMIN)


def require_multimodal_access():
    """FastAPI dependency: require a role with multimodal access."""
    async def _guard(user: AuthUser = Depends(require_auth)) -> AuthUser:
        role = _get_user_role(user)
        perm = PermissionManager.get_permission_for_role_str(role)
        if not perm.multimodal_access:
            raise HTTPException(
                status_code=403,
                detail=f"Multimodal access requires PRO or above. Current role: {role}",
            )
        return user
    return _guard


def require_model_access(model_provider: str):
    """FastAPI dependency factory: require access to a specific model provider.

    Usage:
        @router.post("/generate")
        def generate(
            user: AuthUser = Depends(require_model_access("openai"))
        ):
            ...
    """
    async def _guard(user: AuthUser = Depends(require_auth)) -> AuthUser:
        role = _get_user_role(user)
        if not PermissionManager.can_use_model(model_provider, Role(role)):
            raise HTTPException(
                status_code=403,
                detail=f"Model '{model_provider}' not available for role '{role}'",
            )
        return user
    return _guard


def check_token_limit(estimated_tokens: int = 0):
    """FastAPI dependency: check if user has enough token budget.

    Usage:
        @router.post("/chat")
        def chat(
            user: AuthUser = Depends(check_token_limit(500))
        ):
            ...
    """
    async def _guard(user: AuthUser = Depends(require_auth)) -> AuthUser:
        try:
            from ..platform.token_budget import TokenBudgetManager
            tbm = TokenBudgetManager(user.id)
            tbm.check_available(estimated_tokens)
        except Exception as e:
            raise HTTPException(status_code=429, detail=str(e))
        return user
    return _guard
