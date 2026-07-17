"""
Phase 6.0 — Runtime Adapter

Internal bridge between the Public Contract Layer and the RuntimeEngine.
Translates TaskRequest → RuntimeContext → RuntimeEngine.run() → TaskResult.

This is the ONLY module that touches RuntimeEngine internals.
All other SDK modules work through contracts only.

Design:
    RuntimeClient
         │
         ▼
    RuntimeAdapter (translates contracts ↔ runtime)
         │
         ▼
    RuntimeEngine (internal, hidden from public API)
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional

from ..contracts.task import TaskRequest, TaskResult, TaskStatus, SessionInfo
from ..config.loader import RuntimeConfig
from ..exceptions import TaskExecutionError, SessionNotFoundError
from ...runtime import (
    RuntimeEngine,
    RuntimeContext,
    TransitionTable,
    AgentState,
    RuntimePolicyEngine,
)
from ...runtime.recovery import RecoveryManager, RecoveryConfig
from ...runtime.lifecycle import LifecycleManager
from ...runtime.explain import ExplanationRecorder


class RuntimeAdapter:
    """
    Translates between Public Contracts and internal RuntimeEngine.

    Hides all Runtime internals (RuntimeEngine, PolicyEngine, Hook, EventBus)
    behind a clean contract-based interface.

    Usage (internal only — called by RuntimeClient):
        adapter = RuntimeAdapter(config)
        result = adapter.execute(task)
        sessions = adapter.list_sessions()
    """

    def __init__(self, config: RuntimeConfig):
        self._config = config
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # session_id → {"result": TaskResult, "recorder": ExplanationRecorder, "ctx": RuntimeContext}

    # ── Execute ────────────────────────────

    def execute(self, task: TaskRequest) -> TaskResult:
        """
        Execute a task through the RuntimeEngine.

        Translates TaskRequest → RuntimeContext → engine.run() → TaskResult.
        All internal details (PolicyEngine, Recovery, Hooks) are hidden.

        Args:
            task: The validated TaskRequest.

        Returns:
            TaskResult with execution outcome.

        Raises:
            TaskExecutionError: If the task cannot be executed.
        """
        t0 = time.time()

        # ── Build RuntimeContext from TaskRequest ──
        ctx = RuntimeContext(
            session_id=task.task_id,
            user_goal=task.objective,
            user_profile=task.context.get("profile"),
            errors=[],
        )

        # ── Build RuntimeEngine ──
        recovery = None
        if self._config.recovery_enabled:
            recovery = RecoveryManager(
                RecoveryConfig(
                    max_retries=self._config.max_retries,
                    retry_delay_seconds=self._config.retry_delay_ms / 1000.0,
                ),
            )

        policy = RuntimePolicyEngine()

        engine = RuntimeEngine(
            session_id=task.task_id,
            policy_engine=policy,
            recovery_manager=recovery,
        )

        # ── Attach observability hooks ──
        lm = LifecycleManager() if self._config.lifecycle_enabled else None
        recorder = ExplanationRecorder() if self._config.explainability_enabled else None

        if lm:
            engine.add_hook(lm)
        if recorder:
            engine.add_hook(recorder)

        # ── Setup state handlers ──
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine._table = table

        def task_handler(ctx_inner):
            ctx_inner.profile = {"objective": task.objective, "agent": task.agent}

        engine.register_handler(AgentState.PROFILE, task_handler)

        # ── Execute ──
        try:
            engine.run()
            execution_time = (time.time() - t0) * 1000
        except Exception as e:
            raise TaskExecutionError(
                str(e), task_id=task.task_id, agent=task.agent, cause=e,
            )

        # ── Build TaskResult ──
        error_count = engine._checkpoint.error_count()
        success = error_count == 0

        result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.COMPLETED if success else TaskStatus.FAILED,
            output=ctx.profile,
            execution_time_ms=execution_time,
            session_id=task.task_id,
            trace_id=task.task_id,
            errors=list(ctx.errors),
            metadata={
                "state_count": engine._checkpoint.state_count(),
                "agent": task.agent,
            },
        )

        # ── Store session for later query ──
        self._sessions[task.task_id] = {
            "result": result,
            "recorder": recorder,
            "lm": lm,
            "ctx": ctx,
        }

        return result

    # ── Sessions ────────────────────────────

    def list_sessions(self) -> List[SessionInfo]:
        """List all executed sessions."""
        return [
            SessionInfo(
                session_id=sid,
                state=data["result"].status.value,
                task_id=sid,
                total_duration_ms=data["result"].execution_time_ms,
                error_count=len(data["result"].errors),
            )
            for sid, data in self._sessions.items()
        ]

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get details for a single session."""
        data = self._sessions.get(session_id)
        if data is None:
            return None

        result = data["result"]
        lm = data.get("lm")
        recorder = data.get("recorder")

        return SessionInfo(
            session_id=session_id,
            state=result.status.value,
            task_id=session_id,
            total_duration_ms=result.execution_time_ms,
            state_count=result.metadata.get("state_count", 0),
            error_count=len(result.errors),
            decision_count=len(recorder.traces) if recorder else 0,
            recovery_count=len(lm._agents) if lm else 0,
            timeline=[],
        )

    # ── Explainability ──────────────────────

    def explain(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get explainability data for a session."""
        data = self._sessions.get(session_id)
        if data is None:
            return None

        recorder = data.get("recorder")
        if recorder is None:
            return None

        return recorder.to_dict()

    # ── Status ──────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Get runtime status summary."""
        return {
            "version": self._config.runtime_version,
            "recovery_enabled": self._config.recovery_enabled,
            "sessions_count": len(self._sessions),
            "plugins_count": len(self._config.plugins),
            "distributed_enabled": self._config.distributed_enabled,
        }
