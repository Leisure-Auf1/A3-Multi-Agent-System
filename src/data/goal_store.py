"""
Phase 8.3-D2 — Goal Store

SQLite persistence for StudentGoal records.
Stores goals, milestones, and progress in the A3 database.

Table: student_goals
  - Stores one goal per student (single active goal model)
  - Full goal JSON as blob for flexibility
  - Separated milestone progress tracking via computed columns

NOT part of Veritas-Core — A3 project-level data layer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..data.db import _get_conn
from ..agents.student_goal import StudentGoal, Milestone


# ──────────────────────────────────────────────
# Schema Migration
# ──────────────────────────────────────────────

def ensure_goals_table() -> None:
    """Create student_goals table and related indices. Idempotent."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS student_goals (
            goal_id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'general',
            target TEXT NOT NULL DEFAULT '',
            target_level TEXT NOT NULL DEFAULT 'beginner',
            milestones_json TEXT NOT NULL DEFAULT '[]',
            deadline TEXT DEFAULT '',
            progress REAL NOT NULL DEFAULT 0.0,
            completed_milestones INTEGER NOT NULL DEFAULT 0,
            total_milestones INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_student_goals_student
            ON student_goals(student_id);

        CREATE INDEX IF NOT EXISTS idx_student_goals_category
            ON student_goals(category, is_active);
    """)
    conn.commit()


# ──────────────────────────────────────────────
# CRUD Operations
# ──────────────────────────────────────────────

def save_goal(goal: StudentGoal) -> bool:
    """
    Save or update a student goal. Uses student_id as UNIQUE key —
    each student has one active goal at a time.

    Returns:
        True on success.
    """
    ensure_goals_table()
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()

    goal.updated_at = now
    goal.recompute_progress()

    milestones_json = json.dumps(
        [m.to_dict() for m in goal.milestones],
        ensure_ascii=False,
    )
    metadata_json = json.dumps(goal.metadata, ensure_ascii=False)

    existing = conn.execute(
        "SELECT goal_id FROM student_goals WHERE student_id = ?",
        (goal.student_id,)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE student_goals
            SET goal_id = ?, category = ?, target = ?, target_level = ?,
                milestones_json = ?, deadline = ?, progress = ?,
                completed_milestones = ?, total_milestones = ?,
                metadata_json = ?, is_active = 1, updated_at = ?
            WHERE student_id = ?
        """, (
            goal.goal_id,
            goal.category, goal.target, goal.target_level,
            milestones_json, goal.deadline, goal.progress,
            goal.completed_milestones, goal.total_milestones,
            metadata_json, now,
            goal.student_id,
        ))
    else:
        conn.execute("""
            INSERT INTO student_goals (
                goal_id, student_id, category, target, target_level,
                milestones_json, deadline, progress,
                completed_milestones, total_milestones,
                metadata_json, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            goal.goal_id, goal.student_id, goal.category,
            goal.target, goal.target_level,
            milestones_json, goal.deadline, goal.progress,
            goal.completed_milestones, goal.total_milestones,
            metadata_json, now, now,
        ))

    conn.commit()
    return True


def get_goal(student_id: str) -> Optional[StudentGoal]:
    """
    Load the active goal for a student.

    Args:
        student_id: Student ID

    Returns:
        StudentGoal or None if no active goal exists.
    """
    ensure_goals_table()
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM student_goals WHERE student_id = ? AND is_active = 1",
        (student_id,)
    ).fetchone()

    if row is None:
        return None

    row_dict = dict(row)
    milestones_data = json.loads(row_dict.get("milestones_json", "[]"))
    milestones = [Milestone.from_dict(m) for m in milestones_data]
    metadata = json.loads(row_dict.get("metadata_json", "{}"))

    return StudentGoal(
        goal_id=row_dict["goal_id"],
        student_id=row_dict["student_id"],
        category=row_dict.get("category", "general"),
        target=row_dict.get("target", ""),
        target_level=row_dict.get("target_level", "beginner"),
        milestones=milestones,
        deadline=row_dict.get("deadline", ""),
        progress=row_dict.get("progress", 0.0),
        metadata=metadata,
        created_at=row_dict.get("created_at", ""),
        updated_at=row_dict.get("updated_at", ""),
    )


def get_goal_by_id(goal_id: str) -> Optional[StudentGoal]:
    """Load a goal by its goal_id."""
    ensure_goals_table()
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM student_goals WHERE goal_id = ?",
        (goal_id,)
    ).fetchone()

    if row is None:
        return None

    row_dict = dict(row)
    milestones_data = json.loads(row_dict.get("milestones_json", "[]"))
    milestones = [Milestone.from_dict(m) for m in milestones_data]
    metadata = json.loads(row_dict.get("metadata_json", "{}"))

    return StudentGoal(
        goal_id=row_dict["goal_id"],
        student_id=row_dict["student_id"],
        category=row_dict.get("category", "general"),
        target=row_dict.get("target", ""),
        target_level=row_dict.get("target_level", "beginner"),
        milestones=milestones,
        deadline=row_dict.get("deadline", ""),
        progress=row_dict.get("progress", 0.0),
        metadata=metadata,
        created_at=row_dict.get("created_at", ""),
        updated_at=row_dict.get("updated_at", ""),
    )


def delete_goal(student_id: str) -> bool:
    """Soft-delete (deactivate) a student's goal."""
    ensure_goals_table()
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE student_goals SET is_active = 0, updated_at = ? "
        "WHERE student_id = ? AND is_active = 1",
        (now, student_id)
    )
    conn.commit()
    return True


