"""
Phase 9.1 / PR #2.1 — Session Store (SQLite-backed)

Persistent token-to-user mapping via SQLite sessions table.
Zero external dependencies — reuses existing db.py infrastructure.
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from src.data.db import _get_conn
from .models import AuthUser

TOKEN_EXPIRY_SECONDS = 86400  # 24 hours


def create_session(user: AuthUser) -> str:
    """Create a persistent session for a user, return token."""
    token = uuid.uuid4().hex
    expires_at = time.time() + TOKEN_EXPIRY_SECONDS
    conn = _get_conn()
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at, created_at) "
        "VALUES (?, ?, ?, ?)",
        (token, user.id, expires_at, time.time()))
    conn.commit()
    return token


def get_user_by_token(token: str) -> Optional[AuthUser]:
    """Validate token and return user, or None if expired/invalid."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT u.id, u.email, u.display_name, u.is_guest, u.created_at, "
        "u.last_login_at, s.expires_at "
        "FROM sessions s JOIN users u ON s.user_id = u.id "
        "WHERE s.token = ?", (token,)).fetchone()

    if row is None:
        return None

    if time.time() > row["expires_at"]:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return None

    return AuthUser(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        is_guest=bool(row["is_guest"]),
        created_at=row["created_at"],
        last_login_at=row["last_login_at"],
    )


def destroy_session(token: str):
    """Remove a session. Idempotent."""
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()


def cleanup_expired():
    """Remove all expired sessions."""
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))
    conn.commit()
