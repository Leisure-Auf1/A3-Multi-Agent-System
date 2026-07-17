"""
Phase 5.9 — Node Registry

Manages runtime nodes in a distributed system. Supports registration,
discovery, health monitoring, and capability-based node lookup.

Usage:
    registry = NodeRegistry()
    registry.register_node(worker_node)
    healthy = registry.list_healthy()
    profile_nodes = registry.find_by_capability("profile_extraction")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .node import RuntimeNode, NodeStatus, NodeInfo


@dataclass
class RegistryEvent:
    """An event recorded when a node is registered or its status changes."""
    node_name: str
    event_type: str  # registered | unregistered | status_change
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    detail: str = ""


class NodeRegistry:
    """
    Central registry for distributed RuntimeNodes.

    Manages node lifecycle: register, unregister, health tracking,
    and capability-based discovery.

    Usage:
        registry = NodeRegistry()

        node = RuntimeNode(name="worker-1", address="localhost:8001")
        registry.register_node(node)

        # Find nodes by capability
        evaluators = registry.find_by_capability("evaluation")

        # Get health summary
        print(registry.health_summary())
    """

    def __init__(self):
        self._nodes: Dict[str, RuntimeNode] = {}
        self._events: List[RegistryEvent] = []
        self._on_change: List[Any] = []  # callbacks for registry changes

    # ── Registration ─────────────────────

    def register_node(self, node: RuntimeNode) -> None:
        """
        Register a new node or update an existing one.

        Raises ValueError if a different node with the same name exists.
        """
        name = node.name
        existing = self._nodes.get(name)
        if existing is not None and existing is not node:
            # Re-registration of same name with different object
            self._nodes[name] = node
            self._record_event(name, "status_change", "Node re-registered")
        else:
            self._nodes[name] = node
            self._record_event(name, "registered", f"Node at {node.address}")

        node.heartbeat()

    def unregister_node(self, name: str) -> Optional[RuntimeNode]:
        """Remove a node from the registry."""
        node = self._nodes.pop(name, None)
        if node:
            node.mark_offline()
            self._record_event(name, "unregistered", "Node removed")
        return node

    # ── Query ────────────────────────────

    def get_node(self, name: str) -> Optional[RuntimeNode]:
        return self._nodes.get(name)

    def list_all(self) -> List[RuntimeNode]:
        return list(self._nodes.values())

    def list_available(self) -> List[RuntimeNode]:
        """Nodes that are healthy or degraded."""
        return [n for n in self._nodes.values() if n.is_available]

    def list_healthy(self) -> List[RuntimeNode]:
        return [n for n in self._nodes.values() if n.status == NodeStatus.HEALTHY]

    def list_degraded(self) -> List[RuntimeNode]:
        return [n for n in self._nodes.values() if n.status == NodeStatus.DEGRADED]

    def list_offline(self) -> List[RuntimeNode]:
        return [n for n in self._nodes.values() if n.status == NodeStatus.OFFLINE]

    def node_names(self) -> List[str]:
        return list(self._nodes.keys())

    # ── Discovery ────────────────────────

    def find_by_capability(self, capability_name: str) -> List[RuntimeNode]:
        """Find all available nodes with a specific capability."""
        return [
            n for n in self._nodes.values()
            if n.is_available and n.has_capability(capability_name)
        ]

    def find_by_label(self, key: str, value: str) -> List[RuntimeNode]:
        """Find nodes by label key-value pair."""
        return [
            n for n in self._nodes.values()
            if n.info.labels.get(key) == value
        ]

    def find_best_for(self, capability_name: str) -> Optional[RuntimeNode]:
        """
        Find the best available node for a capability.

        Preference: HEALTHY > DEGRADED. Within same status, picks first.
        """
        candidates = self.find_by_capability(capability_name)
        healthy = [n for n in candidates if n.status == NodeStatus.HEALTHY]
        return healthy[0] if healthy else (candidates[0] if candidates else None)

    # ── Health ────────────────────────────

    def health_summary(self) -> Dict[str, Any]:
        """Get a health overview of all registered nodes."""
        all_nodes = self.list_all()
        return {
            "total": len(all_nodes),
            "healthy": len(self.list_healthy()),
            "degraded": len(self.list_degraded()),
            "offline": len(self.list_offline()),
            "available": len(self.list_available()),
            "nodes": {
                n.name: {
                    "status": n.status.value,
                    "address": n.address,
                    "capabilities": [c.name for c in n.info.capabilities],
                }
                for n in all_nodes
            },
        }

    def check_health(self) -> Dict[str, str]:
        """
        Check health of all nodes and return status changes.

        Nodes that haven't heartbeat recently are marked UNREACHABLE/offline
        based on their current status.
        """
        changes = {}
        for node in self.list_all():
            old_status = node.status
            # Force status re-evaluation
            new_status = node.status  # property recalculates
            if old_status != new_status:
                changes[node.name] = f"{old_status.value} → {new_status.value}"
                self._record_event(
                    node.name, "status_change",
                    f"Health: {old_status.value} → {new_status.value}",
                )
        return changes

    # ── Events ────────────────────────────

    def _record_event(self, node_name: str, event_type: str, detail: str = "") -> None:
        event = RegistryEvent(
            node_name=node_name,
            event_type=event_type,
            detail=detail,
        )
        self._events.append(event)
        for cb in self._on_change:
            try:
                cb(event)
            except Exception:
                pass

    def on_change(self, callback: Any) -> None:
        """Register a callback for registry events."""
        self._on_change.append(callback)

    @property
    def events(self) -> List[RegistryEvent]:
        return list(self._events)

    # ── Bulk ──────────────────────────────

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, name: str) -> bool:
        return name in self._nodes

    def clear(self) -> None:
        for node in self._nodes.values():
            node.mark_offline()
        self._nodes.clear()
        self._events.clear()
