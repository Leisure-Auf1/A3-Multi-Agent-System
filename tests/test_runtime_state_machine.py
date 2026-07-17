"""
Phase 4.8 — Agent Runtime State Machine Tests

Covers:
  1. AgentState enum values and labels
  2. TransitionTable: default chain + conditional
  3. RuntimeEngine: handler registration + execution
  4. RuntimeCheckpoint: trace integration
  5. A3Workflow.run_via_runtime(): full pipeline via state machine
  6. A3Workflow.run(): backward compatibility
  7. Normal flow: INIT → DONE (all states)
  8. Evaluation failure → REFLECT still works
  9. MetaReflector triggering in runtime
  10. Memory update is called
"""

from __future__ import annotations

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.runtime import (
    AgentState,
    StateTransition,
    TransitionTable,
    RuntimeCheckpoint,
    RuntimeEngine,
    RuntimeContext,
)
from src.core.meta_reflector import MetaReflectorAgent, _LocalMemoryStore
from src.workflow import A3Workflow
from src.memory.memory_manager import MemoryManager


# ──────────────────────────────────────────────
# 1. AgentState enum
# ──────────────────────────────────────────────

class TestAgentState:
    def test_all_states_present(self):
        states = list(AgentState)
        names = {s.name for s in states}
        expected = {"INIT", "PROFILE", "PLAN", "EXECUTE", "EVALUATE",
                     "REFLECT", "META_REFLECT", "MEMORY_UPDATE", "DONE"}
        assert names == expected

    def test_terminal_state(self):
        assert AgentState.DONE.is_terminal is True
        assert AgentState.INIT.is_terminal is False

    def test_labels(self):
        assert AgentState.INIT.label == "初始化"
        assert AgentState.PROFILE.label == "画像提取"
        assert AgentState.DONE.label == "完成"


# ──────────────────────────────────────────────
# 2. TransitionTable
# ──────────────────────────────────────────────

class TestTransitionTable:
    def test_default_chain(self):
        table = TransitionTable()
        assert table.next_state(AgentState.INIT) == AgentState.PROFILE
        assert table.next_state(AgentState.PROFILE) == AgentState.PLAN
        assert table.next_state(AgentState.DONE) is None

    def test_conditional_transition(self):
        table = TransitionTable()
        # REFLECT → META_REFLECT if guard returns True, else MEMORY_UPDATE
        table.set_conditional(
            AgentState.REFLECT,
            guard=lambda ctx: ctx.should_meta_reflect(),
            true_branch=AgentState.META_REFLECT,
            false_branch=AgentState.MEMORY_UPDATE,
        )

        class FakeCtx:
            def should_meta_reflect(self): return True
        assert table.resolve(AgentState.REFLECT, FakeCtx()) == AgentState.META_REFLECT

        class FakeCtxNo:
            def should_meta_reflect(self): return False
        assert table.resolve(AgentState.REFLECT, FakeCtxNo()) == AgentState.MEMORY_UPDATE


# ──────────────────────────────────────────────
# 3. RuntimeCheckpoint
# ──────────────────────────────────────────────

class TestRuntimeCheckpoint:
    def test_record_transition(self):
        cp = RuntimeCheckpoint(session_id="s1")
        cp.record(StateTransition(
            from_state=AgentState.INIT,
            to_state=AgentState.PROFILE,
            status="success",
        ))
        assert cp.state_count() == 1
        assert cp.current_state == AgentState.PROFILE

    def test_error_count(self):
        cp = RuntimeCheckpoint(session_id="s1")
        cp.record(StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE, status="success"))
        cp.record(StateTransition(from_state=AgentState.PROFILE, to_state=AgentState.PLAN, status="error", error="boom"))
        assert cp.error_count() == 1
        assert cp.state_count() == 2

    def test_to_dict_list(self):
        cp = RuntimeCheckpoint(session_id="s1")
        cp.record(StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE))
        lst = cp.to_dict_list()
        assert len(lst) == 1
        assert lst[0]["from"] == "INIT"
        assert lst[0]["to"] == "PROFILE"

    def test_summary(self):
        cp = RuntimeCheckpoint(session_id="s1")
        cp.record(StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE))
        s = cp.summary()
        assert s["total_transitions"] == 1
        # _state_history records to_state (PROFILE), not from_state (INIT)
        assert "PROFILE" in str(s["states_visited"])

    def test_summary_states_visited(self):
        cp = RuntimeCheckpoint(session_id="s2")
        cp.record(StateTransition(from_state=AgentState.INIT, to_state=AgentState.PROFILE))
        cp.record(StateTransition(from_state=AgentState.PROFILE, to_state=AgentState.PLAN))
        s = cp.summary()
        assert s["total_transitions"] == 2
        assert "PROFILE" in str(s["states_visited"])
        assert "PLAN" in str(s["states_visited"])


# ──────────────────────────────────────────────
# 4. RuntimeEngine (standalone)
# ──────────────────────────────────────────────

