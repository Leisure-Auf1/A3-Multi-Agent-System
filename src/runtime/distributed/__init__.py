"""
Phase 5.9 — Distributed Runtime Layer

Foundation for multi-node runtime orchestration. Provides node management,
cross-node event propagation, remote execution, and distributed trace collection.

Modules:
    node           — RuntimeNode + NodeStatus + NodeCapability
    registry       — NodeRegistry (registration, discovery, health)
    event_bus      — DistributedEventBus (cross-node event propagation)
    remote         — RemoteExecutionManager (task dispatching)
    trace_collector — DistributedTraceCollector (cross-node trace aggregation)

Usage:
    from src.runtime.distributed import RuntimeNode, NodeRegistry, DistributedEventBus

    # Set up nodes
    registry = NodeRegistry()
    worker = RuntimeNode(name="worker-1", address="localhost:8001")
    registry.register_node(worker)

    # Distributed event bus
    bus = DistributedEventBus()
    bus.emit(event)  # local + remote propagation
"""

from .node import RuntimeNode, NodeStatus, NodeCapability, NodeInfo
from .registry import NodeRegistry, RegistryEvent
from .event_bus import DistributedEventBus, InMemoryTransport
from .remote import RemoteExecutionManager, RemoteTask, TaskStatus
from .trace_collector import DistributedTraceCollector, TraceEntry

__all__ = [
    "RuntimeNode",
    "NodeStatus",
    "NodeCapability",
    "NodeInfo",
    "NodeRegistry",
    "RegistryEvent",
    "DistributedEventBus",
    "InMemoryTransport",
    "RemoteExecutionManager",
    "RemoteTask",
    "TaskStatus",
    "DistributedTraceCollector",
    "TraceEntry",
]
