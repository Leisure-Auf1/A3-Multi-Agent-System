"""
Phase 6.0 — SDK Tests

Covers:
  1. TaskRequest: creation, validation, to_dict
  2. TaskResult: creation, is_success, to_dict
  3. SessionInfo: creation, to_dict, is_completed
  4. TaskStatus: enum values
  5. RuntimeConfig: defaults, to_dict, custom
  6. ConfigLoader: load from dict, overrides
  7. Exceptions: VeritasError hierarchy
  8. RuntimeClient: run, sessions, get_session, explain, status
  9. RuntimeClient: error handling (invalid task, missing session)
 10. Contract validation edge cases
 11. Backward compat: old RuntimeEngine still works
"""
from __future__ import annotations

import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from veritas.sdk import (
    RuntimeClient,
    TaskRequest,
    TaskResult,
    SessionInfo,
    TaskStatus,
    RuntimeConfig,
    ConfigLoader,
    PluginEntry,
)
from veritas.sdk.exceptions import (
    VeritasError,
    ConfigError,
    ContractValidationError,
    TaskExecutionError,
    SessionNotFoundError,
    PluginError,
)
from veritas.runtime import RuntimeEngine, TransitionTable, AgentState


# ══════════════════════════════════════════════
# 1. TaskRequest
# ══════════════════════════════════════════════

class TestTaskRequest:
    def test_create(self):
        t = TaskRequest(objective="analyze", agent="evaluator")
        assert t.objective == "analyze"
        assert t.agent == "evaluator"

    def test_auto_task_id(self):
        t = TaskRequest(objective="x", agent="y")
        assert len(t.task_id) == 12

    def test_validate_valid(self):
        t = TaskRequest(objective="learn", agent="planner")
        assert t.is_valid()
        assert t.validate() == []

    def test_validate_empty_objective(self):
        t = TaskRequest(objective="", agent="planner")
        assert not t.is_valid()
        assert any("objective" in i for i in t.validate())

    def test_validate_empty_agent(self):
        t = TaskRequest(objective="learn", agent="")
        assert not t.is_valid()

    def test_validate_negative_timeout(self):
        t = TaskRequest(objective="learn", agent="p", timeout_seconds=-1)
        assert not t.is_valid()

    def test_to_dict(self):
        t = TaskRequest(objective="learn", agent="p",
                        context={"level": "beginner"}, metadata={"source": "test"})
        d = t.to_dict()
        assert d["objective"] == "learn"
        assert d["context"]["level"] == "beginner"
        assert d["metadata"]["source"] == "test"


# ══════════════════════════════════════════════
# 2. TaskResult + TaskStatus
# ══════════════════════════════════════════════

class TestTaskResult:
    def test_is_success(self):
        r = TaskResult(task_id="t1", status=TaskStatus.COMPLETED)
        assert r.is_success
        r2 = TaskResult(task_id="t2", status=TaskStatus.FAILED)
        assert not r2.is_success

    def test_to_dict(self):
        r = TaskResult(
            task_id="t1", status=TaskStatus.COMPLETED,
            output={"score": 85}, execution_time_ms=42.0,
            session_id="s1", trace_id="tr1",
            errors=["warn"], metadata={"steps": 5},
        )
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "completed"
        assert d["is_success"] is True
        assert d["execution_time_ms"] == 42.0


class TestTaskStatus:
    def test_all_values(self):
        values = {s.value for s in TaskStatus}
        assert "pending" in values
        assert "completed" in values
        assert "failed" in values


# ══════════════════════════════════════════════
# 3. SessionInfo
# ══════════════════════════════════════════════

class TestSessionInfo:
    def test_defaults(self):
        s = SessionInfo()
        assert s.state == "unknown"
        assert not s.is_completed

    def test_completed(self):
        s = SessionInfo(state="completed")
        assert s.is_completed

    def test_to_dict(self):
        s = SessionInfo(
            session_id="s1", state="completed", task_id="t1",
            total_duration_ms=100.0, state_count=5, timeline=["a", "b"],
        )
        d = s.to_dict()
        assert d["session_id"] == "s1"
        assert d["timeline"] == ["a", "b"]


