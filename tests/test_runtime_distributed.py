"""
Phase 5.9 — Distributed Runtime Layer Tests

Covers:
  1. NodeStatus: enum values, is_available
  2. NodeCapability: creation, to_dict
  3. RuntimeNode: identity, heartbeat, status transitions
  4. RuntimeNode: capabilities, registry binding
  5. NodeRegistry: register, unregister, query
  6. NodeRegistry: discovery (by_capability, by_label, find_best)
  7. NodeRegistry: health (summary, check_health)
  8. DistributedEventBus: local-only, remote forwarding
  9. DistributedEventBus: broadcast, event_filter, InMemoryTransport
 10. RemoteExecutionManager: submit, execute, wait_for
 11. RemoteExecutionManager: task lifecycle, cancel, history
 12. DistributedTraceCollector: add_node_traces, query, aggregation
 13. Integration: full distributed pipeline
 14. Backward compatibility
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import time

from veritas.runtime import RuntimeEvent, RuntimeEventBus
from veritas.runtime.distributed import (
    RuntimeNode,
    NodeStatus,
    NodeCapability,
    NodeInfo,
    NodeRegistry,
    RegistryEvent,
    DistributedEventBus,
    InMemoryTransport,
    RemoteExecutionManager,
    RemoteTask,
    TaskStatus,
    DistributedTraceCollector,
    TraceEntry,
)


# ══════════════════════════════════════════════
# 1. NodeStatus
# ══════════════════════════════════════════════

class TestNodeStatus:
    def test_all_states(self):
        values = {s.value for s in NodeStatus}
        assert "healthy" in values
        assert "offline" in values

    def test_is_available(self):
        assert NodeStatus.HEALTHY.is_available is True
        assert NodeStatus.DEGRADED.is_available is True
        assert NodeStatus.OFFLINE.is_available is False
        assert NodeStatus.UNKNOWN.is_available is False


# ══════════════════════════════════════════════
# 2. NodeCapability + NodeInfo
# ══════════════════════════════════════════════

class TestNodeCapability:
    def test_create(self):
        c = NodeCapability(name="evaluation", version="2.0", max_concurrency=3)
        assert c.name == "evaluation"
        assert c.max_concurrency == 3

    def test_to_dict(self):
        c = NodeCapability(name="profile", metadata={"lang": "zh"})
        d = c.to_dict()
        assert d["name"] == "profile"
        assert d["metadata"]["lang"] == "zh"

    def test_node_info_to_dict(self):
        info = NodeInfo(name="n1", address="localhost:8001",
                        labels={"region": "us-east"})
        d = info.to_dict()
        assert d["name"] == "n1"
        assert d["labels"]["region"] == "us-east"


# ══════════════════════════════════════════════
# 3. RuntimeNode
# ══════════════════════════════════════════════

class TestRuntimeNode:
    @pytest.fixture
    def node(self):
        return RuntimeNode(name="worker-1", address="localhost:8001")

    def test_identity(self, node):
        assert node.name == "worker-1"
        assert node.address == "localhost:8001"

    def test_initial_status(self, node):
        assert node.status == NodeStatus.UNKNOWN

    def test_heartbeat(self, node):
        node.heartbeat()
        assert node.status == NodeStatus.HEALTHY
        assert node.is_available

    def test_mark_degraded(self, node):
        node.heartbeat()
        node.mark_degraded("high latency")
        assert node.status == NodeStatus.DEGRADED

    def test_mark_offline(self, node):
        node.heartbeat()
        node.mark_offline()
        assert node.status == NodeStatus.OFFLINE

    def test_capabilities(self, node):
        node.add_capability(NodeCapability(name="eval"))
        assert node.has_capability("eval")
        assert not node.has_capability("profile")

    def test_get_capability(self, node):
        node.add_capability(NodeCapability(name="eval", max_concurrency=5))
        c = node.get_capability("eval")
        assert c is not None
        assert c.max_concurrency == 5
        assert node.get_capability("nonexistent") is None

    def test_duplicate_capability(self, node):
        node.add_capability(NodeCapability(name="eval"))
        node.add_capability(NodeCapability(name="eval"))
        # Should not duplicate
        assert len(node.info.capabilities) == 1

    def test_to_dict(self, node):
        node.heartbeat()
        d = node.to_dict()
        assert d["info"]["name"] == "worker-1"
        assert d["status"] == "healthy"


# ══════════════════════════════════════════════
# 4. NodeRegistry — Registration
# ══════════════════════════════════════════════

class TestNodeRegistryRegistration:
    @pytest.fixture
    def registry(self):
        return NodeRegistry()

    def test_register(self, registry):
        n = RuntimeNode(name="w1", address="a1")
        registry.register_node(n)
        assert "w1" in registry
        assert len(registry) == 1

    def test_unregister(self, registry):
        n = RuntimeNode(name="w1", address="a1")
        registry.register_node(n)
        removed = registry.unregister_node("w1")
        assert removed is n
        assert len(registry) == 0

    def test_unregister_missing(self, registry):
        assert registry.unregister_node("nope") is None

    def test_get_node(self, registry):
        n = RuntimeNode(name="w1", address="a1")
        registry.register_node(n)
        assert registry.get_node("w1") is n
        assert registry.get_node("nope") is None

    def test_node_names(self, registry):
        registry.register_node(RuntimeNode(name="a", address="x"))
        registry.register_node(RuntimeNode(name="b", address="y"))
        names = registry.node_names()
        assert "a" in names
        assert "b" in names


# ══════════════════════════════════════════════
# 5. NodeRegistry — Query & Discovery
# ══════════════════════════════════════════════

class TestNodeRegistryDiscovery:
    @pytest.fixture
    def registry(self):
        r = NodeRegistry()
        n1 = RuntimeNode(name="w1", address="a1")
        n1.add_capability(NodeCapability(name="evaluation"))
        n1.heartbeat()
        r.register_node(n1)

        n2 = RuntimeNode(name="w2", address="a2")
        n2.add_capability(NodeCapability(name="profile"))
        n2.add_capability(NodeCapability(name="evaluation"))
        n2.heartbeat()
        r.register_node(n2)

        n3 = RuntimeNode(name="w3", address="a3")
        n3.add_capability(NodeCapability(name="profile"))
        n3.heartbeat()
        n3.mark_offline()
        r.register_node(n3)

        return r

    def test_list_healthy(self, registry):
        healthy = registry.list_healthy()
        assert len(healthy) == 2  # w1, w2

    def test_list_offline(self, registry):
        offline = registry.list_offline()
        assert len(offline) == 1  # w3

    def test_list_available(self, registry):
        available = registry.list_available()
        assert len(available) == 2

    def test_find_by_capability(self, registry):
        evaluators = registry.find_by_capability("evaluation")
        assert len(evaluators) == 2  # w1, w2
        profilers = registry.find_by_capability("profile")
        assert len(profilers) == 1  # only w2 (w3 is offline)

    def test_find_best_for(self, registry):
        best = registry.find_best_for("evaluation")
        assert best is not None
        assert best.status == NodeStatus.HEALTHY

    def test_find_by_label(self, registry):
        n = RuntimeNode(name="labelled", address="a",
                        labels={"env": "prod"})
        n.heartbeat()
        registry.register_node(n)
        found = registry.find_by_label("env", "prod")
        assert len(found) == 1


# ══════════════════════════════════════════════
# 6. NodeRegistry — Health & Events
# ══════════════════════════════════════════════

class TestNodeRegistryHealth:
    def test_health_summary(self):
        r = NodeRegistry()
        n = RuntimeNode(name="w1", address="a1")
        n.heartbeat()
        r.register_node(n)
        summary = r.health_summary()
        assert summary["total"] == 1
        assert summary["healthy"] == 1

    def test_check_health(self):
        r = NodeRegistry()
        n = RuntimeNode(name="w1", address="a1")
        n.heartbeat()
        r.register_node(n)
        changes = r.check_health()
        # Should be no changes since all healthy
        assert len(changes) == 0

    def test_registry_events(self):
        r = NodeRegistry()
        n = RuntimeNode(name="w1", address="a1")
        r.register_node(n)
        assert len(r.events) >= 1
        assert r.events[0].event_type == "registered"

    def test_on_change_callback(self):
        r = NodeRegistry()
        calls = []
        r.on_change(lambda e: calls.append(e.event_type))
        r.register_node(RuntimeNode(name="w1", address="a1"))
        assert "registered" in calls


# ══════════════════════════════════════════════
# 7. DistributedEventBus
# ══════════════════════════════════════════════

class TestDistributedEventBus:
    @pytest.fixture
    def bus(self):
        return DistributedEventBus()

    def test_is_runtime_event_bus(self, bus):
        assert isinstance(bus, RuntimeEventBus)

    def test_local_emit(self, bus):
        received = []
        bus.subscribe("test", lambda e: received.append(e))
        bus.emit(RuntimeEvent(event_type="test"))
        assert len(received) == 1

    def test_remote_propagation(self, bus):
        transport = InMemoryTransport()
        bus.register_node("remote-1", transport=transport.send)
        bus.emit(RuntimeEvent(event_type="test"))
        assert transport.received_count == 1

    def test_remote_filter(self, bus):
        transport = InMemoryTransport()
        bus.register_node("remote-1", transport=transport.send,
                          event_filter=["evaluation"])
        bus.emit(RuntimeEvent(event_type="transition"))  # filtered out
        bus.emit(RuntimeEvent(event_type="evaluation"))   # allowed
        assert transport.received_count == 1

    def test_broadcast(self, bus):
        t1 = InMemoryTransport()
        t2 = InMemoryTransport()
        bus.register_node("r1", transport=t1.send)
        bus.register_node("r2", transport=t2.send)
        results = bus.broadcast(RuntimeEvent(event_type="test"))
        assert results == {"r1": True, "r2": True}

    def test_emit_local(self, bus):
        transport = InMemoryTransport()
        bus.register_node("r1", transport=transport.send)
        received = []
        bus.subscribe_all(lambda e: received.append(e))
        bus.emit_local(RuntimeEvent(event_type="local_only"))
        assert len(received) == 1
        assert transport.received_count == 0  # not forwarded

    def test_unregister_node(self, bus):
        transport = InMemoryTransport()
        bus.register_node("r1", transport=transport.send)
        assert bus.unregister_node("r1") is True
        bus.emit(RuntimeEvent(event_type="test"))
        assert transport.received_count == 0

    def test_remote_failure_isolation(self, bus):
        def bad_transport(e):
            raise RuntimeError("boom")
        good = InMemoryTransport()
        bus.register_node("bad", transport=bad_transport)
        bus.register_node("good", transport=good.send)
        bus.emit(RuntimeEvent(event_type="test"))
        assert good.received_count == 1  # good still got it

    def test_list_remote_nodes(self, bus):
        bus.register_node("a", transport=lambda e: None)
        bus.register_node("b", transport=lambda e: None)
        assert "a" in bus.list_remote_nodes()
        assert "b" in bus.list_remote_nodes()


# ══════════════════════════════════════════════
# 8. RemoteExecutionManager
# ══════════════════════════════════════════════

class TestRemoteExecutionManager:
    @pytest.fixture
    def rem(self):
        return RemoteExecutionManager()

    def test_submit(self, rem):
        task = rem.submit("evaluation", {"goal": "test"})
        assert task.capability == "evaluation"
        assert task.status == TaskStatus.PENDING

    def test_submit_with_registry(self):
        r = NodeRegistry()
        n = RuntimeNode(name="w1", address="a1")
        n.add_capability(NodeCapability(name="eval"))
        n.heartbeat()
        r.register_node(n)

        rem = RemoteExecutionManager(r)
        task = rem.submit("eval", {"x": 1})
        assert task.status == TaskStatus.ASSIGNED
        assert task.assigned_node == "w1"

    def test_execute(self, rem):
        rem.register_executor("calc", lambda p: p["a"] + p["b"])
        task = rem.submit("calc", {"a": 3, "b": 4})
        result = rem.execute(task.id)
        assert result == 7
        assert task.status == TaskStatus.COMPLETED

    def test_execute_no_executor(self, rem):
        task = rem.submit("unknown_cap", {})
        result = rem.execute(task.id)
        assert result is None
        assert task.status == TaskStatus.FAILED

    def test_execute_already_completed(self, rem):
        rem.register_executor("calc", lambda p: 42)
        task = rem.submit("calc", {})
        rem.execute(task.id)
        result = rem.execute(task.id)  # re-execute
        assert result == 42  # returns same result

    def test_wait_for(self, rem):
        rem.register_executor("fast", lambda p: "done")
        task = rem.submit("fast", {})
        rem.execute(task.id)
        result = rem.wait_for(task.id, timeout=1.0)
        assert result == "done"

    def test_wait_for_timeout(self, rem):
        task = rem.submit("slow", {})
        result = rem.wait_for(task.id, timeout=0.01)
        assert result is None
        assert task.status == TaskStatus.TIMEOUT

    def test_cancel(self, rem):
        task = rem.submit("eval", {})
        assert rem.cancel(task.id) is True
        assert task.status == TaskStatus.CANCELLED

    def test_cancel_completed_fails(self, rem):
        rem.register_executor("e", lambda p: 1)
        task = rem.submit("e", {})
        rem.execute(task.id)
        assert rem.cancel(task.id) is False

    def test_summary(self, rem):
        rem.register_executor("c", lambda p: 1)
        rem.submit("c", {})
        rem.submit("c", {})
        s = rem.summary()
        assert s["total"] == 2
        assert s["pending"] == 2

    def test_history(self, rem):
        rem.register_executor("c", lambda p: p.get("v", 0))
        t = rem.submit("c", {"v": 10})
        rem.execute(t.id)
        assert len(rem.history) == 1


# ══════════════════════════════════════════════
# 9. DistributedTraceCollector
# ══════════════════════════════════════════════

class TestDistributedTraceCollector:
    @pytest.fixture
    def collector(self):
        return DistributedTraceCollector()

    def test_add_node_traces(self, collector):
        data = {
            "traces": [
                {"action": "CONTINUE", "reason": {"category": "normal_flow"}},
                {"action": "RETRY", "reason": {"category": "failure_recovery"}},
            ],
        }
        added = collector.add_node_traces("w1", data)
        assert added == 2
        assert collector.total_traces() == 2

    def test_by_node(self, collector):
        collector.add_node_traces("a", {"traces": [{"action": "x"}]})
        collector.add_node_traces("b", {"traces": [{"action": "y"}]})
        assert len(collector.by_node("a")) == 1
        assert len(collector.by_node("b")) == 1

    def test_by_action(self, collector):
        collector.add_node_traces("n", {"traces": [
            {"action": "RETRY"}, {"action": "CONTINUE"}, {"action": "RETRY"},
        ]})
        assert len(collector.by_action("RETRY")) == 2
        assert len(collector.by_action("TERMINATE")) == 0

    def test_by_category(self, collector):
        collector.add_node_traces("n", {"traces": [
            {"action": "RETRY", "reason": {"category": "failure_recovery"}},
            {"action": "CONTINUE", "reason": {"category": "normal_flow"}},
        ]})
        assert len(collector.by_category("failure_recovery")) == 1

    def test_aggregate_summary(self, collector):
        collector.add_node_traces("w1", {"traces": [
            {"action": "RETRY", "recovery_attempted": True, "recovery_success": True},
            {"action": "CONTINUE", "recovery_attempted": False},
        ]})
        summary = collector.aggregate_summary()
        assert summary["total_traces"] == 2
        assert summary["recoveries"]["attempted"] == 1

    def test_timeline(self, collector):
        collector.add_node_traces("n", {"traces": [{"action": "C", "timestamp": "2026-01-01T00:00:02"}]})
        collector.add_node_traces("n", {"traces": [{"action": "A", "timestamp": "2026-01-01T00:00:01"}]})
        timeline = collector.timeline()
        assert timeline[0]["action"] == "A"
        assert timeline[1]["action"] == "C"

    def test_to_dict(self, collector):
        collector.add_node_traces("n", {"traces": [{"action": "X"}]})
        d = collector.to_dict()
        assert d["node_count"] == 1
        assert d["total_traces"] == 1

    def test_clear(self, collector):
        collector.add_node_traces("n", {"traces": [{"action": "X"}]})
        collector.clear()
        assert collector.total_traces() == 0


# ══════════════════════════════════════════════
# 10. Integration
# ══════════════════════════════════════════════

class TestDistributedIntegration:
    def test_full_pipeline(self):
        """Node → Registry → EventBus → RemoteExec → Trace"""
        # Nodes
        registry = NodeRegistry()
        w1 = RuntimeNode(name="worker-1", address="localhost:8001")
        w1.add_capability(NodeCapability(name="evaluation"))
        w1.heartbeat()
        registry.register_node(w1)

        # Event bus
        bus = DistributedEventBus()
        transport = InMemoryTransport()
        bus.register_node("worker-1", transport=transport.send)

        # Remote execution
        rem = RemoteExecutionManager(registry)
        rem.register_executor("evaluation", lambda p: {"score": p.get("score", 0) + 10})

        # Submit + execute
        task = rem.submit("evaluation", {"score": 75})
        assert task.assigned_node == "worker-1"
        result = rem.execute(task.id)
        assert result == {"score": 85}

        # Send event
        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 85}))
        assert transport.received_count == 1

        # Trace collection
        collector = DistributedTraceCollector()
        collector.add_node_traces("worker-1", {
            "traces": [{"action": "CONTINUE", "reason": {"category": "normal_flow"}}],
        })
        assert collector.total_traces() == 1

    def test_backward_compat_no_nodes(self):
        """Everything works with zero nodes."""
        registry = NodeRegistry()
        assert len(registry) == 0

        bus = DistributedEventBus()
        bus.emit(RuntimeEvent(event_type="test"))  # noop, should not crash

        rem = RemoteExecutionManager()
        task = rem.submit("cap", {})
        assert task.status == TaskStatus.PENDING

        collector = DistributedTraceCollector()
        assert collector.total_traces() == 0


# ══════════════════════════════════════════════
# 11. Edge Cases
# ══════════════════════════════════════════════

class TestDistributedEdgeCases:
    @pytest.fixture
    def rem(self):
        return RemoteExecutionManager()

    def test_node_re_registration(self):
        r = NodeRegistry()
        n1 = RuntimeNode(name="w1", address="a1")
        r.register_node(n1)
        n2 = RuntimeNode(name="w1", address="a2")  # same name
        r.register_node(n2)
        assert r.get_node("w1") is n2

    def test_registry_clear(self):
        r = NodeRegistry()
        n = RuntimeNode(name="w1", address="a1")
        r.register_node(n)
        r.clear()
        assert len(r) == 0
        assert n.status == NodeStatus.OFFLINE

    def test_task_to_dict(self):
        task = RemoteTask(
            capability="eval",
            payload={"x": 1},
            assigned_node="w1",
        )
        d = task.to_dict()
        assert d["capability"] == "eval"
        assert d["status"] == "pending"

    def test_executor_error(self, rem):
        rem.register_executor("fail", lambda p: exec('raise ValueError("bad")'))
        t = rem.submit("fail", {})
        result = rem.execute(t.id)
        assert result is None
        assert t.status == TaskStatus.FAILED

    def test_multiple_nodes_same_capability(self):
        r = NodeRegistry()
        for i in range(5):
            n = RuntimeNode(name=f"w{i}", address=f"a{i}")
            n.add_capability(NodeCapability(name="eval"))
            n.heartbeat()
            r.register_node(n)
        assert len(r.find_by_capability("eval")) == 5