def list_active_goals(category: str = "") -> List[Dict[str, Any]]:
    """List all active goals, optionally filtered by category."""
    ensure_goals_table()
    conn = _get_conn()
    if category:
        rows = conn.execute(
            "SELECT goal_id, student_id, category, target, target_level, "
            "progress, completed_milestones, total_milestones, deadline, "
            "created_at, updated_at "
            "FROM student_goals WHERE is_active = 1 AND category = ? "
            "ORDER BY created_at DESC",
            (category,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT goal_id, student_id, category, target, target_level, "
            "progress, completed_milestones, total_milestones, deadline, "
            "created_at, updated_at "
            "FROM student_goals WHERE is_active = 1 "
            "ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_milestone(
    student_id: str,
    milestone_id: str,
    completed: bool,
) -> Optional[StudentGoal]:
    """
    Mark a specific milestone as completed or not.

    Args:
        student_id: Student ID
        milestone_id: Milestone ID within the goal
        completed: New completion status

    Returns:
        Updated StudentGoal or None if not found.
    """
    goal = get_goal(student_id)
    if goal is None:
        return None

    for m in goal.milestones:
        if m.milestone_id == milestone_id:
            m.completed = completed
            m.completed_at = (
                datetime.now(timezone.utc).isoformat() if completed else ""
            )
            break
    else:
        return goal  # milestone not found, return unchanged

    goal.recompute_progress()
    save_goal(goal)
    return goal


def check_and_update_goal_progress(
    student_id: str,
    mastery_map: Dict[str, float],
) -> Optional[StudentGoal]:
    """
    Check all milestones against current mastery_map and update.
    Automatically marks milestones as completed when all target
    concepts reach the threshold.

    Args:
        student_id: Student ID
        mastery_map: Current mastery_map {concept: score}

    Returns:
        Updated StudentGoal or None.
    """
    goal = get_goal(student_id)
    if goal is None:
        return None

    result = goal.check_milestones_against_mastery(mastery_map)

    if result["newly_completed"]:
        save_goal(goal)

    return goal


def get_goal_summary(student_id: str) -> Dict[str, Any]:
    """
    Get a summary of the student's goal progress for dashboard display.

    Returns:
        {
            "has_goal": bool,
            "goal": {...} or None,
            "next_milestone": {...} or None,
            "pending_concepts": [...],
            "progress": float,
            "days_remaining": int or None,
            "is_overdue": bool,
        }
    """
    goal = get_goal(student_id)
    if goal is None:
        return {"has_goal": False, "goal": None}

    next_ms = goal.get_next_milestone()

    return {
        "has_goal": True,
        "goal": goal.to_dict(),
        "next_milestone": next_ms.to_dict() if next_ms else None,
        "pending_concepts": goal.get_pending_concepts(),
        "progress": goal.progress,
        "days_remaining": goal.days_remaining,
        "is_overdue": goal.is_overdue,
    }


# ──────────────────────────────────────────────
# Preset Helpers
# ──────────────────────────────────────────────

def create_goal_from_preset(
    student_id: str,
    category: str,
    preset_id: str,
    deadline: str = "",
) -> Optional[StudentGoal]:
    """
    Create and persist a goal from a preset.

    Args:
        student_id: Student ID
        category: "career" or "exam"
        preset_id: Key in CAREER_PATHS or EXAM_PATHS
        deadline: Optional deadline ISO date

    Returns:
        Persisted StudentGoal or None.
    """
    goal = StudentGoal.from_preset(
        student_id=student_id,
        category=category,
        preset_id=preset_id,
        deadline=deadline,
    )
    if goal is None:
        return None

    save_goal(goal)
    return goal
