"""
Phase 9.1 — SQLite Database Layer

Single-file SQLite database for A3 application data.
Zero external dependencies — uses Python stdlib sqlite3.

Schema v1:
  - users:           student accounts + auth
  - learning_records: lesson history, quiz results
  - chat_threads:     conversation sessions
  - chat_messages:    per-thread messages
"""
from __future__ import annotations

import sqlite3
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "storage", "a3.db")

SCHEMA_VERSION = 1

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Thread-local connection with WAL mode."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def init_db():
    """Create tables if they don't exist. Idempotent."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS learning_records (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            course_id TEXT DEFAULT '',
            agent TEXT NOT NULL,
            action TEXT NOT NULL,
            result_json TEXT DEFAULT '{}',
            score REAL DEFAULT 0.0,
            duration_ms INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_threads (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL DEFAULT '',
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES chat_threads(id)
        );

        CREATE INDEX IF NOT EXISTS idx_learning_records_user
            ON learning_records(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_chat_messages_thread
            ON chat_messages(thread_id, created_at);
    """)
    # Ensure schema version
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)",
                     (SCHEMA_VERSION,))
    elif row["version"] != SCHEMA_VERSION:
        conn.execute("UPDATE schema_version SET version = ?",
                     (SCHEMA_VERSION,))
    conn.commit()


def close_db():
    """Close thread-local connection."""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None


# ── User CRUD ──────────────────────────────────────────────

@dataclass
class UserRecord:
    id: str
    email: str
    display_name: str = ""
    created_at: str = ""
    last_login_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def create_user(user_id: str, email: str, password_hash: str,
                display_name: str = "") -> UserRecord:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, display_name, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, email, password_hash, display_name, now))
    conn.commit()
    return UserRecord(id=user_id, email=email, display_name=display_name,
                      created_at=now)


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?",
                       (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?",
                       (email,)).fetchone()
    return dict(row) if row else None


def update_last_login(user_id: str):
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?",
                 (now, user_id))
    conn.commit()


# ── Learning Records CRUD ─────────────────────────────────

@dataclass
class LearningRecord:
    id: str
    user_id: str
    agent: str
    action: str
    course_id: str = ""
    result_json: str = "{}"
    score: float = 0.0
    duration_ms: int = 0
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "user_id": self.user_id, "agent": self.agent,
            "action": self.action, "course_id": self.course_id,
            "result": self.result_json, "score": self.score,
            "duration_ms": self.duration_ms, "created_at": self.created_at,
        }


def create_learning_record(record: LearningRecord) -> LearningRecord:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO learning_records "
        "(id, user_id, agent, action, course_id, result_json, score, "
        "duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (record.id, record.user_id, record.agent, record.action,
         record.course_id, record.result_json, record.score,
         record.duration_ms, now))
    conn.commit()
    record.created_at = now
    return record


def get_user_records(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM learning_records WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_user_stats(user_id: str) -> Dict[str, Any]:
    conn = _get_conn()
    total = conn.execute(
        "SELECT COUNT(*) as cnt FROM learning_records WHERE user_id = ?",
        (user_id,)).fetchone()
    avg_score = conn.execute(
        "SELECT AVG(score) as avg FROM learning_records "
        "WHERE user_id = ? AND score > 0", (user_id,)).fetchone()
    total_duration = conn.execute(
        "SELECT SUM(duration_ms) as total FROM learning_records "
        "WHERE user_id = ?", (user_id,)).fetchone()
    return {
        "total_sessions": total["cnt"],
        "avg_score": round(avg_score["avg"] or 0, 2),
        "total_duration_ms": total_duration["total"] or 0,
    }


# ── Chat Threads CRUD ─────────────────────────────────────

@dataclass
class ChatThread:
    id: str
    user_id: str
    title: str = "New Chat"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def create_thread(thread_id: str, user_id: str, title: str = "New Chat") -> ChatThread:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO chat_threads (id, user_id, title, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)", (thread_id, user_id, title, now, now))
    conn.commit()
    return ChatThread(id=thread_id, user_id=user_id, title=title,
                      created_at=now, updated_at=now)


def get_user_threads(user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM chat_threads WHERE user_id = ? "
        "ORDER BY updated_at DESC LIMIT ?", (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def update_thread_title(thread_id: str, title: str):
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE chat_threads SET title = ?, updated_at = ? WHERE id = ?",
        (title, now, thread_id))
    conn.commit()


# ── Chat Messages CRUD ────────────────────────────────────

@dataclass
class ChatMessage:
    id: str
    thread_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str = ""
    metadata_json: str = "{}"
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "thread_id": self.thread_id, "role": self.role,
            "content": self.content, "metadata": self.metadata_json,
            "created_at": self.created_at,
        }


def create_message(msg: ChatMessage) -> ChatMessage:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO chat_messages (id, thread_id, role, content, "
        "metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (msg.id, msg.thread_id, msg.role, msg.content,
         msg.metadata_json, now))
    # Update thread's updated_at
    conn.execute(
        "UPDATE chat_threads SET updated_at = ? WHERE id = ?",
        (now, msg.thread_id))
    conn.commit()
    msg.created_at = now
    return msg


def get_thread_messages(thread_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM chat_messages WHERE thread_id = ? "
        "ORDER BY created_at ASC LIMIT ?", (thread_id, limit)).fetchall()
    return [dict(r) for r in rows]


# ── Initialize on import ──────────────────────────────────
init_db()
