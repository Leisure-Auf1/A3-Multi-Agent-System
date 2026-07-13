#!/usr/bin/env python3
"""
反馈闭环测试 — FeedbackRecord + FeedbackLoop
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.contracts import FeedbackRecord
from core.feedback_loop import FeedbackLoop, create_feedback_loop
from core.user_simulation import UserSimulationAgent, STUDENT_PROFILES


class MockReflector:
    """模拟 MetaReflector"""
    def __init__(self):
        self.recall_calls = []

    def recall_lessons(self, query, n_results=3):
        self.recall_calls.append(query)
        # 返回模拟教训
        from core.contracts import FailurePatternLesson
        return [
            FailurePatternLesson(
                error_type="CognitiveOverload",
                problem_context="概念密度过高",
                root_cause_analysis="单节超过3个新概念",
                anti_pattern_code="# 10 concepts in one section",
                golden_patch_code="# max 3 concepts per section",
                abstract_lint_rule="每节 ≤ 3 新概念",
            ),
        ]


class TestFeedbackRecord(unittest.TestCase):
    """FeedbackRecord 数据模型"""

    def test_creation(self):
        r = FeedbackRecord(
            record_id="fb_node1_c1",
            node_id="node1",
            sim_score=65,
            would_drop_out=True,
            revision_required=True,
            top_issues=["概念过载", "缺少对比"],
            cycle_number=1,
        )
        self.assertEqual(r.record_id, "fb_node1_c1")
        self.assertEqual(r.sim_score, 65)
        self.assertTrue(r.would_drop_out)
        self.assertEqual(r.status, "PENDING")

    def test_to_dict_roundtrip(self):
        r = FeedbackRecord(
            record_id="fb_node1_c1",
            node_id="node1",
            sim_score=85,
            recalled_lessons=[{"error_type": "Test", "lint_rule": "rule"}],
            prompt_refinement="优化后 Prompt",
            cycle_number=2,
            effect_delta=10,
            status="APPLIED",
        )
        d = r.to_dict()
        r2 = FeedbackRecord.from_dict(d)
        self.assertEqual(r2.record_id, "fb_node1_c1")
        self.assertEqual(r2.sim_score, 85)
        self.assertEqual(len(r2.recalled_lessons), 1)
        self.assertEqual(r2.status, "APPLIED")
        self.assertEqual(r2.effect_delta, 10)

    def test_to_json(self):
        r = FeedbackRecord(
            record_id="fb_node1_c1",
            top_issues=["概念过载"],
        )
        j = r.to_json()
        self.assertIn("fb_node1_c1", j)
        self.assertIn("概念过载", j)


class TestFeedbackLoop(unittest.TestCase):
    """反馈循环编排器"""

    def setUp(self):
        self.sim = UserSimulationAgent(profile_name="python_beginner_hates_theory")
        self.reflector = MockReflector()
        self.loop = FeedbackLoop(
            sim_agent=self.sim,
            reflector=self.reflector,
            threshold=70,
        )

    def _good_lecture(self) -> str:
        return """# 闭包基础

当你定义一个函数时，它会携带它所在作用域的变量，就像一个隐形的背包。
这种「函数 + 它引用的自由变量」的组合，就是闭包。

```python
def make_adder(x: int):
    def adder(y: int) -> int:
        return x + y
    return adder

add5 = make_adder(5)
print(add5(3))  # 8
```

✅ 闭包 = 函数 + 自由变量
❌ 不是所有的嵌套函数都是闭包

闭包的核心价值在于：
- 数据封装 — 外部无法直接访问 x
- 工厂函数 — 批量生产相似功能的函数
"""

    def _poor_lecture(self) -> str:
        return """# 闭包

