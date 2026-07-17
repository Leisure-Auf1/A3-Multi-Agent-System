"""Phase 9.1 — Auth Package"""
from .models import AuthUser, AuthToken, RegisterRequest, LoginRequest
from .auth_manager import register, login, login_guest, logout, get_current_user
from .middleware import require_auth, optional_auth

__all__ = [
    "AuthUser", "AuthToken", "RegisterRequest", "LoginRequest",
    "register", "login", "login_guest", "logout", "get_current_user",
    "require_auth", "optional_auth",
]
