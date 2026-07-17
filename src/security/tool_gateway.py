"""
Phase 5.3 — Tool Call Gateway

All tool/LLM calls pass through this gateway:
  1. Permission check (agent × capability)
  2. Argument validation (basic safety)
  3. Execution audit logging

Usage:
    from src.security import ToolGateway, PermissionMatrix, AuditLogger

    matrix = PermissionMatrix()
    logger = AuditLogger()
    gateway = ToolGateway(matrix, logger)

    result = gateway.execute(
        agent="ProfileAgent",
        capability="call_llm",
        args={"prompt": "...", "temperature": 0.5},
    )
    # result.ok = True/False
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .permission import PermissionMatrix, Capability
from .audit import AuditLogger


# ──────────────────────────────────────────────
# Gateway Result
# ──────────────────────────────────────────────

@dataclass
class GatewayResult:
    """Result of a tool execution through the gateway."""

    ok: bool = False
    allowed: bool = False
    agent: str = ""
    action: str = ""
    reason: str = ""   # "permitted" | "denied: <reason>" | "error: <msg>"
    risk: str = "LOW"
    data: Any = None
    audit_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "allowed": self.allowed,
            "agent": self.agent,
            "action": self.action,
            "reason": self.reason,
            "risk": self.risk,
            "audit_id": self.audit_id,
        }


# ──────────────────────────────────────────────
# ToolGateway
# ──────────────────────────────────────────────

class ToolGateway:
    """
    Centralized tool call gateway with permission + audit.

    Usage:
        gateway = ToolGateway(permission_matrix, audit_logger)
        result = gateway.execute(
            agent="ProfileAgent",
            capability=Capability.CALL_LLM,
            args={"prompt": "hello"},
        )
    """

    # Argument safety limits
    MAX_PROMPT_LENGTH = 50000
    MAX_TOKENS = 32768
    MIN_TEMPERATURE = 0.0
    MAX_TEMPERATURE = 2.0

    def __init__(
        self,
        permissions: PermissionMatrix,
        logger: Optional[AuditLogger] = None,
    ):
        self._permissions = permissions
        self._logger = logger or AuditLogger()

    def execute(
        self,
        agent: str,
        capability: Capability,
        args: Optional[Dict[str, Any]] = None,
        session_id: str = "",
    ) -> GatewayResult:
        """
        Execute a tool call with permission check + argument validation.

        Args:
            agent: Agent name (e.g. "ProfileAgent")
            capability: What the agent wants to do
            args: Tool arguments (optional)
            session_id: Runtime session for audit trail

        Returns:
            GatewayResult with ok=True if allowed, ok=False if denied.
        """
        args = args or {}

        # Step 1: Permission check
        permission = self._check_permission(agent, capability)
        if not permission:
            self._logger.record_denied(
                agent=agent,
                action=capability.value,
                reason=f"Agent '{agent}' lacks capability '{capability.value}'",
            )
            return GatewayResult(
                ok=False,
                allowed=False,
                agent=agent,
                action=capability.value,
                reason=f"denied: missing capability '{capability.value}'",
            )

        # Step 2: Argument validation
        validation = self._validate_args(capability, args)
        if not validation["valid"]:
            self._logger.record_denied(
                agent=agent,
                action=capability.value,
                reason=validation["reason"],
            )
            return GatewayResult(
                ok=False,
                allowed=False,
                agent=agent,
                action=capability.value,
                reason=f"denied: {validation['reason']}",
                risk="HIGH",
            )

        # Step 3: Execution audit
        audit = self._logger.record_allowed(
            agent=agent,
            action=capability.value,
            detail=f"Arguments validated; {validation.get('summary', '')}",
        )

        return GatewayResult(
            ok=True,
            allowed=True,
            agent=agent,
            action=capability.value,
            reason="permitted",
            risk="LOW",
            audit_id=audit.record_id,
        )

    # ── Permission ───────────────────────────

    def _check_permission(self, agent: str, capability: Capability) -> bool:
        return self._permissions.check(agent, capability)

    # ── Validation ───────────────────────────

    def _validate_args(
        self,
        capability: Capability,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate arguments for safety."""

        if capability == Capability.CALL_LLM:
            prompt = args.get("prompt", "")
            if isinstance(prompt, str) and len(prompt) > self.MAX_PROMPT_LENGTH:
                return {"valid": False, "reason": f"prompt too long ({len(prompt)} > {self.MAX_PROMPT_LENGTH})"}
            temp = args.get("temperature", 0.5)
            if isinstance(temp, (int, float)) and not (self.MIN_TEMPERATURE <= temp <= self.MAX_TEMPERATURE):
                return {"valid": False, "reason": f"temperature out of range ({temp})"}
            tokens = args.get("max_tokens", 2048)
            if isinstance(tokens, int) and tokens > self.MAX_TOKENS:
                return {"valid": False, "reason": f"max_tokens too high ({tokens} > {self.MAX_TOKENS})"}
            return {"valid": True, "summary": f"prompt={len(prompt)}chars"}

        if capability == Capability.EXECUTE_CODE:
            code = args.get("code", "")
            if isinstance(code, str) and len(code) > 100000:
                return {"valid": False, "reason": "code too long"}
            return {"valid": True, "summary": f"code={len(code)}chars"}

        if capability == Capability.ACCESS_FILESYSTEM:
            path = args.get("path", "")
            dangerous = ["/etc/passwd", "/etc/shadow", "/root/", "~/.ssh/", "../" * 5]
            if isinstance(path, str) and any(d in path for d in dangerous):
                return {"valid": False, "reason": "dangerous filesystem path"}
            return {"valid": True, "summary": f"path={path}"}

        # Default: valid for other capabilities
        return {"valid": True, "summary": ""}

    # ── Security hook (for RuntimeEngine integration) ──

    def as_runtime_hook(self):
        """
        Return a RuntimeHook that audits transitions through this gateway.

        Usage:
            engine.add_hook(gateway.as_runtime_hook())
        """
        from src.runtime.hooks import RuntimeHook

        gateway = self

        class _SecurityHook(RuntimeHook):
            def after_transition(self, engine, from_state, to_state, ctx, transition):
                gateway._logger.record(
                    agent=f"RuntimeEngine",
                    action=f"transition:{to_state.name}",
                    result=transition.status,
                    session_id=getattr(engine, 'session_id', ''),
                    metadata={"from": from_state.name, "duration_ms": transition.duration_ms},
                )

            def on_error(self, engine, state, ctx, error):
                gateway._logger.record(
                    agent=f"RuntimeEngine",
                    action=f"error:{state.name}",
                    result="error",
                    risk="HIGH",
                    detail=error,
                    session_id=getattr(engine, 'session_id', ''),
                )

        return _SecurityHook()
