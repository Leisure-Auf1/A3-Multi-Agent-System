"""
Phase 9.4-B — User Adaptive Model Preference Layer

Learns from user behavior to influence model selection.
Preferences are stored in workspace/{student_id}/memory/model_preferences.json.

Usage:
    from src.orchestration.user_preferences import UserPreferenceManager

    mgr = UserPreferenceManager("student-001")
    mgr.record_feedback(task_type="generate_material", model="gpt-5.6", rating=5)
    pref = mgr.get_preference("generate_material")
    # → {"preferred_model": "gpt-5.6", "quality_score": 0.95}

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Data models ───────────────────────────────

@dataclass
class TaskPreference:
    """Per-task type preference record."""
    task_type: str
    preferred_model: str = ""
    preferred_provider: str = ""
    quality_score: float = 0.5       # 0.0–1.0, learned from ratings
    use_count: int = 0
    avg_rating: float = 0.0
    last_used: float = 0.0
    notes: str = ""


@dataclass
class UserModelPreference:
    """Complete user model preference profile."""
    student_id: str
    task_preferences: Dict[str, TaskPreference] = field(default_factory=dict)
    preferred_style: str = ""         # e.g. "concise", "detailed", "visual"
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "task_preferences": {
                k: {
                    "task_type": v.task_type,
                    "preferred_model": v.preferred_model,
                    "preferred_provider": v.preferred_provider,
                    "quality_score": v.quality_score,
                    "use_count": v.use_count,
                    "avg_rating": v.avg_rating,
                    "last_used": v.last_used,
                    "notes": v.notes,
                }
                for k, v in self.task_preferences.items()
            },
            "preferred_style": self.preferred_style,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserModelPreference":
        prefs = {}
        for k, v in d.get("task_preferences", {}).items():
            prefs[k] = TaskPreference(
                task_type=v.get("task_type", k),
                preferred_model=v.get("preferred_model", ""),
                preferred_provider=v.get("preferred_provider", ""),
                quality_score=v.get("quality_score", 0.5),
                use_count=v.get("use_count", 0),
                avg_rating=v.get("avg_rating", 0.0),
                last_used=v.get("last_used", 0.0),
                notes=v.get("notes", ""),
            )
        return cls(
            student_id=d.get("student_id", ""),
            task_preferences=prefs,
            preferred_style=d.get("preferred_style", ""),
            updated_at=d.get("updated_at", time.time()),
        )


# ── Preference Manager ─────────────────────────

def _get_prefs_path(student_id: str) -> Path:
    """Get path to model_preferences.json."""
    base = Path(os.path.expanduser("~/.a3-agent/workspace"))
    return base / student_id / "memory" / "model_preferences.json"


class UserPreferenceManager:
    """
    Manages per-user model preferences learned from behavior.

    Stores preferences in workspace/{student_id}/memory/model_preferences.json.
    Updates are incremental — each feedback call adjusts quality scores via EMA.
    """

    def __init__(self, student_id: str):
        self.student_id = student_id
        self._prefs: Optional[UserModelPreference] = None

    # ── Load / Save ───────────────────────

    def _load(self) -> UserModelPreference:
        if self._prefs is not None:
            return self._prefs
        path = _get_prefs_path(self.student_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._prefs = UserModelPreference.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                self._prefs = UserModelPreference(student_id=self.student_id)
        else:
            self._prefs = UserModelPreference(student_id=self.student_id)
        return self._prefs

    def _save(self):
        if self._prefs is None:
            return
        path = _get_prefs_path(self.student_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._prefs.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Public API ────────────────────────

    def get_preference(self, task_type: str) -> Optional[TaskPreference]:
        """Get learned preference for a specific task type."""
        prefs = self._load()
        return prefs.task_preferences.get(task_type)

    def get_all_preferences(self) -> Dict[str, TaskPreference]:
        """Get all task preferences."""
        return dict(self._load().task_preferences)

    def record_feedback(
        self,
        task_type: str,
        model: str = "",
        provider: str = "",
        rating: int = 0,        # 1-5 scale
        success: bool = True,
        user_comment: str = "",
    ):
        """
        Record user feedback to update preferences.

        Uses EMA (Exponential Moving Average) to adjust quality scores:
            new_score = old_score * 0.7 + rating/5 * 0.3

        Args:
            task_type: TaskType value
            model: Selected model ID
            provider: Selected provider
            rating: User rating 1-5 (0 = no rating)
            success: Whether the call succeeded
            user_comment: Optional user comment
        """
        prefs = self._load()
        tp = prefs.task_preferences.get(task_type)

        if tp is None:
            tp = TaskPreference(task_type=task_type)
            prefs.task_preferences[task_type] = tp

        # Update model/provider tracking
        if model:
            tp.preferred_model = model
        if provider:
            tp.preferred_provider = provider

        tp.use_count += 1
        tp.last_used = time.time()

        # Update quality score via EMA
        if rating > 0:
            normalized = rating / 5.0  # 1-5 → 0.2-1.0
            tp.quality_score = round(tp.quality_score * 0.7 + normalized * 0.3, 3)
            tp.avg_rating = tp.quality_score
        elif success:
            # Successful use without explicit rating → slight boost
            tp.quality_score = min(1.0, tp.quality_score + 0.01)

        if user_comment:
            tp.notes = user_comment

        prefs.updated_at = time.time()
        self._save()

    def get_preferred_model(self, task_type: str) -> Optional[str]:
        """Get the user's preferred model for a task type."""
        tp = self.get_preference(task_type)
        if tp and tp.preferred_model:
            return tp.preferred_model
        return None

    def get_preferred_provider(self, task_type: str) -> Optional[str]:
        """Get the user's preferred provider for a task type."""
        tp = self.get_preference(task_type)
        if tp and tp.preferred_provider:
            return tp.preferred_provider
        return None

    def get_quality_score(self, task_type: str) -> float:
        """Get quality score for a task type (0.0–1.0)."""
        tp = self.get_preference(task_type)
        return tp.quality_score if tp else 0.5

    def set_preferred_style(self, style: str):
        """Set global style preference (concise/detailed/visual)."""
        prefs = self._load()
        prefs.preferred_style = style
        self._save()

    def clear_preferences(self):
        """Clear all preferences for this student."""
        self._prefs = UserModelPreference(student_id=self.student_id)
        path = _get_prefs_path(self.student_id)
        if path.exists():
            path.unlink()
