"""
Phase 4.8 — Agent Runtime Engine

State machine that drives the A3 agent pipeline.
Designed to be called from A3Workflow (backward compat) or standalone.

Usage:
    engine = RuntimeEngine(session_id="abc")
    engine.register_handler(AgentState.PROFILE, my_profile_handler)
    result = engine.run()
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .state import AgentState
from .transition import StateTransition, TransitionTable, StateHandler
from .checkpoint import RuntimeCheckpoint
from .hooks import RuntimeHook
from .policy import RuntimePolicyEngine  # Phase 5.2


@dataclass
class RuntimeContext:
    """
    Mutable context passed to every state handler.

    Handlers read/write this structure to produce pipeline outputs.
    """
    session_id: str = ""
    user_goal: str = ""
    user_profile: Optional[Dict[str, Any]] = None
    knowledge_gaps: List[str] = field(default_factory=list)
    student_id: str = ""

    # Agent outputs (filled by handlers)
    profile: Optional[Dict[str, Any]] = None
    learning_plan: Optional[Dict[str, Any]] = None
    resources: Optional[List[Dict[str, Any]]] = None
    evaluation: Optional[Dict[str, Any]] = None
    reflection: Optional[Dict[str, Any]] = None
    meta_reflection: Optional[Dict[str, Any]] = None

    # Metadata
    errors: List[str] = field(default_factory=list)
    meta_reflector: Any = None          # MetaReflectorAgent instance
    meta_adapter: Any = None            # MetaReflectionAdapter instance

    def evaluation_score(self) -> int:
        if self.evaluation and isinstance(self.evaluation, dict):
            return self.evaluation.get("score", 100)
        return 100

    def should_meta_reflect(self) -> bool:
        """Guard for REFLECT → META_REFLECT transition."""
        if self.meta_adapter is None:
            return False
        try:
            return self.meta_adapter.should_trigger(self.evaluation)
        except Exception:
            return False


class RuntimeEngine:
    """
    Agent Runtime State Machine.

    Manages the execution of agent pipeline states:
    INIT → PROFILE → PLAN → EXECUTE → EVALUATE → REFLECT → [META_REFLECT] → MEMORY_UPDATE → DONE

    Usage:
        engine = RuntimeEngine(session_id="s1")
        engine.register_handler(AgentState.PROFILE, handle_profile)
        engine.register_handler(AgentState.PLAN, handle_plan)
        # ... register all handlers ...
        result = engine.run()

    Handlers receive RuntimeContext and raise exceptions on error.
    The engine catches exceptions, records failed transitions, and
    continues to the next state.
    """

    MAX_TRANSITIONS = 20  # Safety limit

    def __init__(
        self,
        session_id: str = "",
        enable_meta_reflect: bool = True,
        policy_engine: Optional[RuntimePolicyEngine] = None,  # Phase 5.2
        recovery_manager: Optional[Any] = None,  # Phase 5.4
    ):
        self.session_id = session_id or f"rt_{int(time.time())}"
        self.enable_meta_reflect = enable_meta_reflect
        self._policy_engine = policy_engine  # Phase 5.2
        self._recovery_manager = recovery_manager  # Phase 5.4

        self._handlers: Dict[AgentState, StateHandler] = {}
        self._table = TransitionTable()
        self._checkpoint = RuntimeCheckpoint(session_id=self.session_id)
        self._hooks: List[RuntimeHook] = []  # Phase 4.10 — native hooks

        # Wire conditional transition for MetaReflector
        if enable_meta_reflect:
            self._table.set_conditional(
                AgentState.REFLECT,
                guard=lambda ctx: ctx.meta_reflector is not None and ctx.should_meta_reflect(),
                true_branch=AgentState.META_REFLECT,
                false_branch=AgentState.MEMORY_UPDATE,
            )

    # ── Handler registration ────────────────

    def register_handler(self, state: AgentState, handler: StateHandler) -> None:
        """Register a handler function for a state."""
        self._handlers[state] = handler

    def add_hook(self, hook: RuntimeHook) -> None:
        """Register a lifecycle hook (Phase 4.10)."""
        self._hooks.append(hook)

    # ── Main execution ──────────────────────

    def run(self, ctx: Optional[RuntimeContext] = None) -> RuntimeContext:
        """
        Execute the state machine from INIT to DONE.

        Args:
            ctx: Pre-configured context (optional). Created fresh if None.

        Returns:
            RuntimeContext with all agent outputs filled.
        """
        ctx = ctx or RuntimeContext(session_id=self.session_id)
        t0 = time.time()

        # Phase 4.10 — on_run_start hook
        for hook in self._hooks:
            try:
                hook.on_run_start(self, ctx)
            except Exception:
                pass

        current = AgentState.INIT
        transitions = 0
        while not current.is_terminal and transitions < self.MAX_TRANSITIONS:
            next_state = self._table.resolve(current, ctx)
            if next_state is None:
                break

            # Phase 5.2 — Policy engine can override next_state
            if self._policy_engine is not None:
                decision = self._policy_engine.decide_pre_transition(
                    current, next_state, ctx,
                )
                if decision.action == "TERMINATE":
                    break
                if decision.action == "RETRY" and decision.to_state:
                    next_state = decision.to_state

            transition = self._execute_transition(current, next_state, ctx)
            self._checkpoint.record(transition)

            # Phase 5.2 — Post-transition policy decision
            if self._policy_engine is not None:
                post_decision = self._policy_engine.decide(
                    current, next_state, ctx, transition,
                )
                if post_decision.action == "TERMINATE":
                    current = next_state
                    break
                if post_decision.action == "RETRY":
                    # Phase 5.4 — Recovery Manager handles retry execution
                    if self._recovery_manager is not None:
                        failure = self._extract_failure(transition, ctx)
                        recovery_result = self._recovery_manager.execute_recovery(
                            failure, ctx, self._handlers.get(next_state),
                        )
                        if not recovery_result.success:
                            # Recovery exhausted → terminate
                            current = next_state
                            break
                    if post_decision.to_state and post_decision.to_state != next_state:
                        current = post_decision.to_state
                        transitions += 1
                        continue
                if post_decision.action in ("REFLECT", "META_REFLECT"):
                    if post_decision.to_state and post_decision.to_state != next_state:
                        current = post_decision.to_state
                        transitions += 1
                        continue  # re-enter loop with new state

            current = next_state
            transitions += 1

        total_duration_ms = (time.time() - t0) * 1000

        # Phase 4.10 — on_run_end hook
        for hook in self._hooks:
            try:
                hook.on_run_end(self, ctx, total_duration_ms)
            except Exception:
                pass

        return ctx

    def _execute_transition(
        self,
        from_state: AgentState,
        to_state: AgentState,
        ctx: RuntimeContext,
    ) -> StateTransition:
        """Execute a single state transition and return the record."""
        t0 = time.time()
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
        )

        # Phase 4.10 — before_transition hook
        for hook in self._hooks:
            try:
                hook.before_transition(self, from_state, to_state, ctx)
            except Exception:
                pass

        handler = self._handlers.get(to_state)
        if handler is None:
            # No handler → skip gracefully
            transition.status = "skipped"
            transition.duration_ms = (time.time() - t0) * 1000

            # after_transition hook (skipped)
            for hook in self._hooks:
                try:
                    hook.after_transition(self, from_state, to_state, ctx, transition)
                except Exception:
                    pass
            return transition

        try:
            handler(ctx)
            transition.status = "success"
            transition.input_summary = f"→ {to_state.label}"
            transition.output_summary = self._output_summary(ctx, to_state)
        except Exception as e:
            transition.status = "error"
            transition.error = str(e)
            ctx.errors.append(f"{to_state.name}: {e}")

            # Phase 4.10 — on_error hook
            for hook in self._hooks:
                try:
                    hook.on_error(self, to_state, ctx, str(e))
                except Exception:
                    pass

        transition.duration_ms = (time.time() - t0) * 1000

        # Phase 4.10 — after_transition hook
        for hook in self._hooks:
            try:
                hook.after_transition(self, from_state, to_state, ctx, transition)
            except Exception:
                pass

        return transition

    @staticmethod
    def _extract_failure(transition: StateTransition, ctx: RuntimeContext) -> Optional[Any]:
        """Extract a FailureEvent from a transition for recovery (Phase 5.4)."""
        from .failure_detector import FailureDetector
        detector = FailureDetector()
        return detector.detect_from_transition(transition, ctx)

    @staticmethod
    def _output_summary(ctx: RuntimeContext, state: AgentState) -> str:
        """Generate a brief output summary for the transition trace."""
        if state == AgentState.PROFILE:
            p = ctx.profile or {}
            kb = p.get("profile", {}).get("knowledge_base", "?")
            return f"knowledge_base={kb}"
        elif state == AgentState.PLAN:
            nodes = len(ctx.learning_plan.get("nodes", [])) if ctx.learning_plan else 0
            return f"{nodes} nodes"
        elif state == AgentState.EXECUTE:
            return f"{len(ctx.resources or [])} resources"
        elif state == AgentState.EVALUATE:
            return f"score={ctx.evaluation_score()}"
        elif state == AgentState.REFLECT:
            s = ctx.reflection or {}
            return f"success={s.get('success', '?')}, score={s.get('score', '?')}"
        elif state == AgentState.META_REFLECT:
            mr = ctx.meta_reflection or {}
            sev = mr.get("severity", "?")
            cause = (mr.get("root_cause", "") or "")[:50]
            return f"severity={sev}, {cause}"
        elif state == AgentState.MEMORY_UPDATE:
            return "saved"
        return ""

    # ── Diagnostics ─────────────────────────

    def timeline(self) -> List[StateTransition]:
        return self._checkpoint.timeline()

    def to_trace_dict_list(self) -> List[Dict[str, Any]]:
        return self._checkpoint.to_dict_list()

    def summary(self) -> Dict[str, Any]:
        return {
            **self._checkpoint.summary(),
            "states_visited_count": self._checkpoint.state_count(),
        }


# ──────────────────────────────────────────────
# Convenience: create from a Workflow
# ──────────────────────────────────────────────

def create_runtime_from_workflow(workflow: Any) -> RuntimeEngine:
    """
    Create a RuntimeEngine with handlers bound to an A3Workflow instance.

    This bridges the old A3Workflow API to the new RuntimeEngine.
    The workflow's existing step methods become state handlers.
    """
    engine = RuntimeEngine(session_id="")
    wf = workflow

    engine.register_handler(AgentState.INIT, lambda ctx: None)  # no-op

    engine.register_handler(AgentState.PROFILE, lambda ctx: _setattr(ctx, 'profile_result',
        wf._run_profile_agent(ctx.user_goal, ctx.user_profile)))

    return engine


def _setattr(ctx, name: str, value):
    """Helper: set attribute and return None (for handler compatibility)."""
    setattr(ctx, name, value)
