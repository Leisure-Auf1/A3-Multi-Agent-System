"""
Phase 9.5-B — Permission System

Role-based access control with resource-specific limits.

Role tiers:
  FREE     — Limited daily usage, basic models only
  STUDENT  — Moderate limits, educational models
  PRO      — High limits, all models, multimodal
  TEACHER  — Extended limits, batch operations
  ADMIN    — Unlimited, all operations

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class Role(str, Enum):
    """User role with hierarchical access levels."""
    FREE = "free"
    STUDENT = "student"
    PRO = "pro"
    TEACHER = "teacher"
    ADMIN = "admin"


@dataclass
class Permission:
    """Resource-specific permission limits for a role."""
    role: Role
    max_tokens: int = 100_000          # max tokens per day
    daily_requests: int = 20           # max API requests per day
    available_models: tuple = ("mock", "rule")  # accessible model providers
    multimodal_access: bool = False    # image/video/audio generation
    max_sessions: int = 5              # concurrent sessions
    storage_limit_mb: int = 50         # workspace storage limit
    can_export: bool = True
    can_share: bool = False


# ── Role Permission Definitions ────────

ROLE_PERMISSIONS: Dict[Role, Permission] = {
    Role.FREE: Permission(
        role=Role.FREE,
        max_tokens=100_000,
        daily_requests=20,
        available_models=("mock", "rule"),
        multimodal_access=False,
        max_sessions=5,
        storage_limit_mb=50,
        can_export=True,
        can_share=False,
    ),
    Role.STUDENT: Permission(
        role=Role.STUDENT,
        max_tokens=500_000,
        daily_requests=100,
        available_models=("mock", "rule", "deepseek", "qwen"),
        multimodal_access=False,
        max_sessions=15,
        storage_limit_mb=200,
        can_export=True,
        can_share=True,
    ),
    Role.PRO: Permission(
        role=Role.PRO,
        max_tokens=2_000_000,
        daily_requests=500,
        available_models=(
            "mock", "rule", "deepseek", "qwen",
            "openai", "anthropic", "google", "kimi", "grok", "spark",
        ),
        multimodal_access=True,
        max_sessions=50,
        storage_limit_mb=1000,
        can_export=True,
        can_share=True,
    ),
    Role.TEACHER: Permission(
        role=Role.TEACHER,
        max_tokens=5_000_000,
        daily_requests=1000,
        available_models=(
            "mock", "rule", "deepseek", "qwen",
            "openai", "anthropic", "google", "kimi", "grok", "spark",
        ),
        multimodal_access=True,
        max_sessions=100,
        storage_limit_mb=2000,
        can_export=True,
        can_share=True,
    ),
    Role.ADMIN: Permission(
        role=Role.ADMIN,
        max_tokens=50_000_000,
        daily_requests=10_000,
        available_models=(
            "mock", "rule", "deepseek", "qwen",
            "openai", "anthropic", "google", "kimi", "grok", "spark",
        ),
        multimodal_access=True,
        max_sessions=1000,
        storage_limit_mb=10_000,
        can_export=True,
        can_share=True,
    ),
}


class PermissionManager:
    """Query and enforce role-based permissions.

    Usage:
        pm = PermissionManager()
        perm = pm.get_permission(Role.PRO)
        pm.can_use_model("gpt-5.6", Role.FREE)  # → False
        pm.can_generate_multimodal(Role.PRO)      # → True
    """

    @staticmethod
    def get_permission(role: Role) -> Permission:
        """Get permission definition for a role."""
        return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Role.FREE])

    @staticmethod
    def get_permission_for_role_str(role_str: str) -> Permission:
        """Get permission from a role string (flexible parsing)."""
        try:
            role = Role(role_str)
        except ValueError:
            role = Role.FREE
        return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Role.FREE])

    @classmethod
    def can_use_model(cls, model_provider: str, role: Role) -> bool:
        """Check if a role can access a specific model provider."""
        perm = cls.get_permission(role)
        return model_provider in perm.available_models

    @classmethod
    def can_generate_multimodal(cls, role: Role) -> bool:
        """Check if role can generate images/video/audio."""
        return cls.get_permission(role).multimodal_access

    @classmethod
    def get_max_tokens(cls, role: Role) -> int:
        """Get daily token limit for a role."""
        return cls.get_permission(role).max_tokens

    @classmethod
    def get_daily_requests(cls, role: Role) -> int:
        """Get daily request limit for a role."""
        return cls.get_permission(role).daily_requests

    @classmethod
    def get_storage_limit(cls, role: Role) -> int:
        """Get storage limit in MB for a role."""
        return cls.get_permission(role).storage_limit_mb

    @classmethod
    def get_max_sessions(cls, role: Role) -> int:
        """Get max concurrent sessions for a role."""
        return cls.get_permission(role).max_sessions

    @classmethod
    def is_admin(cls, role: Role) -> bool:
        """Check if role has admin privileges."""
        return role == Role.ADMIN

    @classmethod
    def is_teacher_or_above(cls, role: Role) -> bool:
        """Check if role is teacher or admin."""
        return role in (Role.TEACHER, Role.ADMIN)

    @classmethod
    def compare_roles(cls, role_a: Role, role_b: Role) -> int:
        """Compare two roles. Returns -1/0/1 like cmp()."""
        order = [Role.FREE, Role.STUDENT, Role.PRO, Role.TEACHER, Role.ADMIN]
        a_idx = order.index(role_a) if role_a in order else 0
        b_idx = order.index(role_b) if role_b in order else 0
        if a_idx < b_idx:
            return -1
        if a_idx > b_idx:
            return 1
        return 0
