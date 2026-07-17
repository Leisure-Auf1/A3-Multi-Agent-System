"""
Phase 5.3 — Agent Permission Matrix

Controls which Agent can perform which capability.
Read-only security layer — no modification of Agent internals.

Usage:
    matrix = PermissionMatrix()
    matrix.grant("ProfileAgent", "read_memory")
    matrix.grant("ProfileAgent", "call_llm")
    allowed = matrix.check("ProfileAgent", "read_memory")  # True
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set
from enum import Enum


# ──────────────────────────────────────────────
# Capabilities
# ──────────────────────────────────────────────

class Capability(Enum):
    """Actions an Agent can perform."""

    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    CALL_LLM = "call_llm"
    CALL_TOOL = "call_tool"
    EXECUTE_CODE = "execute_code"
    ACCESS_FILESYSTEM = "access_filesystem"
    SEND_EVENT = "send_event"
    MODIFY_PROFILE = "modify_profile"
    GENERATE_CONTENT = "generate_content"
    EVALUATE = "evaluate"


# ──────────────────────────────────────────────
# Default Agent Permissions
# ──────────────────────────────────────────────

DEFAULT_PERMISSIONS: Dict[str, List[Capability]] = {
    "ProfileAgent": [
        Capability.READ_MEMORY, Capability.WRITE_MEMORY,
        Capability.CALL_LLM, Capability.MODIFY_PROFILE,
        Capability.SEND_EVENT,
    ],
    "PlannerAgent": [
        Capability.READ_MEMORY, Capability.CALL_LLM,
        Capability.GENERATE_CONTENT, Capability.SEND_EVENT,
    ],
    "ResourceAgent": [
        Capability.READ_MEMORY, Capability.ACCESS_FILESYSTEM,
        Capability.SEND_EVENT,
    ],
    "ReflectionAgent": [
        Capability.READ_MEMORY, Capability.CALL_LLM,
        Capability.EVALUATE, Capability.SEND_EVENT,
    ],
    "MetaReflector": [
        Capability.READ_MEMORY, Capability.WRITE_MEMORY,
        Capability.CALL_LLM, Capability.SEND_EVENT,
    ],
    "EvaluationManager": [
        Capability.READ_MEMORY, Capability.EVALUATE,
        Capability.SEND_EVENT,
    ],
}


# ──────────────────────────────────────────────
# PermissionMatrix
# ──────────────────────────────────────────────

class PermissionMatrix:
    """
    Agent × Capability access control matrix.

    Agents are denied all capabilities by default.
    Explicit grants required.
    """

    def __init__(
        self,
        permissions: Optional[Dict[str, List[Capability]]] = None,
        strict_mode: bool = True,
    ):
        self._matrix: Dict[str, Set[Capability]] = {}
        self._strict_mode = strict_mode

        # Seed defaults
        seed = permissions or DEFAULT_PERMISSIONS
        for agent, caps in seed.items():
            for cap in caps:
                self.grant(agent, cap)

    # ── CRUD ─────────────────────────────────

    def grant(self, agent: str, capability: Capability) -> None:
        """Grant a capability to an agent."""
        if agent not in self._matrix:
            self._matrix[agent] = set()
        self._matrix[agent].add(capability)

    def revoke(self, agent: str, capability: Capability) -> None:
        """Revoke a capability from an agent."""
        if agent in self._matrix:
            self._matrix[agent].discard(capability)

    def check(self, agent: str, capability: Capability) -> bool:
        """Check if an agent has a specific capability."""
        if agent not in self._matrix:
            return not self._strict_mode
        return capability in self._matrix[agent]

    def check_all(
        self, agent: str, capabilities: List[Capability]
    ) -> Dict[Capability, bool]:
        """Batch check multiple capabilities for one agent."""
        return {c: self.check(agent, c) for c in capabilities}

    def capabilities(self, agent: str) -> List[Capability]:
        """List all capabilities granted to an agent."""
        return sorted(
            self._matrix.get(agent, set()),
            key=lambda c: c.name,
        )

    def agents(self) -> List[str]:
        """List all registered agents."""
        return sorted(self._matrix.keys())

    # ── Query ─────────────────────────────────

    def is_denied(self, agent: str, capability: Capability) -> bool:
        """Negation of check() — for readability in guard clauses."""
        return not self.check(agent, capability)

    def audit_summary(self) -> Dict[str, Any]:
        """Produce a summary of the current permission state."""
        return {
            "agents": len(self._matrix),
            "strict_mode": self._strict_mode,
            "permissions": {
                agent: [c.value for c in sorted(caps, key=lambda c: c.name)]
                for agent, caps in self._matrix.items()
            },
        }
