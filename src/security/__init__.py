"""
Phase 5.3 — Runtime Security Foundation

Independent security layer for Agent Runtime.
No modifications to Agent business logic.
Connects to RuntimeEngine via RuntimeHook.

Modules:
  permission    — Agent × Capability access control matrix
  tool_gateway  — Tool call permission + validation + audit
  prompt_guard  — Prompt injection detection and sanitization
  audit         — Audit event logger

Usage:
    from src.security import PermissionMatrix, ToolGateway, PromptGuard, AuditLogger

    # Permission check
    matrix = PermissionMatrix()
    matrix.check("ProfileAgent", Capability.CALL_LLM)

    # Tool gateway
    gateway = ToolGateway(matrix)
    result = gateway.execute("ProfileAgent", Capability.CALL_LLM, {"prompt": "hello"})

    # Prompt guard
    guard = PromptGuard()
    risk = guard.scan("Ignore all previous instructions...")

    # Audit
    logger = AuditLogger()
    logger.record(agent="PlannerAgent", action="call_llm", result="allowed")
"""

from .permission import PermissionMatrix, Capability, DEFAULT_PERMISSIONS
from .tool_gateway import ToolGateway, GatewayResult
from .prompt_guard import PromptGuard, PromptRisk
from .audit import AuditLogger, AuditRecord

__all__ = [
    "PermissionMatrix",
    "Capability",
    "DEFAULT_PERMISSIONS",
    "ToolGateway",
    "GatewayResult",
    "PromptGuard",
    "PromptRisk",
    "AuditLogger",
    "AuditRecord",
]
