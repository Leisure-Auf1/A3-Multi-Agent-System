"""
Phase 9.1 — Session Store

In-memory token-to-user mapping. Tokens are UUIDs.
For production, replace with Redis or JWT.
"""
from __future__ import annotations

import time
from typing import Optional, Dict
from .models import AuthUser


# In-memory session store: {token: {user, expires_at}}
_sessions: Dict[str, dict] = {}

TOKEN_EXPIRY_SECONDS = 86400  # 24 hours


def create_session(user: AuthUser) -> str:
    """Create a session for a user, return token."""
    import uuid
    token = uuid.uuid4().hex
    _sessions[token] = {
        "user": user,
        "expires_at": time.time() + TOKEN_EXPIRY_SECONDS,
    }
    return token


def get_user_by_token(token: str) -> Optional[AuthUser]:
    """Validate token and return user, or None if expired/invalid."""
    session = _sessions.get(token)
    if session is None:
        return None
    if time.time() > session["expires_at"]:
        del _sessions[token]
        return None
    return session["user"]


def destroy_session(token: str):
    """Remove a session. Idempotent."""
    _sessions.pop(token, None)


def cleanup_expired():
    """Remove all expired sessions."""
    now = time.time()
    expired = [t for t, s in _sessions.items() if now > s["expires_at"]]
    for t in expired:
        del _sessions[t]
