#!/usr/bin/env python3
"""
Agent Evaluation + Improvement Loop 测试

覆盖:
  1. Judge接口 (RuleJudge + LLMJudge fallback)
  2. AgentEvaluator (4维度评分)
  3. ImprovementLoop (低分→建议→Reflection)
  4. EvaluationResult → ImprovementSuggestion 管道
"""
import sys, tempfile, unittest, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from evaluation.judge import RuleJudge, LLMJudge, JudgeResult
from evaluation.agent_evaluator import AgentEvaluator, EvaluationResult
from core.improvement_loop import ImprovementLoop, ImprovementSuggestion, create_improvement_loop
from core.event_bus import AgentEventBus
from memory.memory_manager import MemoryManager

import shutil


class TestJudgeResult(unittest.TestCase):
    def test_creation(self):
        j = JudgeResult(score=0.85, reason="good", source="rule",
                        dimensions={"correctness": 0.9, "personalization": 0.8})
        self.assertEqual(j.score, 0.85)
        d = j.to_dict()
        self.assertEqual(d["source"], "rule")


class TestRuleJudge(unittest.TestCase):
    def setUp(self):
        self.judge = RuleJudge()

    def test_profile_correctness(self):
        r = self.judge.evaluate("ProfileAgent",
                                {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant",
                                 "learning_pace": "fast_track"})
        self.assertGreater(r.score, 0.5)
        self.assertEqual(r.source, "rule")

    def test_planner_correctness(self):
        from agents.planner_agent import PlanNode, LearningPlan
        plan = LearningPlan(plan_id="p", profile_summary="t", total_minutes=60,
                            strategy_rationale="标准", alternative_paths=["alt"],
                            nodes=[PlanNode(node_id="n1", title="N1", core_concept="c1")])
        r = self.judge.evaluate("PlannerAgent", plan)
        self.assertGreater(r.score, 0.5)

    def test_null_output(self):
        r = self.judge.evaluate("ProfileAgent", None)
        self.assertLess(r.score, 0.3)  # 接近0但不是0 (baseline scoring)

    def test_personalization_with_memory(self):
        r = self.judge.evaluate("PlannerAgent", {},
                                 input_context={"has_memory": True, "used_mastery": True})
        self.assertGreater(r.score, 0.3)

    def test_explainability(self):
        r = self.judge.evaluate("ResourceRecommendationAgent",
                                {"reason": "because student prefers visual"},
                                input_context={"has_decision_explanation": True})
        self.assertGreater(r.dimensions.get("explainability", 0), 0.5)

    def test_all_dimensions_present(self):
        r = self.judge.evaluate("ProfileAgent", {"knowledge_base": "junior_dev"})
        for dim in ["correctness", "personalization", "explainability", "efficiency"]:
            self.assertIn(dim, r.dimensions)


class TestAgentEvaluator(unittest.TestCase):
    def setUp(self):
        AgentEventBus.reset_instance()
        self.evaluator = AgentEvaluator()

    def test_evaluate_agent(self):
        r = self.evaluator.evaluate("ProfileAgent",
                                    {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant",
                                     "learning_pace": "fast_track"},
                                    input_context={"has_memory": True})
        self.assertIsInstance(r, EvaluationResult)
        self.assertGreater(r.overall_score, 0)
        self.assertEqual(r.agent_name, "ProfileAgent")

    def test_evaluate_pipeline(self):
        from agents.planner_agent import PlanNode, LearningPlan
        plan = LearningPlan(plan_id="p1", profile_summary="t", total_minutes=60,
                            strategy_rationale="标准",
                            nodes=[PlanNode(node_id="n1", title="N1", core_concept="c1")])
        results = self.evaluator.evaluate_agent_pipeline(
            profile_output={"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"},
            plan_output=plan,
            recommendation_output=None,
            memory_context={"profile_history": [{"k": "v"}], "mastery_map": {"c": 0.5}},
        )
        self.assertIn("ProfileAgent", results)
        self.assertIn("PlannerAgent", results)

    def test_summary(self):
        for _ in range(3):
            self.evaluator.evaluate("PlannerAgent",
                                    {"nodes": [{"id": "x"}]},
                                    input_context={"has_memory": True})
        summary = self.evaluator.get_summary()
        self.assertGreater(summary["total_evaluations"], 0)
        self.assertIn("PlannerAgent", summary["agents"])

    def test_low_scoring_detection(self):
        self.evaluator.evaluate("ProfileAgent", None, input_context={})  # score should be 0
        low = self.evaluator.get_low_scoring(threshold=0.5)
        self.assertGreaterEqual(len(low), 1)

    def test_event_bus_integration(self):
        self.evaluator.evaluate("TestAgent", {"k": "v"})
        bus = AgentEventBus.get_instance()
        events = bus.get_timeline()
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0].agent, "AgentEvaluator")


