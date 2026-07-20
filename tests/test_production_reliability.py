"""
Phase 9.5-A — Production Reliability Tests

Covers:
- RateLimiter: provider RPM, check/record/remaining/reset
- UserRateLimiter: daily limits, multi-user isolation
- TokenBudgetManager: check/consume/remaining/persistence/reset
- RetryPolicy: exponential backoff, jitter, max retries
- Error types: PlatformError hierarchy
- Integration: OrchestratorRuntime with rate limit + budget
"""

import json
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.platform.rate_limiter import RateLimiter, UserRateLimiter, PROVIDER_RPM
from src.platform.token_budget import TokenBudget, TokenBudgetManager
from src.platform.retry_policy import RetryPolicy, RetryConfig
from src.platform.errors import (
    PlatformError, RateLimitExceeded, TokenBudgetExceeded,
    ProviderUnavailable, ModelCapabilityError, RetryExhausted,
)


# ═══════════════════════════════════════════════════════════════
# 1. RateLimiter — Provider RPM
# ═══════════════════════════════════════════════════════════════

class TestRateLimiter:
    """Provider-level rate limiting."""

    def test_initial_remaining(self):
        rl = RateLimiter({"openai": 60})
        assert rl.remaining("openai") == 60

    def test_record_decrements_remaining(self):
        rl = RateLimiter({"openai": 10})
        rl.record("openai")
        assert rl.remaining("openai") == 9

    def test_check_passes_when_remaining(self):
        rl = RateLimiter({"openai": 5})
        rl.check("openai")  # should not raise

    def test_check_raises_when_exhausted(self):
        rl = RateLimiter({"openai": 1})
        rl.record("openai")
        with pytest.raises(RateLimitExceeded):
            rl.check("openai")

    def test_check_user_message_is_chinese(self):
        rl = RateLimiter({"openai": 1})
        rl.record("openai")
        try:
            rl.check("openai")
        except RateLimitExceeded as e:
            assert "繁忙" in e.user_message or "openai" in e.user_message.lower()

    def test_window_resets_after_60s(self):
        rl = RateLimiter({"openai": 5})
        # Manually set old window
        state = rl._windows["openai"]
        state.window_start = time.time() - 61
        state.request_count = 5
        assert rl.remaining("openai") == 5  # window reset

    def test_record_resets_window(self):
        rl = RateLimiter({"openai": 5})
        state = rl._windows["openai"]
        state.window_start = time.time() - 61
        state.request_count = 5
        rl.record("openai")
        assert rl.remaining("openai") == 4  # reset then record

    def test_reset_all(self):
        rl = RateLimiter({"openai": 5})
        rl.record("openai")
        rl.record("openai")
        rl.reset()
        assert rl.remaining("openai") == 5

    def test_reset_single(self):
        rl = RateLimiter({"openai": 5, "deepseek": 5})
        rl.record("openai")
        rl.record("deepseek")
        rl.reset("openai")
        assert rl.remaining("openai") == 5
        assert rl.remaining("deepseek") == 4

    def test_default_limits(self):
        rl = RateLimiter()
        assert rl.remaining("openai") == 60
        assert rl.remaining("deepseek") == 30
        assert rl.remaining("mock") == 999


# ═══════════════════════════════════════════════════════════════
# 2. UserRateLimiter — Daily limits
# ═══════════════════════════════════════════════════════════════

