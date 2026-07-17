"""
Phase 9.1 — Learning Records

High-level API over the db.py learning_records table.
Provides session tracking, statistics, and progress queries.
"""
from __future__ import annotations

import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .db import (
    LearningRecord, create_learning_record,
    get_user_records, get_user_stats,
)


def record_agent_action(
    user_id: str,
    agent: str,
    action: str,
    course_id: str = "",
    result: Any = None,
    score: float = 0.0,
    duration_ms: int = 0,
) -> dict:
    """Record a learning event."""
    record = LearningRecord(
        id=uuid.uuid4().hex[:16],
        user_id=user_id,
        agent=agent,
        action=action,
        course_id=course_id,
        result_json=json.dumps(result, ensure_ascii=False) if result else "{}",
        score=score,
        duration_ms=duration_ms,
    )
    saved = create_learning_record(record)
    return saved.to_dict()


def get_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get user's learning history."""
    return get_user_records(user_id, limit)


def get_stats(user_id: str) -> Dict[str, Any]:
    """Get aggregated learning statistics."""
    return get_user_stats(user_id)
