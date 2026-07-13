#!/usr/bin/env python3
"""
PlannerAgent 测试 — 画像差异 → 路线差异
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.agent_router import DynamicProfile
from agents.planner_agent import (
    PlannerAgent, LearningPlan, PlanNode,
    PACE_ADJUSTMENTS, COGNITIVE_TEACHING_MAP,
)


class TestPlanNode(unittest.TestCase):
    """PlanNode 数据模型"""

    def test_creation(self):
        n = PlanNode(
            node_id="closures",
            title="闭包",
            core_concept="作用域",
            depth=3,
            estimated_minutes=30,
            required_concepts=["functions"],
            exercise_count=5,
            teaching_strategy="visual",
            notes="重点图解",
        )
        self.assertEqual(n.node_id, "closures")
        self.assertEqual(n.depth, 3)
        self.assertEqual(n.estimated_minutes, 30)

    def test_to_dict_roundtrip(self):
        n = PlanNode(
            node_id="closures",
            title="闭包",
            core_concept="作用域",
            depth=3,
        )
        d = n.to_dict()
        n2 = PlanNode.from_dict(d)
        self.assertEqual(n.node_id, n2.node_id)
        self.assertEqual(n.depth, n2.depth)
        self.assertEqual(n.core_concept, n2.core_concept)


class TestLearningPlan(unittest.TestCase):
    """LearningPlan 数据模型"""

    def test_creation_empty(self):
        plan = LearningPlan(
            plan_id="p1",
            profile_summary="test",
            total_minutes=0,
        )
        self.assertEqual(plan.plan_id, "p1")
        self.assertEqual(len(plan.nodes), 0)

    def test_with_nodes(self):
        nodes = [
            PlanNode(node_id="n1", title="N1", core_concept="c1"),
            PlanNode(node_id="n2", title="N2", core_concept="c2"),
        ]
        plan = LearningPlan(
            plan_id="p2",
            profile_summary="test",
            nodes=nodes,
            total_minutes=60,
            strategy_rationale="快速通道",
        )
        self.assertEqual(len(plan.nodes), 2)
        self.assertEqual(plan.total_minutes, 60)
        self.assertIn("快速通道", plan.strategy_rationale)

    def test_to_json(self):
        nodes = [PlanNode(node_id="n1", title="N1", core_concept="c1")]
        plan = LearningPlan(
            plan_id="p3",
            profile_summary="test",
            nodes=nodes,
            total_minutes=15,
        )
        json_str = plan.to_json()
        self.assertIn("p3", json_str)
        self.assertIn("N1", json_str)

    def test_from_dict_roundtrip(self):
        nodes = [PlanNode(node_id="n1", title="N1", core_concept="c1")]
        plan = LearningPlan(
            plan_id="p4",
            profile_summary="junior/visual/normal",
            nodes=nodes,
            total_minutes=30,
            strategy_rationale="标准路径",
            alternative_paths=["深潜", "快速"],
            metadata={"course": "python_advanced"},
        )
        d = plan.to_dict()
        plan2 = LearningPlan.from_dict(d)
        self.assertEqual(plan2.plan_id, "p4")
        self.assertEqual(plan2.total_minutes, 30)
        self.assertEqual(len(plan2.nodes), 1)
        self.assertEqual(len(plan2.alternative_paths), 2)


class TestPlannerAgent(unittest.TestCase):
    """核心: 画像差异 → 路线差异"""

    def setUp(self):
        self.agent = PlannerAgent()

    def test_plan_basic(self):
        """基本规划: 默认画像"""
        profile = DynamicProfile(
            knowledge_base="junior_dev",
            cognitive_style="visual_dominant",
            error_prone_bias="magic_syntax_blind",
            learning_pace="normal",
            interaction_preference="code_sandbox",
            frustration_threshold="medium",
        )
        plan = self.agent.plan(profile, course_id="python_advanced")
        self.assertIsInstance(plan, LearningPlan)
        self.assertGreater(len(plan.nodes), 0)
        self.assertGreater(plan.total_minutes, 0)
        self.assertIn("标准路径", plan.strategy_rationale)

    def test_fast_track_vs_deep_dive_differs(self):
        """快速 vs 深潜 — 路径应不同"""
        fast_profile = DynamicProfile(
            knowledge_base="mid_level",
            learning_pace="fast_track",
        )
        deep_profile = DynamicProfile(
            knowledge_base="mid_level",
            learning_pace="deep_dive",
        )

        fast_plan = self.agent.plan(fast_profile, course_id="python_advanced")
        deep_plan = self.agent.plan(deep_profile, course_id="python_advanced")

        # 深潜模式的节点应有更高深度
        deep_depths = [n.depth for n in deep_plan.nodes]
        fast_depths = [n.depth for n in fast_plan.nodes]
        avg_deep = sum(deep_depths) / len(deep_depths)
        avg_fast = sum(fast_depths) / len(fast_depths)
        self.assertGreater(avg_deep, avg_fast,
            f"深潜深度 ({avg_deep:.1f}) 应 > 快速 ({avg_fast:.1f})")

    def test_different_styles_generate_different_strategies(self):
        """不同认知风格 → 不同教学策略"""
        visual = DynamicProfile(cognitive_style="visual_dominant")
        auditory = DynamicProfile(cognitive_style="auditory")
        text = DynamicProfile(cognitive_style="text_linear")

        v_plan = self.agent.plan(visual)
        a_plan = self.agent.plan(auditory)
        t_plan = self.agent.plan(text)

        v_strat = v_plan.nodes[0].teaching_strategy if v_plan.nodes else ""
        a_strat = a_plan.nodes[0].teaching_strategy if a_plan.nodes else ""
        t_strat = t_plan.nodes[0].teaching_strategy if t_plan.nodes else ""

        self.assertEqual(v_strat, "visual")
        self.assertEqual(a_strat, "analogy")
        self.assertEqual(t_strat, "standard")

    def test_junior_vs_senior_different_length(self):
        """初级 vs 高级 — 路径长度应不同"""
        junior_profile = DynamicProfile(knowledge_base="junior_dev")
        senior_profile = DynamicProfile(knowledge_base="senior")

        j_plan = self.agent.plan(junior_profile, course_id="python_advanced")
        s_plan = self.agent.plan(senior_profile, course_id="python_advanced")

        # 高级学生可能跳过更多节点（取决于知识图谱结构）
        self.assertGreaterEqual(len(j_plan.nodes), len(s_plan.nodes),
            "初级路径不短于高级路径")

    def test_plan_has_alternative_paths(self):
        """规划应包含备选路径"""
        profile = DynamicProfile()
        plan = self.agent.plan(profile)
        self.assertGreater(len(plan.alternative_paths), 0)

    def test_plan_with_topic_filter(self):
        """话题过滤"""
        profile = DynamicProfile()
        plan = self.agent.plan(
            profile,
            course_id="python_advanced",
            topic_filter=["closures"],
        )
        self.assertEqual(len(plan.nodes), 1)
        self.assertEqual(plan.nodes[0].node_id, "closures")

    def test_plan_nodes_have_required_notes(self):
        """节点应包含教学备注"""
        profile = DynamicProfile(
            cognitive_style="visual_dominant",
            frustration_threshold="low",
            error_prone_bias="magic_syntax_blind",
        )
        plan = self.agent.plan(profile)
        for node in plan.nodes:
            self.assertTrue(node.notes, f"Node {node.node_id} has no notes")

    def test_plan_for_multiple_profiles(self):
        """批量生成: 多画像 → 不同路径"""
        profiles = [
            {"knowledge_base": "junior_dev", "learning_pace": "fast_track"},
            {"knowledge_base": "mid_level", "learning_pace": "deep_dive"},
        ]
        plans = self.agent.plan_for_multiple_profiles(
            profiles, course_id="python_advanced"
        )
        self.assertEqual(len(plans), 2)
        plan_ids = list(plans.keys())
        self.assertIn("fast_track", plan_ids[0])
        self.assertIn("deep_dive", plan_ids[1])


class TestPaceAdjustments(unittest.TestCase):
    """节奏调整常量"""

    def test_all_paces_have_adjustments(self):
        for pace in ["fast_track", "normal", "deep_dive"]:
            self.assertIn(pace, PACE_ADJUSTMENTS)

    def test_deep_dive_adds_exercises(self):
        self.assertGreater(
            PACE_ADJUSTMENTS["deep_dive"]["exercise_offset"],
            PACE_ADJUSTMENTS["normal"]["exercise_offset"],
        )


class TestCognitiveTeachingMap(unittest.TestCase):
    """认知风格 → 教学策略映射"""

    def test_all_styles_mapped(self):
        for style in ["visual_dominant", "text_linear", "auditory"]:
            self.assertIn(style, COGNITIVE_TEACHING_MAP)


class TestPlannerAgentMultiAgentCurriculum(unittest.TestCase):
    """Phase 7.5: Multi-Agent AI 课程测试"""

    def setUp(self):
        self.agent = PlannerAgent()

    def test_python_curriculum_unchanged(self):
        """Case 1: Python 关键词 → Python 课程（不破坏已有行为）"""
        profile = DynamicProfile(
            knowledge_base="mid_level",
            cognitive_style="visual_dominant",
            learning_pace="normal",
        )
        plan = self.agent.plan(
            profile,
            course_id="python_advanced",
            goal_text="我想学习Python，特别是装饰器和生成器",
        )
        # Python 课程节点：closures, decorators_intro, decorators_advanced, generators
        titles = [n.title for n in plan.nodes]
        self.assertIn("闭包与作用域", titles)
        self.assertIn("装饰器入门", titles)
        # 不应包含 Agent 课程节点
        self.assertNotIn("Agent 主循环", titles)
        self.assertNotIn("LLM 基础原理", titles)

    def test_multi_agent_english_keywords(self):
        """Case 2: English multi-agent keywords → Multi-Agent 课程"""
        profile = DynamicProfile()
        plan = self.agent.plan(
            profile,
            course_id="",
            goal_text="I want to learn Multi-Agent AI system development",
        )
        titles = [n.title for n in plan.nodes]
        self.assertIn("LLM 基础原理", titles)
        self.assertIn("Agent 主循环", titles)
        self.assertIn("Agent 角色分工", titles)
        self.assertIn("Agent 通信模式", titles)
        # 不应包含 Python 课程节点
        self.assertNotIn("闭包与作用域", titles)
        self.assertNotIn("装饰器入门", titles)

    def test_multi_agent_chinese_keywords(self):
        """Case 3: Chinese 智能体 keywords → Multi-Agent 课程"""
        profile = DynamicProfile()
        plan = self.agent.plan(
            profile,
            course_id="",
            goal_text="学习智能体开发，掌握大模型应用",
        )
        titles = [n.title for n in plan.nodes]
        self.assertIn("LLM 基础原理", titles)
        self.assertIn("Agent 主循环", titles)
        self.assertIn("EventBus 架构设计", titles)
        self.assertIn("反思与改进循环", titles)
        # 不应包含 Python 课程节点
        self.assertNotIn("生成器与迭代器", titles)

    def test_python_agent_hybrid_falls_to_agent(self):
        """Case 4: Python + Agent 混合 → Agent 课程 (Agent 优先级高于 Python)"""
        profile = DynamicProfile()
        plan = self.agent.plan(
            profile,
            course_id="",
            goal_text="Python + Agent应用开发",
        )
        titles = [n.title for n in plan.nodes]
        # "agent" 关键词触发 multi_agent_ai
        self.assertIn("Agent 主循环", titles)
        self.assertIn("Agent 规划与推理", titles)

    def test_multi_agent_course_has_all_levels(self):
        """验证 Multi-Agent 课程包含所有 5 个级别"""
        profile = DynamicProfile(learning_pace="normal")
        plan = self.agent.plan(
            profile,
            course_id="multi_agent_ai",
        )
        titles = set(n.title for n in plan.nodes)
        # Level 1: LLM Fundamentals
        self.assertIn("LLM 基础原理", titles)
        self.assertIn("Prompt 工程", titles)
        # Level 2: Agent Fundamentals
        self.assertIn("Agent 主循环", titles)
        self.assertIn("Tool Calling 与 Function Calling", titles)
        # Level 3: Multi-Agent Architecture
        self.assertIn("Agent 角色分工", titles)
        self.assertIn("Agent 通信模式", titles)
        self.assertIn("任务分解与协作", titles)
        # Level 4: Runtime Engineering
        self.assertIn("EventBus 架构设计", titles)
        self.assertIn("Memory 管理", titles)
        self.assertIn("Trace 可观测性", titles)
        # Level 5: Production Optimization
        self.assertIn("Agent 评估体系", titles)
        self.assertIn("反思与改进循环", titles)
        self.assertIn("系统优化", titles)
        # 应包含所有 16 个节点 (junior_dev + normal pace)
        self.assertEqual(len(plan.nodes), 16)

    def test_detect_course_python_unchanged(self):
        """detect_course: Python 文本 → python_advanced"""
        result = self.agent.detect_course("学习Python装饰器和闭包")
        self.assertEqual(result, "python_advanced")

    def test_detect_course_multi_agent(self):
        """detect_course: Multi-Agent 文本 → multi_agent_ai"""
        result = self.agent.detect_course("我想学多智能体系统")
        self.assertEqual(result, "multi_agent_ai")

    def test_detect_course_default(self):
        """detect_course: 无关键词 → python_advanced (default)"""
        result = self.agent.detect_course("想学编程", {"knowledge_base": "mid_level"})
        self.assertEqual(result, "python_advanced")


class TestIntegrationProfilePlanner(unittest.TestCase):
    """集成测试: ProfileAgent → PlannerAgent 端到端"""

    def test_pipeline(self):
        """完整管道: ProfileAgent 提取 → PlannerAgent 规划"""
        from agents.profile_agent import ProfileAgent

        p_agent = ProfileAgent()
        planner = PlannerAgent()

        # 学生输入
        student_text = "零基础小白，看视频学，看到@就头大，想快速学会写代码"
        result = p_agent.extract(student_text)
        profile = result.profile

        # 验证画像
        self.assertEqual(profile.knowledge_base, "junior_dev")
        self.assertEqual(profile.cognitive_style, "visual_dominant")

        # 生成规划
        plan = planner.plan(profile)
        self.assertIsInstance(plan, LearningPlan)
        self.assertGreater(len(plan.nodes), 0)

        # 验证教学策略匹配
        for node in plan.nodes:
            self.assertEqual(node.teaching_strategy, "visual")


if __name__ == "__main__":
    unittest.main()
