#!/usr/bin/env python3
"""
ResourceRecommendationAgent 测试

覆盖:
  case1: 视觉型学生 → 优先推荐图解/Mermaid
  case2: 代码实践型 → 优先推荐代码实验
  case3: 有weak_points → 推荐包含对应知识点
  case4: mastery高 → 减少基础, 增加挑战
  case5: Memory反馈记录成功保存
"""
import sys, unittest
from typing import Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from agents.resource_recommendation_agent import (
    ResourceRecommendationAgent,
    RecommendedResource,
    PersonalizedResourcePlan,
    ResourceFeedback,
    RESOURCE_TYPES,
)
from memory.memory_manager import MemoryManager
from memory.student_memory import StudentMemory
from agents.planner_agent import PlannerAgent
from core.agent_router import DynamicProfile

import tempfile, shutil


# ──────────────────────────────────────────────
# 数据模型测试
# ──────────────────────────────────────────────

class TestDataModels(unittest.TestCase):
    def test_recommended_resource_creation(self):
        r = RecommendedResource(
            resource_type="lecture",
            title="闭包入门",
            concept="closures",
            reason="视觉偏好",
            priority=8,
            estimated_minutes=15,
        )
        self.assertEqual(r.resource_type, "lecture")
        self.assertEqual(r.priority, 8)
        d = r.to_dict()
        self.assertEqual(d["title"], "闭包入门")

    def test_personalized_resource_plan(self):
        plan = PersonalizedResourcePlan(
            student_id="s1",
            today_goal="掌握递归",
            recommended_resources=[],
            total_minutes=30,
            mastery_summary="2/4 掌握",
            reasoning="test",
        )
        d = plan.to_dict()
        self.assertEqual(d["student_id"], "s1")
        self.assertEqual(d["today_goal"], "掌握递归")

    def test_resource_feedback(self):
        fb = ResourceFeedback(
            resource_id="r1",
            student_id="s1",
            resource_type="lecture",
            concept="closures",
            clicked=True,
            completed=True,
            score=85,
        )
        d = fb.to_dict()
        self.assertTrue(d["clicked"])
        self.assertEqual(d["score"], 85)


# ──────────────────────────────────────────────
# 核心推荐逻辑
# ──────────────────────────────────────────────

