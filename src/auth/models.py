"""
Phase 9.1 / 9.6-A — Auth Models

Dataclass contracts for the auth system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RegisterRequest:
    email: str
    password: str
    display_name: str = ""


@dataclass
class LoginRequest:
    email: str
    password: str


@dataclass
class AuthToken:
    token: str
    user_id: str
    display_name: str
    created_at: str = ""


@dataclass
class AuthUser:
    """User object returned after authentication."""
    id: str
    email: str
    display_name: str
    created_at: str = ""
    last_login_at: Optional[str] = None
    is_guest: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
            "is_guest": self.is_guest,
        }


# Re-export UserToken from jwt_manager for convenience
from .jwt_manager import UserToken  # noqa: E402, F401
