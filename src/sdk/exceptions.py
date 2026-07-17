"""
Phase 6.0 — SDK Exception Hierarchy

Structured exceptions for the Veritas Public API.
All errors inherit from VeritasError for consistent handling.

Usage:
    from src.sdk.exceptions import VeritasError, ConfigError, TaskExecutionError

    try:
        client.run(task)
    except TaskExecutionError as e:
        print(e.task_id, e.detail)
"""

from __future__ import annotations
from typing import Any, Dict, Optional


class VeritasError(Exception):
    """
    Base exception for all Veritas SDK errors.

    All public API errors inherit from this class so callers
    can catch VeritasError to handle any SDK-level failure.
    """
    def __init__(self, message: str = "", detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail or message


class ConfigError(VeritasError):
    """Configuration loading or validation failure."""
    def __init__(self, message: str = "", path: str = ""):
        super().__init__(message, detail=f"Config error at '{path}': {message}")
        self.path = path


class RuntimeClientError(VeritasError):
    """General RuntimeClient operation failure."""
    pass


class TaskExecutionError(VeritasError):
    """Task execution failed during processing."""
    def __init__(
        self,
        message: str = "",
        task_id: str = "",
        agent: str = "",
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, detail=f"Task '{task_id}' ({agent}) failed: {message}")
        self.task_id = task_id
        self.agent = agent
        self.cause = cause


class ContractValidationError(VeritasError):
    """Contract validation failure (invalid TaskRequest, malformed input)."""
    def __init__(self, message: str = "", field: str = "", value: Any = None):
        detail = f"Validation error on '{field}': {message}" if field else message
        super().__init__(message, detail=detail)
        self.field = field
        self.value = value


class SessionNotFoundError(VeritasError):
    """Requested session does not exist."""
    def __init__(self, session_id: str = ""):
        super().__init__(
            f"Session '{session_id}' not found",
            detail=f"No session with id '{session_id}'",
        )
        self.session_id = session_id


class PluginError(VeritasError):
    """Plugin registration or lifecycle failure."""
    def __init__(self, message: str = "", plugin_name: str = ""):
        super().__init__(message, detail=f"Plugin '{plugin_name}': {message}")
        self.plugin_name = plugin_name
