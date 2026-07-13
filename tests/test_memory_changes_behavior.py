#!/usr/bin/env python3
"""
Memory 真实集成验证 — 证明 Memory 改变了 Agent 行为 (不只是存 JSON)
"""
import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from memory.memory_manager import MemoryManager
from memory.student_memory import StudentMemory
from agents.profile_agent import ProfileAgent
from agents.planner_agent import PlannerAgent
from core.agent_router import DynamicProfile
from core.meta_reflector import MetaReflectorAgent
from core.contracts import FailurePatternLesson

import shutil


class TestMemoryChangesProfileBehavior(unittest.TestCase):
    """ProfileAgent: 有 Memory vs 无 Memory → knowledge_base 不同"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.agent = ProfileAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_with_memory_promotes_knowledge(self):
        """第2次来访 + 进步信号 → knowledge_base 升级"""
        # 第1次: 小白
        r1 = self.agent.extract("小白零基础")
        self.assertEqual(r1.profile.knowledge_base, "junior_dev")
        self.mm.update_student_memory("s1", profile=r1.profile.to_dict())

        # 第2次: 有进步
        mem = self.mm.get_student_memory("s1")
        r2 = self.agent.extract_with_memory("学会了一些基础语法，会写简单的函数了", mem)

        # 无 Memory 时会是 junior_dev (因为没"零基础"关键词)
        baseline = self.agent.extract("学会了一些基础语法，会写简单的函数了")
        self.assertEqual(baseline.profile.knowledge_base, "junior_dev",
                         "无 Memory 基准应为 junior_dev")

        # 有 Memory 看到上次是 junior + 本次有进步 → 应该升级
        self.assertEqual(r2.profile.knowledge_base, "mid_level",
                         f"Memory 应促进 knowledge_base 升级, got: {r2.profile.knowledge_base}")

    def test_with_memory_frustration_evolves(self):
        """历史评分高 → frustration_threshold 从 low 升为 medium"""
        r1 = self.agent.extract("小白容易放弃")
        self.assertEqual(r1.profile.frustration_threshold, "low")
        self.mm.update_student_memory("s2", profile=r1.profile.to_dict())

        # 注入高分历史
        for i in range(5):
            self.mm.update_student_memory("s2", feedback={"node_id": f"n{i}", "score": 85})

        mem = self.mm.get_student_memory("s2")
        r2 = self.agent.extract_with_memory("继续学习", mem)
        self.assertEqual(r2.profile.frustration_threshold, "medium")

    def test_without_memory_unchanged(self):
        """无 Memory → behavior 不变"""
        baseline = self.agent.extract("小白零基础")
        result = self.agent.extract_with_memory("小白零基础", None)
        self.assertEqual(result.profile.knowledge_base, baseline.profile.knowledge_base)
        self.assertEqual(result.source, "rule")  # 无 memory → 回退到普通 extract


class TestMemoryChangesPlanBehavior(unittest.TestCase):
    """PlannerAgent: 有 Memory vs 无 Memory → 路径不同"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.planner = PlannerAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_mastered_node_is_skipped(self):
        """已掌握节点 → 从路径中移除"""
        profile = DynamicProfile(knowledge_base="mid_level", learning_pace="normal")

        # 无 Memory 的 baseline
        base_plan = self.planner.plan(profile, course_id="python_advanced")
        base_ids = [n.node_id for n in base_plan.nodes]
        self.assertIn("closures", base_ids, "baseline should include closures")

        # 注入 mastery: closures=0.95 (已掌握, EMA后≈0.72→需要两次更新)
        self.mm.update_student_memory("s1", mastery_updates={"closures": 0.95})
        self.mm.update_student_memory("s1", mastery_updates={"closures": 0.95})
        mem = self.mm.get_student_memory("s1")

        # 有 Memory 的 plan
        mem_plan = self.planner.plan(profile, course_id="python_advanced", student_memory=mem)
        mem_ids = [n.node_id for n in mem_plan.nodes]
        self.assertNotIn("closures", mem_ids,
                         f"closures(0.9) should be SKIPPED, got nodes: {mem_ids}")
        self.assertLess(len(mem_plan.nodes), len(base_plan.nodes),
                        "有 Memory 应跳过已掌握节点")

    def test_weak_concept_gets_deeper_plan(self):
        """薄弱概念 → 更深 + 更多练习 + 更长时间"""
        profile = DynamicProfile(knowledge_base="junior_dev", learning_pace="normal")

        self.mm.update_student_memory("s2", mastery_updates={"closures": 0.1})
        mem = self.mm.get_student_memory("s2")
        plan = self.planner.plan(profile, course_id="python_advanced", student_memory=mem)

        # closures 应该在 path 中 (薄弱, 不能跳过)
        closures_node = next(
            (n for n in plan.nodes if n.node_id == "closures"), None
        )
        self.assertIsNotNone(closures_node, "薄弱概念不应被跳过")

        # 薄弱概念应该有更高深度 + 更多练习 + 更长时长
        self.assertGreaterEqual(closures_node.depth, 3, "薄弱 → depth >= 3")
        self.assertGreaterEqual(closures_node.exercise_count, 5, "薄弱 → exercise >= 5")

    def test_no_memory_plan_unchanged(self):
        """无 Memory → plan 不变 (backward compat)"""
        profile = DynamicProfile()
        base = self.planner.plan(profile, course_id="python_advanced")
        no_mem = self.planner.plan(profile, course_id="python_advanced", student_memory=None)
        self.assertEqual(len(base.nodes), len(no_mem.nodes))


class TestMetaReflectorWritesExperience(unittest.TestCase):
    """MetaReflector → store_lesson → 同步到 ExperienceMemory"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.reflector = MetaReflectorAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_store_lesson_syncs_to_experience(self):
        """MetaReflector store_lesson → ExperienceMemory 自动写入"""
        # 注入 ExperienceMemory
        self.reflector.set_experience_store(self.mm.experience)

        lesson = FailurePatternLesson(
            error_type="CognitiveOverload",
            problem_context="单节引入5个概念, 学生认知过载",
            root_cause_analysis="大模型低估初学者认知负荷",
            anti_pattern_code="# 10 concepts",
            golden_patch_code="# max 3 per section",
            abstract_lint_rule="每节 ≤ 3 新概念",
            node_id="closures",
            severity="CRITICAL",
        )
        self.reflector.store_lesson("closures", lesson)

        # 验证 ExperienceMemory 有同步
        exp_stats = self.mm.get_experience_stats()
        self.assertGreaterEqual(exp_stats["total_lessons"], 1)

        results = self.mm.recall_experience(node_id="closures")
        self.assertGreaterEqual(len(results), 1)

    def test_store_lesson_without_exp_store_is_safe(self):
        """无 exp_store → store_lesson 不崩溃"""
        reflector = MetaReflectorAgent()
        lesson = FailurePatternLesson(
            error_type="Test",
            problem_context="test",
            root_cause_analysis="test",
            anti_pattern_code="",
            golden_patch_code="",
            abstract_lint_rule="rule",
        )
        # 不应抛异常
        reflector.store_lesson("test", lesson)


if __name__ == "__main__":
    unittest.main()
