"""
Phase 6.0 — Veritas Runtime SDK

Public API for the Veritas Agent Runtime. Provides a clean contract-based
interface that hides all internal Runtime details.

Modules:
    client      — RuntimeClient (public entry point)
    contracts   — TaskRequest, TaskResult, SessionInfo
    config      — RuntimeConfig, ConfigLoader
    adapters    — RuntimeAdapter (internal bridge)
    exceptions  — VeritasError hierarchy

Usage:
    from src.sdk import RuntimeClient, TaskRequest

    client = RuntimeClient()
    result = client.run(TaskRequest(objective="analyze", agent="evaluator"))
    print(result.status, result.execution_time_ms)
"""

from .client import RuntimeClient
from .contracts.task import TaskRequest, TaskResult, SessionInfo, TaskStatus
from .config.loader import RuntimeConfig, ConfigLoader, PluginEntry
from .exceptions import (
    VeritasError,
    ConfigError,
    RuntimeClientError,
    TaskExecutionError,
    ContractValidationError,
    SessionNotFoundError,
    PluginError,
)

__all__ = [
    # Client
    "RuntimeClient",
    # Contracts
    "TaskRequest",
    "TaskResult",
    "SessionInfo",
    "TaskStatus",
    # Config
    "RuntimeConfig",
    "ConfigLoader",
    "PluginEntry",
    # Exceptions
    "VeritasError",
    "ConfigError",
    "RuntimeClientError",
    "TaskExecutionError",
    "ContractValidationError",
    "SessionNotFoundError",
    "PluginError",
]
