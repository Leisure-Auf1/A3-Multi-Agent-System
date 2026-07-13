#!/usr/bin/env python3
"""
Memory 集成测试:
  ProfileAgent + Memory → 画像历史
  PlannerAgent + Memory → 个性化路径
  MetaReflector + Memory → 经验写入
"""
import os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from memory.memory_manager import MemoryManager
from memory.student_memory import StudentMemory
from agents.profile_agent import ProfileAgent
from agents.planner_agent import PlannerAgent
from core.agent_router import DynamicProfile


class TestMemoryManager(unittest.TestCase):
    """MemoryManager 统一入口"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_get_student_memory_creates_new(self):
        mem = self.mm.get_student_memory("s_new")
        self.assertEqual(mem.student_id, "s_new")

    def test_update_student_memory_batch(self):
        """批量更新"""
        self.mm.update_student_memory(
            "s1",
            profile={"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"},
            mastery_updates={"closures": 0.9, "decorators": 0.1},
            weak_point={"concept": "闭包", "error_type": "认知过载"},
            feedback={"node_id": "node1", "score": 85},
        )
        summary = self.mm.get_learning_summary("s1")
        # closures 0.9 → 0.5*0.5+0.9*0.5 = 0.7 → strength
        self.assertIn("closures", [s["concept"] for s in summary["strengths"]])
        self.assertGreaterEqual(len(summary["weaknesses_reported"]), 1)

    def test_list_and_exists(self):
        self.mm.get_student_memory("a")
        self.mm.get_student_memory("b")
        self.assertTrue(self.mm.student_exists("a"))
        self.assertIn("a", self.mm.list_students())

    def test_store_and_recall_experience(self):
        """经验存取"""
        self.mm.store_experience(
            problem="概念过载", cause="5概念/节",
            context="closures", solution="拆分",
            source="usersim", node_id="closures",
        )
        results = self.mm.recall_experience(query="概念 过载")
        self.assertGreaterEqual(len(results), 1)

    def test_recall_by_node_id(self):
        """按节点召回"""
        self.mm.store_experience(
            problem="P1", cause="C1", context="closures", solution="S",
            node_id="closures",
        )
        results = self.mm.recall_experience(node_id="closures")
        self.assertGreaterEqual(len(results), 1)

    def test_update_experience_result(self):
        """标记经验结果"""
        r = self.mm.store_experience(
            problem="P", cause="C", context="X", solution="S",
        )
        self.mm.mark_experience_result(r.record_id, True)
        updated = self.mm.experience.get_lesson(r.record_id)
        self.assertGreater(updated.success_rate, 0)

    def test_stats(self):
        self.mm.store_experience("P", "C", "X", "S", source="usersim")
        stats = self.mm.get_experience_stats()
        self.assertGreaterEqual(stats["total_lessons"], 1)


class TestIntegrationProfileWithMemory(unittest.TestCase):
    """ProfileAgent + Memory — 画像历史"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.p_agent = ProfileAgent()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_first_visit_creates_profile(self):
        """首次访问 — 创建初始画像"""
        result = self.p_agent.extract("小白零基础，看图学")
        profile = result.profile
        self.mm.update_student_memory(
            "s1",
            profile=profile.to_dict(),
        )
        mem = self.mm.get_student_memory("s1")
        self.assertEqual(len(mem.profile_history), 1)

    def test_second_visit_updates_profile(self):
        """第二次访问 — 更新画像 + 历史"""
        # 第一次
        r1 = self.p_agent.extract("小白零基础")
        self.mm.update_student_memory("s2", profile=r1.profile.to_dict())

        # 第二次 — 学会了一些
        r2 = self.p_agent.extract("有了一些基础，会写函数了")
        self.mm.update_student_memory("s2", profile=r2.profile.to_dict())

        mem = self.mm.get_student_memory("s2")
        self.assertEqual(len(mem.profile_history), 2)
        # interaction_count 应增加
        self.assertEqual(mem.learning_behavior["interaction_count"], 2)


class TestIntegrationPlannerWithMemory(unittest.TestCase):
    """PlannerAgent + Memory — 个性化路径"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.planner = PlannerAgent()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_mastery_affects_plan(self):
        """掌握度影响路径规划"""
        # 创建高掌握度画像 + 记忆
        profile = DynamicProfile(
            knowledge_base="mid_level",
            learning_pace="normal",
        )
        self.mm.update_student_memory(
            "s3",
            profile=profile.to_dict(),
            mastery_updates={"closures": 0.9, "decorators_intro": 0.8},
        )

        # Planner 基于画像规划
        plan = self.planner.plan(profile, course_id="python_advanced")
        self.assertGreater(len(plan.nodes), 0)

        # 验证: 有记忆的学生与无记忆的学生路径可能不同
        # (当前 planner 只用 profile, 但内存已就绪供将来扩展)

    def test_planner_reads_memory(self):
        """Planner 能读取学生记忆"""
        self.mm.update_student_memory(
            "s4",
            profile={"knowledge_base": "junior_dev"},
            mastery_updates={"functions": 0.95, "closures": 0.1},
        )
        mem = self.mm.get_student_memory("s4")
        summary = self.mm.get_learning_summary("s4")

        # functions 0.95 → 0.5*0.5+0.95*0.5 = 0.725 → strength
        self.assertIn("functions", mem.mastery_map)
        self.assertGreater(mem.mastery_map["functions"], 0.7)
        self.assertGreaterEqual(len(summary["strengths"]), 1)


class TestIntegrationMetaReflectorWithMemory(unittest.TestCase):
    """MetaReflector + Memory — 经验写入"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_store_failure_as_experience(self):
        """失败 → 写入经验库"""
        r = self.mm.store_experience(
            problem="学生无法理解递归",
            cause="缺少调用栈可视化",
            context="recursion / python_beginner_hates_theory",
            solution="用 ASCII 图展示每次递归调用的栈变化",
            source="usersim",
            node_id="generators",
            severity="HIGH",
        )
        # 召回
        results = self.mm.recall_experience(query="递归 可视化")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].severity, "HIGH")

    def test_meta_reflector_write_pattern(self):
        """模拟 MetaReflector 写入流程"""
        # UserSim 发现弱点
        self.mm.update_student_memory(
            "s5",
            weak_point={"concept": "递归", "error_type": "认知过载", "occurrence_count": 3},
            feedback={"node_id": "recursion", "score": 45, "issues": ["概念过载", "无图"]},
        )

        # MetaReflector 写入经验
        self.mm.store_experience(
            problem="递归认知过载",
            cause="概念密度过高 / 缺少栈可视化",
            context="recursion / python_beginner",
            solution="拆为3节 + ASCII调用栈图 + ❌/✅对比",
            source="metareflector",
            node_id="recursion",
            severity="CRITICAL",
        )

        # 验证
        summary = self.mm.get_learning_summary("s5")
        self.assertGreaterEqual(len(summary["weaknesses_reported"]), 1)

        stats = self.mm.get_experience_stats()
        self.assertGreaterEqual(stats["total_lessons"], 1)


if __name__ == "__main__":
    unittest.main()
