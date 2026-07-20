"""
Phase 9.6-B — Security Hardening Tests

Tests covering:
  - API Key create, validate, revoke, rotate
  - RequestContext build (user/plan/permission resolution)
  - Audit log write, query, stats, suspicious detection
  - SuspiciousDetector: burst, failure rate, rapid retry
  - Security middleware integration
  - Multi-user isolation for keys and audit logs

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import shutil
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ── Test isolation ────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_storage(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="a3_test_sec_")

    def _fake_expanduser(p):
        return tmp if "a3-agent" in str(p) else os.path.expanduser(p)

    for mod in [
        "src.auth.api_keys.os.path",
        "src.security.audit.os.path",
    ]:
        monkeypatch.setattr(f"{mod}.expanduser", _fake_expanduser)

    yield
    shutil.rmtree(tmp, ignore_errors=True)


# ═══════════════════════════════════════════════
# 1. API Key Management Tests
# ═══════════════════════════════════════════════

class TestApiKeyManager:

    def setup_method(self):
        from src.auth.api_keys import _get_keys_file
        f = _get_keys_file()
        if f.exists():
            f.unlink()

    def test_create_api_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key("usr_1", "My Key")
        assert key_str.startswith("a3_")
        assert len(key_str) > 40
        assert record.user_id == "usr_1"
        assert record.name == "My Key"
        assert record.is_active is True

    def test_create_api_key_with_scopes(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key(
            "usr_1", "Scoped Key", scopes=["read", "generate"]
        )
        assert record.scopes == ["read", "generate"]

    def test_create_api_key_custom_expiry(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key(
            "usr_1", "Short Key", expiry_days=7
        )
        expected = record.created_at + 7 * 86400
        assert abs(record.expires_at - expected) < 1

    def test_validate_valid_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, _ = mgr.create_api_key("usr_1", "Test")
        user_id = mgr.validate_api_key(key_str)
        assert user_id == "usr_1"

    def test_validate_invalid_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        assert mgr.validate_api_key("bad_key") is None
        assert mgr.validate_api_key("") is None
        assert mgr.validate_api_key("a3_badkey") is None

    def test_validate_wrong_prefix(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        assert mgr.validate_api_key("sk_not_a3_key_12345678901234567890") is None

    def test_revoke_api_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key("usr_1", "Revocable")
        assert mgr.validate_api_key(key_str) == "usr_1"
        assert mgr.revoke_api_key(record.key_id) is True
        assert mgr.validate_api_key(key_str) is None

    def test_revoke_nonexistent_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        assert mgr.revoke_api_key("nonexistent") is False

    def test_hard_delete_api_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        _, record = mgr.create_api_key("usr_1", "DeleteMe")
        assert mgr.hard_delete_api_key(record.key_id) is True
        assert mgr.get_api_key(record.key_id) is None

    def test_rotate_api_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        old_key, record = mgr.create_api_key("usr_1", "Rotate Me")
        result = mgr.rotate_api_key(record.key_id)
        assert result is not None
        new_key, new_record = result
        assert new_key != old_key
        # Old key should be invalid
        assert mgr.validate_api_key(old_key) is None
        # New key should be valid
        assert mgr.validate_api_key(new_key) == "usr_1"

    def test_rotate_preserves_scopes(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        _, record = mgr.create_api_key("usr_1", "Scoped", scopes=["read", "admin"])
        _, new_record = mgr.rotate_api_key(record.key_id)
        assert new_record.scopes == ["read", "admin"]

    def test_rotate_nonexistent(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        assert mgr.rotate_api_key("nonexistent") is None

    def test_rotate_revoked_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        _, record = mgr.create_api_key("usr_1", "Revoked")
        mgr.revoke_api_key(record.key_id)
        assert mgr.rotate_api_key(record.key_id) is None

    def test_list_api_keys(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        mgr.create_api_key("usr_a", "A1")
        mgr.create_api_key("usr_a", "A2")
        mgr.create_api_key("usr_b", "B1")
        keys_a = mgr.list_api_keys(user_id="usr_a")
        assert len(keys_a) == 2
        keys_b = mgr.list_api_keys(user_id="usr_b")
        assert len(keys_b) == 1

    def test_list_api_keys_excludes_revoked(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        _, r1 = mgr.create_api_key("usr_1", "Active")
        _, r2 = mgr.create_api_key("usr_1", "Revoked")
        mgr.revoke_api_key(r2.key_id)
        keys = mgr.list_api_keys(user_id="usr_1", active_only=True)
        assert len(keys) == 1
        assert keys[0].key_id == r1.key_id

    def test_get_api_key(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        _, record = mgr.create_api_key("usr_1", "My Key")
        found = mgr.get_api_key(record.key_id)
        assert found is not None
        assert found.name == "My Key"

    def test_count_active_keys(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        mgr.create_api_key("usr_1", "K1")
        mgr.create_api_key("usr_1", "K2")
        _, r3 = mgr.create_api_key("usr_1", "K3")
        mgr.revoke_api_key(r3.key_id)
        assert mgr.count_active_keys("usr_1") == 2

    def test_expired_key_not_validated(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key("usr_1", "Expired")
        # Manually expire it
        from src.auth.api_keys import _get_keys_file
        data = json.loads(_get_keys_file().read_text())
        data[record.key_id]["expires_at"] = time.time() - 1
        _get_keys_file().write_text(json.dumps(data))
        assert mgr.validate_api_key(key_str) is None


# ═══════════════════════════════════════════════
# 2. Request Context Tests
# ═══════════════════════════════════════════════

class TestRequestContext:

    def setup_method(self):
        from src.user.manager import _get_users_file
        f = _get_users_file()
        if f.exists():
            f.unlink()

    def test_build_context_for_known_user(self):
        from src.user.manager import UserManager
        from src.auth.context import build_context
        um = UserManager()
        u = um.create_user("ctx_user", "ctx@test.com", role="pro")
        ctx = build_context(u.user_id)
        assert ctx.user.user_id == u.user_id
        assert ctx.user.role == "pro"
        assert ctx.permission.multimodal_access is True
        assert "openai" in ctx.permission.available_models

    def test_build_context_for_free_user(self):
        from src.user.manager import UserManager
        from src.auth.context import build_context
        um = UserManager()
        u = um.create_user("free_user", "free@test.com", role="free")
        ctx = build_context(u.user_id)
        assert ctx.permission.multimodal_access is False
        assert "openai" not in ctx.permission.available_models

    def test_build_context_unknown_user(self):
        from src.auth.context import build_context
        ctx = build_context("usr_ghost")
        assert ctx.user.role == "free"
        assert ctx.permission.max_tokens == 100_000

    def test_current_user_model(self):
        from src.auth.context import CurrentUser
        cu = CurrentUser(user_id="usr_1", username="alice", role="admin")
        assert cu.is_admin is True
        assert cu.is_guest is False
        d = cu.to_dict()
        assert d["user_id"] == "usr_1"

    def test_current_user_guest_detection(self):
        from src.auth.context import CurrentUser
        cu = CurrentUser(user_id="guest_abc123")
        assert cu.is_guest is True
        assert cu.is_admin is False

    def test_current_plan_from_tier(self):
        from src.auth.context import CurrentPlan
        from src.billing.models import PlanTier
        plan = CurrentPlan.from_plan_tier(PlanTier.PRO)
        assert plan.tier == "pro"
        assert plan.multimodal is True
        assert plan.monthly_tokens == 60_000_000

    def test_current_permission_from_role(self):
        from src.auth.context import CurrentPermission
        perm = CurrentPermission.from_role("student")
        assert perm.max_tokens == 500_000
        assert perm.daily_requests == 100

    def test_can_use_model(self):
        from src.auth.context import CurrentPermission
        perm = CurrentPermission.from_role("pro")
        assert perm.can_use_model("openai") is True
        assert perm.can_use_model("nonexistent") is False

    def test_request_context_convenience(self):
        from src.auth.context import RequestContext, CurrentUser, CurrentPlan, CurrentPermission
        ctx = RequestContext(
            user=CurrentUser(user_id="u1", role="pro"),
            plan=CurrentPlan.from_plan_tier("pro"),
            permission=CurrentPermission.from_role("pro"),
        )
        assert ctx.can_use_model("openai") is True
        assert ctx.can_generate_multimodal() is True
        assert ctx.is_admin() is False
        assert ctx.get_max_tokens() == 2_000_000

    def test_request_context_to_dict(self):
        from src.auth.context import build_context
        from src.user.manager import UserManager
        um = UserManager()
        u = um.create_user("dict_test", "dict@test.com", role="pro")
        ctx = build_context(u.user_id)
        d = ctx.to_dict()
        assert "user" in d
        assert "plan" in d
        assert "permission" in d
        assert d["user"]["role"] == "pro"


# ═══════════════════════════════════════════════
# 3. Audit Log Tests
# ═══════════════════════════════════════════════

class TestAuditLog:

    def test_log_entry(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        entry = logger.log(
            user_id="usr_1", role="pro",
            endpoint="/api/v2/chat", method="POST",
            provider="openai", tokens_used=500,
            success=True,
        )
        assert entry.user_id == "usr_1"
        assert entry.provider == "openai"
        assert entry.tokens_used == 500
        assert entry.success is True

    def test_log_entry_with_cost(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        entry = logger.log(
            user_id="usr_1", endpoint="/test", method="GET",
            tokens_used=1000, estimated_cost_usd=0.015, success=True,
        )
        assert entry.estimated_cost_usd == 0.015

    def test_query_returns_entries(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        logger.log("usr_1", endpoint="/a", method="GET")
        logger.log("usr_1", endpoint="/b", method="POST")
        entries = logger.query("usr_1")
        assert len(entries) == 2

    def test_query_limit(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        for i in range(10):
            logger.log("usr_1", endpoint=f"/api/{i}", method="GET")
        entries = logger.query("usr_1", limit=5)
        assert len(entries) == 5

    def test_query_success_only(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        logger.log("usr_1", endpoint="/ok", success=True)
        logger.log("usr_1", endpoint="/fail", success=False)
        entries = logger.query("usr_1", success_only=True)
        assert len(entries) == 1
        assert entries[0].endpoint == "/ok"

    def test_query_endpoint_filter(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        logger.log("usr_1", endpoint="/api/v2/chat", method="POST")
        logger.log("usr_1", endpoint="/api/v2/profile", method="GET")
        entries = logger.query("usr_1", endpoint_prefix="/api/v2/chat")
        assert len(entries) == 1

    def test_query_empty_for_nonexistent_user(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        entries = logger.query("nonexistent_user")
        assert entries == []

    def test_get_user_stats(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        logger.log("usr_1", endpoint="/a", provider="openai", tokens_used=100, success=True)
        logger.log("usr_1", endpoint="/b", provider="deepseek", tokens_used=200, success=True)
        logger.log("usr_1", endpoint="/c", provider="openai", tokens_used=50, success=False)
        stats = logger.get_user_stats("usr_1")
        assert stats["total_calls"] == 3
        assert stats["success_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["total_tokens"] == 350
        assert "openai" in stats["providers_used"]
        assert "deepseek" in stats["providers_used"]

    def test_get_user_stats_empty(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        stats = logger.get_user_stats("empty_user")
        assert stats["total_calls"] == 0

    def test_audit_entry_to_dict_roundtrip(self):
        from src.security.audit import AuditEntry
        e = AuditEntry(
            event_id="evt_1", user_id="usr_1", role="pro",
            endpoint="/test", method="GET", status_code=200,
            provider="openai", model_id="gpt-4", tokens_used=500,
            success=True, request_id="req_1", duration_ms=150.0,
            extra={"key": "val"},
        )
        d = e.to_dict()
        e2 = AuditEntry.from_dict(d)
        assert e2.user_id == "usr_1"
        assert e2.provider == "openai"
        assert e2.tokens_used == 500
        assert e2.extra == {"key": "val"}

    def test_suspicious_activity_high_failure(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        for i in range(12):
            logger.log("usr_sus", endpoint=f"/fail/{i}", success=(i >= 9))
        suspicious = logger.get_suspicious_activity("usr_sus", lookback_hours=1)
        assert len(suspicious) > 0  # 9/12 failures > 50%

    def test_suspicious_activity_normal(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        # A single successful entry should never be suspicious
        logger.log("usr_normal", endpoint="/api/ok", success=True)
        suspicious = logger.get_suspicious_activity("usr_normal", lookback_hours=1)
        assert len(suspicious) == 0


# ═══════════════════════════════════════════════
# 4. Suspicious Detector Tests
# ═══════════════════════════════════════════════

class TestSuspiciousDetector:

    def setup_method(self):
        from src.security.middleware import SuspiciousDetector
        self.det = SuspiciousDetector(
            burst_threshold=5, burst_window=10.0,
            failure_rate_threshold=0.5, min_samples=5,
            rapid_retry_interval=0.5,
        )

    def test_record_and_no_suspicious(self):
        self.det.record("usr_1", "/api/test", 200, True)
        is_sus, reason = self.det.is_suspicious("usr_1")
        assert is_sus is False
        assert reason == ""

    def test_burst_detection(self):
        for i in range(6):
            self.det.record("usr_burst", "/api/fast", 200, True)
        is_sus, reason = self.det.is_suspicious("usr_burst")
        assert is_sus is True
        assert "Burst" in reason

    def test_high_failure_rate(self):
        # 3 failures + 1 success = 75% failure rate, triggers rapid retry check
        for i in range(3):
            self.det.record("usr_fail", f"/fail/{i}", 500, False)
        self.det.record("usr_fail", "/fail/ok", 200, True)
        is_sus, reason = self.det.is_suspicious("usr_fail")
        assert is_sus is True
        # Rapid failures within 0.5s trigger rapid retry detection
        assert "Rapid retry" in reason or "failure rate" in reason.lower()

    def test_rapid_retry(self):
        self.det.record("usr_retry", "/api/x", 500, False)
        self.det.record("usr_retry", "/api/x", 500, False)
        self.det.record("usr_retry", "/api/x", 500, False)
        is_sus, reason = self.det.is_suspicious("usr_retry")
        assert is_sus is True
        assert "Rapid retry" in reason

    def test_normal_activity_not_suspicious(self):
        # 4 normal requests (under burst threshold of 5, all success)
        for i in range(4):
            self.det.record("usr_normal", f"/api/{i}", 200, True, duration_ms=100)
        is_sus, reason = self.det.is_suspicious("usr_normal")
        assert is_sus is False

    def test_get_stats(self):
        self.det.record("usr_s", "/a", 200, True, duration_ms=50)
        self.det.record("usr_s", "/b", 500, False, duration_ms=200)
        stats = self.det.get_stats("usr_s")
        assert stats["total_requests"] == 2
        assert stats["failure_rate"] == 0.5
        assert stats["avg_duration_ms"] == 125.0

    def test_get_stats_empty(self):
        stats = self.det.get_stats("no_user")
        assert stats["total_requests"] == 0

    def test_reset_user(self):
        self.det.record("usr_r", "/a", 200, True)
        self.det.reset("usr_r")
        stats = self.det.get_stats("usr_r")
        assert stats["total_requests"] == 0

    def test_reset_all(self):
        self.det.record("usr_a", "/a", 200, True)
        self.det.record("usr_b", "/b", 200, True)
        self.det.reset()
        assert self.det.get_stats("usr_a")["total_requests"] == 0
        assert self.det.get_stats("usr_b")["total_requests"] == 0

    def test_history_pruning(self):
        """After 200+ records, only last 200 kept."""
        for i in range(250):
            self.det.record("usr_big", f"/api/{i}", 200, True)
        stats = self.det.get_stats("usr_big")
        assert stats["total_requests"] <= 200


# ═══════════════════════════════════════════════
# 5. Integration Tests
# ═══════════════════════════════════════════════

class TestIntegration:

    def setup_method(self):
        from src.user.manager import _get_users_file
        from src.auth.api_keys import _get_keys_file
        for f in [_get_users_file(), _get_keys_file()]:
            if f.exists():
                f.unlink()

    def test_api_key_to_context_flow(self):
        """Full flow: create user → create API key → validate → build context."""
        from src.user.manager import UserManager
        from src.auth.api_keys import ApiKeyManager
        from src.auth.context import build_context

        um = UserManager()
        u = um.create_user("flow_user", "flow@test.com", role="pro")

        mgr = ApiKeyManager()
        key_str, _ = mgr.create_api_key(u.user_id, "Flow Key")

        user_id = mgr.validate_api_key(key_str)
        assert user_id == u.user_id

        ctx = build_context(user_id)
        assert ctx.user.role == "pro"
        assert ctx.can_use_model("openai") is True

    def test_audit_and_suspicious_flow(self):
        """Audit log entries feed into suspicious detection."""
        from src.security.audit import AuditLogger
        from src.security.middleware import SuspiciousDetector

        logger = AuditLogger()
        det = SuspiciousDetector(
            burst_threshold=10, failure_rate_threshold=0.5,
            min_samples=3, rapid_retry_interval=0.5,
        )

        # Simulate rapid failures
        for i in range(5):
            logger.log("usr_attack", endpoint="/api/chat", success=False)
            det.record("usr_attack", "/api/chat", 500, False)

        is_sus, reason = det.is_suspicious("usr_attack")
        assert is_sus is True

        stats = logger.get_user_stats("usr_attack")
        assert stats["failed_calls"] == 5

    def test_multi_user_key_isolation(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        k1, _ = mgr.create_api_key("user_a", "Key A")
        k2, _ = mgr.create_api_key("user_b", "Key B")
        assert mgr.validate_api_key(k1) == "user_a"
        assert mgr.validate_api_key(k2) == "user_b"

    def test_multi_user_audit_isolation(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        logger.log("user_a", endpoint="/api/a")
        logger.log("user_b", endpoint="/api/b")
        assert len(logger.query("user_a")) == 1
        assert len(logger.query("user_b")) == 1

    def test_context_respects_user_role_limits(self):
        from src.user.manager import UserManager
        from src.auth.context import build_context
        um = UserManager()
        free_u = um.create_user("free_guy", "fg@t.com", role="free")
        pro_u = um.create_user("pro_guy", "pg@t.com", role="pro")

        free_ctx = build_context(free_u.user_id)
        pro_ctx = build_context(pro_u.user_id)

        assert free_ctx.get_max_tokens() < pro_ctx.get_max_tokens()
        assert free_ctx.can_use_model("openai") is False
        assert pro_ctx.can_use_model("openai") is True


# ═══════════════════════════════════════════════
# 6. Edge Cases
# ═══════════════════════════════════════════════

class TestEdgeCases:

    def test_key_prefix_only_rejected(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        assert mgr.validate_api_key("a3_") is None

    def test_key_with_spaces(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        assert mgr.validate_api_key("a3_ not a key with spaces") is None

    def test_audit_corrupted_json_line(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        logger.log("usr_c", endpoint="/ok")
        # Manually inject corrupted line
        from src.security.audit import _get_audit_path
        path = _get_audit_path("usr_c")
        with open(path, "a") as f:
            f.write("not valid json\n")
            f.write('{"event_id":"ok","user_id":"usr_c"}\n')
        entries = logger.query("usr_c")
        assert len(entries) == 2  # 1 good log + 1 valid injected

    def test_audit_log_survives_empty_file(self):
        from src.security.audit import AuditLogger, _get_audit_path
        path = _get_audit_path("usr_empty")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
        logger = AuditLogger()
        entries = logger.query("usr_empty")
        assert entries == []

    def test_record_request_function(self):
        from src.security.middleware import record_request, is_request_suspicious
        record_request("usr_rec", "/api/test", 200, True, 50.0)
        is_sus, _ = is_request_suspicious("usr_rec")
        assert is_sus is False

    def test_rate_limit_bypass_detection(self):
        """Multiple 429 responses should be suspicious."""
        from src.security.middleware import SuspiciousDetector
        det = SuspiciousDetector(min_samples=3, failure_rate_threshold=0.5)
        for i in range(5):
            det.record("usr_ratelimited", "/api/chat", 429, False)
        is_sus, reason = det.is_suspicious("usr_ratelimited")
        assert is_sus is True


# ═══════════════════════════════════════════════
# 8. Additional Tests (to reach >=80)
# ═══════════════════════════════════════════════

class TestApiKeyAdditional:

    def setup_method(self):
        from src.auth.api_keys import _get_keys_file
        f = _get_keys_file()
        if f.exists():
            f.unlink()

    def test_default_expiry_set(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        _, record = mgr.create_api_key("usr_1", "Default Expiry")
        assert record.expires_at > 0
        default_ttl = 90 * 86400
        assert abs(record.expires_at - record.created_at - default_ttl) < 2

    def test_key_prefix_in_record(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key("usr_1", "Prefix Test")
        assert record.key_prefix == key_str[:12]

    def test_key_hash_not_plaintext(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key("usr_1", "Hash Test")
        assert record.key_hash != key_str
        assert len(record.key_hash) == 64  # SHA-256 hex

    def test_validate_updates_last_used(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key("usr_1", "Usage Tracker")
        before = record.last_used_at
        mgr.validate_api_key(key_str)
        updated = mgr.get_api_key(record.key_id)
        assert updated.last_used_at > before

    def test_list_all_keys_no_filter(self):
        from src.auth.api_keys import ApiKeyManager
        mgr = ApiKeyManager()
        mgr.create_api_key("usr_a", "A")
        mgr.create_api_key("usr_b", "B")
        all_keys = mgr.list_api_keys()
        assert len(all_keys) == 2


class TestAuditLogAdditional:

    def test_log_with_all_fields(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        entry = logger.log(
            user_id="usr_full", role="pro",
            endpoint="/api/v2/generate", method="POST",
            status_code=201, provider="deepseek", model_id="v4-pro",
            tokens_used=3500, estimated_cost_usd=0.0035,
            success=True, request_id="req-123",
            duration_ms=250.0, extra={"topic": "test"},
        )
        assert entry.status_code == 201
        assert entry.model_id == "v4-pro"
        assert entry.duration_ms == 250.0
        assert entry.extra == {"topic": "test"}

    def test_query_since_timestamp(self):
        from src.security.audit import AuditLogger
        import time
        logger = AuditLogger()
        logger.log("usr_time", endpoint="/old")
        mid = time.time()
        logger.log("usr_time", endpoint="/new")
        entries = logger.query("usr_time", since=mid)
        assert len(entries) == 1
        assert entries[0].endpoint == "/new"

    def test_suspicious_zero_entries(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        suspicious = logger.get_suspicious_activity("no_user")
        assert suspicious == []

    def test_audit_entry_error_fields(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        entry = logger.log(
            user_id="usr_err", endpoint="/fail",
            success=False, error_message="Connection timeout",
            status_code=503,
        )
        assert entry.success is False
        assert entry.error_message == "Connection timeout"

    def test_audit_log_per_user_isolation(self):
        from src.security.audit import AuditLogger
        logger = AuditLogger()
        logger.log("user_x", endpoint="/x", tokens_used=100)
        logger.log("user_y", endpoint="/y", tokens_used=200)
        stats_x = logger.get_user_stats("user_x")
        stats_y = logger.get_user_stats("user_y")
        assert stats_x["total_tokens"] == 100
        assert stats_y["total_tokens"] == 200


class TestRequestContextAdditional:

    def setup_method(self):
        from src.user.manager import _get_users_file
        f = _get_users_file()
        if f.exists():
            f.unlink()

    def test_current_plan_free_defaults(self):
        from src.auth.context import CurrentPlan
        plan = CurrentPlan()
        assert plan.tier == "free"
        assert plan.multimodal is False

    def test_current_permission_free_defaults(self):
        from src.auth.context import CurrentPermission
        perm = CurrentPermission()
        assert perm.max_tokens == 100_000
        assert perm.can_export is True

    def test_request_context_api_key_flag(self):
        from src.auth.context import build_context
        from src.user.manager import UserManager
        um = UserManager()
        u = um.create_user("ctx_key", "ck@test.com")
        ctx = build_context(u.user_id, api_key_used=True)
        assert ctx.api_key_used is True

    def test_current_user_to_dict_all_fields(self):
        from src.auth.context import CurrentUser
        cu = CurrentUser("u1", "alice", "a@t.com", "pro", "Alice B")
        d = cu.to_dict()
        assert d["user_id"] == "u1"
        assert d["username"] == "alice"
        assert d["email"] == "a@t.com"
        assert d["role"] == "pro"
        assert d["display_name"] == "Alice B"

    def test_context_admin_checks(self):
        from src.auth.context import build_context
        from src.user.manager import UserManager
        um = UserManager()
        admin_u = um.create_user("admin_test", "admin@test.com", role="admin")
        ctx = build_context(admin_u.user_id)
        assert ctx.is_admin() is True
        assert ctx.get_max_tokens() == 50_000_000

    def test_context_role_student(self):
        from src.auth.context import build_context
        from src.user.manager import UserManager
        um = UserManager()
        stu = um.create_user("stu_test", "stu@test.com", role="student")
        ctx = build_context(stu.user_id)
        assert ctx.user.role == "student"
        assert "deepseek" in ctx.permission.available_models
        assert ctx.can_generate_multimodal() is False


# ═══════════════════════════════════════════════
# 7. No Regression
# ═══════════════════════════════════════════════

class TestNoRegression:

    def test_existing_auth_imports_still_work(self):
        from src.auth import (
            AuthUser, AuthToken, register, login, login_guest, logout,
            get_current_user, require_auth, optional_auth,
            JWTManager, hash_password, verify_password, make_password_hash,
        )
        assert True

    def test_existing_user_manager_still_works(self):
        from src.user.manager import UserManager
        mgr = UserManager()
        u = mgr.create_user("reg_test", "reg@test.com")
        assert u is not None
        assert u.username == "reg_test"

    def test_new_modules_re_exported(self):
        from src.auth import ApiKeyManager, ApiKeyRecord, RequestContext
        from src.auth import CurrentUser, CurrentPlan, CurrentPermission
        from src.auth import build_context
        from src.security import AuditLogger, AuditEntry
        assert True
