"""
Phase 8 — AgentEventBus: 轻量 Agent 执行追踪

所有 Agent 通过此总线发出事件, 用于:
  - Web Demo 中的 Agent Trace 面板 (类似 LangSmith)
  - Debug 日志
  - 后续 Offline Evaluation

使用:
    bus = AgentEventBus()
    bus.emit("ProfileAgent", "extract_profile",
             input_summary="学生输入: 零基础...",
             output_summary="knowledge_base=junior_dev")
    events = bus.get_timeline()
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class AgentEvent:
    """一次 Agent 执行事件"""
    agent: str
    action: str
    input_summary: str = ""
    output_summary: str = ""
    status: str = "success"          # success | error | skipped
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "action": self.action,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


# ──────────────────────────────────────────────
# EventBus
# ──────────────────────────────────────────────

class AgentEventBus:
    """
    全局 Agent 事件总线 (单例模式).

    使用:
        bus = AgentEventBus.get_instance()
        bus.emit(...)
    """

    _instance: Optional["AgentEventBus"] = None

    def __init__(self):
        self._events: List[AgentEvent] = []
        self._session_id: str = ""

    @classmethod
    def get_instance(cls) -> "AgentEventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = cls()

    def start_session(self, session_id: str) -> None:
        self._session_id = session_id
        self._events.clear()
        self.emit("System", "session_start",
                  input_summary=f"Session: {session_id}",
                  output_summary="Session started")

    def emit(
        self,
        agent: str,
        action: str,
        input_summary: str = "",
        output_summary: str = "",
        status: str = "success",
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
        event = AgentEvent(
            agent=agent,
            action=action,
            input_summary=input_summary[:200],
            output_summary=output_summary[:300],
            status=status,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def get_timeline(self) -> List[AgentEvent]:
        return list(self._events)

    def get_recent(self, n: int = 20) -> List[AgentEvent]:
        return self._events[-n:]

    def to_json(self) -> str:
        return json.dumps(
            [e.to_dict() for e in self._events],
            ensure_ascii=False, indent=2,
        )

    def clear(self) -> None:
        self._events.clear()

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def latest_event(self) -> Optional[AgentEvent]:
        return self._events[-1] if self._events else None


# ──────────────────────────────────────────────
# 便捷装饰器
# ──────────────────────────────────────────────

def trace_agent(agent_name: str, action: str = ""):
    """装饰器: 自动追踪 Agent 方法调用"""
    import time
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bus = AgentEventBus.get_instance()
            act = action or func.__name__
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                # 提取摘要
                input_s = _summarize_args(args, kwargs)
                output_s = _summarize_result(result)
                bus.emit(agent_name, act,
                         input_summary=input_s[:200],
                         output_summary=output_s[:300],
                         duration_ms=round(elapsed, 1))
                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                bus.emit(agent_name, act,
                         input_summary=str(args)[:100],
                         output_summary=f"Error: {e}",
                         status="error",
                         duration_ms=round(elapsed, 1))
                raise
        return wrapper
    return decorator


def _summarize_args(args, kwargs) -> str:
    parts = []
    for a in args[:1]:
        s = str(a)
        if len(s) > 80:
            s = s[:80] + "..."
        parts.append(s)
    for k, v in list(kwargs.items())[:2]:
        sv = str(v)
        if len(sv) > 50:
            sv = sv[:50] + "..."
        parts.append(f"{k}={sv}")
    return ", ".join(parts) or "(no args)"


def _summarize_result(result) -> str:
    if result is None:
        return "None"
    if hasattr(result, "to_dict"):
        d = result.to_dict()
        return json.dumps(d, ensure_ascii=False)[:200]
    if isinstance(result, (list, tuple)):
        return f"[{len(result)} items]"
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)[:200]
    s = str(result)
    return s[:200] if len(s) > 200 else s
