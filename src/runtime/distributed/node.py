"""
Phase 5.9 — Runtime Node

Represents a single runtime instance in a distributed system.
Each node has identity, status, capabilities, and a local engine reference.

Usage:
    node = RuntimeNode(name="worker-1", address="localhost:8001")
    node.heartbeat()  # mark as alive
    print(node.status)  # healthy
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeStatus(Enum):
    """Health status of a RuntimeNode."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    OFFLINE = "offline"

    @property
    def is_available(self) -> bool:
        return self in (NodeStatus.HEALTHY, NodeStatus.DEGRADED)


@dataclass
class NodeCapability:
    """A capability that a node can advertise."""
    name: str
    """Capability name (e.g. 'profile_extraction', 'evaluation')."""

    version: str = "1.0.0"
    """Version of this capability."""

    max_concurrency: int = 1
    """Maximum concurrent executions."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional capability metadata."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "max_concurrency": self.max_concurrency,
            "metadata": self.metadata,
        }


@dataclass
class NodeInfo:
    """Serializable node metadata for registry and discovery."""
    name: str
    address: str
    capabilities: List[NodeCapability] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    runtime_version: str = "5.9"
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "address": self.address,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "labels": self.labels,
            "runtime_version": self.runtime_version,
            "started_at": self.started_at,
        }


class RuntimeNode:
    """
    A single runtime instance in a distributed system.

    Each node registers with a NodeRegistry, advertises capabilities,
    and reports its health via heartbeats.

    Usage:
        node = RuntimeNode(
            name="worker-1",
            address="localhost:8001",
            capabilities=[
                NodeCapability(name="profile_extraction"),
                NodeCapability(name="evaluation", max_concurrency=2),
            ],
        )
        node.register_with(registry)

        # Periodic health reporting
        node.heartbeat()
        print(node.status)  # healthy | degraded | unreachable
    """

    HEARTBEAT_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        name: str,
        address: str,
        capabilities: Optional[List[NodeCapability]] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        self.info = NodeInfo(
            name=name,
            address=address,
            capabilities=list(capabilities or []),
            labels=dict(labels or {}),
        )
        self._status = NodeStatus.UNKNOWN
        self._last_heartbeat: Optional[datetime] = None
        self._registry: Any = None
        self._engine: Any = None

    # ── Identity ──────────────────────────

    @property
    def name(self) -> str:
        return self.info.name

    @property
    def address(self) -> str:
        return self.info.address

    @property
    def status(self) -> NodeStatus:
        """Current health status based on last heartbeat."""
        if self._last_heartbeat is None:
            return NodeStatus.UNKNOWN
        elapsed = (datetime.now(timezone.utc) - self._last_heartbeat).total_seconds()
        if elapsed > self.HEARTBEAT_TIMEOUT_SECONDS * 2:
            return NodeStatus.OFFLINE
        if elapsed > self.HEARTBEAT_TIMEOUT_SECONDS:
            return NodeStatus.UNREACHABLE
        if self._status == NodeStatus.UNKNOWN:
            return NodeStatus.HEALTHY
        return self._status

    @status.setter
    def status(self, value: NodeStatus) -> None:
        self._status = value

    @property
    def is_available(self) -> bool:
        return self.status.is_available

    # ── Heartbeat ─────────────────────────

    def heartbeat(self) -> None:
        """Record a heartbeat — marks the node as alive."""
        self._last_heartbeat = datetime.now(timezone.utc)
        if self._status in (NodeStatus.UNKNOWN, NodeStatus.UNREACHABLE):
            self._status = NodeStatus.HEALTHY

    def mark_degraded(self, reason: str = "") -> None:
        """Mark the node as degraded."""
        self._status = NodeStatus.DEGRADED

    def mark_offline(self) -> None:
        """Mark the node as offline."""
        self._status = NodeStatus.OFFLINE

    # ── Capabilities ──────────────────────

    def has_capability(self, name: str) -> bool:
        """Check if the node advertises a specific capability."""
        return any(c.name == name for c in self.info.capabilities)

    def get_capability(self, name: str) -> Optional[NodeCapability]:
        for c in self.info.capabilities:
            if c.name == name:
                return c
        return None

    def add_capability(self, capability: NodeCapability) -> None:
        if not self.has_capability(capability.name):
            self.info.capabilities.append(capability)

    # ── Registry ──────────────────────────

    def register_with(self, registry: Any) -> None:
        """Register this node with a NodeRegistry."""
        self._registry = registry
        if hasattr(registry, 'register_node'):
            registry.register_node(self)
        self._status = NodeStatus.HEALTHY

    def unregister(self) -> None:
        """Remove this node from its registry."""
        if self._registry and hasattr(self._registry, 'unregister_node'):
            self._registry.unregister_node(self.name)
        self._registry = None

    # ── Engine Binding ────────────────────

    def bind_engine(self, engine: Any) -> None:
        """Bind a local RuntimeEngine to this node."""
        self._engine = engine

    @property
    def engine(self) -> Any:
        return self._engine

    # ── Serialization ─────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "info": self.info.to_dict(),
            "status": self.status.value,
            "last_heartbeat": (
                self._last_heartbeat.isoformat()
                if self._last_heartbeat else None
            ),
            "is_available": self.is_available,
        }
