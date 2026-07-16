"""
Phase 4.2.6 — EventBus Isolation Tests

Verifies that independent EventBus instances prevent trace
cross-contamination across concurrent API requests.

Strategy:
  1. Direct A3Workflow test: two workflows with separate buses
  2. Threaded API test: two concurrent TestClient calls
"""

from __future__ import annotations

import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.workflow import A3Workflow
from src.core.event_bus import AgentEventBus
from src.memory.memory_manager import MemoryManager

import tempfile

GOAL_A = "学习 Python 装饰器和生成器"
GOAL_B = "学习 Docker 容器化部署"


def _make_workflow(bus=None):
    tmp = tempfile.mkdtemp(prefix="a3_bus_iso_")
    return A3Workflow(
        memory_manager=MemoryManager(storage_root=tmp),
        student_id="iso_test",
        bus=bus,
    )


# ──────────────────────────────────────────────
# 1. Direct Workflow — Independent EventBus
# ──────────────────────────────────────────────

class TestDirectWorkflowIsolation:
    def test_two_workflows_separate_buses(self):
        """两个 workflow 使用独立 EventBus，trace 互不干扰."""
        bus_a = AgentEventBus()
        bus_b = AgentEventBus()

        wf_a = _make_workflow(bus=bus_a)
        wf_b = _make_workflow(bus=bus_b)

        result_a = wf_a.run(user_goal=GOAL_A)
        result_b = wf_b.run(user_goal=GOAL_B)

        assert result_a.success
        assert result_b.success

        # 各自的 trace 只包含自己的 session 事件
        assert len(result_a.trace) > 0
        assert len(result_b.trace) > 0

        # trace 中的 input 与各自 goal 匹配
        a_outputs = {t.get("output", "") for t in result_a.trace}
        b_outputs = {t.get("output", "") for t in result_b.trace}

        # A 不应包含 B 的内容
        assert not any("Docker" in o for o in a_outputs)
        assert not any("容器化" in o for o in a_outputs)
        # B 不应包含 A 的内容
        assert not any("装饰器" in o for o in b_outputs)
        assert not any("生成器" in o for o in b_outputs)

    def test_sequential_calls_no_accumulation(self):
        """同一 workflow 连续两次 run()，trace 不累积上一次的事件."""
        bus = AgentEventBus()
        wf = _make_workflow(bus=bus)

        r1 = wf.run(user_goal=GOAL_A)
        r2 = wf.run(user_goal=GOAL_B)

        # run() 内部 clear() 清空了上一次的事件
        # 两个 trace 大小应该相近（同数量的 agent steps）
        assert abs(len(r1.trace) - len(r2.trace)) <= 1  # ±1 容忍度


# ──────────────────────────────────────────────
# 2. Threaded API — Concurrent Requests
# ──────────────────────────────────────────────

class TestThreadedAPIIsolation:
    def test_concurrent_api_requests_isolated(self):
        """两个并发 API 请求各自独立 trace，互不交叉."""
        results = {}

        def call_a():
            from src.api.dependencies import get_workflow
            wf = get_workflow(provider_mode="rule", student_id="thread_a")
            r = wf.run(user_goal=GOAL_A)
            results["a"] = r

        def call_b():
            from src.api.dependencies import get_workflow
            wf = get_workflow(provider_mode="rule", student_id="thread_b")
            r = wf.run(user_goal=GOAL_B)
            results["b"] = r

        t_a = threading.Thread(target=call_a)
        t_b = threading.Thread(target=call_b)

        t_a.start()
        t_b.start()
        t_a.join()
        t_b.join()

        assert "a" in results
        assert "b" in results
        assert results["a"].success
        assert results["b"].success

        trace_a = results["a"].trace
        trace_b = results["b"].trace

        assert len(trace_a) > 0
        assert len(trace_b) > 0

        # 验证 trace 数量一致（同时启动的 session，agent 执行次数相同）
        assert len(trace_a) == len(trace_b)

        # 关键断言：两个 trace 是不同对象（不是共享引用）
        assert trace_a is not trace_b

        # 各自 trace 只包含自己的 goal 痕迹
        # thread_a → GOAL_A (装饰器/生成器)
        # thread_b → GOAL_B (Docker/容器化)
        a_all_text = " ".join(str(t) for t in trace_a)
        b_all_text = " ".join(str(t) for t in trace_b)

        # A 不包含 B 的关键词
        assert "Docker" not in a_all_text
        assert "容器化" not in a_all_text
        # B 不包含 A 的关键词
        assert "装饰器" not in b_all_text
        assert "生成器" not in b_all_text


# ──────────────────────────────────────────────
# 3. Backward Compat — Global EventBus still works
# ──────────────────────────────────────────────

class TestBackwardCompat:
    def test_no_bus_defaults_to_global_singleton(self):
        """不传 bus 参数时，仍使用全局单例 (Streamlit 兼容)."""
        wf = _make_workflow()  # 不传 bus
        assert wf._owns_bus is False
        assert wf._bus is AgentEventBus.get_instance()

    def test_explicit_none_defaults_to_global_singleton(self):
        """显式传 bus=None 也走全局单例."""
        wf = _make_workflow(bus=None)
        assert wf._owns_bus is False
        assert wf._bus is AgentEventBus.get_instance()

    def test_with_bus_owns_instance(self):
        """传入独立 EventBus 时标记为 owns."""
        bus = AgentEventBus()
        wf = _make_workflow(bus=bus)
        assert wf._owns_bus is True
        assert wf._bus is bus  # 同一个实例，不是全局单例

    def test_workflow_still_succeeds_with_global_singleton(self):
        """全局单例模式下 run() 仍然成功 (Streamlit 路径)."""
        wf = _make_workflow()  # 全局单例
        result = wf.run(user_goal=GOAL_A)
        assert result.success
        assert len(result.trace) >= 5
        assert result.memory_saved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
