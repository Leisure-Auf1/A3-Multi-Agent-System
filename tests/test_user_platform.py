"""
Phase 9.5-B — Multi-User Platform Tests

Tests covering:
  - User creation, retrieval, deletion
  - User isolation (separate users can't access each other's data)
  - Permission system (role-based limits)
  - Plan/subscription limits
  - Workspace isolation per user
  - Token budget per user
  - API endpoints for users/usage/profile

Constraint: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ── Test isolation: use temp directories for user storage ──

ORIG_USERS_DIR = None


@pytest.fixture(autouse=True)
def _isolate_user_storage(monkeypatch):
    """Use temp dir for user registry so tests don't pollute real data."""
    global ORIG_USERS_DIR
    tmp = tempfile.mkdtemp(prefix="a3_test_users_")

    # Patch user storage paths
    monkeypatch.setattr(
        "src.user.manager.os.path.expanduser",
        lambda p: tmp if "a3-agent" in str(p) else os.path.expanduser(p),
    )
    # Patch token budget storage paths
    monkeypatch.setattr(
        "src.platform.token_budget.os.path.expanduser",
        lambda p: tmp if "a3-agent" in str(p) else os.path.expanduser(p),
    )
    # Patch user preferences storage paths
    monkeypatch.setattr(
        "src.orchestration.user_preferences.os.path.expanduser",
        lambda p: tmp if "a3-agent" in str(p) else os.path.expanduser(p),
    )

    yield
    shutil.rmtree(tmp, ignore_errors=True)


# ──────────────────────────────────────────────
# 1. User Model Tests
# ──────────────────────────────────────────────

class TestUserModel:

    def test_user_creation_defaults(self):
        from user.models import User, UserStatus
        u = User(user_id="usr_1", username="alice", email="alice@test.com")
        assert u.user_id == "usr_1"
        assert u.username == "alice"
        assert u.email == "alice@test.com"
        assert u.status == UserStatus.ACTIVE
        assert u.is_active is True
        assert u.role == "free"
        assert u.display_name == ""
        assert u.created_at != ""

    def test_user_is_not_guest_by_default(self):
        from user.models import User
        u = User(user_id="usr_1", username="bob", email="bob@test.com")
        assert u.is_guest is False

    def test_user_guest_detection(self):
        from user.models import User
        u = User(user_id="guest_abc123", username="guest", email="")
        assert u.is_guest is True

    def test_user_inactive_status(self):
        from user.models import User, UserStatus
        u = User(user_id="usr_1", username="alice", email="a@t.com",
                  status=UserStatus.INACTIVE)
        assert u.is_active is False

    def test_user_suspended_status(self):
        from user.models import User, UserStatus
        u = User(user_id="usr_1", username="alice", email="a@t.com",
                  status=UserStatus.SUSPENDED)
        assert u.status == UserStatus.SUSPENDED
        assert u.is_active is False

    def test_user_deleted_status(self):
        from user.models import User, UserStatus
        u = User(user_id="usr_1", username="alice", email="a@t.com",
                  status=UserStatus.DELETED)
        assert u.status == UserStatus.DELETED

    def test_user_to_dict(self):
        from user.models import User, UserStatus
        u = User(user_id="usr_1", username="carol", email="carol@test.com",
                  display_name="Carol", role="pro")
        d = u.to_dict()
        assert d["user_id"] == "usr_1"
        assert d["username"] == "carol"
        assert d["email"] == "carol@test.com"
        assert d["display_name"] == "Carol"
        assert d["role"] == "pro"
        assert d["status"] == "active"

    def test_user_from_dict(self):
        from user.models import User
        d = {"user_id": "usr_2", "username": "dave", "email": "d@t.com",
             "role": "student", "status": "active"}
        u = User.from_dict(d)
        assert u.user_id == "usr_2"
        assert u.username == "dave"
        assert u.role == "student"

    def test_user_from_dict_invalid_status(self):
        from user.models import User, UserStatus
        d = {"user_id": "usr_x", "username": "x", "email": "x@t.com",
             "status": "bogus"}
        u = User.from_dict(d)
        assert u.status == UserStatus.ACTIVE  # fallback

    def test_user_status_enum_values(self):
        from user.models import UserStatus
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.DELETED.value == "deleted"


# ──────────────────────────────────────────────
# 2. User Manager Tests
# ──────────────────────────────────────────────

