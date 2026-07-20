"""
Phase 9.5-B — User Profile Manager

Unified user profile aggregating:
  - Learning profile (from Veritas-Core MemoryManager)
  - Model preferences (from UserPreferenceManager)
  - Usage statistics (from TokenBudgetManager)
  - Workspace info (from WorkspaceManager)

Architecture: does NOT modify Veritas-Core or src/core/.
Reuses: WorkspaceManager, TokenBudgetManager, UserPreferenceManager
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import User
from .permission import PermissionManager, Role


@dataclass
class UsageStats:
    """Aggregated usage statistics for a user."""
    total_tokens_used: int = 0
    daily_requests: int = 0
    total_sessions: int = 0
    active_sessions: int = 0
    storage_bytes: int = 0
    total_artifacts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tokens_used": self.total_tokens_used,
            "daily_requests": self.daily_requests,
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "storage_bytes": self.storage_bytes,
            "total_artifacts": self.total_artifacts,
        }


@dataclass
class UserProfile:
    """Complete user profile with learning history and preferences."""
    user_id: str
    username: str
    email: str
    role: str
    display_name: str
    created_at: str
    usage: UsageStats = field(default_factory=UsageStats)
    model_preferences: Dict[str, Any] = field(default_factory=dict)
    learning_profile: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "usage": self.usage.to_dict(),
            "model_preferences": self.model_preferences,
            "learning_profile": self.learning_profile,
            "permissions": self.permissions,
        }


class UserProfileManager:
    """Unified profile manager for platform users.

    Wraps existing managers to provide a single entry point for
    user profile queries. Does NOT duplicate storage — delegates
    to existing managers.

    Usage:
        pm = UserProfileManager("usr_abc123")
        profile = pm.get_full_profile()
        stats = pm.get_usage_stats()
    """

    def __init__(self, user_id: str):
        self.user_id = user_id

    def get_full_profile(self) -> UserProfile:
        """Build complete user profile from all sources."""
        from .manager import UserManager

        um = UserManager()
        user = um.get_user(self.user_id)
        if user is None:
            # Return minimal profile for unknown users
            return UserProfile(
                user_id=self.user_id,
                username="unknown",
                email="",
                role=Role.FREE,
                display_name="Unknown User",
                created_at="",
                permissions=self._get_permissions_dict(Role.FREE),
            )

        return UserProfile(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            display_name=user.display_name,
            created_at=user.created_at,
            usage=self.get_usage_stats(),
            model_preferences=self._get_model_preferences(),
            learning_profile=self._get_learning_profile(),
            permissions=self._get_permissions_dict(user.role),
        )

    def get_usage_stats(self) -> UsageStats:
        """Collect usage stats from TokenBudgetManager and WorkspaceManager."""
        stats = UsageStats()

        # Token budget
        try:
            from src.platform.token_budget import TokenBudgetManager
            tbm = TokenBudgetManager(self.user_id)
            budget = tbm.get_budget()
            stats.total_tokens_used = budget.used_tokens
        except Exception:
            pass

        # Session count
        try:
            from src.session.manager import SessionManager
            sm = SessionManager()
            sessions = sm.list_sessions(self.user_id)
            stats.total_sessions = len(sessions)
            stats.active_sessions = sum(1 for s in sessions if s.is_active)
        except Exception:
            pass

        # Workspace storage
        try:
            from src.workspace.manager import WorkspaceManager
            wm = WorkspaceManager()
            info = wm.get_workspace_info(self.user_id)
            stats.storage_bytes = info.total_size_bytes
            stats.total_artifacts = sum(info.artifact_counts.values())
        except Exception:
            pass

        return stats

    def _get_model_preferences(self) -> Dict[str, Any]:
        """Get user model preferences."""
        try:
            from src.orchestration.user_preferences import UserPreferenceManager
            upm = UserPreferenceManager(self.user_id)
            prefs = upm.get_all_preferences()
            return {
                task: {
                    "preferred_model": p.preferred_model,
                    "preferred_provider": p.preferred_provider,
                    "quality_score": p.quality_score,
                    "use_count": p.use_count,
                }
                for task, p in prefs.items()
            }
        except Exception:
            return {}

    def _get_learning_profile(self) -> Dict[str, Any]:
        """Get learning profile from Veritas-Core memory."""
        try:
            from veritas.memory import MemoryManager
            mm = MemoryManager()
            if mm.student_exists(self.user_id):
                sm = mm.get_student_memory(self.user_id)
                if sm:
                    return {
                        "weak_concepts": sm.weak_concepts,
                        "mastery_levels": sm.mastery_levels,
                        "total_sessions": len(sm.session_summaries),
                    }
            return {}
        except Exception:
            return {}

    def _get_permissions_dict(self, role_str: str) -> Dict[str, Any]:
        """Get permissions as a dict for the given role."""
        perm = PermissionManager.get_permission_for_role_str(role_str)
        return {
            "max_tokens": perm.max_tokens,
            "daily_requests": perm.daily_requests,
            "available_models": list(perm.available_models),
            "multimodal_access": perm.multimodal_access,
            "max_sessions": perm.max_sessions,
            "storage_limit_mb": perm.storage_limit_mb,
            "can_export": perm.can_export,
            "can_share": perm.can_share,
        }
