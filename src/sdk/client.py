"""
Phase 6.0 — RuntimeClient

Public entry point for the Veritas Runtime SDK. Hides all internal
Runtime details behind a clean, contract-based API.

Usage:
    from src.sdk import RuntimeClient, TaskRequest

    client = RuntimeClient()
    result = client.run(TaskRequest(objective="generate plan", agent="planner"))
    print(result.status, result.execution_time_ms)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from .contracts.task import TaskRequest, TaskResult, SessionInfo, TaskStatus
from .config.loader import RuntimeConfig, ConfigLoader
from .adapters.runtime_adapter import RuntimeAdapter
from .exceptions import (
    VeritasError,
    ConfigError,
    ContractValidationError,
    TaskExecutionError,
    SessionNotFoundError,
    PluginError,
)


class RuntimeClient:
    """
    Public API client for the Veritas Runtime.

    Hides RuntimeEngine, PolicyEngine, Hooks, and EventBus.
    Exposes only contracts: TaskRequest → TaskResult.

    Usage:
        client = RuntimeClient()

        # Execute a task
        result = client.run(TaskRequest(objective="analyze", agent="evaluator"))

        # Query sessions
        sessions = client.sessions()
        session = client.get_session(result.session_id)

        # Explainability
        explanation = client.explain(result.session_id)

        # Runtime status
        print(client.status())
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        config_path: Optional[str] = None,
    ):
        """
        Initialize the RuntimeClient.

        Args:
            config: Programmatic RuntimeConfig (highest priority).
            config_path: Path to YAML config file.
        """
        loader = ConfigLoader()

        if config is not None:
            self._config = config
        elif config_path is not None:
            self._config = loader.load(config_path)
        else:
            self._config = loader.load()

        self._adapter = RuntimeAdapter(self._config)

    # ── Core API ───────────────────────────

    def run(self, task: TaskRequest) -> TaskResult:
        """
        Execute a task through the Veritas Runtime.

        Args:
            task: Validated TaskRequest.

        Returns:
            TaskResult with execution status and output.

        Raises:
            ContractValidationError: If the task is invalid.
            TaskExecutionError: If execution fails.
        """
        issues = task.validate()
        if issues:
            raise ContractValidationError(
                "; ".join(issues),
                field="task",
            )

        return self._adapter.execute(task)

    # ── Sessions ────────────────────────────

    def sessions(self) -> List[SessionInfo]:
        """List all executed sessions."""
        return self._adapter.list_sessions()

    def get_session(self, session_id: str) -> SessionInfo:
        """
        Get details for a single session.

        Raises:
            SessionNotFoundError: If the session doesn't exist.
        """
        info = self._adapter.get_session(session_id)
        if info is None:
            raise SessionNotFoundError(session_id)
        return info

    # ── Explainability ──────────────────────

    def explain(self, session_id: str) -> Dict[str, Any]:
        """
        Get decision explainability data for a session.

        Returns the recorder's to_dict() output including all
        DecisionTraces, chains, and explainability scores.

        Raises:
            SessionNotFoundError: If the session doesn't exist.
        """
        data = self._adapter.explain(session_id)
        if data is None:
            raise SessionNotFoundError(session_id)
        return data

    # ── Status ──────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Get runtime status summary."""
        return self._adapter.status()

    # ── Config ──────────────────────────────

    @property
    def config(self) -> RuntimeConfig:
        return self._config
