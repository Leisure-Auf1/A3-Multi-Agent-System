"""
A3 Test Suite — conftest fixtures.

Provides automatic test environment management.
"""

from __future__ import annotations
import pytest
from pathlib import Path


# ── Auto-cleanup: persistent student IDs used across learning_loop tests ──

_LEARNING_LOOP_IDS = [
    "persist_test",
    "full_loop_test",
    "ema_test_1",
    "ema_test_2",
    "time_test_2",
    "weak_area_test",
    "quiz_flow_test",
    "profile_grow",
    "phase_8d_fresh_test",
    "phase_8d_evolved_test",
]


@pytest.fixture(autouse=True)
def _clean_learning_loop_memory():
    """Auto-clean memory files for learning_loop tests to prevent
    stale session accumulation from capping at 10 (Veritas-Core limit)."""
    try:
        from veritas.memory import MemoryManager
        mm = MemoryManager()
        for sid in _LEARNING_LOOP_IDS:
            if mm.student_exists(sid):
                try:
                    mm.students.delete(sid)
                except Exception:
                    pass
    except Exception:
        pass
    yield
