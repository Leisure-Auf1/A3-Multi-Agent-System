"""
Phase 9.4-A — Orchestration Analytics Tests

Covers:
- DecisionAnalytics: log parsing, statistics, fallback count, cost calculation
- Runtime metrics: counters, averages, get_metrics()
- ModelExecutionContext: estimated_cost, fallback_chain serialization
- Empty workspace handling
- Multi-user isolation
- Edge cases
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.orchestration.analytics import DecisionAnalytics, _get_log_path
from src.orchestration.runtime import OrchestratorRuntime, get_runtime
from src.orchestration.context import ModelExecutionContext, ExecutionResult


# ═══════════════════════════════════════════════════════════════
# HTTP mock (for runtime tests)
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


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _write_log(tmp_path, student_id, entries):
    """Write test decision log entries."""
    log_dir = tmp_path / student_id / "history"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "model_decisions.jsonl"
    with open(log_path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return log_path


# ═══════════════════════════════════════════════════════════════
# 1. Decision Analytics — Basic
# ═══════════════════════════════════════════════════════════════

class TestDecisionAnalyticsBasic:
    """DecisionAnalytics: log loading and basic stats."""

    def test_empty_workspace(self, tmp_path):
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("no-student")
            summary = analytics.get_summary()
            assert summary["total_requests"] == 0
            assert summary["models"] == {}

    def test_single_entry(self, tmp_path):
        log = [{
            "task_type": "chat", "agent_name": "TutorAgent",
            "student_id": "s1", "selected_model": "gpt-4o",
            "selected_provider": "openai", "success": True,
            "fallback_used": False, "latency_ms": 150.0,
            "usage_prompt_tokens": 10, "usage_completion_tokens": 20,
            "timestamp": time.time(),
        }]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            summary = analytics.get_summary()
            assert summary["total_requests"] == 1
            assert summary["success_rate"] == 100.0

    def test_model_usage_counts(self, tmp_path):
        log = [
            {"task_type": "chat", "selected_model": "gpt-4o", "selected_provider": "openai", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
            {"task_type": "chat", "selected_model": "gpt-4o", "selected_provider": "openai", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
            {"task_type": "chat", "selected_model": "deepseek-v3", "selected_provider": "deepseek", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            usage = analytics.get_model_usage()
            assert usage["gpt-4o"] == 2
            assert usage["deepseek-v3"] == 1

    def test_provider_success_rates(self, tmp_path):
        log = [
            {"selected_provider": "openai", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
            {"selected_provider": "openai", "success": False, "fallback_used": True, "latency_ms": 100, "timestamp": time.time()},
            {"selected_provider": "deepseek", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            rates = analytics.get_provider_success_rates()
            assert rates["openai"]["total"] == 2
            assert rates["openai"]["success_rate"] == 50.0
            assert rates["deepseek"]["success_rate"] == 100.0

    def test_task_distribution(self, tmp_path):
        log = [
            {"task_type": "chat", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
            {"task_type": "chat", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
            {"task_type": "generate_material", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            tasks = analytics.get_task_distribution()
            assert tasks["chat"] == 2
            assert tasks["generate_material"] == 1

    def test_entry_count(self, tmp_path):
        log = [{"success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()} for _ in range(5)]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            assert analytics.get_entry_count() == 5


# ═══════════════════════════════════════════════════════════════
# 2. Decision Analytics — Cost Calculation
# ═══════════════════════════════════════════════════════════════

class TestAnalyticsCost:
    """Cost estimation from decision logs."""

    def test_cost_calculation(self, tmp_path):
        log = [{
            "selected_provider": "openai",
            "usage_prompt_tokens": 1000,
            "usage_completion_tokens": 500,
            "success": True, "fallback_used": False, "latency_ms": 100,
            "timestamp": time.time(),
        }]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            cost = analytics.get_estimated_cost()
            # 1500 tokens / 1M * $2.50 = $0.00375
            assert cost > 0
            assert cost < 0.01

    def test_cost_multiple_providers(self, tmp_path):
        log = [
            {"selected_provider": "openai", "usage_prompt_tokens": 1000, "usage_completion_tokens": 0,
             "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
            {"selected_provider": "deepseek", "usage_prompt_tokens": 10000, "usage_completion_tokens": 0,
             "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            cost = analytics.get_estimated_cost()
            # OpenAI 1K * $2.50/1M + DeepSeek 10K * $0.14/1M ≈ $0.0025 + $0.0014
            assert cost > 0.003
            assert cost < 0.005


# ═══════════════════════════════════════════════════════════════
# 3. Decision Analytics — Fallback & Latency
# ═══════════════════════════════════════════════════════════════

class TestAnalyticsFallback:
    """Fallback rate and latency analytics."""

    def test_fallback_rate(self, tmp_path):
        log = [
            {"fallback_used": False, "success": True, "latency_ms": 100, "timestamp": time.time()},
            {"fallback_used": False, "success": True, "latency_ms": 100, "timestamp": time.time()},
            {"fallback_used": True, "success": True, "latency_ms": 100, "timestamp": time.time()},
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            assert analytics.get_fallback_rate() == pytest.approx(33.3, 0.1)

    def test_avg_latency(self, tmp_path):
        log = [
            {"latency_ms": 100, "success": True, "fallback_used": False, "timestamp": time.time()},
            {"latency_ms": 300, "success": True, "fallback_used": False, "timestamp": time.time()},
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            summary = analytics.get_summary()
            assert summary["avg_latency_ms"] == 200.0

    def test_success_rate(self, tmp_path):
        log = [
            {"success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
            {"success": False, "fallback_used": True, "latency_ms": 100, "timestamp": time.time()},
            {"success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()},
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            summary = analytics.get_summary()
            assert summary["success_rate"] == pytest.approx(66.7, 0.1)


# ═══════════════════════════════════════════════════════════════
# 4. Decision Analytics — Recent Entries
# ═══════════════════════════════════════════════════════════════

class TestAnalyticsRecent:
    """Recent entries and edge cases."""

    def test_recent_entries(self, tmp_path):
        t0 = time.time()
        log = [
            {"success": True, "fallback_used": False, "latency_ms": 100, "timestamp": t0 - 100, "task_type": f"task{i}"}
            for i in range(10)
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            recent = analytics.get_recent_entries(limit=3)
            assert len(recent) == 3

    def test_malformed_json_skipped(self, tmp_path):
        """Malformed lines are silently skipped."""
        log_dir = tmp_path / "s1" / "history"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "model_decisions.jsonl", "w") as f:
            f.write('{"valid": true, "success": true, "fallback_used": false, "latency_ms": 1, "timestamp": 1}\n')
            f.write("NOT VALID JSON\n")
            f.write('{"also_valid": true, "success": true, "fallback_used": false, "latency_ms": 1, "timestamp": 1}\n')

        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            assert analytics.get_entry_count() == 2  # malformed skipped

    def test_no_file_is_ok(self, tmp_path):
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("unknown-student")
            assert analytics.get_entry_count() == 0
            summary = analytics.get_summary()
            assert summary["total_requests"] == 0

    def test_daily_requests(self, tmp_path):
        t = time.time()
        log = [
            {"success": True, "fallback_used": False, "latency_ms": 1, "timestamp": t - 86400 * 2},
            {"success": True, "fallback_used": False, "latency_ms": 1, "timestamp": t - 86400},
            {"success": True, "fallback_used": False, "latency_ms": 1, "timestamp": t},
        ]
        _write_log(tmp_path, "s1", log)
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("s1")
            summary = analytics.get_summary()
            assert len(summary["daily_requests"]) == 3


# ═══════════════════════════════════════════════════════════════
# 5. ModelExecutionContext — New Fields
# ═══════════════════════════════════════════════════════════════

class TestContextNewFields:
    """estimated_cost and fallback_chain serialization."""

    def test_context_has_new_fields(self):
        ctx = ModelExecutionContext(
            estimated_cost=0.005,
            fallback_chain=["openai", "deepseek"],
        )
        assert ctx.estimated_cost == 0.005
        assert ctx.fallback_chain == ["openai", "deepseek"]

    def test_context_to_dict_includes_new_fields(self):
        ctx = ModelExecutionContext(
            task_type="chat",
            selected_provider="openai",
            estimated_cost=0.003,
            fallback_chain=["openai"],
        )
        d = ctx.to_dict()
        assert d["estimated_cost"] == 0.003
        assert d["fallback_chain"] == ["openai"]

    def test_context_from_dict_new_fields(self):
        d = {"task_type": "chat", "estimated_cost": 0.007, "fallback_chain": ["a", "b"]}
        ctx = ModelExecutionContext.from_dict(d)
        assert ctx.estimated_cost == 0.007
        assert ctx.fallback_chain == ["a", "b"]

    def test_context_defaults(self):
        ctx = ModelExecutionContext()
        assert ctx.estimated_cost == 0.0
        assert ctx.fallback_chain == []

    def test_context_to_json_includes_cost(self):
        ctx = ModelExecutionContext(estimated_cost=0.005, task_type="chat")
        j = ctx.to_json()
        assert "0.005" in j


# ═══════════════════════════════════════════════════════════════
# 6. Runtime Metrics
# ═══════════════════════════════════════════════════════════════

class TestRuntimeMetrics:
    """OrchestratorRuntime metrics tracking."""

    def test_initial_metrics(self):
        rt = OrchestratorRuntime()
        m = rt.get_metrics()
        assert m["total_calls"] == 0
        assert m["success_calls"] == 0
        assert m["error_calls"] == 0

    def test_metrics_after_success(self, mock_http):
        rt = OrchestratorRuntime()
        rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        m = rt.get_metrics()
        assert m["total_calls"] == 1
        assert m["success_calls"] == 1

    def test_metrics_after_failure(self, mock_http):
        import urllib.error
        with mock.patch("urllib.request.urlopen") as m2:
            m2.side_effect = urllib.error.HTTPError("url", 500, "err", {}, __import__("io").BytesIO(b"{}"))
            rt = OrchestratorRuntime()
            rt.execute(task_type="chat", prompt="Hi", agent_name="T")
            m = rt.get_metrics()
            # After 3 failed attempts, total_calls increments once for the exhaustion path
            assert m["total_calls"] >= 1

    def test_metrics_avg_latency(self, mock_http):
        rt = OrchestratorRuntime()
        rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        m = rt.get_metrics()
        assert m["avg_latency_ms"] > 0
        assert m["total_calls"] == 2

    def test_metrics_success_rate(self, mock_http):
        rt = OrchestratorRuntime()
        rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        m = rt.get_metrics()
        assert m["success_rate"] == 100.0

    def test_metrics_cost_tracking(self, mock_http):
        rt = OrchestratorRuntime()
        rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        m = rt.get_metrics()
        assert "total_cost" in m

    def test_metrics_fallback_rate_zero_on_success(self, mock_http):
        rt = OrchestratorRuntime()
        rt.execute(task_type="chat", prompt="Hi", agent_name="T")
        m = rt.get_metrics()
        assert m["fallback_rate"] == 0.0

    def test_metrics_reset_not_available(self):
        """Metrics accumulate; no reset method exposed (by design)."""
        rt = OrchestratorRuntime()
        assert not hasattr(rt, "reset_metrics")


# ═══════════════════════════════════════════════════════════════
# 7. Runtime Decision Logging with New Fields
# ═══════════════════════════════════════════════════════════════

class TestRuntimeDecisionLog:
    """Decision log now includes estimated_cost and fallback_chain."""

    def test_success_context_has_cost(self, mock_http, tmp_path):
        with mock.patch("src.orchestration.runtime.os.path.expanduser", return_value=str(tmp_path)):
            rt = OrchestratorRuntime()
            result = rt.execute(task_type="chat", prompt="Hi", agent_name="T", student_id="s1")
            assert result.context.estimated_cost > 0
            assert result.context.fallback_chain == []

    def test_decision_log_written_with_new_fields(self, mock_http, tmp_path):
        with mock.patch("src.orchestration.runtime.os.path.expanduser", return_value=str(tmp_path)):
            rt = OrchestratorRuntime()
            rt.execute(task_type="chat", prompt="Hi", agent_name="T", student_id="s1")

            log_path = tmp_path / "s1" / "history" / "model_decisions.jsonl"
            assert log_path.exists()
            content = log_path.read_text()
            assert "estimated_cost" in content
            assert "fallback_chain" in content

    def test_cost_calc_uses_provider_rate(self, mock_http):
        rt = OrchestratorRuntime()
        cost = rt._calc_cost("openai", 1000, 500)
        # 1500/1M * 2.50 = 0.00375
        assert cost > 0.003
        assert cost < 0.004

    def test_cost_calc_deepseek_cheaper(self, mock_http):
        rt = OrchestratorRuntime()
        cost_openai = rt._calc_cost("openai", 10000, 0)
        cost_deepseek = rt._calc_cost("deepseek", 10000, 0)
        assert cost_deepseek < cost_openai


# ═══════════════════════════════════════════════════════════════
# 8. Settings UI Functions
# ═══════════════════════════════════════════════════════════════

class TestSettingsUI:
    """Settings tab functions exist."""

    def test_render_orchestrator_dashboard_exists(self):
        from web.settings_tab import render_orchestrator_dashboard
        assert callable(render_orchestrator_dashboard)

    def test_render_model_status_page_exists(self):
        from web.settings_tab import render_model_status_page
        assert callable(render_model_status_page)


# ═══════════════════════════════════════════════════════════════
# 9. Multi-User Isolation
# ═══════════════════════════════════════════════════════════════

class TestMultiUserIsolation:
    """Different students have separate decision logs."""

    def test_different_students_separate_logs(self, tmp_path):
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            log_a = [{"selected_model": "gpt-4o", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()}]
            log_b = [{"selected_model": "deepseek-v3", "success": True, "fallback_used": False, "latency_ms": 100, "timestamp": time.time()} for _ in range(3)]
            _write_log(tmp_path, "student-a", log_a)
            _write_log(tmp_path, "student-b", log_b)

            analytics_a = DecisionAnalytics("student-a")
            analytics_b = DecisionAnalytics("student-b")

            assert analytics_a.get_entry_count() == 1
            assert analytics_b.get_entry_count() == 3


# ═══════════════════════════════════════════════════════════════
# 10. Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Boundary conditions."""

    def test_context_cost_rounding(self):
        ctx = ModelExecutionContext(estimated_cost=0.12345678)
        d = ctx.to_dict()
        assert d["estimated_cost"] == 0.123457  # 6 decimal places

    def test_empty_fallback_chain(self):
        ctx = ModelExecutionContext(fallback_chain=[])
        d = ctx.to_dict()
        assert d["fallback_chain"] == []

    def test_analytics_get_summary_empty(self, tmp_path):
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("empty")
            s = analytics.get_summary()
            assert s["student_id"] == "empty"
            assert s["total_requests"] == 0

    def test_analytics_provider_rates_empty(self, tmp_path):
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("empty")
            rates = analytics.get_provider_success_rates()
            assert rates == {}

    def test_analytics_task_distribution_empty(self, tmp_path):
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("empty")
            tasks = analytics.get_task_distribution()
            assert tasks == {}

    def test_analytics_recent_entries_empty(self, tmp_path):
        with mock.patch("src.orchestration.analytics.os.path.expanduser", return_value=str(tmp_path)):
            analytics = DecisionAnalytics("empty")
            recent = analytics.get_recent_entries()
            assert recent == []

    def test_runtime_metrics_before_any_calls(self):
        rt = OrchestratorRuntime()
        m = rt.get_metrics()
        assert m["avg_latency_ms"] == 0.0
        assert m["success_rate"] == 0.0
