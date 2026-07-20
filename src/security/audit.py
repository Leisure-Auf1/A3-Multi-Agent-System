"""
Phase 9.6-B — Security Audit Log

Records every API call with:
  - who (user_id, role)
  - when (timestamp)
  - what API (endpoint, method)
  - which model (provider, model_id)
  - cost (tokens used, estimated USD)
  - result (success/failure, status code)

Storage: JSONL file per user under workspace/{user_id}/security/audit.jsonl

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Storage ──────────────────────────────────

def _get_audit_path(user_id: str) -> Path:
    base = Path(os.path.expanduser("~/.a3-agent/workspace"))
    return base / user_id / "security" / "audit.jsonl"


def _ensure_audit_dir(user_id: str) -> Path:
    p = _get_audit_path(user_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ── Data Models ──────────────────────────────

@dataclass
class AuditEntry:
    """A single audit log entry."""
    event_id: str                            # unique event ID
    user_id: str                             # who
    role: str = ""                           # user role at time of call
    timestamp: float = field(default_factory=time.time)
    # API details
    endpoint: str = ""                       # e.g. "/api/v2/chat/stream"
    method: str = ""                         # GET, POST, etc.
    status_code: int = 0                     # HTTP response code
    # Model details
    provider: str = ""                       # e.g. "openai", "deepseek"
    model_id: str = ""                       # e.g. "gpt-5.6"
    # Cost
    tokens_used: int = 0                     # prompt + completion tokens
    estimated_cost_usd: float = 0.0
    # Result
    success: bool = True
    error_message: str = ""
    # Metadata
    request_id: str = ""
    client_ip: str = ""
    user_agent: str = ""
    duration_ms: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "role": self.role,
            "timestamp": self.timestamp,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "provider": self.provider,
            "model_id": self.model_id,
            "tokens_used": self.tokens_used,
            "estimated_cost_usd": self.estimated_cost_usd,
            "success": self.success,
            "error_message": self.error_message,
            "request_id": self.request_id,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "duration_ms": self.duration_ms,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AuditEntry":
        return cls(
            event_id=d.get("event_id", ""),
            user_id=d.get("user_id", ""),
            role=d.get("role", ""),
            timestamp=d.get("timestamp", 0.0),
            endpoint=d.get("endpoint", ""),
            method=d.get("method", ""),
            status_code=d.get("status_code", 0),
            provider=d.get("provider", ""),
            model_id=d.get("model_id", ""),
            tokens_used=d.get("tokens_used", 0),
            estimated_cost_usd=d.get("estimated_cost_usd", 0.0),
            success=d.get("success", True),
            error_message=d.get("error_message", ""),
            request_id=d.get("request_id", ""),
            client_ip=d.get("client_ip", ""),
            user_agent=d.get("user_agent", ""),
            duration_ms=d.get("duration_ms", 0.0),
            extra=d.get("extra", {}),
        )


# ── Audit Logger ─────────────────────────────

class AuditLogger:
    """Append-only security audit logger.

    Usage:
        logger = AuditLogger()
        logger.log(
            user_id="usr_1",
            role="pro",
            endpoint="/api/v2/chat/stream",
            method="POST",
            provider="openai",
            tokens_used=1500,
            success=True,
        )
        entries = logger.query("usr_1", limit=50)
    """

    def log(
        self,
        user_id: str,
        role: str = "",
        endpoint: str = "",
        method: str = "",
        status_code: int = 0,
        provider: str = "",
        model_id: str = "",
        tokens_used: int = 0,
        estimated_cost_usd: float = 0.0,
        success: bool = True,
        error_message: str = "",
        request_id: str = "",
        duration_ms: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Write an audit entry. Returns the created entry.

        This is fire-and-forget — errors are caught and logged to stderr
        so they never break the main request flow.
        """
        import uuid
        event_id = f"audit_{uuid.uuid4().hex[:16]}"

        entry = AuditEntry(
            event_id=event_id,
            user_id=user_id,
            role=role,
            timestamp=time.time(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            provider=provider,
            model_id=model_id,
            tokens_used=tokens_used,
            estimated_cost_usd=estimated_cost_usd,
            success=success,
            error_message=error_message,
            request_id=request_id,
            duration_ms=duration_ms,
            extra=extra or {},
        )

        try:
            path = _ensure_audit_dir(user_id)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            import sys
            print(f"[AuditLogger] Failed to write audit entry for {user_id}", file=sys.stderr)

        return entry

    def query(
        self,
        user_id: str,
        limit: int = 50,
        success_only: Optional[bool] = None,
        since: float = 0.0,
        endpoint_prefix: str = "",
    ) -> List[AuditEntry]:
        """Query audit entries for a user.

        Args:
            user_id: User to query
            limit: Max entries to return (most recent first)
            success_only: Filter by success/failure (None = all)
            since: Only entries after this timestamp
            endpoint_prefix: Filter by endpoint prefix

        Returns:
            List of AuditEntry, most recent first
        """
        path = _get_audit_path(user_id)
        if not path.exists():
            return []

        entries = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        entry = AuditEntry.from_dict(d)

                        if success_only is not None and entry.success != success_only:
                            continue
                        if since > 0 and entry.timestamp < since:
                            continue
                        if endpoint_prefix and not entry.endpoint.startswith(endpoint_prefix):
                            continue

                        entries.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        pass
        except FileNotFoundError:
            return []

        # Most recent first
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def get_user_stats(self, user_id: str, since: float = 0.0) -> Dict[str, Any]:
        """Get aggregate usage stats from audit log.

        Returns:
            { total_calls, success_calls, failed_calls, total_tokens,
              estimated_cost, providers_used, models_used, endpoints_hit }
        """
        entries = self.query(user_id, limit=10_000, since=since)

        if not entries:
            return {
                "total_calls": 0, "success_calls": 0, "failed_calls": 0,
                "total_tokens": 0, "estimated_cost": 0.0,
                "providers_used": [], "models_used": [], "endpoints_hit": [],
            }

        providers = set()
        models = set()
        endpoints = set()

        for e in entries:
            if e.provider:
                providers.add(e.provider)
            if e.model_id:
                models.add(e.model_id)
            if e.endpoint:
                endpoints.add(e.endpoint)

        return {
            "total_calls": len(entries),
            "success_calls": sum(1 for e in entries if e.success),
            "failed_calls": sum(1 for e in entries if not e.success),
            "total_tokens": sum(e.tokens_used for e in entries),
            "estimated_cost": round(sum(e.estimated_cost_usd for e in entries), 6),
            "providers_used": sorted(providers),
            "models_used": sorted(models),
            "endpoints_hit": sorted(endpoints),
        }

    def get_suspicious_activity(
        self,
        user_id: str,
        lookback_hours: int = 24,
    ) -> List[AuditEntry]:
        """Detect suspicious activity: rapid failures, high error rates.

        Returns entries that may indicate abuse or security issues.
        """
        cutoff = time.time() - lookback_hours * 3600
        entries = self.query(user_id, limit=500, since=cutoff)

        suspicious = []
        # Pattern 1: High failure rate (>50%)
        if len(entries) >= 10:
            failures = sum(1 for e in entries if not e.success)
            failure_rate = failures / len(entries)
            if failure_rate > 0.5:
                suspicious.extend([e for e in entries if not e.success][:20])

        # Pattern 2: Rapid-fire requests (<100ms apart)
        entries_by_time = sorted(entries, key=lambda e: e.timestamp)
        for i in range(1, len(entries_by_time)):
            gap = entries_by_time[i].timestamp - entries_by_time[i-1].timestamp
            if gap < 0.1:  # <100ms
                if entries_by_time[i] not in suspicious:
                    suspicious.append(entries_by_time[i])

        return suspicious[:50]