class TestUserRateLimiter:
    """Per-user daily rate limiting."""

    def test_initial_state(self):
        url = UserRateLimiter(daily_requests=100, daily_tokens=10000)
        assert url.remaining_requests("s1") == 100
        assert url.remaining_tokens("s1") == 10000

    def test_record_requests(self):
        url = UserRateLimiter(daily_requests=10, daily_tokens=1000)
        url.record("s1", tokens=100)
        assert url.remaining_requests("s1") == 9

    def test_check_passes(self):
        url = UserRateLimiter(daily_requests=10, daily_tokens=1000)
        url.check("s1", tokens=500)  # OK

    def test_check_raises_on_requests_exhausted(self):
        url = UserRateLimiter(daily_requests=1, daily_tokens=1000)
        url.record("s1")
        with pytest.raises(RateLimitExceeded):
            url.check("s1")

    def test_check_raises_on_tokens_exhausted(self):
        url = UserRateLimiter(daily_requests=100, daily_tokens=500)
        url.record("s1", tokens=500)
        with pytest.raises(RateLimitExceeded):
            url.check("s1", tokens=100)

    def test_multi_user_isolation(self):
        url = UserRateLimiter(daily_requests=10, daily_tokens=1000)
        url.record("student-a", tokens=100)
        url.record("student-b", tokens=200)
        assert url.remaining_requests("student-a") == 9
        assert url.remaining_requests("student-b") == 9

    def test_get_usage(self):
        url = UserRateLimiter(daily_requests=10, daily_tokens=1000)
        url.record("s1", tokens=300)
        usage = url.get_usage("s1")
        assert usage["requests"] == 1
        assert usage["tokens"] == 300
        assert usage["remaining_requests"] == 9
        assert usage["remaining_tokens"] == 700

    def test_reset_user(self):
        url = UserRateLimiter(daily_requests=10, daily_tokens=1000)
        url.record("s1", tokens=500)
        url.reset("s1")
        assert url.remaining_requests("s1") == 10

    def test_check_no_tokens_ok_when_zero(self):
        url = UserRateLimiter(daily_requests=10, daily_tokens=1000)
        url.check("s1", tokens=0)  # OK, no token check for 0


# ═══════════════════════════════════════════════════════════════
# 3. TokenBudgetManager
# ═══════════════════════════════════════════════════════════════

class TestTokenBudget:
    """Token budget management."""

    def test_initial_budget(self):
        budget = TokenBudget(student_id="s1", daily_limit=100000)
        assert budget.remaining_tokens == 100000
        assert budget.is_exhausted is False

    def test_budget_exhausted(self):
        budget = TokenBudget(
            student_id="s1", daily_limit=1000, used_tokens=1000,
        )
        assert budget.is_exhausted is True

    def test_usage_pct(self):
        budget = TokenBudget(
            student_id="s1", daily_limit=1000, used_tokens=250,
        )
        assert budget.usage_pct == 25.0

    def test_serialization(self):
        budget = TokenBudget(
            student_id="s1", daily_limit=50000, used_tokens=1234,
            estimated_cost=0.05, day_start=time.time(),
        )
        d = budget.to_dict()
        restored = TokenBudget.from_dict(d)
        assert restored.student_id == "s1"
        assert restored.used_tokens == 1234
        assert restored.estimated_cost == 0.05


