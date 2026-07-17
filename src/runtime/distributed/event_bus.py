"""
Phase 5.9 — Distributed Event Bus

Extends RuntimeEventBus with cross-node event propagation.
Events emitted locally are forwarded to remote nodes via registered
transports. Acts as a standard local bus when no remote nodes are configured.

Backward compatible: drop-in replacement for RuntimeEventBus.

Usage:
    bus = DistributedEventBus()
    bus.register_node(worker_node, transport=my_transport)
    bus.emit(event)  # local + remote propagation
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional

from ..events import RuntimeEvent, RuntimeEventBus, Subscriber


class DistributedEventBus(RuntimeEventBus):
    """
    Extends RuntimeEventBus for distributed systems.

    Events are emitted locally (as usual) AND forwarded to registered
    remote nodes. Each remote node has a transport function that
    handles the actual delivery.

    Usage:
        bus = DistributedEventBus()

        # Local subscriptions work as before
        bus.subscribe("evaluation", my_handler)

        # Register remote nodes for cross-node propagation
        bus.register_node("worker-1", transport=send_to_worker1)

        # Emit — propagates locally AND to worker-1
        bus.emit(RuntimeEvent(event_type="evaluation", metadata={"score": 85}))
    """

    def __init__(self):
        super().__init__()
        self._remote_nodes: Dict[str, Any] = {}
        # node_name → {"transport": callable, "event_filter": set or None}

    # ── Remote Node Management ──────────

    def register_node(
        self,
        node_name: str,
        transport: Callable[[RuntimeEvent], None],
        event_filter: Optional[List[str]] = None,
    ) -> None:
        """
        Register a remote node for event forwarding.

        Args:
            node_name: Unique name for the remote node.
            transport: Callable that sends an event to the remote.
            event_filter: If set, only forward matching event types.
        """
        self._remote_nodes[node_name] = {
            "transport": transport,
            "event_filter": set(event_filter) if event_filter else None,
        }

    def unregister_node(self, node_name: str) -> bool:
        """Remove a remote node from event propagation."""
        return self._remote_nodes.pop(node_name, None) is not None

    def list_remote_nodes(self) -> List[str]:
        return list(self._remote_nodes.keys())

    def remote_node_count(self) -> int:
        return len(self._remote_nodes)

    # ── Emit (extended) ──────────────────

    def emit(self, event: RuntimeEvent) -> None:
        """
        Emit an event locally AND forward to remote nodes.

        Local behavior is identical to RuntimeEventBus.emit().
        Remote forwarding is best-effort — failures are isolated.
        """
        # Local propagation (parent behavior)
        super().emit(event)

        # Remote propagation
        for node_name, config in self._remote_nodes.items():
            event_filter = config["event_filter"]
            if event_filter and event.event_type not in event_filter:
                continue

            try:
                config["transport"](event)
            except Exception:
                pass  # isolation — one remote failure doesn't break others

    # ── Broadcast (new) ──────────────────

    def broadcast(self, event: RuntimeEvent) -> Dict[str, bool]:
        """
        Broadcast to all remote nodes and return per-node delivery status.

        Returns:
            Dict mapping node_name → delivery_success.
        """
        results = {}
        for node_name, config in self._remote_nodes.items():
            try:
                config["transport"](event)
                results[node_name] = True
            except Exception:
                results[node_name] = False
        return results

    # ── Local-only ───────────────────────

    def emit_local(self, event: RuntimeEvent) -> None:
        """Emit only to local subscribers, skip remote nodes."""
        super().emit(event)


# ──────────────────────────────────────────────
# In-Memory Transport (for testing / local dev)
# ──────────────────────────────────────────────


class InMemoryTransport:
    """
    An in-memory event transport for local testing.

    Captures events that would otherwise be sent over the network.

    Usage:
        transport = InMemoryTransport()
        bus.register_node("remote-1", transport=transport.send)

        bus.emit(some_event)
        print(transport.received)  # [some_event]
    """

    def __init__(self):
        self._received: List[RuntimeEvent] = []

    def send(self, event: RuntimeEvent) -> None:
        self._received.append(event)

    @property
    def received(self) -> List[RuntimeEvent]:
        return list(self._received)

    @property
    def received_count(self) -> int:
        return len(self._received)

    def clear(self) -> None:
        self._received.clear()
