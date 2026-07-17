"""
Phase 5.9 — Remote Execution Manager

Manages dispatching tasks to remote RuntimeNodes. Uses a simple
task-queue model: submit → assign → execute → collect.

Non-invasive — does not modify RuntimeEngine.run(). Works with
the existing PluginSystem and NodeRegistry for integration.

Usage:
    rem = RemoteExecutionManager(registry)
    task = rem.submit(
        capability="evaluation",
        payload={"goal": "learn Python"},
    )
    result = rem.wait_for(task.id)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import time
import uuid

from ..runtime import RuntimeContext


class TaskStatus(Enum):
    """Status of a remote execution task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class RemoteTask:
    """
    A task dispatched to a remote RuntimeNode.

    Tracks the task lifecycle: submit → assign → execute → collect.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    capability: str = ""
    """Required node capability (e.g. 'evaluation', 'profile_extraction')."""

    payload: Dict[str, Any] = field(default_factory=dict)
    """Task input data."""

    status: TaskStatus = TaskStatus.PENDING

    assigned_node: Optional[str] = None
    """Name of the assigned RuntimeNode."""

    result: Optional[Any] = None
    """Task result (set on completion)."""

    error: Optional[str] = None
    """Error message (set on failure)."""

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    timeout_seconds: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "capability": self.capability,
            "status": self.status.value,
            "assigned_node": self.assigned_node,
            "error": self.error,
            "created_at": self.created_at,
        }


class RemoteExecutionManager:
    """
    Manages dispatching tasks to remote RuntimeNodes.

    Uses a task queue model with capability-based routing.
    Integrates with NodeRegistry for node discovery.

    Usage:
        registry = NodeRegistry()
        registry.register_node(worker_node)

        rem = RemoteExecutionManager(registry)
        task = rem.submit("evaluation", {"goal": "learn"})
        result = rem.wait_for(task.id, timeout=5.0)
    """

    def __init__(self, registry: Any = None):
        self._registry = registry
        self._tasks: Dict[str, RemoteTask] = {}
        self._executors: Dict[str, Callable[[Any], Any]] = {}
        """capability → executor function (for local testing)."""

        self._history: List[RemoteTask] = []

    # ── Submit ───────────────────────────

    def submit(
        self,
        capability: str,
        payload: Dict[str, Any],
        timeout: float = 60.0,
    ) -> RemoteTask:
        """
        Submit a task for remote execution.

        The task is assigned to the best available node with the
        required capability.

        Args:
            capability: Required node capability.
            payload: Task input data.
            timeout: Maximum execution time in seconds.

        Returns:
            The created RemoteTask (status: PENDING or ASSIGNED).
        """
        task = RemoteTask(
            capability=capability,
            payload=payload,
            timeout_seconds=timeout,
        )

        # Try to assign to a remote node
        if self._registry:
            node = self._registry.find_best_for(capability)
            if node:
                task.assigned_node = node.name
                task.status = TaskStatus.ASSIGNED

        self._tasks[task.id] = task
        return task

    # ── Execute ───────────────────────────

    def execute(
        self,
        task_id: str,
        executor: Optional[Callable[[Any], Any]] = None,
    ) -> Optional[Any]:
        """
        Execute a pending task.

        If an executor is provided (for local testing), runs synchronously.
        Otherwise, delegates to the assigned node's executor.

        Returns the result if successful, None otherwise.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return task.result

        fn = executor or self._executors.get(task.capability)
        if fn is None:
            task.status = TaskStatus.FAILED
            task.error = f"No executor for capability '{task.capability}'"
            return None

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()

        try:
            task.result = fn(task.payload)
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self._history.append(task)
            return task.result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self._history.append(task)
            return None

    def register_executor(
        self,
        capability: str,
        executor: Callable[[Any], Any],
    ) -> None:
        """Register an executor function for a capability."""
        self._executors[capability] = executor

    # ── Wait ──────────────────────────────

    def wait_for(
        self,
        task_id: str,
        timeout: float = 30.0,
        poll_interval: float = 0.1,
    ) -> Optional[Any]:
        """
        Wait for a task to complete.

        Polls the task status until COMPLETED, FAILED, or timeout.

        Args:
            task_id: Task to wait for.
            timeout: Maximum wait time in seconds.
            poll_interval: Time between status checks.

        Returns:
            Task result if completed, None otherwise.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None

        t0 = time.time()
        while time.time() - t0 < timeout:
            if task.status == TaskStatus.COMPLETED:
                return task.result
            if task.status == TaskStatus.FAILED:
                return None
            if task.status == TaskStatus.CANCELLED:
                return None
            time.sleep(poll_interval)

        task.status = TaskStatus.TIMEOUT
        return None

    # ── Query ─────────────────────────────

    def get_task(self, task_id: str) -> Optional[RemoteTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[RemoteTask]:
        if status:
            return [t for t in self._tasks.values() if t.status == status]
        return list(self._tasks.values())

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status in (TaskStatus.PENDING, TaskStatus.ASSIGNED):
            task.status = TaskStatus.CANCELLED
            return True
        return False

    @property
    def history(self) -> List[RemoteTask]:
        return list(self._history)

    def summary(self) -> Dict[str, Any]:
        tasks = self.list_tasks()
        return {
            "total": len(tasks),
            "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
            "assigned": len([t for t in tasks if t.status == TaskStatus.ASSIGNED]),
            "running": len([t for t in tasks if t.status == TaskStatus.RUNNING]),
            "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
            "history": len(self._history),
        }
