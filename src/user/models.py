"""
Phase 9.5-B — User Identity Models

Platform-level User model with status tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class User:
    """Platform-level user identity.

    This is the unified user model for the multi-user platform.
    It bridges the auth layer (SQLite users table) and the workspace layer.
    """
    user_id: str
    username: str
    email: str
    created_at: str = ""
    status: UserStatus = UserStatus.ACTIVE
    display_name: str = ""
    role: str = "free"                     # references src.user.permission.Role
    last_active_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @property
    def is_guest(self) -> bool:
        return self.user_id.startswith("guest_")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
            "status": self.status.value if isinstance(self.status, UserStatus) else self.status,
            "display_name": self.display_name,
            "role": self.role,
            "last_active_at": self.last_active_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "User":
        status = d.get("status", "active")
        if isinstance(status, str):
            try:
                status = UserStatus(status)
            except ValueError:
                status = UserStatus.ACTIVE
        return cls(
            user_id=d.get("user_id", ""),
            username=d.get("username", ""),
            email=d.get("email", ""),
            created_at=d.get("created_at", ""),
            status=status,
            display_name=d.get("display_name", ""),
            role=d.get("role", "free"),
            last_active_at=d.get("last_active_at", ""),
        )