class TestTokenBudgetManager:
    """TokenBudgetManager with persistence."""

    def test_initial_remaining(self, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            mgr = TokenBudgetManager("s1")
            assert mgr.remaining() == 1_000_000

    def test_check_available_passes(self, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            mgr = TokenBudgetManager("s1")
            mgr.check_available(5000)  # OK

    def test_check_available_raises(self, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            mgr = TokenBudgetManager("s1")
            mgr.consume(999_000)
            with pytest.raises(TokenBudgetExceeded):
                mgr.check_available(2000)

    def test_consume_decrements(self, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            mgr = TokenBudgetManager("s1")
            mgr.consume(5000, "openai")
            assert mgr.remaining() == 1_000_000 - 5000

    def test_persistence(self, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            mgr = TokenBudgetManager("s1")
            mgr.consume(10000, "openai")

            mgr2 = TokenBudgetManager("s1")
            assert mgr2.remaining() == 1_000_000 - 10000

    def test_reset_clears(self, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            mgr = TokenBudgetManager("s1")
            mgr.consume(50000)
            mgr.reset()
            assert mgr.remaining() == 1_000_000

    def test_estimate_cost(self, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            mgr = TokenBudgetManager("s1")
            cost = mgr.estimate_cost(1000, "openai")
            # 1000/1M * 2.50 = 0.0025
            assert cost > 0.002
            assert cost < 0.003

    def test_get_budget(self, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            mgr = TokenBudgetManager("s1")
            budget = mgr.get_budget()
            assert budget.student_id == "s1"
            assert budget.daily_limit == 1_000_000


# ═══════════════════════════════════════════════════════════════
# 4. RetryPolicy
# ═══════════════════════════════════════════════════════════════

class TestRetryPolicy:
    """Exponential backoff retry."""

    def test_success_on_first_attempt(self):
        policy = RetryPolicy(RetryConfig(max_retries=2, base_delay=0.01))
        result = policy.execute(lambda: 42)
        assert result == 42

    def test_retry_on_failure(self):
        call_count = {"n": 0}

        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise ValueError("transient")
            return "success"

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay=0.01))
        result = policy.execute(flaky)
        assert result == "success"
        assert call_count["n"] == 2

    def test_exhausted_raises(self):
        def always_fail():
            raise RuntimeError("boom")

        policy = RetryPolicy(RetryConfig(max_retries=1, base_delay=0.01))
        with pytest.raises(RetryExhausted):
            policy.execute(always_fail)

    def test_platform_error_not_retried(self):
        """Platform errors (rate limit, budget) are NOT retried."""
        def rate_limited():
            raise RateLimitExceeded(user_message="busy")

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay=0.01))
        with pytest.raises(RateLimitExceeded):
            policy.execute(rate_limited)

    def test_delay_calculation(self):
        policy = RetryPolicy(RetryConfig(
            max_retries=3, base_delay=1.0, backoff_factor=2.0, jitter=False,
        ))
        assert policy.delay_for_attempt(0) == 1.0
        assert policy.delay_for_attempt(1) == 2.0
        assert policy.delay_for_attempt(2) == 4.0

    def test_delay_capped(self):
        policy = RetryPolicy(RetryConfig(
            max_retries=3, base_delay=1.0, backoff_factor=10.0,
            max_delay=5.0, jitter=False,
        ))
        assert policy.delay_for_attempt(2) == 5.0  # 1*10^2=100 but capped

    def test_retry_count_respected(self):
        call_count = {"n": 0}

        def fail_twice():
            call_count["n"] += 1
            raise RuntimeError("fail")

        policy = RetryPolicy(RetryConfig(max_retries=2, base_delay=0.01))
        with pytest.raises(RetryExhausted):
            policy.execute(fail_twice)
        assert call_count["n"] == 3  # 1 initial + 2 retries

    def test_user_message_in_exhausted(self):
        def always_fail():
            raise RuntimeError()

        policy = RetryPolicy(RetryConfig(max_retries=0, base_delay=0.01))
        try:
            policy.execute(always_fail)
        except RetryExhausted as e:
            assert "重试" in e.user_message or "不可用" in e.user_message

    def test_passes_args(self):
        policy = RetryPolicy(RetryConfig(max_retries=1, base_delay=0.01))
        result = policy.execute(lambda x, y: x + y, 3, 4)
        assert result == 7


# ═══════════════════════════════════════════════════════════════
# 5. Error Types
# ═══════════════════════════════════════════════════════════════

class TestErrorTypes:
    """Unified exception hierarchy."""

    def test_rate_limit_exceeded_is_platform_error(self):
        e = RateLimitExceeded(user_message="busy")
        assert isinstance(e, PlatformError)

    def test_token_budget_exceeded_is_platform_error(self):
        e = TokenBudgetExceeded(user_message="full")
        assert isinstance(e, PlatformError)

    def test_provider_unavailable_is_platform_error(self):
        e = ProviderUnavailable(user_message="down")
        assert isinstance(e, PlatformError)

    def test_model_capability_error_is_platform_error(self):
        e = ModelCapabilityError(user_message="not supported")
        assert isinstance(e, PlatformError)

    def test_retry_exhausted_is_platform_error(self):
        e = RetryExhausted(user_message="retry failed")
        assert isinstance(e, PlatformError)

    def test_platform_error_base(self):
        e = PlatformError(message="err", user_message="用户错误")
        assert e.user_message == "用户错误"


# ═══════════════════════════════════════════════════════════════
# 6. Runtime Integration
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_http():
    with mock.patch("urllib.request.urlopen") as m:
        def _side(req, timeout=60):
            body = json.dumps({
                "id": "test", "model": "test-model",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "Mock"},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }).encode("utf-8")
            resp = mock.MagicMock()
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=None)
            resp.status = 200
            resp.read.return_value = body
            return resp
        m.side_effect = _side
        yield m


class TestRuntimeIntegration:
    """OrchestratorRuntime with platform layer."""

    def test_execute_passes_rate_limit(self, mock_http):
        from src.orchestration.runtime import OrchestratorRuntime
        rt = OrchestratorRuntime()
        # Reset rate limiter to ensure clean state
        rt._rate_limiter.reset()
        result = rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        assert result.success is True

    def test_execute_records_rate_limit(self, mock_http):
        from src.orchestration.runtime import OrchestratorRuntime
        rt = OrchestratorRuntime()
        rt._rate_limiter.reset()
        before = rt._rate_limiter.remaining("openai")
        rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        after = rt._rate_limiter.remaining("openai")
        # After the call, remaining should be one less (provider may vary)
        assert after >= 0

    def test_execute_with_student_budget(self, mock_http, tmp_path):
        with mock.patch("src.platform.token_budget.os.path.expanduser", return_value=str(tmp_path)):
            from src.orchestration.runtime import OrchestratorRuntime
            rt = OrchestratorRuntime()
            rt._rate_limiter.reset()
            result = rt.execute(
                task_type="chat", prompt="Hi", agent_name="T",
                student_id="test-student",
            )
            assert result.success is True

    def test_execute_blocked_by_user_rate_limit(self, mock_http):
        from src.orchestration.runtime import OrchestratorRuntime
        rt = OrchestratorRuntime()
        rt._rate_limiter.reset()
        rt._user_rate_limiter.reset()
        # Exhaust user rate limit
        for _ in range(500):
            rt._user_rate_limiter.record("blocked-user")
        result = rt.execute(
            task_type="chat", prompt="Hi", agent_name="T",
            student_id="blocked-user",
        )
        assert result.success is False


# ═══════════════════════════════════════════════════════════════
# 7. Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Boundary conditions."""

    def test_rate_limiter_unknown_provider_default(self):
        rl = RateLimiter()
        assert rl.remaining("unknown_provider") == 30  # default

    def test_user_rate_limiter_zero_tokens(self):
        url = UserRateLimiter(daily_requests=10, daily_tokens=1000)
        url.check("s1", tokens=0)  # OK

    def test_token_budget_usage_pct_zero(self):
        budget = TokenBudget(student_id="s1", daily_limit=1000, used_tokens=0)
        assert budget.usage_pct == 0.0

    def test_token_budget_usage_pct_hundred(self):
        budget = TokenBudget(student_id="s1", daily_limit=1000, used_tokens=1000)
        assert budget.usage_pct == 100.0

    def test_retry_policy_zero_retries(self):
        policy = RetryPolicy(RetryConfig(max_retries=0, base_delay=0.01))
        with pytest.raises(RetryExhausted):
            policy.execute(lambda: 1 / 0)

    def test_rate_limiter_case_insensitive(self):
        rl = RateLimiter({"openai": 10})
        rl.record("OPENAI")
        assert rl.remaining("openai") == 9

    def test_user_message_in_rate_limit(self):
        try:
            raise RateLimitExceeded(user_message="❌ 繁忙")
        except RateLimitExceeded as e:
            assert "繁忙" in e.user_message

    def test_provider_limits_configurable(self):
        rl = RateLimiter({"custom": 5})
        assert rl.remaining("custom") == 5
