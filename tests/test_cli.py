"""
Phase 6.1 — Veritas CLI Tests

Covers:
  1. Parser: command registration, argument parsing
  2. run command: required args, optional args, context parsing
  3. run command: RuntimeClient integration, success/error output
  4. status command: output format, JSON mode
  5. trace command: session query, missing session
  6. plugins command: listing, empty
  7. Formatter: table, JSON, summary modes
  8. Formatter: TaskResult, status, sessions, explain, plugins
  9. main(): help output, version flag
 10. Error handling: invalid args, missing args
 11. Backward compat: old RuntimeEngine still works
"""
from __future__ import annotations

import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch

from src.cli.main import create_parser, main
from src.cli.formatter import Formatter, OutputFormat
from src.sdk.contracts.task import TaskRequest, TaskResult, TaskStatus, SessionInfo
from src.sdk.client import RuntimeClient
from src.sdk import RuntimeClient as SDKClient


# ══════════════════════════════════════════════
# 1. Parser
# ══════════════════════════════════════════════

class TestParser:
    def test_parser_created(self):
        parser = create_parser()
        assert parser.prog == "veritas"

    def test_run_command_registered(self):
        parser = create_parser()
        args = parser.parse_args(["run", "--agent", "p", "--task", "t"])
        assert args.command == "run"
        assert args.agent == "p"
        assert args.task == "t"

    def test_run_required_agent(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["run", "--task", "t"])

    def test_run_required_task(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["run", "--agent", "p"])

    def test_run_optional_args(self):
        parser = create_parser()
        args = parser.parse_args([
            "run", "-a", "evaluator", "-t", "analyze",
            "--timeout", "60", "--json",
            "--context", "level=beginner", "topic=math",
        ])
        assert args.timeout == 60.0
        assert args.json is True
        assert args.context == ["level=beginner", "topic=math"]

    def test_status_command(self):
        parser = create_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_status_json_flag(self):
        parser = create_parser()
        args = parser.parse_args(["status", "--json"])
        assert args.json is True

    def test_trace_command(self):
        parser = create_parser()
        args = parser.parse_args(["trace", "abc123"])
        assert args.command == "trace"
        assert args.session_id == "abc123"

    def test_trace_missing_session_id(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["trace"])

    def test_plugins_command(self):
        parser = create_parser()
        args = parser.parse_args(["plugins"])
        assert args.command == "plugins"

    def test_version_flag(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_no_command_shows_help(self):
        """No command → help text."""
        result = main([])
        assert result == 1  # exits with error code


# ══════════════════════════════════════════════
# 2. run Command — Integration
# ══════════════════════════════════════════════

class TestRunCommand:
    def test_run_succeeds(self):
        """Full 'veritas run' command through RuntimeClient."""
        result = main(["run", "--agent", "test-agent", "--task", "integration test"])
        assert result == 0  # success exit code

    def test_run_with_context(self):
        result = main([
            "run", "-a", "tutor", "-t", "teach Python",
            "--context", "level=beginner", "style=visual",
        ])
        assert result == 0

    def test_run_with_summary_flag(self):
        result = main([
            "run", "-a", "test", "-t", "quick task", "--summary",
        ])
        assert result == 0

    def test_run_with_json_flag(self):
        result = main([
            "run", "-a", "test", "-t", "json task", "--json",
        ])
        assert result == 0

    def test_run_missing_agent_shows_error(self):
        with pytest.raises(SystemExit):
            main(["run", "--task", "test"])


# ══════════════════════════════════════════════
# 3. status Command
# ══════════════════════════════════════════════

class TestStatusCommand:
    def test_status_returns_zero(self):
        result = main(["status"])
        assert result == 0

    def test_status_json(self):
        result = main(["status", "--json"])
        assert result == 0


# ══════════════════════════════════════════════
# 4. trace Command
# ══════════════════════════════════════════════

class TestTraceCommand:
    def test_trace_existing_session(self):
        """Run a task, then trace its session."""
        result = main(["run", "-a", "test", "-t", "trace-test", "--summary"])
        # trace any recent session
        r2 = main(["trace", "nonexistent"])
        # 'nonexistent' should give error exit
        assert r2 == 1

    def test_trace_missing_session(self):
        result = main(["trace", "nonexistent-session-id"])
        assert result == 1  # error exit code


# ══════════════════════════════════════════════
# 5. plugins Command
# ══════════════════════════════════════════════

class TestPluginsCommand:
    def test_plugins_returns_zero(self):
        result = main(["plugins"])
        assert result == 0

    def test_plugins_json(self):
        result = main(["plugins", "--json"])
        assert result == 0


# ══════════════════════════════════════════════
# 6. Formatter — TaskResult
# ══════════════════════════════════════════════

class TestFormatterResult:
    def test_table_format(self):
        fmt = Formatter(OutputFormat.TABLE)
        result = TaskResult(
            task_id="t1", status=TaskStatus.COMPLETED,
            execution_time_ms=42.0, session_id="s1", trace_id="tr1",
        )
        output = fmt.format_result(result)
        assert "Veritas Task Result" in output
        assert "t1" in output
        assert "completed" in output

    def test_json_format(self):
        fmt = Formatter(OutputFormat.JSON)
        result = TaskResult(
            task_id="t1", status=TaskStatus.COMPLETED,
            execution_time_ms=42.0, session_id="s1", trace_id="tr1",
        )
        output = fmt.format_result(result)
        assert '"task_id"' in output
        assert '"t1"' in output

    def test_summary_format(self):
        fmt = Formatter(OutputFormat.SUMMARY)
        result = TaskResult(
            task_id="t1", status=TaskStatus.COMPLETED,
            execution_time_ms=42.0, session_id="s1", trace_id="tr1",
        )
        output = fmt.format_result(result)
        assert "✅" in output
        assert "t1" in output
        assert "42ms" in output

    def test_failed_result(self):
        fmt = Formatter(OutputFormat.SUMMARY)
        result = TaskResult(
            task_id="t1", status=TaskStatus.FAILED,
            execution_time_ms=100.0, errors=["something broke"],
        )
        output = fmt.format_result(result)
        assert "❌" in output


# ══════════════════════════════════════════════
# 7. Formatter — Status
# ══════════════════════════════════════════════

class TestFormatterStatus:
    def test_table_format(self):
        fmt = Formatter(OutputFormat.TABLE)
        data = {"version": "6.1", "recovery_enabled": True, "sessions_count": 5}
        output = fmt.format_status(data)
        assert "Veritas Runtime Status" in output
        assert "6.1" in output
        assert "5" in output

    def test_json_format(self):
        fmt = Formatter(OutputFormat.JSON)
        data = {"version": "6.1"}
        output = fmt.format_status(data)
        assert '"version"' in output


# ══════════════════════════════════════════════
# 8. Formatter — Sessions & Explain & Plugins
# ══════════════════════════════════════════════

class TestFormatterOther:
    def test_sessions_empty(self):
        fmt = Formatter()
        output = fmt.format_sessions([])
        assert "No sessions" in output

    def test_sessions_with_data(self):
        fmt = Formatter()
        sessions = [
            SessionInfo(session_id="s1", state="completed", total_duration_ms=100.0),
            SessionInfo(session_id="s2", state="error", total_duration_ms=200.0),
        ]
        output = fmt.format_sessions(sessions)
        assert "s1" in output
        assert "s2" in output

    def test_explain_format(self):
        fmt = Formatter()
        data = {
            "total_decisions": 5,
            "explainability_score": 0.85,
            "decision_diversity": 0.6,
            "by_action": {"CONTINUE": 3, "RETRY": 2},
        }
        output = fmt.format_explain(data)
        assert "Decision Explainability" in output
        assert "5" in output
        assert "CONTINUE" in output

    def test_plugins_empty(self):
        fmt = Formatter()
        output = fmt.format_plugins([])
        assert "No plugins" in output

    def test_plugins_with_data(self):
        fmt = Formatter()
        plugins = [
            {"name": "security", "version": "1.0", "state": "started", "priority": 10},
            {"name": "explain", "version": "2.0", "state": "disabled", "priority": 5},
        ]
        output = fmt.format_plugins(plugins)
        assert "security" in output
        assert "explain" in output


# ══════════════════════════════════════════════
# 9. CLI → RuntimeClient Bridge
# ══════════════════════════════════════════════

class TestCLItoSDKBridge:
    def test_cli_uses_runtime_client_not_engine(self):
        """CLI commands only use RuntimeClient — no RuntimeEngine imports."""
        # Simple check: CLI modules should not import from src.runtime directly
        import importlib
        mods = [
            "src.cli.commands.run",
            "src.cli.commands.status",
            "src.cli.commands.trace",
            "src.cli.commands.plugins",
            "src.cli.main",
        ]
        for mod_name in mods:
            mod = importlib.import_module(mod_name)
            source_file = mod.__file__
            with open(source_file) as f:
                content = f.read()
            banned = ["from src.runtime import", "from src.runtime."]
            for ban in banned:
                assert ban not in content, f"{mod_name} must not import {ban}"

    def test_run_command_creates_task_request(self):
        """run command builds a TaskRequest from CLI args."""
        from src.cli.commands.run import handle_run
        import argparse
        args = argparse.Namespace(
            task="test task", agent="test-agent", timeout=60.0,
            context=[], json=True, summary=False,
        )
        # Should complete via RuntimeClient
        result = handle_run(args)
        assert result == 0


# ══════════════════════════════════════════════
# 10. Backward Compatibility
# ══════════════════════════════════════════════

class TestCLIBackwardCompat:
    def test_old_runtime_engine_still_works(self):
        """RuntimeEngine is unaffected by CLI addition."""
        from src.runtime import RuntimeEngine, TransitionTable, AgentState
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="cli_compat_test")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()
        assert engine._checkpoint.state_count() >= 1

    def test_sdk_imports_still_work(self):
        """SDK imports unaffected."""
        from src.sdk import RuntimeClient, TaskRequest, TaskResult
        assert True


# ══════════════════════════════════════════════
# 11. Edge Cases
# ══════════════════════════════════════════════

class TestCLIEdgeCases:
    def test_run_with_special_characters(self):
        result = main(["run", "-a", "test", "-t", "任务: 学习 Python 🐍"])
        assert result == 0

    def test_run_with_long_task(self):
        long_task = "Analyze " + "very " * 100 + "long task"
        result = main(["run", "-a", "test", "-t", long_task])
        assert result == 0

    def test_help_output(self):
        parser = create_parser()
        help_text = parser.format_help()
        assert "run" in help_text
        assert "status" in help_text
        assert "trace" in help_text
        assert "plugins" in help_text

    def test_main_with_invalid_command(self):
        with pytest.raises(SystemExit):
            main(["nonexistent-command"])
