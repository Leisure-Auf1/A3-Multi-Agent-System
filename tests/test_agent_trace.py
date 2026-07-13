#!/usr/bin/env python3
"""
Agent Trace + Decision Explanation + Self Reflection 测试

覆盖:
  1. AgentTraceCollector — 监听EventBus, 持久化, 查询
  2. DecisionExplainer — Profile/Planner/Resource 解释生成
  3. MetaReflector.reflect() — ReflectionResult + ExperienceMemory 写入
  4. ReflectionResult — 数据模型
"""
import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.event_bus import AgentEventBus
from core.agent_trace import AgentTraceCollector, TraceEvent
from core.decision_explainer import (
    DecisionExplainer, DecisionExplanation, ReflectionResult,
)
from core.meta_reflector import MetaReflectorAgent
from memory.memory_manager import MemoryManager

import shutil, json


class TestTraceEvent(unittest.TestCase):
    def test_creation(self):
        t = TraceEvent(
            timestamp="t", session_id="s1", agent_name="A", action="run",
            reasoning_type="rule", latency_ms=12.5,
        )
        self.assertEqual(t.agent_name, "A")
        self.assertEqual(t.reasoning_type, "rule")

    def test_to_dict(self):
        t = TraceEvent(timestamp="t", session_id="s1", agent_name="A", action="run",
                       decision_context={"k": "v"})
        d = t.to_dict()
        self.assertEqual(d["decision_context"]["k"], "v")


class TestAgentTraceCollector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.collector = AgentTraceCollector(storage_dir=self.tmp)
        AgentEventBus.reset_instance()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_record_and_query(self):
        self.collector.new_session("s1")
        self.collector.record("ProfileAgent", "extract",
                              input_summary="student text",
                              reasoning_type="rule", latency_ms=5.0)
        self.collector.record("PlannerAgent", "plan",
                              input_summary="course=adv",
                              reasoning_type="heuristic")

        # query by agent
        results = self.collector.query(agent_name="ProfileAgent")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].reasoning_type, "rule")

        # query by session (from disk)
        self.collector.save()
        loaded = self.collector.load("s1")
        self.assertEqual(len(loaded), 2)

    def test_sync_from_bus(self):
        self.collector.new_session("s2")
        self.collector.set_reasoning_type("ProfileAgent", "rule")
        self.collector.set_reasoning_type("PlannerAgent", "heuristic")

        bus = AgentEventBus.get_instance()
        bus.start_session("s2")
        bus.emit("ProfileAgent", "extract", input_summary="test", output_summary="junior")
        bus.emit("PlannerAgent", "plan", input_summary="adv", output_summary="4 nodes")

        count = self.collector.sync_from_bus()
        self.assertEqual(count, 3)  # session_start + extract + plan

        # 检查 reasoning_type 映射
        traces = self.collector.get_timeline()
        profile_trace = [t for t in traces if t.agent_name == "ProfileAgent"][0]
        self.assertEqual(profile_trace.reasoning_type, "rule")

    def test_save_and_load(self):
        self.collector.new_session("s3")
        self.collector.record("A", "run", reasoning_type="llm")
        self.collector.save()

        loaded = self.collector.load("s3")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].reasoning_type, "llm")

    def test_stats(self):
        self.collector.new_session("s4")
        self.collector.record("A", "run", status="success")
        self.collector.record("A", "fail", status="error")
        stats = self.collector.stats()
        self.assertEqual(stats["total_events"], 2)
        self.assertEqual(stats["agents"]["A"]["errors"], 1)

    def test_query_by_status(self):
        self.collector.new_session("s5")
        self.collector.record("A", "run", status="error")
        self.collector.record("B", "run", status="success")
        errors = self.collector.query(status="error")
        self.assertEqual(len(errors), 1)


