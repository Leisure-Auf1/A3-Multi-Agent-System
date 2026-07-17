"""
Phase 9.1 — Student Profile Store

Persists student learning profiles. Wraps Veritas-Core StudentMemory
types for database serialization.
"""
from __future__ import annotations

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ..data.db import _get_conn


def save_profile(user_id: str, profile_data: Dict[str, Any]) -> bool:
    """Save or update a student profile as JSON blob."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute(
        "SELECT id FROM student_profiles WHERE user_id = ?",
        (user_id,)).fetchone()

    if existing:
        conn.execute(
            "UPDATE student_profiles SET profile_json = ?, updated_at = ? "
            "WHERE user_id = ?",
            (json.dumps(profile_data, ensure_ascii=False), now, user_id))
    else:
        import uuid
        conn.execute(
            "INSERT INTO student_profiles (id, user_id, profile_json, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, user_id,
             json.dumps(profile_data, ensure_ascii=False), now, now))
    conn.commit()
    return True


def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Load a student profile."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT profile_json FROM student_profiles WHERE user_id = ?",
        (user_id,)).fetchone()
    if row is None:
        return None
    return json.loads(row["profile_json"])


def delete_profile(user_id: str) -> bool:
    """Delete a student profile."""
    conn = _get_conn()
    conn.execute("DELETE FROM student_profiles WHERE user_id = ?", (user_id,))
    conn.commit()
    return True


def ensure_profiles_table():
    """Create the student_profiles table if it doesn't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            id TEXT PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            profile_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
