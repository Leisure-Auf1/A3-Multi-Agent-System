"""
Phase 9.1 — Auth Manager

Handles registration, login, logout. Uses hashlib for password hashing.
Zero external dependencies (no bcrypt, no JWT).
"""
from __future__ import annotations

import hashlib
import uuid
import os
from datetime import datetime, timezone
from typing import Optional

from .models import AuthUser, AuthToken, RegisterRequest, LoginRequest
from .session import create_session, get_user_by_token, destroy_session
from ..data.db import (
    create_user, get_user_by_email, get_user_by_id, update_last_login,
)


def _hash_password(password: str, salt: str = "") -> tuple[str, str]:
    """Hash password with salt. Returns (hash, salt)."""
    if not salt:
        salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return h.hex(), salt


def _make_hash(password: str) -> str:
    """One-shot: generate salt and hash, return combined string."""
    salt = os.urandom(16).hex()
    h, _ = _hash_password(password, salt)
    return f"{salt}:{h}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify password against stored salt:hash string."""
    try:
        salt, expected_hash = stored.split(":", 1)
        actual_hash, _ = _hash_password(password, salt)
        return actual_hash == expected_hash
    except (ValueError, AttributeError):
        return False


def register(req: RegisterRequest) -> Optional[AuthToken]:
    """Register a new user. Returns token on success, None if email exists."""
    if not req.email or not req.password:
        return None
    if len(req.password) < 4:
        return None  # Minimum password length

    existing = get_user_by_email(req.email)
    if existing:
        return None  # Email already registered

    user_id = uuid.uuid4().hex[:12]
    password_hash = _make_hash(req.password)
    create_user(user_id, req.email, password_hash, req.display_name)

    user = AuthUser(
        id=user_id, email=req.email,
        display_name=req.display_name or req.email.split("@")[0],
        created_at=datetime.now(timezone.utc).isoformat(),
        is_guest=False,
    )
    token = create_session(user)
    return AuthToken(token=token, user_id=user_id,
                     display_name=user.display_name)


def login(req: LoginRequest) -> Optional[AuthToken]:
    """Login with email and password. Returns token on success."""
    if not req.email or not req.password:
        return None

    row = get_user_by_email(req.email)
    if not row:
        return None
    if not _verify_password(req.password, row["password_hash"]):
        return None

    update_last_login(row["id"])

    user = AuthUser(
        id=row["id"], email=row["email"],
        display_name=row["display_name"],
        created_at=row["created_at"],
        last_login_at=row.get("last_login_at"),
        is_guest=False,
    )
    token = create_session(user)
    return AuthToken(token=token, user_id=row["id"],
                     display_name=user.display_name)


def login_guest(display_name: str = "Guest") -> AuthToken:
    """Create a guest session (no password, no persistence)."""
    user_id = f"guest_{uuid.uuid4().hex[:8]}"
    user = AuthUser(
        id=user_id, email="", display_name=display_name,
        is_guest=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    token = create_session(user)
    return AuthToken(token=token, user_id=user_id,
                     display_name=display_name)


def logout(token: str) -> bool:
    """Destroy a session."""
    destroy_session(token)
    return True


def get_current_user(token: str) -> Optional[AuthUser]:
    """Validate token and return user."""
    return get_user_by_token(token)
