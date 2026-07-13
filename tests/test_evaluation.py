#!/usr/bin/env python3
"""Evaluation Pipeline 测试"""
import sys, json, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from evaluation.evaluator import (
    EvaluationCase, EvaluationReport, EvaluationRunner,
    RuleBasedJudge, LLMJudge, generate_benchmark_dataset,
)
from agents.profile_agent import ProfileAgent
from agents.planner_agent import PlannerAgent
from agents.resource_recommendation_agent import ResourceRecommendationAgent
from memory.memory_manager import MemoryManager

import shutil


class TestEvaluationDataModels(unittest.TestCase):
    def test_case(self):
        c = EvaluationCase(
            case_id="test_01",
            profile={"knowledge_base": "junior_dev"},
            history="零基础小白",
            expected_behavior={"should_detect": "junior"},
            category="beginner",
        )
        d = c.to_dict()
        c2 = EvaluationCase.from_dict(d)
        self.assertEqual(c2.case_id, "test_01")

    def test_report(self):
        r = EvaluationReport(
            report_id="r1",
            total_cases=10, passed=8, failed=2,
            profile_accuracy=0.85, plan_quality=0.9,
            scores=[{"case_id": "c1", "profile_accuracy": 0.8}],
        )
        self.assertEqual(r.total_cases, 10)
        j = r.to_json()
        self.assertIn("profile_accuracy", j)


class TestRuleBasedJudge(unittest.TestCase):
    def setUp(self):
        self.judge = RuleBasedJudge()

    def test_perfect_profile(self):
        p = {
            "knowledge_base": "junior_dev", "cognitive_style": "visual_dominant",
            "error_prone_bias": "magic_syntax_blind",
            "learning_pace": "fast_track", "interaction_preference": "code_sandbox",
            "frustration_threshold": "low",
        }
        s = self.judge.score_profile(p, p)
        self.assertGreater(s, 0.5)

    def test_empty_profile(self):
        self.assertEqual(self.judge.score_profile({}, {"k": "v"}), 0.0)

    def test_invalid_values(self):
        p = {"knowledge_base": "invalid_value"}
        s = self.judge.score_profile(p, {"knowledge_base": "junior_dev"})
        self.assertLess(s, 1.0)

    def test_score_plan_good(self):
        from agents.planner_agent import PlanNode, LearningPlan
        plan = LearningPlan(
            plan_id="p1", profile_summary="test", total_minutes=60,
            strategy_rationale="标准路径",
            alternative_paths=["alt1"],
            nodes=[PlanNode(node_id="n1", title="N1", core_concept="c1")],
        )
        s = self.judge.score_plan(plan)
        self.assertGreater(s, 0.5)

    def test_score_plan_none(self):
        self.assertEqual(self.judge.score_plan(None), 0.0)

    def test_score_recommendations(self):
        from agents.resource_recommendation_agent import (
            ResourceRecommendationAgent, PersonalizedResourcePlan,
        )
        agent = ResourceRecommendationAgent()
        # Just test the scoring, not the actual recommendation
        rec_plan = PersonalizedResourcePlan(
            student_id="s1", today_goal="test", reasoning="test",
        )
        s = self.judge.score_recommendations(rec_plan)
        self.assertGreater(s, 0.3)


class TestEvaluationRunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.runner = EvaluationRunner(
            profile_agent=ProfileAgent(),
            planner=PlannerAgent(),
            recommender=ResourceRecommendationAgent(),
            memory_manager=self.mm,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run_mini_benchmark(self):
        """用 mini dataset 验证评估管道"""
        # 创建 mini 数据集
        mini_path = Path(self.tmp) / "mini_benchmark.json"
        generate_benchmark_dataset(str(mini_path))

        # 只跑前 5 个 cases
        data = json.loads(mini_path.read_text())
        mini_data = {"name": "mini", "total_cases": 5, "cases": data["cases"][:5]}
        mini_path.write_text(json.dumps(mini_data, ensure_ascii=False))

        report = self.runner.run_benchmark(str(mini_path))
        self.assertEqual(report.total_cases, 5)
        self.assertGreaterEqual(report.passed, 3)  # 至少 3 个通过
        self.assertGreater(report.profile_accuracy, 0.0)
        self.assertGreaterEqual(report.plan_quality, 0.0)

    def test_edge_cases(self):
        """Edge cases 不崩溃"""
        mini_path = Path(self.tmp) / "edge.json"
        data = json.loads(Path("datasets/students/benchmark.json").read_text())
        edge_cases = [c for c in data["cases"] if c["category"] == "edge"]
        mini = {"name": "edge", "total_cases": len(edge_cases), "cases": edge_cases}
        mini_path.write_text(json.dumps(mini, ensure_ascii=False))

        report = self.runner.run_benchmark(str(mini_path))
        self.assertEqual(report.total_cases, 2)
        self.assertEqual(report.failed, 0, f"Edge cases should not fail: {report.errors}")


class TestBenchmarkDataset(unittest.TestCase):
    def test_dataset_structure(self):
        data = json.loads(Path("datasets/students/benchmark.json").read_text())
        self.assertEqual(data["total_cases"], 20)
        cases = data["cases"]
        self.assertEqual(len(cases), 20)

        # 分类检查
        cats = [c["category"] for c in cases]
        self.assertIn("beginner", cats)
        self.assertIn("intermediate", cats)
        self.assertIn("advanced", cats)
        self.assertIn("edge", cats)

    def test_each_case_has_required_fields(self):
        data = json.loads(Path("datasets/students/benchmark.json").read_text())
        for c in data["cases"]:
            self.assertIn("case_id", c)
            self.assertIn("profile", c)
            self.assertIn("history", c)  # edge case may be empty
            self.assertIn("expected_behavior", c)


class TestFullPipeline(unittest.TestCase):
    """集成: EventBus + Evaluation + Dataset"""

    def test_event_bus_integration(self):
        from core.event_bus import AgentEventBus
        AgentEventBus.reset_instance()
        bus = AgentEventBus.get_instance()
        bus.start_session("eval_test")

        pa = ProfileAgent()
        pa.extract("零基础小白")

        events = bus.get_timeline()
        self.assertGreaterEqual(len(events), 1)

    def test_pipeline_with_dataset(self):
        """ProfileAgent + Planner + Recommender 在 benchmark 上不崩溃"""
        pa = ProfileAgent()
        planner = PlannerAgent()
        recommender = ResourceRecommendationAgent()

        data = json.loads(Path("datasets/students/benchmark.json").read_text())
        for case in data["cases"][:5]:  # 只测前5个
            try:
                result = pa.extract(case["history"])
                self.assertIsNotNone(result.profile)
                plan = planner.plan(result.profile, course_id="python_advanced")
                self.assertGreater(len(plan.nodes), 0)
            except Exception as e:
                self.fail(f"Case {case['case_id']} failed: {e}")


if __name__ == "__main__":
    unittest.main()
