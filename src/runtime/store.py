"""
Phase 5.1 — Runtime Store

Short-term system execution memory.
Optimized for speed — in-memory with optional JSON persistence.

Responsibilities:
  - Session state management (create, update, query)
  - Checkpoint snapshot storage (save/load execution state)
  - Runtime cache (key-value with TTL)
  - Execution trace index (query by state, status, session)

Separate from Agent Memory (long-term learning knowledge).
"""

from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .state import AgentState
from .transition import StateTransition


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

@dataclass
class SessionRecord:
    """One runtime session."""
    session_id: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    current_state: Optional[str] = None
    total_transitions: int = 0
    error_count: int = 0
    evaluation_score: Optional[int] = None
    is_complete: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "current_state": self.current_state,
            "total_transitions": self.total_transitions,
            "error_count": self.error_count,
            "evaluation_score": self.evaluation_score,
            "is_complete": self.is_complete,
            "meta": self.meta,
        }


@dataclass
class CacheEntry:
    """A cached value with optional TTL."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None  # None = no expiration

    @property
    def expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds


# ──────────────────────────────────────────────
# RuntimeStore
# ──────────────────────────────────────────────

class RuntimeStore:
    """
    Short-term system execution memory.

    Usage:
        store = RuntimeStore()
        sid = store.create_session(user_goal="learn Python")
        store.update_state(sid, AgentState.EVALUATE, transitions=5)
        store.save_checkpoint(sid, transitions=[...])
        store.cache_set("last_user", "student_1", ttl_seconds=300)
        val = store.cache_get("last_user")

    Storage: in-memory (default) or JSON file for checkpoint persistence.
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        max_sessions: int = 100,
    ):
        # Sessions
        self._sessions: Dict[str, SessionRecord] = {}
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._traces: Dict[str, List[Dict[str, Any]]] = {}

        # Cache
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        # Persistence (optional)
        self._storage_dir = (
            Path(storage_dir) if storage_dir else None
        )
        if self._storage_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_persisted()

        self._max_sessions = max_sessions

    # ── Session Management ────────────────────

    def create_session(
        self,
        user_goal: str = "",
        session_id: str = "",
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new runtime session. Returns session_id."""
        sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"

        # Evict oldest if at capacity
        if len(self._sessions) >= self._max_sessions:
            oldest = min(
                self._sessions.keys(),
                key=lambda k: self._sessions[k].created_at,
            )
            del self._sessions[oldest]

        self._sessions[sid] = SessionRecord(
            session_id=sid,
            meta=meta or {},
        )
        self._traces[sid] = []
        return sid

    def update_state(
        self,
        session_id: str,
        state: Optional[AgentState] = None,
        transitions: int = 0,
        errors: int = 0,
        completed: bool = False,
        score: Optional[int] = None,
    ) -> None:
        """Update session state in-place."""
        session = self._sessions.get(session_id)
        if session is None:
            return
        if state is not None:
            session.current_state = state.name
        if transitions:
            session.total_transitions += transitions
        if errors:
            session.error_count += errors
        if completed:
            session.is_complete = True
        if score is not None:
            session.evaluation_score = score

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[str]:
        return list(self._sessions.keys())

    # ── Checkpoint Storage ────────────────────

    def save_checkpoint(
        self,
        session_id: str,
        state: Optional[AgentState] = None,
        transitions: Optional[List[StateTransition]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save a session checkpoint for potential recovery."""
        checkpoint = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": state.name if state else None,
            "transitions": [
                t.to_dict() for t in transitions
            ] if transitions else [],
            "context": context or {},
        }
        self._checkpoints[session_id] = checkpoint
        self._persist_checkpoint(session_id, checkpoint)

    def load_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a previously saved checkpoint."""
        cp = self._checkpoints.get(session_id)
        if cp is None and self._storage_dir:
            cp = self._load_checkpoint_file(session_id)
            if cp:
                self._checkpoints[session_id] = cp
        return cp

    # ── Runtime Cache ─────────────────────────

    def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """Store a value in the runtime cache with optional TTL."""
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
        )

    def cache_get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Returns None if missing or expired."""
        entry = self._cache.get(key)
        if entry is None:
            self._cache_misses += 1
            return None
        if entry.expired:
            del self._cache[key]
            self._cache_misses += 1
            return None
        self._cache_hits += 1
        return entry.value

    def cache_delete(self, key: str) -> bool:
        """Delete a key from cache. Returns True if existed."""
        return self._cache.pop(key, None) is not None

    def cache_stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": (
                self._cache_hits / max(self._cache_hits + self._cache_misses, 1)
            ),
        }

    # ── Execution Trace Index ─────────────────

    def trace_record(
        self,
        session_id: str,
        transition: StateTransition,
    ) -> None:
        """Append a transition to a session's trace."""
        if session_id not in self._traces:
            self._traces[session_id] = []
        self._traces[session_id].append(transition.to_dict())

    def trace_query(
        self,
        session_id: str = "",
        state: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query execution traces with optional filters."""
        if session_id and session_id in self._traces:
            traces = self._traces[session_id]
        else:
            traces = []
            for t_list in self._traces.values():
                traces.extend(t_list)

        result = []
        for t in traces:
            if state and t.get("to") != state:
                continue
            if status and t.get("status") != status:
                continue
            result.append(t)
            if len(result) >= limit:
                break
        return result

    # ── Runtime Snapshot ──────────────────────

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Return an aggregate snapshot of all runtime state."""
        sessions = []
        for sid, s in self._sessions.items():
            sessions.append({
                "session_id": sid,
                "state": s.current_state,
                "transitions": s.total_transitions,
                "errors": s.error_count,
                "score": s.evaluation_score,
                "complete": s.is_complete,
            })

        return {
            "sessions": sessions,
            "active_count": sum(1 for s in self._sessions.values() if not s.is_complete),
            "completed_count": sum(1 for s in self._sessions.values() if s.is_complete),
            "checkpoints": len(self._checkpoints),
            "cache": self.cache_stats(),
            "total_traces": sum(len(t) for t in self._traces.values()),
        }

    # ── Persistence ───────────────────────────

    def _persist_checkpoint(self, session_id: str, checkpoint: Dict[str, Any]) -> None:
        if self._storage_dir is None:
            return
        path = self._storage_dir / f"checkpoint_{session_id}.json"
        try:
            path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))
        except Exception:
            pass

    def _load_checkpoint_file(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self._storage_dir is None:
            return None
        path = self._storage_dir / f"checkpoint_{session_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except Exception:
            return None

    def _load_persisted(self) -> None:
        """Load all persisted checkpoints on init."""
        if self._storage_dir is None:
            return
        for f in self._storage_dir.glob("checkpoint_*.json"):
            try:
                cp = json.loads(f.read_text())
                sid = cp.get("session_id", "")
                if sid:
                    self._checkpoints[sid] = cp
            except Exception:
                pass

    # ── Reset ─────────────────────────────────

    def reset(self) -> None:
        """Clear all in-memory state (checkpoints on disk remain)."""
        self._sessions.clear()
        self._checkpoints.clear()
        self._traces.clear()
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
