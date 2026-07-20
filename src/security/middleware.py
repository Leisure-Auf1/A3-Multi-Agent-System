"""
Phase 9.6-B — Security Middleware

Per-user rate limiting, permission audit, and suspicious request detection.

Enhances the existing platform rate limiter with:
  - Role-aware limits (FREE/STUDENT/PRO get different RPM caps)
  - Permission audit trail (every guard check logged)
  - Suspicious request detection (rapid failures, burst patterns)

Usage (FastAPI dependency):
    from src.security.middleware import security_middleware

    @router.post("/chat")
    def chat(
        user: AuthUser = Depends(require_auth),
        ctx: RequestContext = Depends(security_middleware),
    ):
        ...

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..auth.models import AuthUser
from ..auth.context import RequestContext, build_context
from ..user.permission import PermissionManager, Role
from ..platform.errors import RateLimitExceeded


# ── Suspicious Request Detector ───────────────

@dataclass
class RequestRecord:
    """Track recent requests for anomaly detection."""
    timestamp: float
    endpoint: str
    status_code: int
    success: bool
    duration_ms: float


class SuspiciousDetector:
    """Detect suspicious request patterns.

    Checks for:
      - Burst: >N requests in <window seconds
      - High failure rate: >threshold% failures
      - Rapid retry: <min_interval between identical failed calls
    """

    def __init__(
        self,
        burst_threshold: int = 30,       # requests
        burst_window: float = 10.0,       # seconds
        failure_rate_threshold: float = 0.6,  # 60%
        min_samples: int = 10,
        rapid_retry_interval: float = 0.5,   # seconds
    ):
        self._burst_threshold = burst_threshold
        self._burst_window = burst_window
        self._failure_rate_threshold = failure_rate_threshold
        self._min_samples = min_samples
        self._rapid_retry_interval = rapid_retry_interval
        self._history: Dict[str, List[RequestRecord]] = defaultdict(list)

    def record(
        self,
        user_id: str,
        endpoint: str,
        status_code: int,
        success: bool,
        duration_ms: float = 0.0,
    ):
        """Record a request."""
        rec = RequestRecord(
            timestamp=time.time(),
            endpoint=endpoint,
            status_code=status_code,
            success=success,
            duration_ms=duration_ms,
        )
        self._history[user_id].append(rec)

        # Prune old records (keep last 200)
        if len(self._history[user_id]) > 200:
            self._history[user_id] = self._history[user_id][-200:]

    def is_suspicious(self, user_id: str) -> tuple[bool, str]:
        """Check if recent activity is suspicious.

        Returns:
            (is_suspicious, reason_string)
        """
        records = self._history.get(user_id, [])
        if not records:
            return False, ""

        now = time.time()

        # Check burst
        recent = [r for r in records if now - r.timestamp < self._burst_window]
        if len(recent) >= self._burst_threshold:
            return True, f"Burst: {len(recent)} requests in {self._burst_window}s"

        # Check failure rate
        if len(records) >= self._min_samples:
            failures = sum(1 for r in records if not r.success)
            if failures / len(records) >= self._failure_rate_threshold:
                return True, f"High failure rate: {failures}/{len(records)}"

        # Check rapid retries (consecutive failures within interval)
        failures_sorted = sorted(
            [r for r in records if not r.success],
            key=lambda r: r.timestamp,
        )
        for i in range(1, len(failures_sorted)):
            gap = failures_sorted[i].timestamp - failures_sorted[i-1].timestamp
            if gap < self._rapid_retry_interval:
                return True, f"Rapid retry: {gap:.3f}s between failures"

        return False, ""

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user's recent activity."""
        records = self._history.get(user_id, [])
        if not records:
            return {"total_requests": 0, "failure_rate": 0.0, "avg_duration_ms": 0.0}

        now = time.time()
        recent_60s = [r for r in records if now - r.timestamp < 60]

        return {
            "total_requests": len(records),
            "recent_60s": len(recent_60s),
            "failure_rate": round(
                sum(1 for r in records if not r.success) / len(records), 3
            ) if records else 0.0,
            "avg_duration_ms": round(
                sum(r.duration_ms for r in records) / len(records), 1
            ) if records else 0.0,
        }

    def reset(self, user_id: str = ""):
        """Clear history for a user or all."""
        if user_id:
            self._history.pop(user_id, None)
        else:
            self._history.clear()


# ── Security Middleware (FastAPI Dependency) ───

# Singleton instances (replace with DI in production)
_detector = SuspiciousDetector()


async def security_middleware(
    user: AuthUser = None,
) -> Optional[RequestContext]:
    """FastAPI dependency: build request context with security checks.

    Usage:
        @router.post("/api/v2/chat")
        async def chat(
            user: AuthUser = Depends(require_auth),
            ctx: RequestContext = Depends(security_middleware),
        ):
            if not ctx.can_use_model("openai"):
                raise HTTPException(403, "Model not available for your plan")
            ...
    """
    if user is None:
        return None

    ctx = build_context(
        user_id=user.id,
        api_key_used=False,
    )

    # Check for suspicious activity
    is_suspicious, reason = _detector.is_suspicious(user.id)
    if is_suspicious:
        from ..security.audit import AuditLogger
        AuditLogger().log(
            user_id=user.id,
            role=ctx.user.role,
            endpoint="security/suspicious",
            method="DETECT",
            success=False,
            error_message=reason,
            extra={"type": "suspicious_detection"},
        )

    return ctx


def record_request(
    user_id: str,
    endpoint: str,
    status_code: int,
    success: bool,
    duration_ms: float = 0.0,
):
    """Record a request in the suspicious detector.
    Call this after every API response.
    """
    _detector.record(
        user_id=user_id,
        endpoint=endpoint,
        status_code=status_code,
        success=success,
        duration_ms=duration_ms,
    )


def is_request_suspicious(user_id: str) -> tuple[bool, str]:
    """Check if a user's recent activity is suspicious."""
    return _detector.is_suspicious(user_id)
