#!/usr/bin/env python3
"""
ProfileAgent 测试 — 规则模式 + LLM 模式 + DynamicProfile 兼容性
"""

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.agent_router import DynamicProfile, DEFAULT_PROFILE
from agents.profile_agent import ProfileAgent, ProfileExtractionResult


class TestDynamicProfileCompat(unittest.TestCase):
    """DynamicProfile 与 agent_router 的兼容性测试"""

    def test_default_profile_fields(self):
        """确保六维字段都在"""
        p = DEFAULT_PROFILE
        d = p.to_dict()
        expected_fields = [
            "knowledge_base", "cognitive_style", "error_prone_bias",
            "learning_pace", "interaction_preference", "frustration_threshold",
        ]
        for f in expected_fields:
            self.assertIn(f, d)
            self.assertTrue(d[f], f"field {f} should not be empty")

    def test_profile_from_dict_roundtrip(self):
        """序列化往返测试"""
        p = DEFAULT_PROFILE
        d = p.to_dict()
        p2 = DynamicProfile.from_dict(d)
        self.assertEqual(p.to_dict(), p2.to_dict())

    def test_system_prompt_hint(self):
        """Prompt 提示生成"""
        p = DEFAULT_PROFILE
        hint = p.to_system_prompt_hint()
        self.assertIn("视觉主导型", hint)
        self.assertIn("学习节奏极快", hint)
        self.assertIn("极度温和", hint)  # low frustration


class TestProfileAgentRuleMode(unittest.TestCase):
    """规则模式 — 各种学生描述 → 六维画像"""

    def setUp(self):
        self.agent = ProfileAgent()

    def _extract_and_check(self, text: str, expected: dict):
        """提取并检查预期字段"""
        result = self.agent.extract(text)
        self.assertEqual(result.source, "rule")
        profile = result.profile
        for field, value in expected.items():
            actual = getattr(profile, field)
            self.assertEqual(actual, value,
                             f"Field '{field}': expected '{value}', got '{actual}'")

    def test_zero_basic_student(self):
        """零基础小白 → junior_dev + visual"""
        self._extract_and_check(
            "我是编程小白，完全没有基础，想学 Python。喜欢看图学习。",
            {
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
            },
        )

    def test_visual_fast_learner(self):
        """视觉型快速学习者"""
        self._extract_and_check(
            "我有一些编程基础，喜欢看图解学习，想快速上手用 Python 写代码。",
            {
                "knowledge_base": "mid_level",
                "cognitive_style": "visual_dominant",
                "learning_pace": "fast_track",
            },
        )

    def test_text_linear_deep_dive(self):
        """文本线性 + 深入学习"""
        self._extract_and_check(
            "我喜欢认真看书阅读，一步步吸收知识。想彻底搞懂底层原理。",
            {
                "cognitive_style": "text_linear",
                "learning_pace": "deep_dive",
            },
        )

    def test_auditory_learner(self):
        """听觉型学习者"""
        self._extract_and_check(
            "我喜欢听讲解和听课，通过音频来学习效率最高。",
            {
                "cognitive_style": "auditory",
            },
        )

    def test_magic_syntax_blind(self):
        """语法糖盲区"""
        self._extract_and_check(
            "每次看到 @ 装饰器这种黑魔法就头大，完全搞不懂语法糖。",
            {
                "error_prone_bias": "magic_syntax_blind",
            },
        )

    def test_indentation_errors(self):
        """缩进错误倾向"""
        self._extract_and_check(
            "我老是 Python 缩进出错，冒号总忘。",
            {
                "error_prone_bias": "indentation_errors",
            },
        )

    def test_type_mismatch(self):
        """类型错误倾向"""
        self._extract_and_check(
            "我经常遇到 int 和 str 类型报错，type error 一大堆。",
            {
                "error_prone_bias": "type_mismatch",
            },
        )

    def test_code_sandbox_preference(self):
        """动手实操偏好"""
        self._extract_and_check(
            "我喜欢动手写代码、调试程序，在沙箱中自己运行看结果。",
            {
                "interaction_preference": "code_sandbox",
            },
        )

    def test_quiz_first_preference(self):
        """做题优先"""
        self._extract_and_check(
            "我喜欢先做题和测试，通过选择题来检验理解程度。",
            {
                "interaction_preference": "quiz_first",
            },
        )

    def test_passive_read_preference(self):
        """先看再动手"""
        self._extract_and_check(
            "我喜欢先看材料再理解，先翻阅浏览看看大纲。",
            {
                "interaction_preference": "passive_read",
            },
        )

    def test_low_frustration_threshold(self):
        """低挫败阈值"""
        self._extract_and_check(
            "我很容易放弃，总出错没信心，需要多鼓励和耐心指导。",
            {
                "frustration_threshold": "low",
            },
        )

    def test_high_frustration_threshold(self):
        """高挫败阈值"""
        self._extract_and_check(
            "我不怕出错，尽管来难题，我抗压能力很强。",
            {
                "frustration_threshold": "high",
            },
        )

    def test_senior_developer(self):
        """高级开发者"""
        self._extract_and_check(
            "我有多年的 Python 开发经验，熟练掌握各种框架，想深入学习架构设计。",
            {
                "knowledge_base": "senior",
                "learning_pace": "deep_dive",
            },
        )

    def test_complex_multi_dimension(self):
        """多维度复杂描述"""
        result = self.agent.extract(
            "我是一个编程小白，完全零基础。害怕出错容易放弃。"
            "但我想快速上手写代码。每次看语法糖 @ 就头大。"
            "喜欢看图学习，动手实操敲代码。"
        )
        p = result.profile
        self.assertEqual(p.knowledge_base, "junior_dev")
        self.assertEqual(p.frustration_threshold, "low")
        self.assertEqual(p.learning_pace, "fast_track")
        self.assertEqual(p.error_prone_bias, "magic_syntax_blind")
        self.assertEqual(p.cognitive_style, "visual_dominant")
        self.assertEqual(p.interaction_preference, "code_sandbox")

    def test_defaults_applied_for_empty(self):
        """空描述返回默认值"""
        result = self.agent.extract("")
        p = result.profile
        for field, default in ProfileAgent.DEFAULTS.items():
            self.assertEqual(getattr(p, field), default)

    def test_result_to_dict(self):
        """结果序列化"""
        result = self.agent.extract("小白，爱看图")
        d = result.to_dict()
        self.assertIn("profile", d)
        self.assertIn("source", d)
        self.assertIn("confidence", d)
        self.assertEqual(d["source"], "rule")


