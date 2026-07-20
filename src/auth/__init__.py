"""Phase 9.1 / 9.6-A / 9.6-B — Auth Package"""
from .models import AuthUser, AuthToken, RegisterRequest, LoginRequest, UserToken
from .auth_manager import register, login, login_guest, logout, get_current_user
from .middleware import require_auth, optional_auth
from .password import hash_password, verify_password, make_password_hash, generate_salt
from .jwt_manager import JWTManager
from .api_keys import ApiKeyManager, ApiKeyRecord
from .context import RequestContext, CurrentUser, CurrentPlan, CurrentPermission, build_context

# Role-based guards (Phase 9.6-A) — lazy import to avoid circular deps
def _lazy_import_middleware_guards():
    from .middleware import (
        require_role, require_pro, require_teacher_or_admin, require_admin,
        require_multimodal_access, require_model_access, check_token_limit,
    )
    return locals()

__all__ = [
    # Models
    "AuthUser", "AuthToken", "RegisterRequest", "LoginRequest", "UserToken",
    # Auth manager
    "register", "login", "login_guest", "logout", "get_current_user",
    # Middleware
    "require_auth", "optional_auth",
    # Password
    "hash_password", "verify_password", "make_password_hash", "generate_salt",
    # JWT
    "JWTManager",
]
