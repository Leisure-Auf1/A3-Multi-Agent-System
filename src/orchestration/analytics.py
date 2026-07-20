"""
Phase 9.4-A — Decision Analytics

Reads and analyzes workspace/model_decisions.jsonl for observability.

Usage:
    from src.orchestration.analytics import DecisionAnalytics

    analytics = DecisionAnalytics("student-001")
    summary = analytics.get_summary()
    # → {total_requests, models, providers, fallback_rate, task_distribution, ...}

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context import ModelExecutionContext
from .cost_optimizer import get_provider_cost_estimate


def _get_log_path(student_id: str) -> Path:
    """Get path to model_decisions.jsonl."""
    return Path(os.path.expanduser("~/.a3-agent/workspace")) / student_id / "history" / "model_decisions.jsonl"


class DecisionAnalytics:
    """
    Analytics engine for orchestrator decision logs.

    Reads model_decisions.jsonl and computes statistics:
    - Model usage distribution
    - Provider success rate
    - Fallback frequency
    - Average latency
    - Cost estimates
    - Task type distribution
    """

    def __init__(self, student_id: str):
        self.student_id = student_id
        self._entries: List[dict] = []
        self._loaded = False

    # ── Data loading ──────────────────────

    def _load(self):
        """Load decision log entries from disk (idempotent)."""
        if self._loaded:
            return
        path = _get_log_path(self.student_id)
        if not path.exists():
            self._loaded = True
            return
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self._entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass  # skip malformed lines
        except Exception:
            pass
        self._loaded = True

    def _ensure_loaded(self):
        self._load()

    # ── Core statistics ───────────────────

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary."""
        self._ensure_loaded()
        entries = self._entries

        if not entries:
            return {
                "student_id": self.student_id,
                "total_requests": 0,
                "models": {},
                "providers": {},
                "fallback_rate": 0.0,
                "task_distribution": {},
                "avg_latency_ms": 0.0,
                "success_rate": 0.0,
                "estimated_cost": 0.0,
                "daily_requests": {},
            }

        # Model usage
        models: Dict[str, int] = defaultdict(int)
        providers: Dict[str, int] = defaultdict(int)
        tasks: Dict[str, int] = defaultdict(int)
        total_latency = 0.0
        success_count = 0
        fallback_count = 0
        total_cost = 0.0
        daily: Dict[str, int] = defaultdict(int)

        for e in entries:
            model = e.get("selected_model", "unknown")
            provider = e.get("selected_provider", "unknown")
            task = e.get("task_type", "unknown")
            success = e.get("success", False)
            fallback = e.get("fallback_used", False)
            latency = e.get("latency_ms", 0)
            timestamp = e.get("timestamp", 0)

            models[model] += 1
            providers[provider] += 1
            tasks[task] += 1
            total_latency += latency
            if success:
                success_count += 1
            if fallback:
                fallback_count += 1

            # Cost estimate: prompt + completion tokens * provider rate
            prompt_tokens = e.get("usage_prompt_tokens", 0)
            completion_tokens = e.get("usage_completion_tokens", 0)
            cost_per_1m = get_provider_cost_estimate(provider)
            total_cost += (prompt_tokens + completion_tokens) / 1_000_000 * cost_per_1m

            # Daily grouping
            if timestamp:
                import datetime
                day = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                daily[day] += 1

        n = len(entries)
        return {
            "student_id": self.student_id,
            "total_requests": n,
            "models": dict(sorted(models.items(), key=lambda x: -x[1])),
            "providers": dict(sorted(providers.items(), key=lambda x: -x[1])),
            "task_distribution": dict(sorted(tasks.items(), key=lambda x: -x[1])),
            "fallback_rate": round(fallback_count / n * 100, 1) if n else 0.0,
            "avg_latency_ms": round(total_latency / n, 1) if n else 0.0,
            "success_rate": round(success_count / n * 100, 1) if n else 0.0,
            "estimated_cost": round(total_cost, 4),
            "daily_requests": dict(sorted(daily.items())),
        }

    def get_model_usage(self) -> Dict[str, int]:
        """Get model usage counts."""
        self._ensure_loaded()
        counts: Dict[str, int] = defaultdict(int)
        for e in self._entries:
            model = e.get("selected_model", "unknown")
            counts[model] += 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def get_provider_success_rates(self) -> Dict[str, Dict[str, Any]]:
        """Get success/failure rates per provider."""
        self._ensure_loaded()
        stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "success": 0, "fallback": 0})
        for e in self._entries:
            provider = e.get("selected_provider", "unknown")
            stats[provider]["total"] += 1
            if e.get("success"):
                stats[provider]["success"] += 1
            if e.get("fallback_used"):
                stats[provider]["fallback"] += 1

        result = {}
        for provider, s in stats.items():
            total = s["total"]
            result[provider] = {
                "total": total,
                "success": s["success"],
                "success_rate": round(s["success"] / total * 100, 1) if total else 0.0,
                "fallback_count": s["fallback"],
                "fallback_rate": round(s["fallback"] / total * 100, 1) if total else 0.0,
            }
        return result

    def get_task_distribution(self) -> Dict[str, int]:
        """Get task type distribution."""
        self._ensure_loaded()
        tasks: Dict[str, int] = defaultdict(int)
        for e in self._entries:
            tasks[e.get("task_type", "unknown")] += 1
        return dict(sorted(tasks.items(), key=lambda x: -x[1]))

    def get_recent_entries(self, limit: int = 20) -> List[dict]:
        """Get most recent decision log entries."""
        self._ensure_loaded()
        return sorted(self._entries, key=lambda e: e.get("timestamp", 0), reverse=True)[:limit]

    def get_fallback_rate(self) -> float:
        """Get overall fallback rate as percentage."""
        self._ensure_loaded()
        if not self._entries:
            return 0.0
        fb = sum(1 for e in self._entries if e.get("fallback_used"))
        return round(fb / len(self._entries) * 100, 1)

    def get_estimated_cost(self) -> float:
        """Get total estimated cost in USD."""
        self._ensure_loaded()
        total = 0.0
        for e in self._entries:
            provider = e.get("selected_provider", "")
            cost_per_1m = get_provider_cost_estimate(provider)
            prompt_tokens = e.get("usage_prompt_tokens", 0)
            completion_tokens = e.get("usage_completion_tokens", 0)
            total += (prompt_tokens + completion_tokens) / 1_000_000 * cost_per_1m
        return round(total, 4)

    def get_entry_count(self) -> int:
        """Get total number of decision log entries."""
        self._ensure_loaded()
        return len(self._entries)
