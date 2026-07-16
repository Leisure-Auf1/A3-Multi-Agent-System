"""
Phase 5 — EventTrace: 增强 Agent 执行追踪

扩展 EventBus 事件格式, 每条 Agent 操作生成结构化追踪记录:

{
    "event": "agent_completed",
    "agent": "PlannerAgent",
    "timestamp": "2026-07-14T...",
    "input": "{...}",
    "output": "{...}",
    "status": "success",
    "duration_ms": 45.2,
}
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json

from src.core.event_bus import AgentEventBus, AgentEvent


# ──────────────────────────────────────────────
# 增强 TraceEvent
# ──────────────────────────────────────────────

@dataclass
class TraceEvent:
    """增强版事件追踪记录"""
    event: str = "agent_completed"              # 事件类型
    agent: str = ""                              # Agent 名称
    action: str = ""                             # 执行动作
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    input: str = ""                              # 输入摘要
    output: str = ""                             # 输出摘要
    status: str = "success"                      # success | error | skipped
    duration_ms: float = 0.0                     # 执行耗时
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "agent": self.agent,
            "action": self.action,
            "timestamp": self.timestamp,
            "input": self.input,
            "output": self.output,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

    @classmethod
    def from_agent_event(cls, ae: AgentEvent) -> "TraceEvent":
        """从 AgentEvent 转换"""
        return cls(
            event="agent_completed" if ae.status == "success" else "agent_error",
            agent=ae.agent,
            action=ae.action,
            timestamp=ae.timestamp,
            input=ae.input_summary,
            output=ae.output_summary,
            status=ae.status,
            duration_ms=ae.duration_ms,
            metadata=ae.metadata,
        )


# ──────────────────────────────────────────────
# TraceCollector — 增强版 (兼容已有 AgentTraceCollector)
# ──────────────────────────────────────────────

class TraceCollector:
    """
    增强版 Trace 收集器.

    提供:
      - 从 EventBus 收集事件
      - 格式化为 TraceEvent 列表
      - 导出 JSON
      - 生成执行时间线可视化文本
    """

    def __init__(self, bus: Optional[AgentEventBus] = None):
        self._bus = bus or AgentEventBus.get_instance()
        self._traces: List[TraceEvent] = []

    def collect(self) -> List[TraceEvent]:
        """从 EventBus 收集并转换事件"""
        raw_events = self._bus.get_timeline()
        self._traces = [TraceEvent.from_agent_event(e) for e in raw_events]
        return self._traces

    def get_traces(self) -> List[TraceEvent]:
        """获取已收集的追踪记录"""
        if not self._traces:
            return self.collect()
        return self._traces

    def to_json(self) -> str:
        """导出 JSON"""
        return json.dumps(
            [t.to_dict() for t in self.get_traces()],
            ensure_ascii=False,
            indent=2,
        )

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """导出为字典列表"""
        return [t.to_dict() for t in self.get_traces()]

    def render_timeline(self) -> str:
        """
        生成可读的执行时间线文本.

        示例输出:
            [00] System        session_start     → Session started
            [01] ProfileAgent  profile_extracted → 画像: junior_dev
            [02] PlannerAgent  plan_generated    → 路径: 6 个节点
            ...
        """
        traces = self.get_traces()
        lines = []
        for i, t in enumerate(traces):
            status_mark = "✓" if t.status == "success" else "✗"
            lines.append(
                f"[{i:02d}] {status_mark} {t.agent:<15s} {t.action:<22s} "
                f"→ {t.output[:80]}"
            )
        return "\n".join(lines)

    def render_compact(self) -> str:
        """生成紧凑格式"""
        traces = self.get_traces()
        lines = []
        for t in traces:
            mark = "✓" if t.status == "success" else "✗"
            lines.append(
                f"  {mark} [{t.agent}] {t.action}"
            )
        return "\n".join(lines)

    def get_agent_summary(self) -> Dict[str, int]:
        """统计每个 Agent 的事件数"""
        traces = self.get_traces()
        summary: Dict[str, int] = {}
        for t in traces:
            summary[t.agent] = summary.get(t.agent, 0) + 1
        return summary

    def clear(self):
        """清除追踪记录"""
        self._traces.clear()


# ──────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────

def create_event_trace(
    agent: str,
    action: str,
    input_summary: str = "",
    output_summary: str = "",
    status: str = "success",
    duration_ms: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> TraceEvent:
    """
    创建一个增强版 TraceEvent 并发布到 EventBus.

    同时返回 TraceEvent 对象。
    """
    bus = AgentEventBus.get_instance()
    ae = bus.emit(
        agent=agent,
        action=action,
        input_summary=input_summary,
        output_summary=output_summary,
        status=status,
        duration_ms=duration_ms,
        metadata=metadata,
    )
    return TraceEvent.from_agent_event(ae)


def get_execution_timeline(bus: Optional[AgentEventBus] = None) -> str:
    """便捷获取可读时间线 (需先执行 pipeline)"""
    collector = TraceCollector(bus)
    return collector.render_timeline()