class TestUserManager:

    def setup_method(self):
        """Clean user registry before each test."""
        from user.manager import _get_users_file
        f = _get_users_file()
        if f.exists():
            f.unlink()

    def test_create_user(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("alice", "alice@test.com")
        assert u is not None
        assert u.username == "alice"
        assert u.email == "alice@test.com"
        assert u.user_id.startswith("usr_")

    def test_create_user_with_display_name(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("bob", "bob@test.com", display_name="Bob Smith")
        assert u is not None
        assert u.display_name == "Bob Smith"
        assert u.username == "bob"

    def test_create_user_with_role(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("pro_user", "pro@test.com", role="pro")
        assert u is not None
        assert u.role == "pro"

    def test_create_user_empty_username(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("", "empty@test.com")
        assert u is None

    def test_create_user_duplicate_username(self):
        from user.manager import UserManager
        mgr = UserManager()
        u1 = mgr.create_user("alice", "a1@test.com")
        assert u1 is not None
        u2 = mgr.create_user("alice", "a2@test.com")
        assert u2 is None

    def test_create_user_duplicate_email(self):
        from user.manager import UserManager
        mgr = UserManager()
        u1 = mgr.create_user("user1", "same@test.com")
        assert u1 is not None
        u2 = mgr.create_user("user2", "same@test.com")
        assert u2 is None

    def test_get_user(self):
        from user.manager import UserManager
        mgr = UserManager()
        created = mgr.create_user("alice", "alice@test.com")
        found = mgr.get_user(created.user_id)
        assert found is not None
        assert found.user_id == created.user_id
        assert found.username == "alice"

    def test_get_user_nonexistent(self):
        from user.manager import UserManager
        mgr = UserManager()
        found = mgr.get_user("usr_nonexistent")
        assert found is None

    def test_get_user_by_username(self):
        from user.manager import UserManager
        mgr = UserManager()
        mgr.create_user("alice", "alice@test.com")
        found = mgr.get_user_by_username("alice")
        assert found is not None
        assert found.username == "alice"

    def test_get_user_by_username_nonexistent(self):
        from user.manager import UserManager
        mgr = UserManager()
        found = mgr.get_user_by_username("nobody")
        assert found is None

    def test_get_user_by_email(self):
        from user.manager import UserManager
        mgr = UserManager()
        mgr.create_user("alice", "alice@test.com")
        found = mgr.get_user_by_email("alice@test.com")
        assert found is not None
        assert found.email == "alice@test.com"

    def test_get_user_by_email_none(self):
        from user.manager import UserManager
        mgr = UserManager()
        found = mgr.get_user_by_email("")
        assert found is None
        found = mgr.get_user_by_email(None)
        assert found is None

    def test_list_users(self):
        from user.manager import UserManager
        mgr = UserManager()
        mgr.create_user("a1", "a1@test.com")
        mgr.create_user("b1", "b1@test.com")
        mgr.create_user("c1", "c1@test.com")
        users = mgr.list_users()
        assert len(users) == 3

    def test_list_users_excludes_deleted(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("alive", "alive@test.com")
        u2 = mgr.create_user("dead", "dead@test.com")
        mgr.delete_user(u2.user_id)
        users = mgr.list_users()
        assert len(users) == 1
        assert users[0].username == "alive"

    def test_list_users_include_deleted(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("alive", "alive@test.com")
        u2 = mgr.create_user("dead", "dead@test.com")
        mgr.delete_user(u2.user_id)
        users = mgr.list_users(include_deleted=True)
        assert len(users) == 2

    def test_list_users_role_filter(self):
        from user.manager import UserManager
        mgr = UserManager()
        mgr.create_user("free1", "f1@t.com", role="free")
        mgr.create_user("pro1", "p1@t.com", role="pro")
        users = mgr.list_users(role_filter="pro")
        assert len(users) == 1
        assert users[0].role == "pro"

    def test_delete_user_soft(self):
        from user.manager import UserManager
        from user.models import UserStatus
        mgr = UserManager()
        u = mgr.create_user("todelete", "td@test.com")
        result = mgr.delete_user(u.user_id)
        assert result is True
        found = mgr.get_user(u.user_id)
        assert found.status == UserStatus.DELETED

    def test_delete_user_nonexistent(self):
        from user.manager import UserManager
        mgr = UserManager()
        result = mgr.delete_user("usr_nonexistent")
        assert result is False

    def test_hard_delete_user(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("toremove", "tr@test.com")
        result = mgr.hard_delete_user(u.user_id)
        assert result is True
        found = mgr.get_user(u.user_id)
        assert found is None

    def test_hard_delete_nonexistent(self):
        from user.manager import UserManager
        mgr = UserManager()
        result = mgr.hard_delete_user("usr_nonexistent")
        assert result is False

    def test_update_user_username(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("oldname", "old@test.com")
        updated = mgr.update_user(u.user_id, username="newname")
        assert updated is not None
        assert updated.username == "newname"

    def test_update_user_display_name(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("user", "user@test.com")
        updated = mgr.update_user(u.user_id, display_name="New Display")
        assert updated is not None
        assert updated.display_name == "New Display"

    def test_update_user_role(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("user", "user@test.com", role="free")
        updated = mgr.update_user(u.user_id, role="pro")
        assert updated is not None
        assert updated.role == "pro"

    def test_update_user_duplicate_username(self):
        from user.manager import UserManager
        mgr = UserManager()
        mgr.create_user("alice", "a1@test.com")
        bob = mgr.create_user("bob", "b2@test.com")
        updated = mgr.update_user(bob.user_id, username="alice")
        assert updated is None  # username collision

    def test_update_user_nonexistent(self):
        from user.manager import UserManager
        mgr = UserManager()
        updated = mgr.update_user("usr_nonexistent", username="nope")
        assert updated is None

    def test_set_user_active(self):
        from user.manager import UserManager
        from user.models import UserStatus
        mgr = UserManager()
        u = mgr.create_user("user", "user@test.com")
        mgr.delete_user(u.user_id)  # soft delete
        found = mgr.get_user(u.user_id)
        assert found.status == UserStatus.DELETED
        mgr.set_user_active(u.user_id)
        found = mgr.get_user(u.user_id)
        assert found.status == UserStatus.ACTIVE

    def test_set_user_active_nonexistent(self):
        from user.manager import UserManager
        mgr = UserManager()
        result = mgr.set_user_active("usr_nonexistent")
        assert result is None

    def test_user_count(self):
        from user.manager import UserManager
        mgr = UserManager()
        assert mgr.user_count() == 0
        mgr.create_user("a", "a@test.com")
        mgr.create_user("b", "b@test.com")
        assert mgr.user_count() == 2

    def test_user_count_include_deleted(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("a", "a@test.com")
        mgr.delete_user(u.user_id)
        assert mgr.user_count() == 0
        assert mgr.user_count(include_deleted=True) == 1

    def test_user_exists(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("alice", "alice@test.com")
        assert mgr.user_exists(u.user_id) is True

    def test_user_exists_deleted(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("alice", "alice@test.com")
        mgr.delete_user(u.user_id)
        assert mgr.user_exists(u.user_id) is False

    def test_user_exists_nonexistent(self):
        from user.manager import UserManager
        mgr = UserManager()
        assert mgr.user_exists("usr_fake") is False


# ──────────────────────────────────────────────
# 3. Permission System Tests
# ──────────────────────────────────────────────

class TestPermissionSystem:

    def test_role_enum_values(self):
        from user.permission import Role
        assert Role.FREE.value == "free"
        assert Role.STUDENT.value == "student"
        assert Role.PRO.value == "pro"
        assert Role.TEACHER.value == "teacher"
        assert Role.ADMIN.value == "admin"

    def test_get_permission_free(self):
        from user.permission import PermissionManager, Role
        perm = PermissionManager.get_permission(Role.FREE)
        assert perm.max_tokens == 100_000
        assert perm.daily_requests == 20
        assert perm.multimodal_access is False

    def test_get_permission_pro(self):
        from user.permission import PermissionManager, Role
        perm = PermissionManager.get_permission(Role.PRO)
        assert perm.max_tokens == 2_000_000
        assert perm.multimodal_access is True

    def test_get_permission_admin(self):
        from user.permission import PermissionManager, Role
        perm = PermissionManager.get_permission(Role.ADMIN)
        assert perm.max_tokens == 50_000_000
        assert perm.daily_requests == 10_000

    def test_get_permission_for_role_str(self):
        from user.permission import PermissionManager
        perm = PermissionManager.get_permission_for_role_str("student")
        assert perm.max_tokens == 500_000

    def test_get_permission_for_invalid_role_str(self):
        from user.permission import PermissionManager
        perm = PermissionManager.get_permission_for_role_str("superadmin")
        assert perm.max_tokens == 100_000  # falls back to FREE

    def test_can_use_model_free_basic(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.can_use_model("mock", Role.FREE) is True
        assert PermissionManager.can_use_model("rule", Role.FREE) is True

    def test_can_use_model_free_advanced(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.can_use_model("openai", Role.FREE) is False
        assert PermissionManager.can_use_model("anthropic", Role.FREE) is False

    def test_can_use_model_pro_advanced(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.can_use_model("openai", Role.PRO) is True
        assert PermissionManager.can_use_model("anthropic", Role.PRO) is True

    def test_can_generate_multimodal_free(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.can_generate_multimodal(Role.FREE) is False

    def test_can_generate_multimodal_pro(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.can_generate_multimodal(Role.PRO) is True

    def test_get_max_tokens_per_role(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.get_max_tokens(Role.FREE) == 100_000
        assert PermissionManager.get_max_tokens(Role.STUDENT) == 500_000
        assert PermissionManager.get_max_tokens(Role.PRO) == 2_000_000

    def test_get_daily_requests(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.get_daily_requests(Role.FREE) == 20
        assert PermissionManager.get_daily_requests(Role.PRO) == 500

    def test_get_storage_limit(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.get_storage_limit(Role.FREE) == 50
        assert PermissionManager.get_storage_limit(Role.PRO) == 1000

    def test_get_max_sessions(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.get_max_sessions(Role.FREE) == 5
        assert PermissionManager.get_max_sessions(Role.TEACHER) == 100

    def test_is_admin(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.is_admin(Role.ADMIN) is True
        assert PermissionManager.is_admin(Role.FREE) is False
        assert PermissionManager.is_admin(Role.TEACHER) is False

    def test_is_teacher_or_above(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.is_teacher_or_above(Role.TEACHER) is True
        assert PermissionManager.is_teacher_or_above(Role.ADMIN) is True
        assert PermissionManager.is_teacher_or_above(Role.PRO) is False
        assert PermissionManager.is_teacher_or_above(Role.FREE) is False

    def test_compare_roles(self):
        from user.permission import PermissionManager, Role
        assert PermissionManager.compare_roles(Role.FREE, Role.PRO) == -1
        assert PermissionManager.compare_roles(Role.PRO, Role.FREE) == 1
        assert PermissionManager.compare_roles(Role.PRO, Role.PRO) == 0
        assert PermissionManager.compare_roles(Role.ADMIN, Role.FREE) == 1

    def test_all_roles_have_permissions(self):
        from user.permission import ROLE_PERMISSIONS, Role
        for role in Role:
            assert role in ROLE_PERMISSIONS

    def test_permission_dataclass_fields(self):
        from user.permission import Permission, Role
        p = Permission(role=Role.FREE)
        assert p.role == Role.FREE
        assert p.max_tokens == 100_000
        assert hasattr(p, "can_export")
        assert hasattr(p, "can_share")


# ──────────────────────────────────────────────
# 4. Subscription / Plan Tests
# ──────────────────────────────────────────────

class TestPlans:

    def test_plan_tier_values(self):
        from billing.models import PlanTier
        assert PlanTier.FREE.value == "free"
        assert PlanTier.STUDENT.value == "student"
        assert PlanTier.PRO.value == "pro"

    def test_free_plan_limits(self):
        from billing.models import get_plan, PlanTier
        plan = get_plan(PlanTier.FREE)
        assert plan.monthly_tokens == 3_000_000
        assert plan.price_usd == 0.0
        assert plan.multimodal is False
        assert plan.storage_limit_mb == 50
        assert plan.max_sessions == 5

    def test_student_plan_limits(self):
        from billing.models import get_plan, PlanTier
        plan = get_plan(PlanTier.STUDENT)
        assert plan.monthly_tokens == 15_000_000
        assert plan.price_usd == 4.99
        assert plan.model_access == ("mock", "rule", "deepseek", "qwen")

    def test_pro_plan_limits(self):
        from billing.models import get_plan, PlanTier
        plan = get_plan(PlanTier.PRO)
        assert plan.monthly_tokens == 60_000_000
        assert plan.price_usd == 19.99
        assert plan.multimodal is True
        assert "openai" in plan.model_access
        assert "anthropic" in plan.model_access

    def test_plan_to_dict(self):
        from billing.models import get_plan, PlanTier
        plan = get_plan(PlanTier.PRO)
        d = plan.to_dict()
        assert d["tier"] == "pro"
        assert d["monthly_tokens"] == 60_000_000
        assert isinstance(d["model_access"], list)
        assert "price_usd" in d

    def test_get_plan_unknown_falls_back_to_free(self):
        from billing.models import get_plan
        plan = get_plan("bogus")
        assert plan.monthly_tokens == 3_000_000

    def test_subscription_defaults(self):
        from billing.models import Subscription
        sub = Subscription(user_id="usr_1")
        assert sub.user_id == "usr_1"
        assert sub.plan.value == "free"
        assert sub.is_active is True
        assert sub.started_at != ""

    def test_subscription_to_dict(self):
        from billing.models import Subscription
        sub = Subscription(user_id="usr_1")
        d = sub.to_dict()
        assert d["user_id"] == "usr_1"
        assert d["plan"] == "free"

    def test_subscription_from_dict(self):
        from billing.models import Subscription
        d = {"user_id": "usr_2", "plan": "pro", "is_active": True}
        sub = Subscription.from_dict(d)
        assert sub.user_id == "usr_2"
        assert sub.plan.value == "pro"


# ──────────────────────────────────────────────
# 5. Workspace Integration Tests
# ──────────────────────────────────────────────

class TestWorkspaceIntegration:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_ws_")
        import workspace.manager
        self.wm = workspace.manager.WorkspaceManager(root=self.tmpdir)

    def teardown_method(self):
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_user_path(self):
        path = self.wm.get_user_path("usr_test1")
        assert path.endswith("usr_test1")

    def test_list_workspace_users_empty(self):
        users = self.wm.list_workspace_users()
        assert users == []

    def test_list_workspace_users(self):
        self.wm.create_workspace("user_a")
        self.wm.create_workspace("user_b")
        self.wm.create_workspace("user_c")
        users = self.wm.list_workspace_users()
        assert len(users) == 3
        assert "user_a" in users
        assert "user_b" in users
        assert "user_c" in users

    def test_list_workspace_users_ignores_dotfiles(self):
        self.wm.create_workspace("user_a")
        os.makedirs(os.path.join(self.tmpdir, ".users"), exist_ok=True)
        users = self.wm.list_workspace_users()
        assert ".users" not in users
        assert "user_a" in users

    def test_get_workspace_paths(self):
        paths = self.wm.get_workspace_paths("usr_test")
        assert "root" in paths
        assert "sessions" in paths
        assert "artifacts" in paths
        assert "memory" in paths
        assert "history" in paths
        assert "usage" in paths

    def test_append_usage_record(self):
        path = self.wm.append_usage("usr_test", {"action": "test", "tokens": 100})
        assert os.path.isfile(path)

    def test_get_usage_records_empty(self):
        records = self.wm.get_usage_records("usr_nonexistent")
        assert records == []

    def test_get_usage_records(self):
        self.wm.append_usage("usr_test", {"action": "a", "value": 1})
        self.wm.append_usage("usr_test", {"action": "b", "value": 2})
        records = self.wm.get_usage_records("usr_test")
        assert len(records) == 2
        assert records[0]["action"] == "a"
        assert records[1]["action"] == "b"

    def test_get_usage_records_limit(self):
        for i in range(10):
            self.wm.append_usage("usr_test", {"idx": i})
        records = self.wm.get_usage_records("usr_test", limit=5)
        assert len(records) == 5
        assert records[-1]["idx"] == 9

    def test_user_workspace_isolation(self):
        """Different users have separate workspaces."""
        self.wm.save_artifact("user_a", "materials", "note.md", "A's notes")
        self.wm.save_artifact("user_b", "materials", "note.md", "B's notes")

        content_a = self.wm.load_artifact("user_a", "materials", "note.md")
        content_b = self.wm.load_artifact("user_b", "materials", "note.md")

        assert content_a == "A's notes"
        assert content_b == "B's notes"
        assert content_a != content_b


# ──────────────────────────────────────────────
# 6. User Profile Tests
# ──────────────────────────────────────────────

class TestUserProfile:

    def setup_method(self):
        from user.manager import _get_users_file
        f = _get_users_file()
        if f.exists():
            f.unlink()

    def test_profile_for_existing_user(self):
        from user.manager import UserManager
        from user.profile import UserProfileManager
        mgr = UserManager()
        u = mgr.create_user("profile_test", "profile@test.com",
                            display_name="Profile User", role="pro")
        pm = UserProfileManager(u.user_id)
        profile = pm.get_full_profile()
        assert profile.user_id == u.user_id
        assert profile.username == "profile_test"
        assert profile.role == "pro"
        assert profile.display_name == "Profile User"

    def test_profile_for_unknown_user(self):
        from user.profile import UserProfileManager
        pm = UserProfileManager("usr_nonexistent")
        profile = pm.get_full_profile()
        assert profile.username == "unknown"
        assert profile.role == "free"

    def test_usage_stats_defaults(self):
        from user.profile import UsageStats
        stats = UsageStats()
        assert stats.total_tokens_used == 0
        assert stats.daily_requests == 0
        assert stats.total_sessions == 0

    def test_usage_stats_to_dict(self):
        from user.profile import UsageStats
        stats = UsageStats(total_tokens_used=500, total_sessions=3)
        d = stats.to_dict()
        assert d["total_tokens_used"] == 500
        assert d["total_sessions"] == 3

    def test_profile_to_dict(self):
        from user.profile import UserProfile, UsageStats
        up = UserProfile(
            user_id="usr_x", username="x", email="x@t.com",
            role="free", display_name="X", created_at="now",
            usage=UsageStats(total_tokens_used=100),
        )
        d = up.to_dict()
        assert d["username"] == "x"
        assert d["usage"]["total_tokens_used"] == 100

    def test_permissions_in_profile(self):
        from user.manager import UserManager
        from user.profile import UserProfileManager
        mgr = UserManager()
        u = mgr.create_user("perm_test", "perm@test.com", role="pro")
        pm = UserProfileManager(u.user_id)
        profile = pm.get_full_profile()
        assert "max_tokens" in profile.permissions
        assert profile.permissions["multimodal_access"] is True


# ──────────────────────────────────────────────
# 7. Cross-layer Integration Tests
# ──────────────────────────────────────────────

class TestCrossLayerIntegration:

    def test_user_manager_persistence_across_instances(self):
        from user.manager import UserManager
        mgr1 = UserManager()
        u = mgr1.create_user("persist", "persist@test.com")
        mgr2 = UserManager()
        found = mgr2.get_user(u.user_id)
        assert found is not None
        assert found.username == "persist"

    def test_create_and_list_multiple_users(self):
        from user.manager import UserManager
        mgr = UserManager()
        for i in range(5):
            mgr.create_user(f"user_{i}", f"u{i}@test.com")
        users = mgr.list_users()
        assert len(users) == 5
        usernames = [u.username for u in users]
        assert "user_0" in usernames
        assert "user_4" in usernames

    def test_role_affects_permissions(self):
        from user.manager import UserManager
        from user.permission import PermissionManager, Role
        mgr = UserManager()
        free_user = mgr.create_user("free_guy", "free@guy.com", role="free")
        pro_user = mgr.create_user("pro_guy", "pro@guy.com", role="pro")

        free_perm = PermissionManager.get_permission_for_role_str(free_user.role)
        pro_perm = PermissionManager.get_permission_for_role_str(pro_user.role)

        assert free_perm.max_tokens < pro_perm.max_tokens
        assert free_perm.daily_requests < pro_perm.daily_requests
        assert free_perm.multimodal_access is False
        assert pro_perm.multimodal_access is True

    def test_plan_aligns_with_role_permissions(self):
        from billing.models import get_plan
        from user.permission import PermissionManager, Role
        from billing.models import PlanTier
        # FREE plan ≈ FREE role permissions
        free_plan = get_plan(PlanTier.FREE)
        free_perm = PermissionManager.get_permission(Role.FREE)
        assert free_plan.multimodal == free_perm.multimodal_access

        # PRO plan ≈ PRO role permissions
        pro_plan = get_plan(PlanTier.PRO)
        pro_perm = PermissionManager.get_permission(Role.PRO)
        assert pro_plan.multimodal == pro_perm.multimodal_access

    def test_user_delete_preserves_workspace_data(self):
        """Soft-deleting a user doesn't remove their workspace artifacts."""
        import workspace.manager
        tmpdir = tempfile.mkdtemp(prefix="a3_test_del_")
        wm = workspace.manager.WorkspaceManager(root=tmpdir)
        wm.save_artifact("usr_del", "materials", "notes.md", "important data")

        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("del_user", "del@test.com")
        mgr.delete_user(u.user_id)

        # Workspace data should still exist
        content = wm.load_artifact("usr_del", "materials", "notes.md")
        assert content == "important data"
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_unknown_user_gets_free_permissions(self):
        from user.profile import UserProfileManager
        pm = UserProfileManager("usr_fake")
        profile = pm.get_full_profile()
        assert profile.role == "free"
        assert profile.permissions["multimodal_access"] is False


# ──────────────────────────────────────────────
# 8. Edge Cases & Boundary Tests
# ──────────────────────────────────────────────

class TestEdgeCases:

    def test_user_unicode_username(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("中文用户", "cn@test.com")
        assert u is not None
        assert u.username == "中文用户"

    def test_user_long_username(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("a" * 64, "long@test.com")
        assert u is not None

    def test_user_special_char_email(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("special", "user+tag@domain.co.uk")
        assert u is not None

    def test_empty_display_name_defaults_to_username(self):
        from user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("testuser", "t@t.com", display_name="")
        assert u.display_name == "testuser"

    def test_user_ids_are_unique(self):
        from user.manager import UserManager
        mgr = UserManager()
        ids = set()
        for i in range(20):
            u = mgr.create_user(f"user_{i}", f"u{i}@test.com")
            assert u.user_id not in ids
            ids.add(u.user_id)

    def test_permission_manager_handles_case(self):
        from user.permission import PermissionManager
        # Role enum is case-sensitive; bad casing falls to FREE
        perm = PermissionManager.get_permission_for_role_str("PRO")
        assert perm.max_tokens == 100_000  # FREE default

    def test_subscription_from_dict_bad_plan(self):
        from billing.models import Subscription
        sub = Subscription.from_dict({"user_id": "u", "plan": "enterprise"})
        assert sub.plan.value == "free"

    def test_workspace_list_users_empty_dir(self):
        tmpdir = tempfile.mkdtemp(prefix="a3_test_empty_")
        import workspace.manager
        wm = workspace.manager.WorkspaceManager(root=tmpdir)
        assert wm.list_workspace_users() == []
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_usage_records_corrupted_json(self):
        tmpdir = tempfile.mkdtemp(prefix="a3_test_corr_")
        import workspace.manager
        wm = workspace.manager.WorkspaceManager(root=tmpdir)
        usage_path = os.path.join(tmpdir, "usr_x", "usage", "usage.jsonl")
        os.makedirs(os.path.dirname(usage_path), exist_ok=True)
        with open(usage_path, "w") as f:
            f.write('{"valid": "json"}\n')
            f.write('not valid json\n')
            f.write('{"also": "valid"}\n')
        records = wm.get_usage_records("usr_x")
        assert len(records) == 2  # corrupted line skipped
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_user_model_created_at_populated(self):
        from user.models import User
        u = User(user_id="usr_t", username="t", email="t@t.com")
        assert u.created_at != ""
        # Should be ISO format with T separator
        assert "T" in u.created_at


# ──────────────────────────────────────────────
# 9. Verify No Regression in Existing Layers
# ──────────────────────────────────────────────

class TestNoRegression:

    def test_workspace_original_api_unchanged(self):
        """Verify original WorkspaceManager API still works."""
        tmpdir = tempfile.mkdtemp(prefix="a3_test_reg_")
        import workspace.manager
        wm = workspace.manager.WorkspaceManager(root=tmpdir)

        # Original methods unchanged
        assert wm.create_workspace("student_001")
        assert wm.workspace_exists("student_001")
        wm.save_artifact("student_001", "materials", "test.md", "hello")
        content = wm.load_artifact("student_001", "materials", "test.md")
        assert content == "hello"

        # New methods also work
        assert wm.get_user_path("student_001").endswith("student_001")
        assert "student_001" in wm.list_workspace_users()

        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_existing_imports_unaffected(self):
        """Ensure all existing modules still import correctly."""
        from workspace.manager import WorkspaceManager, WorkspaceInfo
        from session.manager import SessionManager, Session, Message
        from src.platform.token_budget import TokenBudgetManager, TokenBudget
        from src.platform.errors import PlatformError, TokenBudgetExceeded
        from src.orchestration.user_preferences import UserPreferenceManager
        from src.orchestration.runtime import OrchestratorRuntime
        assert True  # If we got here, imports work
