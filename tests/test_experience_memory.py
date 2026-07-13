#!/usr/bin/env python3
"""ExperienceMemoryStore 测试"""
import os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from memory.experience_memory import ExperienceMemoryStore, ExperienceRecord


class TestExperienceMemoryStore(unittest.TestCase):
    """经验库测试"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = ExperienceMemoryStore(storage_dir=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_add_lesson(self):
        """添加经验"""
        r = self.store.add_lesson(
            problem="概念过载",
            cause="5个概念/节",
            context="node-1",
            solution="拆为3节",
            source="usersim",
        )
        self.assertIsNotNone(r)
        self.assertEqual(r.problem, "概念过载")
        self.assertEqual(r.usage_count, 1)

    def test_add_duplicate_increments_count(self):
        """重复经验 → 增加计数"""
        r1 = self.store.add_lesson(
            problem="概念过载", cause="5个概念/节",
            context="node-1", solution="拆节", source="usersim",
        )
        r2 = self.store.add_lesson(
            problem="概念过载", cause="5个概念/节",
            context="node-2", solution="拆节", source="metareflector",
        )
        self.assertEqual(r2.usage_count, 2)

    def test_search_similar(self):
        """关键词搜索"""
        self.store.add_lesson(
            problem="概念密度过高", cause="5概念/节",
            context="closures", solution="拆分",
            source="usersim",
        )
        self.store.add_lesson(
            problem="类型注解缺失", cause="LLM省略注解",
            context="decorators", solution="强制注解",
            source="reviewgate",
        )
        results = self.store.search_similar("概念 过载")
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("概念", results[0].problem)

    def test_search_by_source_filter(self):
        """按来源过滤"""
        self.store.add_lesson(
            problem="P1", cause="C1", context="X", solution="S",
            source="usersim",
        )
        self.store.add_lesson(
            problem="P2", cause="C2", context="X", solution="S",
            source="reviewgate",
        )
        results = self.store.search_similar("P", source_filter="usersim")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "usersim")

    def test_get_relevant_lessons_by_node(self):
        """按节点获取相关经验"""
        self.store.add_lesson(
            problem="P1", cause="C1", context="closures", solution="S",
            source="usersim", node_id="closures",
        )
        self.store.add_lesson(
            problem="P2", cause="C2", context="decorators", solution="S",
            source="usersim", node_id="decorators",
        )
        results = self.store.get_relevant_lessons(node_id="closures")
        self.assertGreaterEqual(len(results), 1)
        # closures 相关经验应排在前面
        self.assertEqual(results[0].node_id, "closures")

    def test_get_relevant_lessons_by_profile(self):
        """按画像获取相关经验"""
        self.store.add_lesson(
            problem="P1", cause="C1", context="python_beginner", solution="S",
            applicable_profile="python_beginner_hates_theory",
        )
        self.store.add_lesson(
            problem="P2", cause="C2", context="generic", solution="S",
        )
        results = self.store.get_relevant_lessons(
            profile_type="python_beginner_hates_theory"
        )
        self.assertGreaterEqual(len(results), 1)

    def test_update_success_rate(self):
        """更新成功率"""
        r = self.store.add_lesson(
            problem="P", cause="C", context="X", solution="S",
        )
        self.store.update_success_rate(r.record_id, True)
        updated = self.store.get_lesson(r.record_id)
        self.assertGreater(updated.success_rate, 0)
        self.assertEqual(updated.usage_count, 2)

    def test_update_success_rate_failure(self):
        """失败更新"""
        r = self.store.add_lesson(
            problem="P", cause="C", context="X", solution="S",
        )
        self.store.update_success_rate(r.record_id, False)
        updated = self.store.get_lesson(r.record_id)
        self.assertLessEqual(updated.success_rate, 0.15)

    def test_seed_default_lessons(self):
        """预置经验"""
        self.store.seed_default_lessons()
        stats = self.store.stats()
        self.assertGreaterEqual(stats["total_lessons"], 4)

    def test_stats(self):
        """统计信息"""
        self.store.add_lesson("P1", "C1", "X", "S", source="usersim")
        self.store.add_lesson("P2", "C2", "X", "S", source="reviewgate")
        stats = self.store.stats()
        self.assertEqual(stats["total_lessons"], 2)
        self.assertIn("usersim", stats["by_source"])

    def test_auto_keyword_extraction(self):
        """自动关键词提取"""
        r = self.store.add_lesson(
            problem="闭包概念过载, 学生无法理解",
            cause="一节引入过多概念",
            context="闭包教学节点",
            solution="拆分并加入可视化",
        )
        self.assertGreater(len(r.keywords), 0)


if __name__ == "__main__":
    unittest.main()