闭包是一个由函数及其引用的环境组合而成的实体，在计算机科学中具有重要地位。
其本质是将函数与词法作用域绑定，从而实现状态的持久化。
自由变量是闭包的核心，它使得函数能够访问定义时的上下文而非调用时的上下文。
"""

    def test_one_cycle_good_lecture(self):
        """好讲义 → 高分 → 无反射触发"""
        record = self.loop.run_one_cycle(
            lecture_text=self._good_lecture(),
            node_id="closures",
            cycle=1,
        )
        self.assertIsInstance(record, FeedbackRecord)
        self.assertGreater(record.sim_score, 0)
        # 好讲义应该不需要反射（如果 reflector 存在且评分 < threshold 才触发）
        # 这里我们只验证 record 被正确填充
        self.assertEqual(record.cycle_number, 1)

    def test_one_cycle_poor_lecture_triggers_reflection(self):
        """差讲义 → 低分 → 触发 MetaReflector"""
        record = self.loop.run_one_cycle(
            lecture_text=self._poor_lecture(),
            node_id="closures",
            target_concept="闭包",
            cycle=1,
        )
        # 如果评分 < 70, 应该触发反射
        if record.sim_score < 70:
            self.assertEqual(record.status, "OPTIMIZED")
            self.assertGreater(len(record.recalled_lessons), 0)
            self.assertTrue(record.prompt_refinement)

    def test_full_loop_no_regenerate_fn(self):
        """无重新生成函数 — 只跑一轮"""
        records = self.loop.run_full_loop(
            lecture_text=self._poor_lecture(),
            node_id="closures",
        )
        self.assertGreaterEqual(len(records), 1)

    def test_full_loop_multiple_cycles(self):
        """多轮循环 — 验证历史"""
        records = self.loop.run_full_loop(
            lecture_text=self._poor_lecture(),
            node_id="closures",
            target_concept="闭包",
            original_prompt="Generate tutorial about closures.",
        )
        self.assertGreaterEqual(len(records), 1)
        # 验证每条都有记录
        for r in records:
            self.assertIsInstance(r, FeedbackRecord)

    def test_history_access(self):
        """验证历史记录可访问"""
        self.loop.run_one_cycle(
            lecture_text=self._good_lecture(),
            node_id="closures",
            cycle=1,
        )
        h = self.loop.history
        self.assertEqual(len(h), 1)
        self.loop.clear_history()
        self.assertEqual(len(self.loop.history), 0)

    def test_no_reflector_no_reflection(self):
        """无 reflector → 不触发反射"""
        loop = FeedbackLoop(sim_agent=self.sim, reflector=None, threshold=70)
        record = loop.run_one_cycle(
            lecture_text=self._poor_lecture(),
            node_id="closures",
            cycle=1,
        )
        self.assertEqual(record.status, "PENDING")  # 无反射器 = 不优化

    def test_extract_top_issues(self):
        """问题提取"""
        sim_result = self.sim.simulate(
            lecture_text=self._poor_lecture(),
            exercise_text="# 实现 retry 装饰器\nuse *args **kwargs",
        )
        issues = self.loop._extract_top_issues(sim_result)
        self.assertIsInstance(issues, list)
        self.assertLessEqual(len(issues), 5)

    def test_factory_function(self):
        """便捷工厂"""
        loop = create_feedback_loop(self.sim, self.reflector, threshold=75)
        self.assertEqual(loop.threshold, 75)

    def test_refinement_build(self):
        """Prompt 优化构建"""
        refinement = self.loop._build_refinement(
            original_prompt="Test prompt",
            issues=["概念过载", "缺少对比"],
            lessons=[{"error_type": "CognitiveOverload", "lint_rule": "≤3 概念/节"}],
            sim_score=55,
        )
        self.assertIn("FEEDBACK LOOP REFINEMENT", refinement)
        self.assertIn("概念过载", refinement)
        self.assertIn("CognitiveOverload", refinement)


class TestIntegrationFeedbackLoop(unittest.TestCase):
    """集成测试: UserSim + FeedbackLoop + MetaReflector"""

    def test_pipeline_scoring_and_feedback(self):
        """完整: 生成 → 模拟 → 评分 → 反馈 (使用差讲义确保触发反射)"""
        sim = UserSimulationAgent(profile_name="python_beginner_hates_theory")
        reflector = MockReflector()
        loop = FeedbackLoop(sim_agent=sim, reflector=reflector, threshold=70)

        # 故意写一个很差的讲义 — 全学术定义、无代码、无对比
        lecture = """# 装饰器入门
装饰器是Python中一种设计模式，在计算机科学中，它是一个用于修改函数行为的可调用对象。
从严格意义上讲，装饰器利用了高阶函数的特性，将函数作为一等公民进行传递和包装。
其本质是闭包的一种应用场景。使用@符号可以简化装饰器的语法，这种语法被称为语法糖。"""

        records = loop.run_full_loop(
            lecture_text=lecture,
            node_id="decorators_intro",
            target_concept="装饰器",
            original_prompt="Generate a decorator tutorial.",
        )

        self.assertGreaterEqual(len(records), 1)
        first = records[0]
        self.assertIsInstance(first, FeedbackRecord)
        self.assertGreater(first.sim_score, 0)

        # 差讲义应该触发反射
        if first.sim_score < 70:
            self.assertGreater(len(reflector.recall_calls), 0)


if __name__ == "__main__":
    unittest.main()
