"""
Phase 13.2 — Provider Runtime Status Layer

Tracks real-time provider state for UI transparency:
  - Connection status (connected / disconnected / unknown)
  - Active model name
  - Last request timestamp + latency
  - Token usage accumulator
  - Fallback chain information

Usage:
    from src.providers.status import ProviderStatusTracker, ProviderStatusSnapshot

    tracker = ProviderStatusTracker()
    tracker.record_request("deepseek", "deepseek-chat", 234.5, 150)
    snapshot = tracker.get_snapshot("deepseek")
    # → ProviderStatusSnapshot(provider="deepseek", connected=True, ...)

Architecture: zero Agent Runtime modification. Pure tracking layer.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────


@dataclass
class ProviderStatusSnapshot:
    """Point-in-time view of one provider's runtime state."""

    provider: str = ""
    label: str = ""
    emoji: str = ""
    category: str = "production"

    # Connection
    connected: bool = False
    last_check_ms: float = 0.0
    check_error: str = ""

    # Active usage
    active_model: str = ""
    last_request_at: float = 0.0
    last_latency_ms: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Fallback
    is_fallback: bool = False
    fallback_from: str = ""
    fallback_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "label": self.label,
            "emoji": self.emoji,
            "category": self.category,
            "connected": self.connected,
            "last_check_ms": round(self.last_check_ms, 1),
            "check_error": self.check_error,
            "active_model": self.active_model,
            "last_request_at": self.last_request_at,
            "last_latency_ms": round(self.last_latency_ms, 1),
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "is_fallback": self.is_fallback,
            "fallback_from": self.fallback_from,
            "fallback_reason": self.fallback_reason,
        }


@dataclass
class ActiveRunInfo:
    """Information about the currently active provider for a learning run."""

    engine: str = ""           # "AI Engine" label (e.g. "DeepSeek v4 Pro")
    provider: str = ""         # provider key
    model: str = ""            # model name
    generation_time_ms: float = 0.0
    is_fallback: bool = False
    fallback_from: str = ""
    fallback_reason: str = ""
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "provider": self.provider,
            "model": self.model,
            "generation_time_ms": round(self.generation_time_ms, 1),
            "is_fallback": self.is_fallback,
            "fallback_from": self.fallback_from,
            "fallback_reason": self.fallback_reason,
            "tokens_used": self.tokens_used,
        }


# ──────────────────────────────────────────────
# Status Tracker (thread-safe singleton)
# ──────────────────────────────────────────────


class ProviderStatusTracker:
    """
    Thread-safe runtime tracker for provider status.

    Records every LLM request so the UI can display:
      - Which model is actually being called
      - Current connection state
      - Latency metrics
      - Token usage
      - Fallback events
    """

    _instance: Optional[ProviderStatusTracker] = None
    _lock = threading.Lock()

    def __init__(self):
        self._lock = threading.Lock()
        self._status: Dict[str, ProviderStatusSnapshot] = {}
        self._active_run: Optional[ActiveRunInfo] = None
        self._init_from_meta()

    def _init_from_meta(self) -> None:
        """Seed all known providers from PROVIDER_META."""
        try:
            from src.config.llm_config import PROVIDER_META
        except ImportError:
            return
        for key, meta in PROVIDER_META.items():
            self._status[key] = ProviderStatusSnapshot(
                provider=key,
                label=meta.get("label", key),
                emoji=meta.get("emoji", "🔌"),
                category=meta.get("category", "production"),
            )

    @classmethod
    def get_instance(cls) -> ProviderStatusTracker:
        """Get or create the global singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Recording ─────────────────────────────

    def record_request(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Record a successful LLM request."""
        with self._lock:
            snap = self._get_or_create(provider)
            snap.connected = True
            snap.active_model = model
            snap.last_request_at = time.time()
            snap.last_latency_ms = latency_ms
            snap.total_requests += 1
            snap.total_tokens += tokens
            snap.total_cost_usd += cost_usd
            snap.check_error = ""

    def record_fallback(
        self,
        from_provider: str,
        to_provider: str,
        reason: str,
    ) -> None:
        """Record a fallback event."""
        with self._lock:
            snap = self._get_or_create(to_provider)
            snap.is_fallback = True
            snap.fallback_from = from_provider
            snap.fallback_reason = reason

    def record_error(self, provider: str, error: str) -> None:
        """Record a connection error."""
        with self._lock:
            snap = self._get_or_create(provider)
            snap.connected = False
            snap.last_check_ms = time.time()
            snap.check_error = error

    def set_connected(self, provider: str) -> None:
        """Mark provider as connected (e.g. after health check)."""
        with self._lock:
            snap = self._get_or_create(provider)
            snap.connected = True
            snap.last_check_ms = time.time()
            snap.check_error = ""

    # ── Active Run ────────────────────────────

    def set_active_run(self, info: ActiveRunInfo) -> None:
        """Set the currently active learning run info."""
        self._active_run = info

    def clear_active_run(self) -> None:
        """Clear the active run info."""
        self._active_run = None

    def get_active_run(self) -> Optional[ActiveRunInfo]:
        """Get the current active run info."""
        return self._active_run

    # ── Querying ──────────────────────────────

    def get_snapshot(self, provider: str) -> ProviderStatusSnapshot:
        """Get runtime snapshot for one provider."""
        with self._lock:
            return self._get_or_create(provider)

    def get_all_snapshots(
        self, category: Optional[str] = None
    ) -> List[ProviderStatusSnapshot]:
        """Get all provider snapshots, optionally filtered by category."""
        with self._lock:
            snaps = list(self._status.values())
        if category:
            snaps = [s for s in snaps if s.category == category]
        return snaps

    def get_summary(self) -> Dict[str, Any]:
        """Get a compact summary for API response."""
        with self._lock:
            production = [
                s.to_dict() for s in self._status.values()
                if s.category == "production"
            ]
            demo = [
                s.to_dict() for s in self._status.values()
                if s.category == "demo"
            ]
            active = {}
            if self._active_run:
                active = self._active_run.to_dict()

            all_connected = [
                s.provider for s in self._status.values() if s.connected
            ]
            total = sum(s.total_tokens for s in self._status.values())

        return {
            "production_providers": production,
            "demo_providers": demo,
            "connected_count": len(all_connected),
            "connected_providers": all_connected,
            "total_tokens_all": total,
            "active_run": active,
        }

    def reset(self) -> None:
        """Reset all tracking state (for testing)."""
        with self._lock:
            self._status.clear()
            self._active_run = None
            self._init_from_meta()

    # ── Internal ──────────────────────────────

    def _get_or_create(self, provider: str) -> ProviderStatusSnapshot:
        if provider not in self._status:
            try:
                from src.config.llm_config import PROVIDER_META
            except ImportError:
                PROVIDER_META = {}
            meta = PROVIDER_META.get(provider, {})
            self._status[provider] = ProviderStatusSnapshot(
                provider=provider,
                label=meta.get("label", provider),
                emoji=meta.get("emoji", "🔌"),
                category=meta.get("category", "production"),
            )
        return self._status[provider]


# ──────────────────────────────────────────────
# Convenience function
# ──────────────────────────────────────────────


def get_provider_status(provider: str) -> Dict[str, Any]:
    """Get runtime status for a provider as a dict."""
    tracker = ProviderStatusTracker.get_instance()
    return tracker.get_snapshot(provider).to_dict()


def get_provider_status_summary() -> Dict[str, Any]:
    """Get full provider status summary as a dict."""
    tracker = ProviderStatusTracker.get_instance()
    return tracker.get_summary()