class TestDecisionExplainer(unittest.TestCase):
    def setUp(self):
        self.explainer = DecisionExplainer()

    def test_explain_profile(self):
        profile = {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "learning_pace": "fast_track",
        }
        explanations = self.explainer.explain_profile_extraction(
            profile, student_text="零基础小白看视频学",
        )
        self.assertGreaterEqual(len(explanations), 3)
        self.assertIn("knowledge_base", explanations[0].action)
        self.assertGreater(explanations[0].confidence, 0.5)

    def test_explain_skip_decision(self):
        exp = self.explainer.explain_plan_decision(
            mastery_map={"closures": 0.95},
            node_id="closures", node_title="闭包",
            action="skip",
        )
        self.assertIn("已掌握", exp.reason)
        self.assertIn("0.95", exp.evidence[0])

    def test_explain_boost_decision(self):
        exp = self.explainer.explain_plan_decision(
            mastery_map={"closures": 0.15},
            node_id="closures", node_title="闭包",
            action="boost", detail="weak_points: 递归",
        )
        self.assertIn("薄弱", exp.reason)

    def test_explain_recommendation(self):
        exp = self.explainer.explain_recommendation(
            resource_type="visual",
            resource_title="闭包图解",
            profile={"cognitive_style": "visual_dominant", "interaction_preference": "code_sandbox"},
            mastery_map={"closures": 0.2},
            concept="closures",
        )
        self.assertIn("视觉学习偏好", exp.reason)
        self.assertIn("薄弱概念", exp.reason)

    def test_markdown_output(self):
        exp = self.explainer.explain_plan_decision(
            {"closures": 0.95}, "closures", "闭包", "skip",
        )
        md = exp.to_markdown()
        self.assertIn("PlannerAgent", md)
        self.assertIn("已掌握", md)

    def test_memory_decision(self):
        exp = self.explainer.explain_memory_decision(
            "PlannerAgent", "mastery", 0.5, 0.9,
        )
        self.assertIn("0.9", exp.decision)


class TestReflectionResult(unittest.TestCase):
    def test_creation(self):
        r = ReflectionResult(
            mistake="学生连续3次无法完成递归题",
            root_cause="concept misunderstanding",
            improvement="add visualization",
            future_strategy="use diagrams for recursion",
            severity="HIGH",
            concept="递归",
            node_id="recursion",
            affected_profiles=["visual_learner"],
        )
        d = r.to_dict()
        self.assertEqual(d["mistake"], r.mistake)
        self.assertEqual(d["severity"], "HIGH")

    def test_to_experience_entry(self):
        r = ReflectionResult(
            mistake="递归题连续失败",
            root_cause="缺少栈可视化",
            improvement="增加ASCII调用栈图",
            future_strategy="对所有递归节点使用图解",
            severity="CRITICAL",
            concept="递归",
            node_id="recursion",
        )
        entry = r.to_experience_entry()
        self.assertIn("递归题连续失败", entry["problem"])
        self.assertIn("缺少栈可视化", entry["cause"])
        self.assertIn("metareflector", entry["source"])


class TestMetaReflectorReflection(unittest.TestCase):
    """MetaReflector.reflect() 集成测试"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.reflector = MetaReflectorAgent()
        self.reflector.set_experience_store(self.mm.experience)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reflect_multi_failures(self):
        """连续3次失败 → 概念误解分析"""
        result = self.reflector.reflect(
            node_id="closures",
            failure_context={
                "mistake": "学生连续3次无法理解闭包",
                "student_id": "s1",
                "scores": [30, 40, 35],
                "attempts": 3,
            },
            concept="闭包",
            severity="HIGH",
        )
        self.assertIsNotNone(result)
        self.assertIn("概念误解", result.root_cause)
        self.assertIn("可视化讲解", result.improvement)

        # 验证写入 ExperienceMemory
        stats = self.mm.get_experience_stats()
        self.assertGreaterEqual(stats["total_lessons"], 1)

    def test_reflect_two_failures(self):
        """2次失败 → 缺少前置知识"""
        result = self.reflector.reflect(
            node_id="decorators",
            failure_context={"mistake": "装饰器失败", "attempts": 2},
            severity="MEDIUM",
        )
        self.assertIn("前置知识", result.root_cause)

    def test_reflect_single_failure(self):
        """1次失败 → 偶发错误"""
        result = self.reflector.reflect(
            node_id="functions",
            failure_context={"mistake": "函数调用失败", "attempts": 1},
        )
        self.assertIn("偶发错误", result.root_cause)

    def test_recall_reflections(self):
        """召回历史反思"""
        self.reflector.reflect("closures",
                               {"mistake": "闭包失败", "attempts": 3},
                               concept="闭包")
        self.reflector.reflect("closures",
                               {"mistake": "闭包再次失败", "attempts": 3},
                               concept="闭包")

        reflections = self.reflector.recall_reflections(concept="闭包", limit=2)
        self.assertGreaterEqual(len(reflections), 1)
        self.assertIn("mistake", reflections[0])


if __name__ == "__main__":
    unittest.main()