class TestResourceRecommendation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.agent = ResourceRecommendationAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_memory(
        self,
        student_id: str,
        mastery: Optional[dict] = None,
        weak_points: Optional[list] = None,
        cognitive_style: str = "visual_dominant",
        interaction: str = "code_sandbox",
    ) -> "StudentMemory":
        self.mm.update_student_memory(
            student_id,
            profile={
                "knowledge_base": "junior_dev",
                "cognitive_style": cognitive_style,
                "interaction_preference": interaction,
            },
            mastery_updates=mastery or {},
        )
        if weak_points:
            for wp in weak_points:
                self.mm.update_student_memory(
                    student_id,
                    weak_point={"concept": wp, "error_type": "test", "occurrence_count": 3},
                )
        return self.mm.get_student_memory(student_id)

    # ── case1: 视觉型 → 图解优先 ──
    def test_visual_learner_gets_diagram_resources(self):
        """视觉型学生 → 应包含 visual 类型资源"""
        mem = self._make_memory(
            "s1",
            mastery={"closures": 0.5, "decorators": 0.5},
            cognitive_style="visual_dominant",
        )
        plan = self.agent.recommend("s1", mem)
        types = [r.resource_type for r in plan.recommended_resources]
        self.assertIn("visual", types, f"Visual learner should get visual resources: {types}")
        # 检查是否有 Mermaid hint
        visual_res = [r for r in plan.recommended_resources if r.resource_type == "visual"]
        for r in visual_res:
            if r.content_hints:
                self.assertTrue(
                    r.content_hints.get("require_mermaid") or r.content_hints.get("require_ascii"),
                    f"Visual resource should have diagram hints: {r.content_hints}"
                )

    # ── case2: 代码实践型 → 代码实验优先 ──
    def test_code_sandbox_learner_gets_code_lab(self):
        """交互偏好 code_sandbox → 应包含 code_lab"""
        mem = self._make_memory(
            "s2",
            mastery={"closures": 0.5},
            interaction="code_sandbox",
        )
        plan = self.agent.recommend("s2", mem)
        types = [r.resource_type for r in plan.recommended_resources]
        self.assertIn("code_lab", types,
                      f"Code-sandbox learner should get code_lab: {types}")
        # 沙箱模式资源应该有 sandbox_mode hint
        sandbox_res = [r for r in plan.recommended_resources
                       if r.resource_type == "code_lab" and r.content_hints.get("sandbox_mode")]
        self.assertGreater(len(sandbox_res), 0, "Should have sandbox_mode hint")

    # ── case3: weak_points → 包含对应知识点 ──
    def test_weak_points_drive_recommendations(self):
        """weak_points 必须影响推荐"""
        mem = self._make_memory(
            "s3",
            mastery={"closures": 0.2, "decorators": 0.5},
            weak_points=["递归", "指针"],
        )
        plan = self.agent.recommend("s3", mem)

        # 应有针对弱点的专项训练
        weak_resources = [
            r for r in plan.recommended_resources
            if r.resource_type == "exercise" and any(
                w in r.title for w in ["递归", "指针"]
            )
        ]
        self.assertGreater(len(weak_resources), 0,
                           f"Weak points should trigger exercises: {[r.title for r in plan.recommended_resources]}")

        # 检查 reason
        for r in weak_resources:
            self.assertIn("历史错误", r.reason)

    # ── case4: mastery高 → 挑战为主 ──
    def test_high_mastery_reduces_basic_adds_challenge(self):
        """mastery ≥ 0.8 → 减少基础资源, 增加挑战"""
        mem = self._make_memory(
            "s4",
            mastery={
                "closures": 0.95,
            },
        )
        # 二次更新让 EMA 积累到 ≥0.8
        self.mm.update_student_memory("s4", mastery_updates={"closures": 0.95})
        mem = self.mm.get_student_memory("s4")  # re-read after 2nd update
        plan = self.agent.recommend("s4", mem)

        # 不应有基础练习
        basic_exercises = [
            r for r in plan.recommended_resources
            if r.resource_type == "exercise" and "基础" in r.title
        ]
        self.assertEqual(len(basic_exercises), 0,
                         f"High mastery should NOT have basic exercises: {[r.title for r in basic_exercises]}")

        # 应有拓展或挑战
        advanced = [
            r for r in plan.recommended_resources
            if r.resource_type in ("extended", "challenge")
        ]
        self.assertGreater(len(advanced), 0,
                           f"High mastery should have advanced resources: {[r.resource_type for r in plan.recommended_resources]}")

    # ── case5: 反馈记录 ──
    def test_feedback_recording(self):
        """资源反馈记录成功保存"""
        fb = self.agent.record_feedback(
            student_id="s1",
            resource_id="res_closure_001",
            resource_type="lecture",
            concept="closures",
            clicked=True,
            completed=True,
            score=92,
            time_spent=25,
        )
        self.assertEqual(fb.student_id, "s1")
        self.assertEqual(fb.resource_type, "lecture")
        self.assertTrue(fb.completed)

        # 验证可查询
        history = self.agent.get_feedback_for_student("s1")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].score, 92)

    def test_feedback_accumulates(self):
        """多次反馈累计"""
        for i in range(3):
            self.agent.record_feedback(
                student_id="s5",
                resource_id=f"r_{i}",
                resource_type="exercise",
                concept="closures",
                clicked=True,
            )
        history = self.agent.get_feedback_for_student("s5")
        self.assertEqual(len(history), 3)


# ──────────────────────────────────────────────
# 集成测试: 与 Memory + Planner 联动
# ──────────────────────────────────────────────

class TestIntegrationRecommendation(unittest.TestCase):
    """完整: Memory → Recommendation → ContentAgent-ready"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.agent = ResourceRecommendationAgent()
        self.planner = PlannerAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_pipeline_with_planner(self):
        """Memory + Planner → Recommendation"""
        # 创建学生
        self.mm.update_student_memory(
            "s1",
            profile={"knowledge_base": "mid_level", "cognitive_style": "visual_dominant",
                     "interaction_preference": "code_sandbox"},
            mastery_updates={"closures": 0.2, "decorators": 0.5, "generators": 0.9},
        )
        self.mm.update_student_memory(
            "s1",
            weak_point={"concept": "递归", "error_type": "overflow", "occurrence_count": 5},
        )

        # Planner
        profile = DynamicProfile(
            knowledge_base="mid_level",
            cognitive_style="visual_dominant",
            learning_pace="normal",
        )
        plan = self.planner.plan(profile, course_id="python_advanced")
        nodes = plan.nodes

        # Recommendation
        mem = self.mm.get_student_memory("s1")
        resource_plan = self.agent.recommend("s1", mem, learning_plan_nodes=nodes)

        # 验证
        self.assertIsNotNone(resource_plan.today_goal)
        self.assertGreater(len(resource_plan.recommended_resources), 0)
        self.assertIn("薄弱", resource_plan.mastery_summary)

        # 记录反馈
        for r in resource_plan.recommended_resources[:2]:
            self.agent.record_feedback(
                student_id="s1",
                resource_id=f"fb_{r.title[:10]}",
                resource_type=r.resource_type,
                concept=r.concept,
                clicked=True,
            )

        history = self.agent.get_feedback_for_student("s1")
        self.assertGreaterEqual(len(history), 1)

    def test_resource_types_enum(self):
        """验证所有资源类型定义"""
        for rtype, info in RESOURCE_TYPES.items():
            self.assertIn("label", info)
            self.assertIn("icon", info)


if __name__ == "__main__":
    unittest.main()