# ══════════════════════════════════════════════
# 4. RuntimeConfig + ConfigLoader
# ══════════════════════════════════════════════

class TestRuntimeConfig:
    def test_defaults(self):
        c = RuntimeConfig()
        assert c.recovery_enabled is True
        assert c.max_retries == 3
        assert c.runtime_version == "6.0"

    def test_to_dict(self):
        c = RuntimeConfig(max_retries=5)
        d = c.to_dict()
        assert d["recovery"]["max_retries"] == 5

    def test_custom(self):
        c = RuntimeConfig(
            recovery_enabled=False,
            max_retries=1,
            distributed_enabled=True,
            security_enabled=True,
        )
        assert c.recovery_enabled is False
        assert c.distributed_enabled is True


class TestConfigLoader:
    def test_load_from_dict(self):
        loader = ConfigLoader()
        c = loader.load_from_dict({
            "runtime": {
                "recovery": {"enabled": False, "max_retries": 1},
                "distributed": {"enabled": True},
            },
        })
        assert c.recovery_enabled is False
        assert c.max_retries == 1
        assert c.distributed_enabled is True

    def test_overrides(self):
        loader = ConfigLoader()
        c = loader.load(overrides={"recovery_enabled": False, "max_retries": 10})
        assert c.recovery_enabled is False
        assert c.max_retries == 10

    def test_direct_init(self):
        """Direct RuntimeConfig constructor works."""
        c = RuntimeConfig(max_retries=7, recovery_enabled=False)
        assert c.max_retries == 7

    def test_plugin_entry(self):
        p = PluginEntry(name="security", enabled=True, config={"level": "strict"})
        assert p.name == "security"
        assert p.config["level"] == "strict"


# ══════════════════════════════════════════════
# 5. Exceptions
# ══════════════════════════════════════════════

class TestExceptions:
    def test_veritas_error_base(self):
        e = VeritasError("base error")
        assert "base error" in str(e)

    def test_config_error(self):
        e = ConfigError("bad yaml", path="/tmp/x.yaml")
        assert "bad yaml" in str(e)
        assert e.path == "/tmp/x.yaml"

    def test_contract_validation_error(self):
        e = ContractValidationError("missing field", field="objective", value="")
        assert e.field == "objective"
        assert "objective" in e.detail

    def test_task_execution_error(self):
        e = TaskExecutionError("boom", task_id="t1", agent="planner")
        assert e.task_id == "t1"
        assert e.agent == "planner"

    def test_session_not_found(self):
        e = SessionNotFoundError("abc123")
        assert e.session_id == "abc123"

    def test_plugin_error(self):
        e = PluginError("init failed", plugin_name="security")
        assert e.plugin_name == "security"

    def test_veritas_error_is_catch_all(self):
        """All SDK errors are catchable as VeritasError."""
        for exc in [ConfigError("x"), TaskExecutionError("x"), ContractValidationError("x")]:
            assert isinstance(exc, VeritasError)


# ══════════════════════════════════════════════
# 6. RuntimeClient — Core
# ══════════════════════════════════════════════

class TestRuntimeClient:
    @pytest.fixture
    def client(self):
        return RuntimeClient()

    def test_run_succeeds(self, client):
        result = client.run(TaskRequest(objective="test", agent="planner"))
        assert result.is_success
        assert result.task_id != ""

    def test_run_with_context(self, client):
        result = client.run(TaskRequest(
            objective="learn", agent="tutor",
            context={"topic": "Python", "level": "beginner"},
        ))
        assert result.is_success

    def test_sessions(self, client):
        client.run(TaskRequest(objective="a", agent="x"))
        client.run(TaskRequest(objective="b", agent="y"))
        sessions = client.sessions()
        assert len(sessions) == 2

    def test_get_session(self, client):
        result = client.run(TaskRequest(objective="test", agent="p"))
        session = client.get_session(result.session_id)
        assert session.session_id == result.session_id

    def test_get_session_missing_raises(self, client):
        with pytest.raises(SessionNotFoundError):
            client.get_session("nonexistent")

    def test_explain(self, client):
        result = client.run(TaskRequest(objective="test", agent="p"))
        explanation = client.explain(result.session_id)
        assert "total_decisions" in explanation

    def test_explain_missing_raises(self, client):
        with pytest.raises(SessionNotFoundError):
            client.explain("nonexistent")

    def test_status(self, client):
        s = client.status()
        assert s["version"] == "6.0"
        assert "sessions_count" in s

    def test_config_access(self, client):
        assert client.config.runtime_version == "6.0"
        assert client.config.recovery_enabled is True


