"""
Phase 10 — AgentTraceCollector: 增强型执行追踪

在 EventBus 之上增加:
  - reasoning_type: heuristic | rule | llm | memory | hybrid
  - session persistence (JSON per session)
  - query by session_id / agent / action

与 EventBus 协同:
  EventBus → 实时内存事件 (Web Trace Panel)
  AgentTraceCollector → 持久化 + 结构化查询
"""

from __future__ import annotations
import json, os, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .event_bus import AgentEventBus, AgentEvent


# ──────────────────────────────────────────────
# 增强 Trace Event
# ──────────────────────────────────────────────

@dataclass
class TraceEvent:
    """增强的追踪事件 — 含推理类型标记"""
    timestamp: str
    session_id: str
    agent_name: str
    action: str
    input_summary: str = ""
    output_summary: str = ""
    reasoning_type: str = "heuristic"  # heuristic | rule | llm | memory | hybrid
    latency_ms: float = 0.0
    status: str = "success"
    decision_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "action": self.action,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "reasoning_type": self.reasoning_type,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "decision_context": self.decision_context,
        }

    @classmethod
    def from_event(cls, event: AgentEvent, session_id: str = "",
                   reasoning_type: str = "heuristic") -> "TraceEvent":
        return cls(
            timestamp=event.timestamp,
            session_id=session_id or "",
            agent_name=event.agent,
            action=event.action,
            input_summary=event.input_summary,
            output_summary=event.output_summary,
            reasoning_type=reasoning_type,
            latency_ms=event.duration_ms,
            status=event.status,
            decision_context=event.metadata or {},
        )


# ──────────────────────────────────────────────
# AgentTraceCollector
# ──────────────────────────────────────────────

class AgentTraceCollector:
    """
    增强的 Agent 追踪收集器.

    功能:
      1. 监听 EventBus → 创建 TraceEvent (增强 reasoning_type)
      2. JSON 持久化 (按 session)
      3. 查询接口 (按 session / agent / action)

    使用:
        collector = AgentTraceCollector()
        collector.new_session("s1")

        bus = AgentEventBus.get_instance()
        bus.emit("ProfileAgent", "extract", ...)
        collector.sync_from_bus()  # 从 EventBus 同步事件

        traces = collector.query(session_id="s1")
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self._dir = Path(storage_dir)
        else:
            base = Path(__file__).resolve().parent.parent.parent
            self._dir = base / "storage" / "memory" / "traces"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._current_session: str = ""
        self._traces: List[TraceEvent] = []
        self._reasoning_map: Dict[str, str] = {}  # agent → default reasoning_type

    def new_session(self, session_id: str) -> None:
        self._current_session = session_id
        self._traces.clear()

    def set_reasoning_type(self, agent: str, rtype: str) -> None:
        """设置 agent 的默认推理类型"""
        self._reasoning_map[agent] = rtype

    def record(
        self,
        agent_name: str,
        action: str,
        input_summary: str = "",
        output_summary: str = "",
        reasoning_type: str = "heuristic",
        latency_ms: float = 0.0,
        status: str = "success",
        decision_context: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """直接记录一条 trace"""
        evt = TraceEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=self._current_session,
            agent_name=agent_name,
            action=action,
            input_summary=input_summary[:200],
            output_summary=output_summary[:300],
            reasoning_type=reasoning_type or self._reasoning_map.get(agent_name, "heuristic"),
            latency_ms=latency_ms,
            status=status,
            decision_context=decision_context or {},
        )
        self._traces.append(evt)
        return evt

    def sync_from_bus(self, reasoning_type: str = "heuristic") -> int:
        """从 EventBus 同步所有事件为 TraceEvent"""
        bus = AgentEventBus.get_instance()
        events = bus.get_timeline()
        count = 0
        for evt in events:
            rtype = self._reasoning_map.get(evt.agent, reasoning_type)
            self._traces.append(TraceEvent.from_event(
                evt, session_id=self._current_session, reasoning_type=rtype,
            ))
            count += 1
        bus.clear()  # 消费后清空 EventBus
        return count

    def save(self) -> None:
        """持久化到 JSON"""
        if not self._current_session:
            return
        f = self._dir / f"{self._current_session}.json"
        f.write_text(json.dumps(
            [t.to_dict() for t in self._traces],
            ensure_ascii=False, indent=2,
        ))

    def load(self, session_id: str) -> List[TraceEvent]:
        f = self._dir / f"{session_id}.json"
        if not f.exists():
            return []
        data = json.loads(f.read_text())
        return [
            TraceEvent(
                timestamp=d.get("timestamp", ""),
                session_id=d.get("session_id", ""),
                agent_name=d.get("agent_name", ""),
                action=d.get("action", ""),
                input_summary=d.get("input_summary", ""),
                output_summary=d.get("output_summary", ""),
                reasoning_type=d.get("reasoning_type", "heuristic"),
                latency_ms=d.get("latency_ms", 0.0),
                status=d.get("status", "success"),
                decision_context=d.get("decision_context", {}),
            )
            for d in data
        ]

    def query(
        self,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[TraceEvent]:
        """查询 trace"""
        traces = self._traces
        if session_id:
            traces = self.load(session_id)
        results = []
        for t in traces:
            if agent_name and t.agent_name != agent_name:
                continue
            if action and t.action != action:
                continue
            if status and t.status != status:
                continue
            results.append(t)
        return results

    def get_timeline(self) -> List[TraceEvent]:
        return list(self._traces)

    def stats(self) -> Dict[str, Any]:
        agents = {}
        for t in self._traces:
            a = t.agent_name
            if a not in agents:
                agents[a] = {"count": 0, "errors": 0, "avg_latency": 0.0}
            agents[a]["count"] += 1
            if t.status == "error":
                agents[a]["errors"] += 1
        return {
            "total_events": len(self._traces),
            "session": self._current_session,
            "agents": agents,
        }
