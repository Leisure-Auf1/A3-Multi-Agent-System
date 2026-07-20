"""
Phase 9.5-B — User Manager

CRUD operations for platform users.
Storage: workspace/.users/users.json (JSON file)

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import User, UserStatus
from .permission import Role


# ── Storage paths ──────────────────────

def _get_users_dir() -> Path:
    """Get path to user registry directory."""
    base = Path(os.path.expanduser("~/.a3-agent/workspace"))
    return base / ".users"


def _get_users_file() -> Path:
    """Get path to users.json registry."""
    return _get_users_dir() / "users.json"


def _ensure_users_dir() -> Path:
    d = _get_users_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_users() -> Dict[str, Dict[str, Any]]:
    """Load all users from registry."""
    f = _get_users_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, KeyError):
        return {}


def _save_users(users: Dict[str, Dict[str, Any]]) -> None:
    """Persist users to registry."""
    _ensure_users_dir()
    _get_users_file().write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── Manager ────────────────────────────

class UserManager:
    """Platform user manager with JSON file persistence.

    Usage:
        mgr = UserManager()
        user = mgr.create_user("alice", "alice@example.com")
        found = mgr.get_user(user.user_id)
        users = mgr.list_users()
    """

    def create_user(
        self,
        username: str,
        email: str,
        display_name: str = "",
        role: str = Role.FREE,
    ) -> Optional[User]:
        """Create a new platform user.

        Args:
            username: Unique username
            email: User email
            display_name: Display name (defaults to username)
            role: Role (free, student, pro, teacher, admin)

        Returns:
            User object or None if username/email already exists
        """
        if not username:
            return None

        users = _load_users()

        # Check uniqueness
        for uid, udata in users.items():
            if udata.get("username") == username:
                return None
            if udata.get("email") == email and email:
                return None

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        user = User(
            user_id=user_id,
            username=username,
            email=email,
            created_at=now,
            status=UserStatus.ACTIVE,
            display_name=display_name or username,
            role=role,
            last_active_at=now,
        )

        users[user_id] = user.to_dict()
        _save_users(users)
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        users = _load_users()
        data = users.get(user_id)
        if data is None:
            return None
        return User.from_dict(data)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        users = _load_users()
        for uid, udata in users.items():
            if udata.get("username") == username:
                return User.from_dict(udata)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        if not email:
            return None
        users = _load_users()
        for uid, udata in users.items():
            if udata.get("email") == email:
                return User.from_dict(udata)
        return None

    def delete_user(self, user_id: str) -> bool:
        """Delete a user (soft delete: sets status to DELETED).

        Returns True if user was found and deleted.
        """
        users = _load_users()
        if user_id not in users:
            return False
        users[user_id]["status"] = UserStatus.DELETED.value
        _save_users(users)
        return True

    def hard_delete_user(self, user_id: str) -> bool:
        """Permanently remove a user from the registry.

        Returns True if user was found and removed.
        """
        users = _load_users()
        if user_id not in users:
            return False
        del users[user_id]
        _save_users(users)
        return True

    def list_users(
        self,
        include_deleted: bool = False,
        role_filter: str = "",
    ) -> List[User]:
        """List all platform users.

        Args:
            include_deleted: Include soft-deleted users
            role_filter: Filter by role

        Returns:
            List of User objects
        """
        users = _load_users()
        result = []
        for uid, data in users.items():
            user = User.from_dict(data)
            if not include_deleted and user.status == UserStatus.DELETED:
                continue
            if role_filter and user.role != role_filter:
                continue
            result.append(user)
        return sorted(result, key=lambda u: u.created_at)

    def update_user(
        self,
        user_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        status: Optional[UserStatus] = None,
        role: Optional[str] = None,
    ) -> Optional[User]:
        """Update user fields. Returns updated User or None if not found."""
        users = _load_users()
        if user_id not in users:
            return None

        data = users[user_id]
        if username is not None:
            # Check uniqueness
            for uid, udata in users.items():
                if uid != user_id and udata.get("username") == username:
                    return None
            data["username"] = username
        if email is not None:
            data["email"] = email
        if display_name is not None:
            data["display_name"] = display_name
        if status is not None:
            data["status"] = status.value if isinstance(status, UserStatus) else status
        if role is not None:
            data["role"] = role

        _save_users(users)
        return User.from_dict(data)

    def set_user_active(self, user_id: str) -> Optional[User]:
        """Mark user as active and update last_active_at."""
        users = _load_users()
        if user_id not in users:
            return None
        users[user_id]["status"] = UserStatus.ACTIVE.value
        users[user_id]["last_active_at"] = datetime.now(timezone.utc).isoformat()
        _save_users(users)
        return User.from_dict(users[user_id])

    def user_count(self, include_deleted: bool = False) -> int:
        """Count users."""
        users = _load_users()
        if include_deleted:
            return len(users)
        return sum(
            1 for u in users.values()
            if u.get("status") != UserStatus.DELETED.value
        )

    def user_exists(self, user_id: str) -> bool:
        """Check if user exists and is active."""
        user = self.get_user(user_id)
        return user is not None and user.is_active
