"""
Phase 9.1 — Session & Conversation Layer

SessionManager: manages learning sessions with message history for real
continuous user conversations. Built on top of WorkspaceManager.

Storage: JSONL files under workspace/history/sessions/

Architecture:
  SessionManager → WorkspaceManager → ~/.a3-agent/workspace/{id}/history/sessions/

Constraints: does NOT modify Veritas-Core, src/core/, or Agent interfaces.
"""

from __future__ import annotations
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.workspace.manager import WorkspaceManager


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

@dataclass
class Message:
    """A single message in a session conversation."""
    role: str                        # user | assistant | system
    content: str                     # Message text
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Session:
    """A learning session tied to a student."""
    session_id: str
    student_id: str
    title: str = "New Session"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    messages: List[Message] = field(default_factory=list)
    related_course: str = ""          # Course name this session belongs to
    artifacts: List[str] = field(default_factory=list)  # artifact IDs
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "related_course": self.related_course,
            "artifacts": self.artifacts,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        return cls(
            session_id=data.get("session_id", ""),
            student_id=data.get("student_id", ""),
            title=data.get("title", "New Session"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            related_course=data.get("related_course", ""),
            artifacts=data.get("artifacts", []),
            is_active=data.get("is_active", True),
            metadata=data.get("metadata", {}),
        )

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def last_message(self) -> Optional[Message]:
        return self.messages[-1] if self.messages else None


# ──────────────────────────────────────────────
# SessionManager
# ──────────────────────────────────────────────

class SessionManager:
    """
    Session & Conversation Layer for continuous user learning.

    Usage:
        sm = SessionManager()
        session = sm.create_session("student_001", "Python Basics")
        sm.append_message(session.session_id, "user", "What is a decorator?")
        sm.append_message(session.session_id, "assistant", "A decorator is...")
        context = sm.load_context(session.session_id, max_messages=10)

    Architecture:
        Storage: JSONL file per session under workspace/history/sessions/
        Index: sessions_index.jsonl for quick lookups
    """

    def __init__(self, workspace: Optional[WorkspaceManager] = None):
        self._workspace = workspace or WorkspaceManager()
        self._sessions: Dict[str, Session] = {}  # In-memory cache

    # ── Session Lifecycle ─────────────

    def create_session(
        self,
        student_id: str,
        title: str = "New Session",
        related_course: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new learning session.

        Args:
            student_id: Student identifier
            title: Session title
            related_course: Associated course name
            metadata: Extra metadata

        Returns:
            Session object
        """
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        session = Session(
            session_id=session_id,
            student_id=student_id,
            title=title,
            created_at=now,
            updated_at=now,
            related_course=related_course,
            metadata=metadata or {},
        )

        # Persist immediately
        self._persist_session(session)

        # Cache
        self._sessions[session_id] = session

        # Record in history
        self._workspace.append_history(student_id, {
            "action": "session_created",
            "session_id": session_id,
            "title": title,
        })

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID. Tries cache first, then loads from disk."""
        if session_id in self._sessions:
            return self._sessions[session_id]
        return self._load_session(session_id)

    def close_session(self, session_id: str) -> bool:
        """
        Close a session (mark as inactive and persist).

        Returns True if session was found and closed.
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        session.is_active = False
        session.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist_session(session)

        self._workspace.append_history(session.student_id, {
            "action": "session_closed",
            "session_id": session_id,
        })

        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its storage files."""
        session = self.get_session(session_id)
        if session is None:
            return False

        # Remove from cache
        self._sessions.pop(session_id, None)

        # Delete file
        file_path = self._session_file(session.student_id, session_id)
        if os.path.isfile(file_path):
            os.remove(file_path)
            return True
        return False

    # ── Message Operations ────────────

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Message]:
        """
        Append a message to a session conversation.

        Args:
            session_id: Session identifier
            role: user | assistant | system
            content: Message text
            metadata: Optional per-message metadata

        Returns:
            Message object or None if session not found
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        msg = Message(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        session.messages.append(msg)
        session.updated_at = datetime.now(timezone.utc).isoformat()

        # Append to JSONL file
        self._append_message_to_file(session, msg)

        # Update cache
        self._sessions[session_id] = session

        return msg

    # ── Context Loading ───────────────

    def load_context(
        self,
        session_id: str,
        max_messages: int = 20,
        max_tokens: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Load conversation context for a session.

        Args:
            session_id: Session identifier
            max_messages: Max number of recent messages to return
            max_tokens: Token budget (approximate, 0 = unlimited)

        Returns:
            List of message dicts in [{"role": ..., "content": ...}] format
            suitable for LLM context injection.
        """
        session = self.get_session(session_id)
        if session is None:
            return []

        messages = session.messages[-max_messages:] if max_messages > 0 else session.messages

        result = []
        approx_tokens = 0
        for msg in reversed(messages):
            entry = {"role": msg.role, "content": msg.content}
            approx_tokens += len(msg.content) // 4  # rough estimate

            if max_tokens > 0 and approx_tokens > max_tokens:
                break

            result.insert(0, entry)

        return result

    def load_full_context(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """Load ALL messages for a session."""
        return self.load_context(session_id, max_messages=0)

    # ── Resume ────────────────────────

    def resume_session(self, session_id: str) -> Optional[Session]:
        """
        Resume a previously created session.

        Returns the session with all messages loaded, ready for continuation.
        Returns None if session doesn't exist.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        # Ensure it's active
        if not session.is_active:
            session.is_active = True
            session.updated_at = datetime.now(timezone.utc).isoformat()
            self._persist_session(session)

        return session

    # ── Session Listing ───────────────

    def list_sessions(
        self,
        student_id: str,
        active_only: bool = False,
    ) -> List[Session]:
        """
        List all sessions for a student.

        Args:
            student_id: Student identifier
            active_only: If True, returns only active sessions

        Returns:
            List of Session objects
        """
        sessions_dir = self._sessions_dir(student_id)
        if not os.path.isdir(sessions_dir):
            return []

        sessions = []
        for fname in sorted(os.listdir(sessions_dir), reverse=True):
            if not fname.endswith(".jsonl"):
                continue
            session_id = fname.replace(".jsonl", "")
            session = self._load_session(session_id)
            if session is None:
                continue
            if active_only and not session.is_active:
                continue
            sessions.append(session)

        return sessions

    def get_sessions_summary(
        self,
        student_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get lightweight session summaries for UI display.

        Returns:
            [{"session_id", "title", "message_count", "is_active", "updated_at"}, ...]
        """
        sessions = self.list_sessions(student_id)
        return [
            {
                "session_id": s.session_id,
                "title": s.title,
                "message_count": s.message_count,
                "is_active": s.is_active,
                "updated_at": s.updated_at,
                "related_course": s.related_course,
            }
            for s in sessions
        ]

    def link_artifact(
        self,
        session_id: str,
        artifact_id: str,
    ) -> bool:
        """Link an artifact to a session."""
        session = self.get_session(session_id)
        if session is None:
            return False
        if artifact_id not in session.artifacts:
            session.artifacts.append(artifact_id)
            self._persist_session(session)
        return True

    # ── Persistence ───────────────────

    def _persist_session(self, session: Session) -> None:
        """Write full session to JSONL file."""
        file_path = self._session_file(session.student_id, session.session_id)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, ensure_ascii=False)

    def _append_message_to_file(self, session: Session, msg: Message) -> None:
        """Append a single message to the session's append-only messages file."""
        msg_path = self._messages_file(session.student_id, session.session_id)
        os.makedirs(os.path.dirname(msg_path), exist_ok=True)
        with open(msg_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + "\n")

    def _load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from disk by scanning all student directories."""
        root = self._workspace.get_root()
        if not os.path.isdir(root):
            return None

        # Scan all student dirs for this session
        for student_dir in os.listdir(root):
            sessions_dir = os.path.join(root, student_dir, "history", "sessions")
            file_path = os.path.join(sessions_dir, f"{session_id}.jsonl")
            if os.path.isfile(file_path):
                return self._load_from_file(file_path)

        return None

    def _load_from_file(self, file_path: str) -> Optional[Session]:
        """Load a session from a JSONL file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
            session = Session.from_dict(data)

            # Also load messages from append-only file
            messages_file = file_path.replace(".jsonl", "_messages.jsonl")
            if os.path.isfile(messages_file):
                with open(messages_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                msg_data = json.loads(line)
                                if not any(
                                    m.role == msg_data.get("role") and
                                    m.content == msg_data.get("content")
                                    for m in session.messages
                                ):
                                    session.messages.append(Message.from_dict(msg_data))
                            except json.JSONDecodeError:
                                pass

            # Cache
            self._sessions[session.session_id] = session
            return session
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def _session_file(self, student_id: str, session_id: str) -> str:
        return os.path.join(
            self._workspace.get_root(), student_id, "history", "sessions",
            f"{session_id}.jsonl",
        )

    def _messages_file(self, student_id: str, session_id: str) -> str:
        return os.path.join(
            self._workspace.get_root(), student_id, "history", "sessions",
            f"{session_id}_messages.jsonl",
        )

    def _sessions_dir(self, student_id: str) -> str:
        return os.path.join(
            self._workspace.get_root(), student_id, "history", "sessions",
        )
