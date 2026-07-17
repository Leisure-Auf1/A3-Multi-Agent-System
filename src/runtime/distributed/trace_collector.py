"""
Phase 5.9 — Distributed Trace Collector

Collects and aggregates DecisionTraces from multiple runtime nodes
for a unified view of distributed decision-making.

Usage:
    collector = DistributedTraceCollector()
    collector.add_node_traces("worker-1", recorder.to_dict())
    collector.add_node_traces("worker-2", recorder.to_dict())
    print(collector.aggregate_summary())
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TraceEntry:
    """A trace entry with node attribution."""
    node_name: str
    trace: Dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DistributedTraceCollector:
    """
    Aggregates decision traces across distributed runtime nodes.

    Collects per-node trace data and provides cross-node queries,
    aggregation, and timeline reconstruction.

    Usage:
        collector = DistributedTraceCollector()

        # Collect from nodes
        collector.add_node_traces("worker-1", recorder1.to_dict())
        collector.add_node_traces("worker-2", recorder2.to_dict())

        # Query across nodes
        all_decisions = collector.all_decisions()
        by_action = collector.by_action("RETRY")
        summary = collector.aggregate_summary()
    """

    def __init__(self):
        self._nodes: Dict[str, List[TraceEntry]] = {}
        self._all_traces: List[TraceEntry] = []

    # ── Collection ────────────────────────

    def add_node_traces(
        self,
        node_name: str,
        trace_data: Dict[str, Any],
    ) -> int:
        """
        Add trace data from a remote node.

        Args:
            node_name: Name of the reporting node.
            trace_data: Output from ExplanationRecorder.to_dict().

        Returns:
            Number of new traces added.
        """
        if node_name not in self._nodes:
            self._nodes[node_name] = []

        traces = trace_data.get("traces", [])
        added = 0
        for trace in traces:
            entry = TraceEntry(node_name=node_name, trace=trace)
            self._nodes[node_name].append(entry)
            self._all_traces.append(entry)
            added += 1

        return added

    # ── Query ─────────────────────────────

    def all_decisions(self) -> List[Dict[str, Any]]:
        """All decision traces across all nodes."""
        return [
            {"node": e.node_name, **e.trace}
            for e in self._all_traces
        ]

    def by_node(self, node_name: str) -> List[Dict[str, Any]]:
        """Decision traces from a specific node."""
        entries = self._nodes.get(node_name, [])
        return [{"node": e.node_name, **e.trace} for e in entries]

    def by_action(self, action: str) -> List[Dict[str, Any]]:
        """Decision traces with a specific action."""
        return [
            {"node": e.node_name, **e.trace}
            for e in self._all_traces
            if e.trace.get("action") == action
        ]

    def by_category(self, category: str) -> List[Dict[str, Any]]:
        """Decision traces with a specific reason category."""
        return [
            {"node": e.node_name, **e.trace}
            for e in self._all_traces
            if e.trace.get("reason", {}).get("category") == category
        ]

    def all_actions(self) -> List[str]:
        """All unique actions across nodes."""
        return list({e.trace.get("action", "") for e in self._all_traces})

    def node_names(self) -> List[str]:
        return list(self._nodes.keys())

    def node_count(self) -> int:
        return len(self._nodes)

    def total_traces(self) -> int:
        return len(self._all_traces)

    # ── Aggregation ───────────────────────

    def aggregate_summary(self) -> Dict[str, Any]:
        """Cross-node aggregate summary."""
        actions: Dict[str, int] = {}
        categories: Dict[str, int] = {}
        per_node: Dict[str, int] = {}

        for entry in self._all_traces:
            action = entry.trace.get("action", "unknown")
            actions[action] = actions.get(action, 0) + 1

            reason = entry.trace.get("reason") or {}
            cat = reason.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

            per_node[entry.node_name] = per_node.get(entry.node_name, 0) + 1

        recoveries = sum(
            1 for e in self._all_traces
            if e.trace.get("recovery_attempted")
        )
        recovery_successes = sum(
            1 for e in self._all_traces
            if e.trace.get("recovery_success")
        )

        return {
            "total_traces": self.total_traces(),
            "node_count": self.node_count(),
            "nodes": per_node,
            "actions": actions,
            "categories": categories,
            "recoveries": {
                "attempted": recoveries,
                "successful": recovery_successes,
                "rate": recovery_successes / max(recoveries, 1),
            },
        }

    # ── Timeline ──────────────────────────

    def timeline(self) -> List[Dict[str, Any]]:
        """
        Reconstruct a cross-node timeline sorted by timestamp.

        Returns all traces ordered chronologically.
        """
        return sorted(
            [{"node": e.node_name, **e.trace} for e in self._all_traces],
            key=lambda t: t.get("timestamp", ""),
        )

    # ── Serialization ─────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_count": self.node_count(),
            "total_traces": self.total_traces(),
            "nodes": list(self._nodes.keys()),
            "traces": [{"node": e.node_name, **e.trace} for e in self._all_traces],
            "summary": self.aggregate_summary(),
        }

    def clear(self) -> None:
        self._nodes.clear()
        self._all_traces.clear()
