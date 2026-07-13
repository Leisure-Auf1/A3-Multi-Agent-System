#!/usr/bin/env python3
"""AgentEventBus 测试"""
import sys, json, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.event_bus import AgentEventBus, AgentEvent, trace_agent


class TestAgentEvent(unittest.TestCase):
    def test_create(self):
        e = AgentEvent(agent="Test", action="run", input_summary="in", output_summary="out")
        self.assertEqual(e.agent, "Test")
        self.assertEqual(e.status, "success")

    def test_to_dict(self):
        e = AgentEvent(agent="A", action="B", duration_ms=12.5, metadata={"k": "v"})
        d = e.to_dict()
        self.assertEqual(d["agent"], "A")
        self.assertEqual(d["duration_ms"], 12.5)
        self.assertEqual(d["metadata"]["k"], "v")


class TestAgentEventBus(unittest.TestCase):
    def setUp(self):
        AgentEventBus.reset_instance()
        self.bus = AgentEventBus.get_instance()

    def test_singleton(self):
        b2 = AgentEventBus.get_instance()
        self.assertIs(self.bus, b2)

    def test_emit_and_timeline(self):
        self.bus.start_session("s1")
        self.bus.emit("Agent1", "action1", input_summary="in", output_summary="out")
        self.bus.emit("Agent2", "action2")
        events = self.bus.get_timeline()
        self.assertEqual(len(events), 3)  # session_start + 2
        self.assertEqual(events[1].agent, "Agent1")
        self.assertEqual(events[2].agent, "Agent2")

    def test_json_export(self):
        self.bus.emit("A", "run")
        j = self.bus.to_json()
        data = json.loads(j)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["agent"], "A")

    def test_clear(self):
        self.bus.emit("A", "run")
        self.bus.clear()
        self.assertEqual(self.bus.event_count, 0)

    def test_latest_event(self):
        self.assertIsNone(self.bus.latest_event)
        self.bus.emit("A", "run")
        self.assertIsNotNone(self.bus.latest_event)
        self.assertEqual(self.bus.latest_event.agent, "A")

    def test_error_status(self):
        self.bus.emit("A", "fail", status="error")
        self.assertEqual(self.bus.latest_event.status, "error")

    def test_input_truncation(self):
        self.bus.emit("A", "test", input_summary="x" * 300)
        self.assertLessEqual(len(self.bus.latest_event.input_summary), 200)


class TestTraceDecorator(unittest.TestCase):
    def setUp(self):
        AgentEventBus.reset_instance()
        self.bus = AgentEventBus.get_instance()

    def test_trace_success(self):
        @trace_agent("MyAgent", "my_action")
        def my_func(x):
            return x * 2

        result = my_func(5)
        self.assertEqual(result, 10)
        self.assertEqual(self.bus.event_count, 1)
        self.assertEqual(self.bus.latest_event.agent, "MyAgent")
        self.assertEqual(self.bus.latest_event.action, "my_action")
        self.assertGreaterEqual(self.bus.latest_event.duration_ms, 0)

    def test_trace_error(self):
        @trace_agent("BrokenAgent")
        def broken():
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            broken()
        self.assertEqual(self.bus.latest_event.status, "error")

    def test_trace_default_action_name(self):
        @trace_agent("AgentX")
        def hello_world():
            return 42

        hello_world()
        self.assertEqual(self.bus.latest_event.action, "hello_world")


if __name__ == "__main__":
    unittest.main()
