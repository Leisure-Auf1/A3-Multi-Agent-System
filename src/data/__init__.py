"""Phase 9.1 — Data Layer Package"""
from .db import init_db, close_db

# Ensure student_profiles table exists
from .student_store import ensure_profiles_table
ensure_profiles_table()

# Phase 8.3-D2 — Ensure student_goals table exists
from .goal_store import ensure_goals_table
ensure_goals_table()
