"""
Phase 5.4 — Checkpoint Manager

Manages RuntimeContext snapshots for rollback recovery.
Saves named checkpoints of context state (profile, plan, evaluation, etc.)
and restores them on demand.

Usage:
    ckm = CheckpointManager()
    ckm.save(ctx, "before_evaluate")
    # ... failure occurs ...
    ckm.rollback(ctx, "before_evaluate")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import copy


@dataclass
class ContextSnapshot:
    """
    A point-in-time snapshot of RuntimeContext state.

    Captures the key outputs of the agent pipeline:
    profile, learning_plan, resources, evaluation, reflection, meta_reflection, errors.
    """
    name: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    profile: Optional[Dict[str, Any]] = None
    learning_plan: Optional[Dict[str, Any]] = None
    resources: Optional[List[Dict[str, Any]]] = None
    evaluation: Optional[Dict[str, Any]] = None
    reflection: Optional[Dict[str, Any]] = None
    meta_reflection: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "has_profile": self.profile is not None,
            "has_plan": self.learning_plan is not None,
            "resources_count": len(self.resources or []),
            "has_evaluation": self.evaluation is not None,
            "errors": self.errors,
        }


class CheckpointManager:
    """
    Manages named context checkpoints for rollback recovery.

    Supports save, load, rollback, and listing of checkpoints.
    Auto-evicts old checkpoints beyond max_checkpoints.

    Usage:
        ckm = CheckpointManager(max_checkpoints=10)
        ckm.save(ctx, "after_profile")
        ckm.save(ctx, "after_plan")
        ckm.rollback(ctx, "after_profile")  # restores profile state
    """

    def __init__(self, max_checkpoints: int = 10):
        self._checkpoints: Dict[str, ContextSnapshot] = {}
        self._order: List[str] = []
        self._max = max(1, max_checkpoints)

    # ── Save ─────────────────────────────────

    def save(self, ctx: Any, name: Optional[str] = None) -> str:
        """
        Save current context state as a named checkpoint.

        Args:
            ctx: RuntimeContext to snapshot.
            name: Optional checkpoint name (auto-generated if None).

        Returns:
            The checkpoint name used.
        """
        snapshot_name = name or f"ckpt_{len(self._order):04d}"
        snapshot = ContextSnapshot(
            name=snapshot_name,
            profile=copy.deepcopy(getattr(ctx, 'profile', None)),
            learning_plan=copy.deepcopy(getattr(ctx, 'learning_plan', None)),
            resources=copy.deepcopy(getattr(ctx, 'resources', None)),
            evaluation=copy.deepcopy(getattr(ctx, 'evaluation', None)),
            reflection=copy.deepcopy(getattr(ctx, 'reflection', None)),
            meta_reflection=copy.deepcopy(getattr(ctx, 'meta_reflection', None)),
            errors=list(getattr(ctx, 'errors', []) or []),
        )
        self._checkpoints[snapshot_name] = snapshot
        if snapshot_name in self._order:
            self._order.remove(snapshot_name)
        self._order.append(snapshot_name)

        # Evict oldest if over capacity
        while len(self._order) > self._max:
            old = self._order.pop(0)
            del self._checkpoints[old]

        return snapshot_name

    # ── Load / Rollback ──────────────────────

    def load(self, name: str) -> Optional[ContextSnapshot]:
        """
        Load a checkpoint by name without restoring context.

        Returns None if the checkpoint does not exist.
        """
        return self._checkpoints.get(name)

    def rollback(self, ctx: Any, name: str) -> bool:
        """
        Restore context to a previously saved checkpoint.

        Args:
            ctx: RuntimeContext to restore into.
            name: Checkpoint name to restore from.

        Returns:
            True if rollback succeeded, False if checkpoint not found.
        """
        snapshot = self._checkpoints.get(name)
        if snapshot is None:
            return False

        if hasattr(ctx, 'profile'):
            ctx.profile = copy.deepcopy(snapshot.profile)
        if hasattr(ctx, 'learning_plan'):
            ctx.learning_plan = copy.deepcopy(snapshot.learning_plan)
        if hasattr(ctx, 'resources'):
            ctx.resources = copy.deepcopy(snapshot.resources)
        if hasattr(ctx, 'evaluation'):
            ctx.evaluation = copy.deepcopy(snapshot.evaluation)
        if hasattr(ctx, 'reflection'):
            ctx.reflection = copy.deepcopy(snapshot.reflection)
        if hasattr(ctx, 'meta_reflection'):
            ctx.meta_reflection = copy.deepcopy(snapshot.meta_reflection)
        if hasattr(ctx, 'errors'):
            ctx.errors = list(snapshot.errors)

        return True

    # ── Query ────────────────────────────────

    def latest(self) -> Optional[ContextSnapshot]:
        """Return the most recent checkpoint, or None if empty."""
        if self._order:
            return self._checkpoints[self._order[-1]]
        return None

    def list_names(self) -> List[str]:
        """Return checkpoint names in save order."""
        return list(self._order)

    def count(self) -> int:
        return len(self._order)

    def clear(self) -> None:
        """Remove all checkpoints."""
        self._checkpoints.clear()
        self._order.clear()

    def __len__(self) -> int:
        return len(self._order)

    def __contains__(self, name: str) -> bool:
        return name in self._checkpoints
