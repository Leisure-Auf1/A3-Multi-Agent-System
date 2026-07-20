"""
Phase 5.0 — Runtime Dashboard API Routes

⚠️ DEPRECATED — v1 runtime routes are frozen.
Use v2 auth-protected endpoints for production.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse

from veritas.runtime import RuntimeBus, RuntimeSnapshot
from src.auth.middleware import require_auth
from src.auth.models import AuthUser

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"], deprecated=True)


def _deprecated_response(content: dict | list) -> JSONResponse:
    """Wrap response with deprecation headers."""
    resp = JSONResponse(content=content)
    resp.headers["X-Deprecated-API"] = "true"
    resp.headers["Sunset"] = "2026-09-01"
    return resp


@router.get("/snapshot", summary="⚠️ DEPRECATED — 获取运行时快照")
def get_snapshot(user: AuthUser = Depends(require_auth)) -> JSONResponse:
    """返回完整 RuntimeSnapshot: 状态 + 事件 + 指标 + 时间线."""
    snapshot = RuntimeBus.snapshot()
    return _deprecated_response(snapshot.to_dict())


@router.get("/metrics", summary="⚠️ DEPRECATED — 获取运行时指标")
def get_metrics(user: AuthUser = Depends(require_auth)) -> JSONResponse:
    """返回 RuntimeMetrics 摘要."""
    metrics = RuntimeBus.get_metrics()
    return _deprecated_response(metrics.summary())


@router.get("/timeline", summary="⚠️ DEPRECATED — 获取状态转换时间线")
def get_timeline(user: AuthUser = Depends(require_auth)) -> JSONResponse:
    """返回所有状态转换事件的时间线."""
    snapshot = RuntimeBus.snapshot()
    return _deprecated_response(snapshot.timeline)


@router.get("/events", summary="⚠️ DEPRECATED — 获取最近运行时事件")
def get_recent_events(
    limit: int = Query(default=20, ge=1, le=100),
    user: AuthUser = Depends(require_auth),
) -> JSONResponse:
    """返回最近的运行时事件."""
    bus = RuntimeBus.get_bus()
    events = bus.event_log()
    return _deprecated_response([e.to_dict() for e in events[-limit:]])


@router.get("/state", summary="⚠️ DEPRECATED — 获取当前状态")
def get_current_state(user: AuthUser = Depends(require_auth)) -> JSONResponse:
    """返回当前状态 + 最近评分."""
    snapshot = RuntimeBus.snapshot()
    return _deprecated_response({
        "current_state": snapshot.current_state,
        "last_state": snapshot.last_state,
        "evaluation_score": snapshot.evaluation_score,
        "has_errors": snapshot.has_errors,
        "last_error": snapshot.last_error,
    })


@router.post("/reset", summary="⚠️ DEPRECATED — 重置运行时数据")
def reset_runtime(user: AuthUser = Depends(require_auth)) -> JSONResponse:
    """清空事件日志和指标 (不重置订阅者)."""
    RuntimeBus.reset()
    return _deprecated_response({"status": "reset", "deprecated": True})
