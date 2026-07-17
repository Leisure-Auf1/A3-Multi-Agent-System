"""
Phase 6.0 — Contract Data Models

Public API contracts: TaskRequest, TaskResult, SessionInfo.
Framework-neutral — no A3-specific fields, no Runtime internals exposed.

Usage:
    from src.sdk.contracts import TaskRequest, TaskResult, SessionInfo

    task = TaskRequest(objective="generate plan", agent="planner")
    result: TaskResult = client.run(task)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


# ══════════════════════════════════════════════
# TaskRequest
# ══════════════════════════════════════════════


class TaskStatus(Enum):
    """Execution status of a task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class TaskRequest:
    """
    Unified task input for the Veritas Public API.

    Framework-neutral: no A3-specific fields like student_profile,
    course, or lesson. Only generic Agent Runtime concepts.

    Fields:
        objective: What the task should accomplish.
        agent: Which agent type to use (e.g. 'planner', 'evaluator').
        context: Optional task-specific data.
        task_id: Unique identifier (auto-generated if empty).
        timeout_seconds: Maximum execution time.
        metadata: Arbitrary metadata for tracing.
    """
    objective: str
    """What to accomplish."""

    agent: str = "default"
    """Agent type identifier."""

    context: Dict[str, Any] = field(default_factory=dict)
    """Task-specific context data."""

    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    """Unique task identifier."""

    timeout_seconds: float = 300.0
    """Maximum execution time."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Caller metadata for tracing."""

    def validate(self) -> List[str]:
        """Validate the request. Returns list of issues (empty = valid)."""
        issues = []
        if not self.objective.strip():
            issues.append("objective is required and must be non-empty")
        if not self.agent.strip():
            issues.append("agent is required and must be non-empty")
        if self.timeout_seconds <= 0:
            issues.append("timeout_seconds must be positive")
        return issues

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "agent": self.agent,
            "context": self.context,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }


# ══════════════════════════════════════════════
# TaskResult
# ══════════════════════════════════════════════


@dataclass
class TaskResult:
    """
    Unified task output from the Veritas Public API.

    Contains execution status, output data, timing, and trace references.
    Designed for programmatic consumption and serialization.
    """
    task_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    output: Optional[Dict[str, Any]] = None
    """Task output data (varies by agent type)."""

    execution_time_ms: float = 0.0
    """Total execution time in milliseconds."""

    session_id: str = ""
    """RuntimeSession identifier for trace correlation."""

    trace_id: str = ""
    """DecisionTrace identifier for explainability."""

    errors: List[str] = field(default_factory=list)
    """Non-fatal errors encountered during execution."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata (agent state, decision count, etc.)."""

    @property
    def is_success(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "is_success": self.is_success,
            "output": self.output,
            "execution_time_ms": self.execution_time_ms,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "errors": self.errors,
            "metadata": self.metadata,
        }


# ══════════════════════════════════════════════
# SessionInfo
# ══════════════════════════════════════════════


@dataclass
class SessionInfo:
    """
    Public view of a RuntimeSession.

    Exposes session metadata without internal Runtime details.
    """
    session_id: str = ""
    state: str = "unknown"
    """Current state of the session (e.g. 'completed', 'error')."""

    task_id: str = ""
    """Associated task identifier."""

    created_at: str = ""
    updated_at: str = ""

    total_duration_ms: float = 0.0
    state_count: int = 0
    error_count: int = 0
    decision_count: int = 0
    recovery_count: int = 0

    timeline: List[str] = field(default_factory=list)
    """Ordered list of states visited."""

    @property
    def is_completed(self) -> bool:
        return self.state == "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_duration_ms": self.total_duration_ms,
            "state_count": self.state_count,
            "error_count": self.error_count,
            "decision_count": self.decision_count,
            "recovery_count": self.recovery_count,
            "timeline": self.timeline,
        }
