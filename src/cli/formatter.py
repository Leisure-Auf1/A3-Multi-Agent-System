"""
Phase 6.1 — CLI Output Formatter

Formats RuntimeClient responses for terminal display.
Supports table, JSON, and summary output modes.

Usage:
    from src.cli.formatter import Formatter
    fmt = Formatter()
    print(fmt.format_result(result))
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from enum import Enum


class OutputFormat(Enum):
    TABLE = "table"
    JSON = "json"
    SUMMARY = "summary"


class Formatter:
    """
    Formats Veritas SDK responses for terminal output.

    Provides consistent formatting for TaskResult, SessionInfo,
    status dicts, and explainability data.
    """

    def __init__(self, format: OutputFormat = OutputFormat.TABLE):
        self.format = format

    # ── TaskResult ─────────────────────────

    def format_result(self, result: Any) -> str:
        """Format a TaskResult for display."""
        if self.format == OutputFormat.JSON:
            import json
            return json.dumps(result.to_dict(), indent=2, default=str)

        if self.format == OutputFormat.SUMMARY:
            return self._result_summary(result)

        return self._result_table(result)

    def _result_table(self, result: Any) -> str:
        lines = [
            "╔══════════════════════════════════════════╗",
            "║         Veritas Task Result              ║",
            "╠══════════════════════════════════════════╣",
            f"║  Task ID:    {result.task_id:<28} ║",
            f"║  Status:     {result.status.value:<28} ║",
            f"║  Success:    {str(result.is_success):<28} ║",
            f"║  Time:       {result.execution_time_ms:.1f}ms{' ' * (22 - len(f'{result.execution_time_ms:.1f}ms'))} ║",
            f"║  Session:    {result.session_id:<28} ║",
            f"║  Trace:      {result.trace_id:<28} ║",
        ]

        if result.errors:
            lines.append("╠══════════════════════════════════════════╣")
            lines.append("║  Errors:                                 ║")
            for err in result.errors[-3:]:
                truncated = str(err)[:36]
                lines.append(f"║    • {truncated:<34} ║")

        if result.metadata:
            lines.append("╠══════════════════════════════════════════╣")
            for k, v in list(result.metadata.items())[:4]:
                lines.append(f"║  {k}: {str(v)[:28]:<28} ║")

        lines.append("╚══════════════════════════════════════════╝")
        return "\n".join(lines)

    def _result_summary(self, result: Any) -> str:
        status_icon = "✅" if result.is_success else "❌"
        return (
            f"{status_icon} {result.task_id} | "
            f"{result.status.value} | "
            f"{result.execution_time_ms:.0f}ms"
        )

    # ── Status ─────────────────────────────

    def format_status(self, data: Dict[str, Any]) -> str:
        """Format runtime status dict."""
        if self.format == OutputFormat.JSON:
            import json
            return json.dumps(data, indent=2)

        lines = [
            "╔══════════════════════════════════════════╗",
            "║         Veritas Runtime Status           ║",
            "╠══════════════════════════════════════════╣",
            f"║  Version:          {data.get('version', '?'):<20} ║",
            f"║  Recovery:         {str(data.get('recovery_enabled', False)):<20} ║",
            f"║  Sessions:         {str(data.get('sessions_count', 0)):<20} ║",
            f"║  Plugins:          {str(data.get('plugins_count', 0)):<20} ║",
            f"║  Distributed:      {str(data.get('distributed_enabled', False)):<20} ║",
            "╚══════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    # ── Sessions ───────────────────────────

    def format_sessions(self, sessions: List[Any]) -> str:
        """Format session list."""
        if self.format == OutputFormat.JSON:
            import json
            return json.dumps([s.to_dict() for s in sessions], indent=2)

        if not sessions:
            return "No sessions found."

        lines = ["Sessions:", "-" * 50]
        for s in sessions:
            icon = "✅" if s.is_completed else "⏳"
            lines.append(
                f"  {icon} {s.session_id} | {s.state} | "
                f"{s.total_duration_ms:.0f}ms | {s.error_count} errors"
            )
        return "\n".join(lines)

    # ── Explainability ─────────────────────

    def format_explain(self, data: Dict[str, Any]) -> str:
        """Format explainability data."""
        if self.format == OutputFormat.JSON:
            import json
            return json.dumps(data, indent=2)

        lines = [
            "╔══════════════════════════════════════════╗",
            "║       Decision Explainability            ║",
            "╠══════════════════════════════════════════╣",
            f"║  Decisions:       {data.get('total_decisions', 0):<20} ║",
            f"║  Explainability:  {data.get('explainability_score', 0):.2f}{' ' * 16} ║",
            f"║  Diversity:       {data.get('decision_diversity', 0):.2f}{' ' * 16} ║",
            "╠══════════════════════════════════════════╣",
        ]

        by_action = data.get("by_action", {})
        for action, count in sorted(by_action.items()):
            if count:
                lines.append(f"║  {action:<14} {count:>4}                    ║")

        lines.append("╚══════════════════════════════════════════╝")
        return "\n".join(lines)

    # ── Plugins ────────────────────────────

    def format_plugins(self, plugins: List[Dict[str, Any]]) -> str:
        """Format plugin list."""
        if self.format == OutputFormat.JSON:
            import json
            return json.dumps(plugins, indent=2)

        if not plugins:
            return "No plugins installed."

        lines = ["Plugins:", "-" * 50]
        for p in plugins:
            enabled_icon = "✅" if p.get("state") == "started" else "⏸️"
            lines.append(
                f"  {enabled_icon} {p['name']} v{p.get('version', '?')} "
                f"| {p.get('state', '?')} | priority={p.get('priority', 0)}"
            )
        return "\n".join(lines)