# ══════════════════════════════════════════════
# 7. RuntimeClient — Error Handling
# ══════════════════════════════════════════════

class TestRuntimeClientErrors:
    def test_invalid_task_raises(self):
        client = RuntimeClient()
        with pytest.raises(ContractValidationError):
            client.run(TaskRequest(objective="", agent=""))

    def test_runtime_client_with_custom_config(self):
        client = RuntimeClient(RuntimeConfig(recovery_enabled=False))
        result = client.run(TaskRequest(objective="test", agent="p"))
        assert result.is_success


# ══════════════════════════════════════════════
# 8. Backward Compatibility
# ══════════════════════════════════════════════

class TestBackwardCompat:
    def test_old_runtime_engine_still_works(self):
        """RuntimeEngine API is unaffected by SDK."""
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="bc_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()
        assert engine._checkpoint.state_count() >= 1

    def test_sdk_does_not_break_existing_imports(self):
        """All existing runtime imports still work."""
        from veritas.runtime import (
            AgentState, RuntimeEngine, RuntimeContext, RuntimeHook,
            RecoveryManager, LifecycleManager, ExplanationRecorder,
            RuntimeNode, NodeRegistry, PluginManager,
        )
        assert True  # imports succeeded


# ══════════════════════════════════════════════
# 9. Edge Cases
# ══════════════════════════════════════════════

class TestSDKEdgeCases:
    def test_multiple_clients(self):
        """Multiple RuntimeClient instances work independently."""
        c1 = RuntimeClient()
        c2 = RuntimeClient()
        c1.run(TaskRequest(objective="a", agent="x"))
        c2.run(TaskRequest(objective="b", agent="y"))
        assert len(c1.sessions()) == 1
        assert len(c2.sessions()) == 1

    def test_task_with_metadata(self):
        client = RuntimeClient()
        result = client.run(TaskRequest(
            objective="test", agent="p",
            metadata={"caller": "test_suite", "version": 1},
        ))
        assert result.is_success

    def test_long_objective(self):
        client = RuntimeClient()
        long_obj = "Analyze the performance of " + "x " * 50
        result = client.run(TaskRequest(objective=long_obj, agent="analyzer"))
        assert result.is_success

    def test_config_does_not_leak(self):
        """RuntimeConfig is not mutated by the client."""
        config = RuntimeConfig(max_retries=99)
        client = RuntimeClient(config)
        assert config.max_retries == 99
        client.run(TaskRequest(objective="test", agent="p"))
        assert config.max_retries == 99  # unchanged

    def test_result_output_preserved(self):
        """TaskResult is complete and contains task metadata."""
        client = RuntimeClient()
        result = client.run(TaskRequest(objective="verify output", agent="test"))
        assert result.is_success
        assert result.task_id != ""
        assert result.session_id != ""
        assert result.metadata.get("agent") == "test"

    def test_status_reflects_sessions(self):
        """Client status count matches sessions count."""
        client = RuntimeClient()
        client.run(TaskRequest(objective="a", agent="x"))
        client.run(TaskRequest(objective="b", agent="y"))
        client.run(TaskRequest(objective="c", agent="z"))
        assert client.status()["sessions_count"] == 3

    def test_exception_inheritance_chain(self):
        """All exceptions have the right MRO."""
        assert issubclass(ContractValidationError, VeritasError)
        assert issubclass(TaskExecutionError, VeritasError)
        assert issubclass(SessionNotFoundError, VeritasError)
        assert issubclass(ConfigError, VeritasError)