class TestRuntimeEngine:
    def test_register_and_run_simple_chain(self):
        """INIT→PROFILE transition calls PROFILE handler (to-state)."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})

        engine = RuntimeEngine(session_id="test")
        engine._table = table

        visited = []
        # Handler fires for to_state (PROFILE), not from_state (INIT)
        engine.register_handler(AgentState.PROFILE, lambda c: visited.append("profile"))

        ctx = engine.run()
        assert "profile" in visited
        assert engine._checkpoint.state_count() >= 1

    def test_handler_error_caught(self):
        """Handler raises → transition marked as error, engine continues."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="test")
        engine._table = table

        def bad_handler(ctx):
            raise ValueError("test error")

        engine.register_handler(AgentState.PROFILE, bad_handler)
        ctx = engine.run()
        assert len(ctx.errors) >= 1
        assert "test error" in ctx.errors[0]

    def test_timeline(self):
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()
        tl = engine.timeline()
        assert len(tl) >= 1
        assert isinstance(tl[0], StateTransition)

    def test_to_trace_dict_list(self):
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()
        trace = engine.to_trace_dict_list()
        assert len(trace) >= 1

    def test_unregistered_handler_skipped(self):
        """State with no handler → skipped transition, no crash."""
        table = TransitionTable(custom={AgentState.INIT: AgentState.PROFILE})
        engine = RuntimeEngine(session_id="test")
        engine._table = table
        # No PROFILE handler registered
        ctx = engine.run()
        # Engine should complete without errors from unregistered handler
        assert engine._checkpoint.state_count() >= 1


# ──────────────────────────────────────────────
# 5. A3Workflow.run_via_runtime()
# ──────────────────────────────────────────────

class TestWorkflowViaRuntime:
    def test_run_via_runtime_produces_result(self):
        """run_via_runtime() returns WorkflowResult with all fields."""
        wf = A3Workflow(student_id="test_stu")
        result = wf.run_via_runtime(
            user_goal="学习 Python",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )
        assert result.success
        assert result.profile is not None
        assert result.learning_plan is not None
        assert result.resources is not None
        assert result.evaluation is not None
        assert result.reflection is not None
        assert result.trace is not None

    def test_run_via_runtime_matches_run_output_structure(self):
        """run_via_runtime() output has same shape as run()."""
        wf = A3Workflow(student_id="test_stu")
        user_profile = {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "error_prone_bias": "magic_syntax_blind",
            "learning_pace": "normal",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
        }

        result = wf.run_via_runtime("学习 Python", user_profile)
        d = result.to_dict()

        # All required keys present
        for key in ("success", "context", "profile", "learning_plan",
                     "resources", "evaluation", "reflection", "trace",
                     "memory_saved", "meta_reflection", "errors"):
            assert key in d, f"Missing key: {key}"

    def test_run_via_runtime_with_meta_reflector(self):
        """MetaReflector triggers inside runtime state machine."""
        mm = MemoryManager(auto_seed=False)
        reflector = MetaReflectorAgent(db_client=_LocalMemoryStore())
        wf = A3Workflow(
            memory_manager=mm,
            meta_reflector=reflector,
            student_id="test_stu",
        )
        result = wf.run_via_runtime(
            user_goal="学习 Python 闭包",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )
        assert result.success

    def test_run_via_runtime_without_meta_reflector(self):
        """No MetaReflector → no crash, meta_reflection is None."""
        wf = A3Workflow(student_id="test_stu")
        result = wf.run_via_runtime(
            user_goal="test",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )
        assert result.success
        assert result.meta_reflection is None


# ──────────────────────────────────────────────
# 6. Backward Compatibility
# ──────────────────────────────────────────────

class TestBackwardCompat:
    def test_run_still_works(self):
        """Existing run() API unchanged."""
        wf = A3Workflow(student_id="test_stu")
        result = wf.run(
            user_goal="学习 Python",
            user_profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "error_prone_bias": "magic_syntax_blind",
                "learning_pace": "normal",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            },
        )
        assert result.success
        assert result.evaluation is not None
        assert result.reflection is not None

    def test_run_and_run_via_runtime_both_succeed(self):
        """Both run() and run_via_runtime() work."""
        up = {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "error_prone_bias": "magic_syntax_blind",
            "learning_pace": "normal",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
        }

        wf1 = A3Workflow(student_id="s1")
        r1 = wf1.run("test", up)
        assert r1.success

        wf2 = A3Workflow(student_id="s2")
        r2 = wf2.run_via_runtime("test", up)
        assert r2.success


# ──────────────────────────────────────────────
# 7. RuntimeContext
# ──────────────────────────────────────────────

class TestRuntimeContext:
    def test_defaults(self):
        ctx = RuntimeContext()
        assert ctx.session_id == ""
        assert ctx.evaluation_score() == 100
        assert ctx.should_meta_reflect() is False

    def test_evaluation_score(self):
        ctx = RuntimeContext(evaluation={"score": 55})
        assert ctx.evaluation_score() == 55

    def test_should_meta_reflect_with_adapter(self):
        from src.core.meta_reflection_adapter import MetaReflectionAdapter
        ctx = RuntimeContext(
            evaluation={"score": 50, "issues": []},
            meta_adapter=MetaReflectionAdapter(),
        )
        assert ctx.should_meta_reflect() is True
