"""
Phase 5.0 — Runtime Dashboard API Routes

FastAPI endpoints for querying runtime state, events, and metrics.

Endpoints:
    GET  /api/v1/runtime/snapshot    — full state snapshot
    GET  /api/v1/runtime/metrics     — metrics summary
    GET  /api/v1/runtime/timeline    — state transition timeline
    GET  /api/v1/runtime/events      — recent events (filterable)
    GET  /api/v1/runtime/state       — current state only
    POST /api/v1/runtime/reset       — reset the runtime bus
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from veritas.runtime import RuntimeBus, RuntimeSnapshot

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])


@router.get("/snapshot", summary="获取运行时快照")
def get_snapshot() -> dict:
    """返回完整 RuntimeSnapshot: 状态 + 事件 + 指标 + 时间线."""
    snapshot = RuntimeBus.snapshot()
    return snapshot.to_dict()


@router.get("/metrics", summary="获取运行时指标")
def get_metrics() -> dict:
    """返回 RuntimeMetrics 摘要."""
    metrics = RuntimeBus.get_metrics()
    return metrics.summary()


@router.get("/timeline", summary="获取状态转换时间线")
def get_timeline() -> list:
    """返回所有状态转换事件的时间线."""
    snapshot = RuntimeBus.snapshot()
    return snapshot.timeline


@router.get("/events", summary="获取最近运行时事件")
def get_recent_events(limit: int = Query(default=20, ge=1, le=100)) -> list:
    """返回最近的运行时事件."""
    bus = RuntimeBus.get_bus()
    events = bus.event_log()
    return [e.to_dict() for e in events[-limit:]]


@router.get("/state", summary="获取当前状态")
def get_current_state() -> dict:
    """返回当前状态 + 最近评分."""
    snapshot = RuntimeBus.snapshot()
    return {
        "current_state": snapshot.current_state,
        "last_state": snapshot.last_state,
        "evaluation_score": snapshot.evaluation_score,
        "has_errors": snapshot.has_errors,
        "last_error": snapshot.last_error,
    }


@router.post("/reset", summary="重置运行时数据")
def reset_runtime() -> dict:
    """清空事件日志和指标 (不重置订阅者)."""
    RuntimeBus.reset()
    return {"status": "reset"}
