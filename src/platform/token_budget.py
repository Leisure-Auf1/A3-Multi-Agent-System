"""
Phase 9.5-A — Token Budget Manager

Manages per-student token budgets with persistence to workspace.

Storage: workspace/{student_id}/memory/token_budget.json

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .errors import TokenBudgetExceeded


@dataclass
class TokenBudget:
    """Per-student token budget."""
    student_id: str
    daily_limit: int = 1_000_000      # tokens per day
    used_tokens: int = 0
    day_start: float = 0.0
    estimated_cost: float = 0.0

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.daily_limit - self.used_tokens)

    @property
    def is_exhausted(self) -> bool:
        return self.remaining_tokens <= 0

    @property
    def usage_pct(self) -> float:
        if self.daily_limit == 0:
            return 100.0
        return round(self.used_tokens / self.daily_limit * 100, 1)

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "daily_limit": self.daily_limit,
            "used_tokens": self.used_tokens,
            "day_start": self.day_start,
            "estimated_cost": self.estimated_cost,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TokenBudget":
        return cls(
            student_id=d.get("student_id", ""),
            daily_limit=d.get("daily_limit", 1_000_000),
            used_tokens=d.get("used_tokens", 0),
            day_start=d.get("day_start", 0.0),
            estimated_cost=d.get("estimated_cost", 0.0),
        )


def _get_budget_path(student_id: str) -> Path:
    base = Path(os.path.expanduser("~/.a3-agent/workspace"))
    return base / student_id / "memory" / "token_budget.json"


class TokenBudgetManager:
    """
    Manages per-student token budgets.

    Auto-resets every 24 hours.
    Persists to workspace/{student_id}/memory/token_budget.json.

    Usage:
        mgr = TokenBudgetManager("student-001")
        mgr.check_available(1000)      # raises TokenBudgetExceeded if over
        mgr.consume(500, "openai")     # consume tokens with cost tracking
        mgr.remaining()                # → int
    """

    def __init__(self, student_id: str):
        self.student_id = student_id
        self._budget: Optional[TokenBudget] = None

    def _load(self) -> TokenBudget:
        if self._budget is not None:
            return self._budget
        path = _get_budget_path(self.student_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                budget = TokenBudget.from_dict(data)
                # Auto-reset if 24h elapsed
                if time.time() - budget.day_start >= 86400:
                    budget = TokenBudget(
                        student_id=self.student_id,
                        daily_limit=budget.daily_limit,
                    )
                    budget.day_start = time.time()
                self._budget = budget
                return budget
            except (json.JSONDecodeError, KeyError):
                pass
        budget = TokenBudget(student_id=self.student_id, day_start=time.time())
        self._budget = budget
        return budget

    def _save(self):
        if self._budget is None:
            return
        path = _get_budget_path(self.student_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._budget.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def check_available(self, tokens: int = 0):
        """Check if enough tokens remain. Raises TokenBudgetExceeded."""
        budget = self._load()
        if budget.used_tokens + tokens > budget.daily_limit:
            raise TokenBudgetExceeded(
                message=f"Token budget exceeded: {budget.used_tokens}+{tokens} > {budget.daily_limit}",
                user_message=f"❌ 今日 Token 用量已满 ({budget.daily_limit})，请明天再试",
            )

    def consume(self, tokens: int = 0, provider: str = ""):
        """Consume tokens and track estimated cost."""
        budget = self._load()
        budget.used_tokens += tokens
        if provider:
            from src.orchestration.cost_optimizer import get_provider_cost_estimate
            rate = get_provider_cost_estimate(provider)
            budget.estimated_cost += tokens / 1_000_000 * rate
        self._save()

    def remaining(self) -> int:
        return self._load().remaining_tokens

    def get_budget(self) -> TokenBudget:
        return self._load()

    def estimate_cost(self, tokens: int, provider: str = "") -> float:
        """Estimate USD cost for a token count."""
        from src.orchestration.cost_optimizer import get_provider_cost_estimate
        rate = get_provider_cost_estimate(provider) if provider else 1.0
        return round(tokens / 1_000_000 * rate, 6)

    def reset(self):
        """Reset budget for this student."""
        self._budget = TokenBudget(
            student_id=self.student_id,
            day_start=time.time(),
        )
        self._save()
