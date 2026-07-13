#!/usr/bin/env python3
"""User Simulation Agent 测试"""
import os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.user_simulation import (
    CognitiveLoadReport,
    MindGapReport,
    ProfileDislikeReport,
    SimulationResult,
    STUDENT_PROFILES,
    UserSimulationAgent,
)


class TestUserSimulationAgent(unittest.TestCase):
    def setUp(self):
        self.agent = UserSimulationAgent(profile_name="python_beginner_hates_theory")

    def test_profile_loading(self):
        self.assertEqual(self.agent.profile["cognitive_limit"], 3)
        self.assertIn("讨厌纯理论", self.agent.profile["description"])

    def test_profile_text(self):
        pt = self.agent.profile_text
        self.assertIn("极其讨厌", pt)
        self.assertIn("特别喜欢", pt)

    def test_cognitive_load_ok(self):
        text = "# Hello\n\n这是一个简单的讲义。\n\n```python\nx = 1\n```"
        r = self.agent._analyze_cognitive_load(text)
        self.assertFalse(r.concept_density_warning)

    def test_cognitive_load_high_density(self):
        concepts = "闭包 装饰器 高阶函数 自由变量 语法糖 一等公民 functools wraps nonlocal 作用域"
        text = f"# 概念轰炸\n\n{concepts}"
        r = self.agent._analyze_cognitive_load(text)
        self.assertTrue(r.concept_density_warning)

    def test_code_text_ratio(self):
        r = self.agent._code_text_ratio("```\ncode\n```")
        self.assertGreater(r, 0)

    def test_profile_dislike_academic(self):
        text = "闭包是一个由函数及其引用的环境组合而成的实体，在计算机科学中具有重要地位。"
        r = self.agent._detect_profile_dislike(text)
        self.assertTrue(len(r.dislikes_detected) > 0)

    def test_profile_missing_compare(self):
        text = "# 无对比的讲义\n\ndef foo(): pass"
        r = self.agent._detect_profile_dislike(text)
        self.assertTrue(len(r.missing_expected_elements) > 0)

    def test_mind_gap_detected(self):
        lecture = "# 基础装饰器\n@decorator\ndef foo(): pass"
        exercise = "实现 @retry(max_tries=3) 装饰器\n使用 *args, **kwargs"
        r = self.agent._analyze_mind_gap(lecture, exercise)
        self.assertTrue(len(r.gaps) > 0 or len(r.taught_in_lecture) > 0)

    def test_simulate_returns_result(self):
        result = self.agent.simulate(
            "# Python 装饰器\n\n你好！今天来学装饰器。\n\n❌ 手动日志\n✅ @decorator\n\n💡 关键: 语法糖",
            "# Exercise: 实现 logger 装饰器"
        )
        self.assertIsInstance(result, SimulationResult)
        self.assertTrue(len(result.diary_text) > 50)
        self.assertIsInstance(result.cognitive_load, CognitiveLoadReport)
        self.assertIsInstance(result.profile_dislike, ProfileDislikeReport)
        self.assertIsInstance(result.mind_gaps, MindGapReport)

    def test_high_quality_lecture_scores_high(self):
        rich_text = """
# Python 装饰器

你好！今天我们来学习装饰器。

## 1. 想象一下

想象你把函数当礼物一样送给另一个函数...

❌ 不好的写法:
```python
def add(a, b):
    print("开始")
    result = a + b
    print("结束")
    return result
```

✅ 装饰器写法:
```python
@logger
def add(a, b):
    return a + b
```

## 2. 核心概念

💡 关键: @decorator 就是语法糖

接下来我们看闭包...

## 3. 动手试试

试试写一个 @timer:
```python
@timer
def slow():
    return sum(i**2 for i in range(1000000))
```

## 回顾

回顾: 函数→闭包→装饰器。你学会了！
"""
        result = self.agent.simulate(rich_text, "实现 logger 装饰器")
        self.assertGreaterEqual(result.would_recommend_score, 60)
        self.assertFalse(result.would_drop_out)

    def test_poor_lecture_scores_low(self):
        poor_text = """
装饰器是一种设计模式。从严格意义上讲，其本质是一个接受函数返回函数的高阶函数。
在计算机科学中，装饰器模式属于结构型设计模式的一种。
"""
        result = self.agent.simulate(poor_text, "实现 @retry(3) 装饰器")
        self.assertLess(result.would_recommend_score, 85)
        self.assertTrue(result.revision_required)

    def test_system_prompt(self):
        prompt = self.agent.build_system_prompt()
        self.assertIn("角色重塑", prompt)
        self.assertIn("第一人称", prompt)

    def test_all_profiles_loadable(self):
        for name in STUDENT_PROFILES:
            agent = UserSimulationAgent(profile_name=name)
            self.assertIn("description", agent.profile)

    def test_extract_concepts_from_exercise(self):
        text = "使用 @retry(3) 和 functools.wraps，传递 *args **kwargs"
        concepts = self.agent._extract_concepts_from_exercise(text)
        self.assertIn("装饰器", concepts)
        self.assertIn("functools", concepts)

    def test_revision_suggestions(self):
        agent = UserSimulationAgent()
        cog = CognitiveLoadReport(
            new_concepts=["闭包", "装饰器", "高阶函数", "自由变量", "语法糖"],
            concept_density_warning=True,
        )
        dislike = ProfileDislikeReport(
            missing_expected_elements=["缺少对比示例"],
            dislikes_detected=["学院派定义"],
        )
        mg = MindGapReport(gaps=["functools.wraps"])
        suggestions = agent._generate_revision_suggestions(cog, dislike, mg)
        self.assertTrue(len(suggestions) >= 3)


class TestUserSimulationCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        Path(self.tmp, "lecture.md").write_text(
            "# 装饰器\n\n你好！\n\n❌ bad\n✅ good\n\n💡 tip"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cli_basic(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "core.user_simulation",
             str(Path(self.tmp, "lecture.md"))],
            capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent / "src"),
        )
        self.assertIn("模拟学生", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
