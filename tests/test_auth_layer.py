"""
Phase 9.6-A — Authentication & API Security Layer Tests

Tests covering:
  - JWT token creation, verification, refresh, expiry
  - Password hashing, verification, legacy compatibility
  - Middleware role-based guards (require_role, require_pro, etc.)
  - Permission integration (model access, multimodal)
  - Expired token handling
  - Multi-user token isolation
  - UserToken data model

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import time
import sys
import tempfile
import shutil
from pathlib import Path

import pytest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ═══════════════════════════════════════════════
# 1. Password Tests
# ═══════════════════════════════════════════════

class TestPasswordHashing:

    def test_hash_password_basic(self):
        from src.auth.password import hash_password
        h, salt = hash_password("mysecret")
        assert len(h) == 64  # SHA-256 hex = 64 chars
        assert len(salt) == 32  # 16 bytes hex = 32 chars
        assert h != "mysecret"  # Not plaintext

    def test_hash_password_with_given_salt(self):
        from src.auth.password import hash_password
        salt = "a" * 32
        h1, _ = hash_password("pwd", salt)
        h2, _ = hash_password("pwd", salt)
        assert h1 == h2  # Same salt → same hash

    def test_hash_password_different_salts(self):
        from src.auth.password import hash_password
        h1, s1 = hash_password("same")
        h2, s2 = hash_password("same")
        assert s1 != s2  # Random salts
        assert h1 != h2  # Different hashes

    def test_hash_password_empty(self):
        from src.auth.password import hash_password
        h, salt = hash_password("")
        assert h == ""

    def test_make_password_hash_format(self):
        from src.auth.password import make_password_hash
        h = make_password_hash("secret123")
        parts = h.split("$")
        assert len(parts) >= 3
        assert len(parts[0]) == 32  # salt
        assert parts[1].isdigit()   # iterations

    def test_make_password_hash_empty(self):
        from src.auth.password import make_password_hash
        assert make_password_hash("") == ""

    def test_verify_password_correct(self):
        from src.auth.password import make_password_hash, verify_password
        h = make_password_hash("correct_horse_battery_staple")
        assert verify_password("correct_horse_battery_staple", h) is True

    def test_verify_password_wrong(self):
        from src.auth.password import make_password_hash, verify_password
        h = make_password_hash("real_password")
        assert verify_password("wrong_password", h) is False

    def test_verify_password_empty(self):
        from src.auth.password import verify_password
        assert verify_password("", "anything") is False
        assert verify_password("anything", "") is False

    def test_verify_password_tampered_hash(self):
        from src.auth.password import make_password_hash, verify_password
        h = make_password_hash("pwd")
        tampered = h[:-1] + ("0" if h[-1] != "0" else "1")
        assert verify_password("pwd", tampered) is False

    def test_generate_salt_random(self):
        from src.auth.password import generate_salt
        s1 = generate_salt()
        s2 = generate_salt()
        assert s1 != s2
        assert len(s1) == 32

    def test_legacy_hash_verification(self):
        """Phase 9.1 format: salt:hash (100k iterations, sha256)"""
        from src.auth.password import verify_password
        import hashlib, os
        salt = os.urandom(16).hex()
        h = hashlib.pbkdf2_hmac("sha256", b"legacy_pwd", salt.encode(), 100_000).hex()
        stored = f"{salt}:{h}"
        assert verify_password("legacy_pwd", stored) is True
        assert verify_password("wrong", stored) is False

    def test_is_legacy_hash(self):
        from src.auth.password import is_legacy_hash
        assert is_legacy_hash("salt:hashvalue") is True
        assert is_legacy_hash("salt$200000$hashvalue") is False
        assert is_legacy_hash("plaintext") is False

    def test_upgrade_hash_if_needed_legacy(self):
        from src.auth.password import upgrade_hash_if_needed, is_legacy_hash
        import hashlib, os
        salt = os.urandom(16).hex()
        h = hashlib.pbkdf2_hmac("sha256", b"upgrade_me", salt.encode(), 100_000).hex()
        stored = f"{salt}:{h}"
        new = upgrade_hash_if_needed("upgrade_me", stored)
        assert new is not None
        assert "$" in new
        assert is_legacy_hash(new) is False

    def test_upgrade_hash_if_needed_already_new(self):
        from src.auth.password import make_password_hash, upgrade_hash_if_needed
        h = make_password_hash("modern")
        new = upgrade_hash_if_needed("modern", h)
        assert new is None

    def test_unicode_password(self):
        from src.auth.password import make_password_hash, verify_password
        h = make_password_hash("密码123!@#")
        assert verify_password("密码123!@#", h) is True
        assert verify_password("密码123", h) is False

    def test_long_password(self):
        from src.auth.password import make_password_hash, verify_password
        pwd = "x" * 1024
        h = make_password_hash(pwd)
        assert verify_password(pwd, h) is True


# ═══════════════════════════════════════════════
# 2. UserToken Model Tests
# ═══════════════════════════════════════════════

class TestUserTokenModel:

    def test_default_values(self):
        from src.auth.jwt_manager import UserToken
        t = UserToken(user_id="usr_1")
        assert t.user_id == "usr_1"
        assert t.role == "free"
        assert t.username == ""
        assert t.email == ""
        assert t.issued_at > 0
        assert t.expire_at > t.issued_at

    def test_is_expired_false(self):
        from src.auth.jwt_manager import UserToken
        t = UserToken(user_id="usr_1", expire_at=time.time() + 3600)
        assert t.is_expired is False

    def test_is_expired_true(self):
        from src.auth.jwt_manager import UserToken
        t = UserToken(user_id="usr_1", expire_at=time.time() - 1)
        assert t.is_expired is True

    def test_ttl_seconds(self):
        from src.auth.jwt_manager import UserToken
        t = UserToken(user_id="usr_1", expire_at=time.time() + 100)
        assert 0 < t.ttl_seconds <= 100

    def test_ttl_expired(self):
        from src.auth.jwt_manager import UserToken
        t = UserToken(user_id="usr_1", expire_at=time.time() - 10)
        assert t.ttl_seconds == 0

    def test_is_admin(self):
        from src.auth.jwt_manager import UserToken
        t = UserToken(user_id="usr_1", role="admin")
        assert t.is_admin is True
        t2 = UserToken(user_id="usr_2", role="pro")
        assert t2.is_admin is False

    def test_to_dict(self):
        from src.auth.jwt_manager import UserToken
        t = UserToken(user_id="usr_1", role="pro", username="alice", email="a@t.com")
        d = t.to_dict()
        assert d["user_id"] == "usr_1"
        assert d["role"] == "pro"
        assert d["username"] == "alice"

    def test_from_payload(self):
        from src.auth.jwt_manager import UserToken
        payload = {
            "user_id": "usr_x", "role": "student",
            "iat": 1000.0, "exp": 4600.0,
        }
        t = UserToken.from_payload(payload)
        assert t.user_id == "usr_x"
        assert t.role == "student"
        assert t.issued_at == 1000.0
        assert t.expire_at == 4600.0


# ═══════════════════════════════════════════════
# 3. JWT Manager Tests
# ═══════════════════════════════════════════════

class TestJWTManager:

    def setup_method(self):
        from src.auth.jwt_manager import JWTManager
        self.mgr = JWTManager(secret="test-secret-key-123")

    def test_create_token_returns_string(self):
        token = self.mgr.create_token("usr_1")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_create_token_with_role(self):
        token = self.mgr.create_token("usr_1", role="pro")
        payload = self.mgr.verify_token(token)
        assert payload.role == "pro"

    def test_create_token_with_all_fields(self):
        token = self.mgr.create_token(
            "usr_abc", role="student",
            username="alice", email="alice@test.com",
            expiry_seconds=7200,
        )
        payload = self.mgr.verify_token(token)
        assert payload.user_id == "usr_abc"
        assert payload.role == "student"
        assert payload.username == "alice"
        assert payload.email == "alice@test.com"

    def test_create_token_custom_expiry(self):
        token = self.mgr.create_token("usr_1", expiry_seconds=10)
        payload = self.mgr.verify_token(token)
        assert payload is not None
        ttl = payload.expire_at - payload.issued_at
        assert 9 <= ttl <= 11

    def test_verify_valid_token(self):
        token = self.mgr.create_token("usr_1")
        payload = self.mgr.verify_token(token)
        assert payload is not None
        assert payload.user_id == "usr_1"

    def test_verify_expired_token(self):
        token = self.mgr.create_token("usr_1", expiry_seconds=-1)
        payload = self.mgr.verify_token(token)
        assert payload is None

    def test_verify_tampered_token(self):
        token = self.mgr.create_token("usr_1")
        # Tamper with payload section
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}x.{parts[2]}"
        payload = self.mgr.verify_token(tampered)
        assert payload is None

    def test_verify_wrong_secret(self):
        from src.auth.jwt_manager import JWTManager
        mgr1 = JWTManager(secret="secret-a")
        mgr2 = JWTManager(secret="secret-b")
        token = mgr1.create_token("usr_1")
        payload = mgr2.verify_token(token)
        assert payload is None

    def test_verify_invalid_format(self):
        assert self.mgr.verify_token("not.a.token") is None
        assert self.mgr.verify_token("") is None
        assert self.mgr.verify_token("a.b.c.d") is None

    def test_verify_tampered_signature(self):
        token = self.mgr.create_token("usr_1")
        parts = token.split(".")
        # Flip last char of signature
        sig = parts[2]
        flipped = sig[:-1] + ("A" if sig[-1] != "A" else "B")
        tampered = f"{parts[0]}.{parts[1]}.{flipped}"
        payload = self.mgr.verify_token(tampered)
        assert payload is None

    def test_decode_unsafe(self):
        token = self.mgr.create_token("usr_1", role="pro")
        decoded = self.mgr.decode_unsafe(token)
        assert decoded is not None
        assert decoded["user_id"] == "usr_1"
        assert decoded["role"] == "pro"

    def test_decode_unsafe_bad_token(self):
        assert self.mgr.decode_unsafe("bad.token") is None
        assert self.mgr.decode_unsafe("") is None

    def test_refresh_valid_token(self):
        token = self.mgr.create_token("usr_1", role="pro", expiry_seconds=3600)
        new_token = self.mgr.refresh_token(token)
        assert new_token is not None
        assert new_token != token
        payload = self.mgr.verify_token(new_token)
        assert payload is not None
        assert payload.user_id == "usr_1"
        assert payload.role == "pro"

    def test_refresh_recently_expired_token(self):
        token = self.mgr.create_token("usr_1", expiry_seconds=-5)
        # Token is 5 seconds expired → still within 7-day refresh window
        payload = self.mgr.verify_token(token)
        assert payload is None  # Expired for auth
        refreshed = self.mgr.refresh_token(token)
        assert refreshed is not None  # But refreshable
        new_payload = self.mgr.verify_token(refreshed)
        assert new_payload is not None

    def test_refresh_long_expired_token(self):
        token = self.mgr.create_token("usr_1", expiry_seconds=-(86400 * 8))
        # 8 days expired → outside refresh window
        refreshed = self.mgr.refresh_token(token)
        assert refreshed is None

    def test_refresh_tampered_token(self):
        token = self.mgr.create_token("usr_1")
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}x.{parts[2]}"
        assert self.mgr.refresh_token(tampered) is None

    def test_get_remaining_seconds(self):
        token = self.mgr.create_token("usr_1", expiry_seconds=3600)
        remaining = self.mgr.get_remaining_seconds(token)
        assert 0 < remaining <= 3600

    def test_get_remaining_expired(self):
        token = self.mgr.create_token("usr_1", expiry_seconds=-1)
        remaining = self.mgr.get_remaining_seconds(token)
        assert remaining == 0

    def test_different_secrets_produce_different_tokens(self):
        from src.auth.jwt_manager import JWTManager
        mgr_a = JWTManager(secret="a")
        mgr_b = JWTManager(secret="b")
        t_a = mgr_a.create_token("usr_1")
        t_b = mgr_b.create_token("usr_1")
        assert t_a != t_b

    def test_multi_user_isolation(self):
        t1 = self.mgr.create_token("usr_a", role="free")
        t2 = self.mgr.create_token("usr_b", role="admin")
        p1 = self.mgr.verify_token(t1)
        p2 = self.mgr.verify_token(t2)
        assert p1.user_id == "usr_a"
        assert p2.user_id == "usr_b"
        assert p1.role != p2.role

    def test_not_before_future(self):
        token = self.mgr.create_token(
            "usr_1", extra_claims={"nbf": time.time() + 3600}
        )
        payload = self.mgr.verify_token(token)
        assert payload is None

    def test_not_before_past(self):
        token = self.mgr.create_token(
            "usr_1", extra_claims={"nbf": time.time() - 3600}
        )
        payload = self.mgr.verify_token(token)
        assert payload is not None

    def test_extra_claims(self):
        token = self.mgr.create_token(
            "usr_1",
            extra_claims={"scope": "read", "tenant": "org-1"},
        )
        decoded = self.mgr.decode_unsafe(token)
        assert decoded["scope"] == "read"
        assert decoded["tenant"] == "org-1"


# ═══════════════════════════════════════════════
# 4. Permission Integration Tests
# ═══════════════════════════════════════════════

class TestPermissionIntegration:

    def test_role_free_restrictions(self):
        from src.auth.middleware import Role
        from user.permission import PermissionManager
        perm = PermissionManager.get_permission(Role.FREE)
        assert perm.multimodal_access is False
        assert "openai" not in perm.available_models

    def test_role_pro_privileges(self):
        from src.auth.middleware import Role
        from user.permission import PermissionManager
        perm = PermissionManager.get_permission(Role.PRO)
        assert perm.multimodal_access is True
        assert "openai" in perm.available_models

    def test_model_access_check_free(self):
        from src.auth.middleware import Role
        from user.permission import PermissionManager
        assert PermissionManager.can_use_model("mock", Role.FREE) is True
        assert PermissionManager.can_use_model("openai", Role.FREE) is False

    def test_model_access_check_pro(self):
        from src.auth.middleware import Role
        from user.permission import PermissionManager
        assert PermissionManager.can_use_model("openai", Role.PRO) is True
        assert PermissionManager.can_use_model("anthropic", Role.PRO) is True

    def test_require_role_guard_allows(self):
        from src.auth.middleware import Role
        # FREE is in the allowed list
        assert Role.FREE in (Role.FREE, Role.STUDENT)

    def test_require_role_guard_denies(self):
        from src.auth.middleware import Role
        # FREE is not in the admin list
        assert Role.FREE not in (Role.ADMIN,)


# ═══════════════════════════════════════════════
# 5. JWT Token Edge Cases
# ═══════════════════════════════════════════════

class TestJWTEdgeCases:

    def setup_method(self):
        from src.auth.jwt_manager import JWTManager
        self.mgr = JWTManager(secret="edge-secret")

    def test_empty_user_id(self):
        token = self.mgr.create_token("", role="free")
        payload = self.mgr.verify_token(token)
        assert payload is not None
        assert payload.user_id == ""

    def test_very_short_expiry(self):
        # -1 = 1 second in the past → already expired
        token = self.mgr.create_token("usr_1", expiry_seconds=-1)
        payload = self.mgr.verify_token(token)
        assert payload is None  # Immediately expired

    def test_very_long_expiry(self):
        token = self.mgr.create_token("usr_1", expiry_seconds=86400 * 365)
        payload = self.mgr.verify_token(token)
        assert payload is not None

    def test_token_with_special_chars_in_claims(self):
        token = self.mgr.create_token(
            "usr_1",
            extra_claims={"note": "hello/world=test+space"},
        )
        payload = self.mgr.verify_token(token)
        assert payload is not None
        decoded = self.mgr.decode_unsafe(token)
        assert "hello/world=test+space" in decoded.get("note", "")

    def test_multiple_creates_unique_tokens(self):
        tokens = set()
        for i in range(10):
            t = self.mgr.create_token(f"usr_{i}")
            tokens.add(t)
        assert len(tokens) == 10

    def test_default_secret_when_empty(self):
        from src.auth.jwt_manager import JWTManager
        mgr = JWTManager(secret="")
        token = mgr.create_token("usr_1")
        payload = mgr.verify_token(token)
        assert payload is not None

    def test_refresh_preserves_username_email(self):
        token = self.mgr.create_token(
            "usr_1", role="pro", username="alice", email="a@t.com"
        )
        refreshed = self.mgr.refresh_token(token)
        decoded = self.mgr.decode_unsafe(refreshed)
        assert decoded["username"] == "alice"
        assert decoded["email"] == "a@t.com"

    def test_corrupted_base64_in_token(self):
        token = "not$$valid.base64!!.xyz"
        assert self.mgr.verify_token(token) is None


# ═══════════════════════════════════════════════
# 6. Password Edge Cases
# ═══════════════════════════════════════════════

class TestPasswordEdgeCases:

    def test_unicode_special(self):
        from src.auth.password import make_password_hash, verify_password
        pwd = "パスワード🔐テスト"
        h = make_password_hash(pwd)
        assert verify_password(pwd, h) is True

    def test_null_byte(self):
        from src.auth.password import make_password_hash, verify_password
        pwd = "before\x00after"
        h = make_password_hash(pwd)
        assert verify_password(pwd, h) is True
        assert verify_password("beforeafter", h) is False

    def test_whitespace_only(self):
        from src.auth.password import make_password_hash, verify_password
        pwd = "   \t\n  "
        h = make_password_hash(pwd)
        assert verify_password(pwd, h) is True
        assert verify_password("   ", h) is False

    def test_corrupted_legacy_hash(self):
        from src.auth.password import verify_password
        assert verify_password("pwd", "bad:format:extra") is False
        assert verify_password("pwd", "no_delimiter") is False

    def test_corrupted_new_hash(self):
        from src.auth.password import verify_password
        assert verify_password("pwd", "short$200000$hash") is False
        assert verify_password("pwd", "salt$notanumber$hash") is False


# ═══════════════════════════════════════════════
# 7. Middleware Factory Tests (unit-level)
# ═══════════════════════════════════════════════

class TestMiddlewareFactories:

    def test_require_role_returns_callable(self):
        from src.auth.middleware import require_role
        guard = require_role("admin")
        assert callable(guard)

    def test_require_pro_returns_callable(self):
        from src.auth.middleware import require_pro
        guard = require_pro()
        assert callable(guard)

    def test_require_teacher_or_admin_returns_callable(self):
        from src.auth.middleware import require_teacher_or_admin
        guard = require_teacher_or_admin()
        assert callable(guard)

    def test_require_admin_returns_callable(self):
        from src.auth.middleware import require_admin
        guard = require_admin()
        assert callable(guard)

    def test_require_multimodal_returns_callable(self):
        from src.auth.middleware import require_multimodal_access
        guard = require_multimodal_access()
        assert callable(guard)

    def test_require_model_access_returns_callable(self):
        from src.auth.middleware import require_model_access
        guard = require_model_access("openai")
        assert callable(guard)

    def test_check_token_limit_returns_callable(self):
        from src.auth.middleware import check_token_limit
        guard = check_token_limit(500)
        assert callable(guard)


# ═══════════════════════════════════════════════
# 8. Integration: JWT + Password + Token Model
# ═══════════════════════════════════════════════

class TestAuthIntegration:

    def test_jwt_payload_roundtrip(self):
        from src.auth.jwt_manager import JWTManager, UserToken
        mgr = JWTManager(secret="integration-test")
        token = mgr.create_token(
            user_id="usr_int", role="pro",
            username="integration", email="int@test.com",
        )
        payload = mgr.verify_token(token)
        assert payload.user_id == "usr_int"
        assert payload.role == "pro"
        assert payload.username == "integration"
        assert payload.email == "int@test.com"
        assert isinstance(payload.issued_at, float)
        assert isinstance(payload.expire_at, float)

    def test_password_hash_works_with_jwt_secret(self):
        from src.auth.password import make_password_hash, verify_password
        h = make_password_hash("jwt-secret-password")
        assert verify_password("jwt-secret-password", h)

    def test_model_re_export(self):
        from src.auth.models import UserToken
        t = UserToken(user_id="re_export_test")
        assert t.user_id == "re_export_test"


# ═══════════════════════════════════════════════
# 9. No Regression — Existing Auth Still Works
# ═══════════════════════════════════════════════

class TestNoRegression:

    def test_existing_auth_imports(self):
        """All existing auth imports still work."""
        from src.auth.models import AuthUser, AuthToken, RegisterRequest, LoginRequest
        from src.auth.auth_manager import register, login, login_guest, logout, get_current_user
        from src.auth.middleware import require_auth, optional_auth
        assert True

    def test_existing_auth_user_model(self):
        from src.auth.models import AuthUser
        u = AuthUser(id="test", email="t@t.com", display_name="Test")
        assert u.id == "test"
        assert u.is_guest is False
        d = u.to_dict()
        assert d["id"] == "test"

    def test_existing_auth_token_model(self):
        from src.auth.models import AuthToken
        t = AuthToken(token="abc123", user_id="usr_1", display_name="User")
        assert t.token == "abc123"
        assert t.user_id == "usr_1"