class TestProfileAgentLLMMode(unittest.TestCase):
    """LLM 模式 — 主要是降级路径测试"""

    def setUp(self):
        self.agent = ProfileAgent()

    def test_no_router_falls_back_to_rule(self):
        """无 router 时回退到规则模式"""
        result = self.agent.extract_with_llm(
            "小白，想学 Python",
            router=None,
        )
        self.assertEqual(result.source, "rule")
        self.assertEqual(result.profile.knowledge_base, "junior_dev")

    def test_extract_result_attributes(self):
        """ProfileExtractionResult 所有属性"""
        from core.agent_router import DynamicProfile
        profile = DynamicProfile(
            knowledge_base="junior_dev",
            cognitive_style="visual_dominant",
            error_prone_bias="magic_syntax_blind",
            learning_pace="fast_track",
            interaction_preference="code_sandbox",
            frustration_threshold="medium",
        )
        result = ProfileExtractionResult(
            profile=profile,
            source="rule",
            confidence=0.8,
            raw_keywords=["小白", "看图"],
            llm_reasoning="",
        )
        self.assertEqual(result.source, "rule")
        self.assertEqual(result.confidence, 0.8)
        self.assertEqual(len(result.raw_keywords), 2)


class TestIntegrationAgentRouterCompat(unittest.TestCase):
    """集成测试 — ProfileAgent 产出与 AgentRouter 兼容"""

    def test_profile_works_with_router_hint(self):
        """ProfileAgent 提取的画像可用 AgentRouter 生成 Prompt hint"""
        agent = ProfileAgent()
        result = agent.extract("小白，视觉型，容易放弃，想快速学")
        hint = agent.get_prompt_hint(result)
        self.assertIn("视觉主导型", hint)
        self.assertIn("极度温和", hint)

    def test_profile_passed_to_build_routed_prompt(self):
        """提取的画像用于 build_routed_prompt"""
        from core.agent_router import AgentRouter
        agent = ProfileAgent()
        result = agent.extract("小白看图学")
        router = AgentRouter()
        prompt = router.build_routed_prompt(
            "ContentAgent",
            "You are a tutor.",
            result.profile,
        )
        self.assertIn("Dynamic Student Profile", prompt)


if __name__ == "__main__":
    unittest.main()