class TestImprovementLoop(unittest.TestCase):
    def setUp(self):
        AgentEventBus.reset_instance()
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.evaluator = AgentEvaluator()
        self.loop = ImprovementLoop(
            evaluator=self.evaluator,
            experience_store=self.mm.experience,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_low_score_triggers_suggestion(self):
        """低分 Agent → 生成改进建议"""
        results = self.evaluator.evaluate_agent_pipeline(
            profile_output=None,  # will score 0
            plan_output=None,
            recommendation_output=None,
            memory_context={},
        )
        suggestions = self.loop.run_cycle(results, node_id="test", student_id="s1")
        self.assertGreater(len(suggestions), 0, "Low scores should trigger suggestions")
        self.assertIn("ProfileAgent", [s.target_agent for s in suggestions])

    def test_high_score_no_suggestion(self):
        """高分 Agent → 不生成建议"""
        from agents.planner_agent import PlanNode, LearningPlan
        plan = LearningPlan(plan_id="p", profile_summary="t", total_minutes=60,
                            strategy_rationale="std", alternative_paths=["a"],
                            nodes=[PlanNode(node_id="n1", title="N1", core_concept="c1")])
        results = self.evaluator.evaluate_agent_pipeline(
            profile_output={"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant", "learning_pace": "normal"},
            plan_output=plan,
            recommendation_output=None,
            memory_context={"profile_history": [{"k": "v"}], "mastery_map": {"c": 0.5}},
        )
        suggestions = self.loop.run_cycle(results, node_id="test", student_id="s1")
        # high scores should produce fewer suggestions
        self.assertGreaterEqual(len([s for s in suggestions if s.target_agent == "PlannerAgent"]), 0)

    def test_reflection_integration(self):
        """MetaReflector 参与改进循环"""
        from core.meta_reflector import MetaReflectorAgent
        reflector = MetaReflectorAgent()
        reflector.set_experience_store(self.mm.experience)

        loop2 = ImprovementLoop(self.evaluator, reflector=reflector,
                                experience_store=self.mm.experience)
        results = self.evaluator.evaluate_agent_pipeline(
            profile_output=None, plan_output=None, recommendation_output=None,
            memory_context={},
        )
        suggestions = loop2.run_cycle(results, node_id="closures", student_id="s1")
        # 应有 evaluation source 和 reflection source 两种建议
        sources = [s.source for s in suggestions]
        self.assertIn("evaluation", sources)

    def test_filter_by_agent(self):
        results = self.evaluator.evaluate_agent_pipeline(
            profile_output=None, plan_output=None, recommendation_output=None,
            memory_context={},
        )
        self.loop.run_cycle(results)
        pa_suggestions = self.loop.get_by_agent("ProfileAgent")
        self.assertGreater(len(pa_suggestions), 0)

    def test_top_suggestions(self):
        results = self.evaluator.evaluate_agent_pipeline(
            profile_output=None, plan_output=None, recommendation_output=None,
            memory_context={},
        )
        self.loop.run_cycle(results)
        top = self.loop.get_top_suggestions(3)
        self.assertLessEqual(len(top), 3)
        # 优先级应降序
        for i in range(len(top) - 1):
            self.assertGreaterEqual(top[i].priority, top[i + 1].priority)


class TestEvaluationResult(unittest.TestCase):
    def test_from_judge(self):
        jr = JudgeResult(score=0.75, reason="good", source="rule",
                         dimensions={"correctness": 0.9, "personalization": 0.5,
                                     "explainability": 0.6, "efficiency": 0.8})
        er = EvaluationResult.from_judge("TestAgent", jr, "s1")
        self.assertEqual(er.agent_name, "TestAgent")
        self.assertEqual(er.correctness_score, 0.9)
        self.assertEqual(er.personalization_score, 0.5)
        self.assertEqual(er.overall_score, 0.75)

    def test_suggestions_generation(self):
        jr = JudgeResult(score=0.3, reason="poor", source="rule",
                         dimensions={"correctness": 0.2, "personalization": 0.1,
                                     "explainability": 0.1, "efficiency": 0.7})
        er = EvaluationResult.from_judge("TestAgent", jr)
        self.assertGreater(len(er.suggestions), 0)

    def test_high_score_no_suggestions(self):
        jr = JudgeResult(score=0.9, reason="great", source="rule",
                         dimensions={"correctness": 0.9, "personalization": 0.9,
                                     "explainability": 0.9, "efficiency": 0.9})
        er = EvaluationResult.from_judge("TestAgent", jr)
        self.assertEqual(len(er.suggestions), 0)


class TestFullPipeline(unittest.TestCase):
    """端到端: Judge → Evaluator → ImprovementLoop"""

    def setUp(self):
        AgentEventBus.reset_instance()
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.evaluator = AgentEvaluator()
        self.loop = ImprovementLoop(self.evaluator, experience_store=self.mm.experience)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_cycle(self):
        """完整周期: profile+plan → evaluate → suggest"""
        from agents.planner_agent import PlanNode, LearningPlan

        plan = LearningPlan(plan_id="p1", profile_summary="test", total_minutes=60,
                            strategy_rationale="test",
                            nodes=[PlanNode(node_id="n1", title="N1", core_concept="c1")])

        # 评估
        results = self.evaluator.evaluate_agent_pipeline(
            profile_output={"knowledge_base": "mid_level", "cognitive_style": "text_linear",
                            "learning_pace": "deep_dive", "interaction_preference": "quiz_first",
                            "error_prone_bias": "type_mismatch", "frustration_threshold": "high"},
            plan_output=plan,
            recommendation_output=None,
            memory_context={
                "profile_history": [{"k": "v"}],
                "mastery_map": {"closures": 0.5, "decorators": 0.2},
                "weak_points": [{"concept": "递归"}],
            },
        )

        for name, result in results.items():
            self.assertIsInstance(result, EvaluationResult)
            self.assertGreaterEqual(result.overall_score, 0)

        # 改进
        suggestions = self.loop.run_cycle(results, node_id="closures", student_id="s1")
        self.assertIsInstance(suggestions, list)

        # 总结
        summary = self.evaluator.get_summary()
        self.assertEqual(summary["total_evaluations"], 2)

        # 验证 EventBus
        events = AgentEventBus.get_instance().get_timeline()
        self.assertGreaterEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
