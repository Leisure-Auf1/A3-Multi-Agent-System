"""
Phase 6.0 — Contract Layer

Public API contracts for the Veritas Runtime.
"""

from .task import TaskRequest, TaskResult, SessionInfo, TaskStatus

__all__ = [
    "TaskRequest",
    "TaskResult",
    "SessionInfo",
    "TaskStatus",
]
