#!/usr/bin/env python3
"""StudentMemoryStore 测试"""
import os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from memory.student_memory import StudentMemory, StudentMemoryStore


class TestStudentMemory(unittest.TestCase):
    """StudentMemory 数据模型"""

    def test_create(self):
        m = StudentMemory(student_id="s1")
        self.assertEqual(m.student_id, "s1")
        self.assertEqual(m.mastery_map, {})
        self.assertEqual(m.weak_points, [])
        self.assertIn("avg_pace", m.learning_behavior)

    def test_to_dict_roundtrip(self):
        m = StudentMemory(
            student_id="s2",
            mastery_map={"closures": 0.8, "decorators": 0.3},
            weak_points=[{"concept": "闭包", "error_type": "overflow", "occurrence_count": 3}],
        )
        d = m.to_dict()
        m2 = StudentMemory.from_dict(d)
        self.assertEqual(m2.student_id, "s2")
        self.assertAlmostEqual(m2.mastery_map["closures"], 0.8)
        self.assertEqual(len(m2.weak_points), 1)


class TestStudentMemoryStore(unittest.TestCase):
    """StudentMemoryStore JSON 存储"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = StudentMemoryStore(storage_dir=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_new_student_creation(self):
        """新学生 → 自动创建空记忆"""
        mem = self.store.load("new_student")
        self.assertEqual(mem.student_id, "new_student")
        self.assertEqual(mem.mastery_map, {})

    def test_save_and_load(self):
        """保存后加载"""
        mem = StudentMemory(
            student_id="s3",
            mastery_map={"functions": 0.9},
        )
        self.store.save(mem)
        loaded = self.store.load("s3")
        self.assertAlmostEqual(loaded.mastery_map["functions"], 0.9)

    def test_update_profile_with_history(self):
        """更新画像 → 历史记录"""
        self.store.update_profile(
            "s4",
            {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"},
        )
        self.store.update_profile(
            "s4",
            {"knowledge_base": "mid_level", "cognitive_style": "text_linear"},
        )
        mem = self.store.load("s4")
        self.assertEqual(len(mem.profile_history), 2)
        self.assertEqual(mem.learning_behavior["interaction_count"], 2)

    def test_add_weak_point(self):
        """添加弱点"""
        self.store.add_weak_point("s5", "闭包", "认知过载")
        self.store.add_weak_point("s5", "闭包", "认知过载")  # 重复
        mem = self.store.load("s5")
        self.assertEqual(len(mem.weak_points), 1)
        self.assertEqual(mem.weak_points[0]["occurrence_count"], 2)

    def test_add_weak_point_new_type(self):
        """不同错误类型 → 不同条目"""
        self.store.add_weak_point("s6", "闭包", "认知过载")
        self.store.add_weak_point("s6", "闭包", "语法错误")
        mem = self.store.load("s6")
        self.assertEqual(len(mem.weak_points), 2)

    def test_update_mastery_ema(self):
        """掌握度指数移动加权平均 (α=0.5)"""
        self.store.update_mastery("s7", {"closures": 0.2})
        self.store.update_mastery("s7", {"closures": 0.8})
        mem = self.store.load("s7")
        # round1: 0.5*0.5 + 0.2*0.5 = 0.25+0.10 = 0.35
        # round2: 0.35*0.5 + 0.8*0.5 = 0.175+0.40 = 0.575
        self.assertAlmostEqual(mem.mastery_map["closures"], 0.57, places=1)

    def test_mastery_default_start(self):
        """未设置的概念默认 0.5"""
        mem = StudentMemory(student_id="s8")
        self.store.save(mem)
        self.store.update_mastery("s8", {"new_concept": 0.9})
        loaded = self.store.load("s8")
        # 0.5*0.5 + 0.9*0.5 = 0.25+0.45 = 0.70
        self.assertAlmostEqual(loaded.mastery_map["new_concept"], 0.70, places=1)

    def test_add_feedback_updates_avg(self):
        """反馈 → 更新平均分"""
        self.store.add_feedback("s9", "node1", 70)
        self.store.add_feedback("s9", "node2", 90)
        mem = self.store.load("s9")
        self.assertEqual(len(mem.feedback_history), 2)
        self.assertEqual(mem.learning_behavior["avg_score"], 80.0)

    def test_learning_summary(self):
        """学习摘要"""
        self.store.update_mastery("s10", {
            "closures": 0.9, "decorators": 0.2, "functions": 0.9, "generators": 0.1,
        })
        self.store.add_weak_point("s10", "装饰器", "语法糖", occurrence_count=5)
        self.store.add_feedback("s10", "node1", 85)
        self.store.add_session_summary("s10", "python_advanced", 4, 85.0, 120)

        summary = self.store.get_learning_summary("s10")
        self.assertEqual(summary["student_id"], "s10")
        self.assertEqual(summary["total_sessions"], 1)
        self.assertEqual(summary["avg_score"], 85.0)

        # strengths: closures(0.7), functions(0.7)
        self.assertGreaterEqual(len(summary["strengths"]), 1)
        strengths = [s["concept"] for s in summary["strengths"]]
        self.assertIn("closures", strengths)

        # weaknesses from mastery: generators(0.1→0.3)
        self.assertGreaterEqual(len(summary["weaknesses_mastery"]), 1)

        # weaknesses from reports
        self.assertGreaterEqual(len(summary["weaknesses_reported"]), 1)

    def test_list_all(self):
        """列出所有学生"""
        self.store.save(StudentMemory(student_id="a"))
        self.store.save(StudentMemory(student_id="b"))
        ids = self.store.list_all()
        self.assertIn("a", ids)
        self.assertIn("b", ids)

    def test_delete(self):
        """删除学生"""
        self.store.save(StudentMemory(student_id="del_me"))
        self.assertTrue(self.store.exists("del_me"))
        self.store.delete("del_me")
        self.assertFalse(self.store.exists("del_me"))

    def test_profile_history_limit(self):
        """画像历史限 10 条"""
        for i in range(15):
            self.store.update_profile("s11", {"knowledge_base": "junior_dev"})
        mem = self.store.load("s11")
        self.assertLessEqual(len(mem.profile_history), 10)

    def test_weak_points_limit(self):
        """弱点限 20 条"""
        for i in range(25):
            self.store.add_weak_point("s12", f"concept_{i}", "test")
        mem = self.store.load("s12")
        self.assertLessEqual(len(mem.weak_points), 20)

    def test_feedback_history_limit(self):
        """反馈历史限 20 条"""
        for i in range(25):
            self.store.add_feedback("s13", f"node_{i}", 80)
        mem = self.store.load("s13")
        self.assertLessEqual(len(mem.feedback_history), 20)


if __name__ == "__main__":
    unittest.main()
