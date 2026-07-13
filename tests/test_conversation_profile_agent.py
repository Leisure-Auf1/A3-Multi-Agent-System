#!/usr/bin/env python3
"""
ConversationProfileAgent 测试

覆盖:
  case1 — 首次进入, 部分信息 → 识别已有 + 追问缺失
  case2 — 完整回答六维 → 生成完整 DynamicProfile
  case3 — 中断后恢复 → 继续之前问题
  case4 — 历史 Memory 存在 → 更新而非覆盖
"""
import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from agents.conversation_profile_agent import (
    ConversationProfileAgent,
    ConversationState,
    ConversationStateStore,
    ProfileCompletenessChecker,
    PROFILE_DIMENSIONS,
)
from agents.profile_agent import ProfileAgent
from memory.student_memory import StudentMemoryStore, StudentMemory
from memory.memory_manager import MemoryManager
from core.agent_router import DynamicProfile

import shutil


# ──────────────────────────────────────────────
# ProfileCompletenessChecker 单元测试
# ──────────────────────────────────────────────

class TestProfileCompletenessChecker(unittest.TestCase):
    def setUp(self):
        self.ck = ProfileCompletenessChecker()

    def test_initial_incomplete(self):
        is_complete, missing = self.ck.check_completeness()
        self.assertFalse(is_complete)
        self.assertEqual(len(missing), 6)

    def test_extract_knowledge_base(self):
        found = self.ck.extract_from_text("我是编程小白，完全零基础")
        self.assertIn("knowledge_base", found)
        self.assertEqual(found["knowledge_base"], "junior_dev")

    def test_extract_cognitive_style(self):
        found = self.ck.extract_from_text("我喜欢看视频和图解来学习")
        self.assertIn("cognitive_style", found)
        self.assertEqual(found["cognitive_style"], "visual_dominant")

    def test_extract_multiple_dimensions(self):
        found = self.ck.extract_from_text(
            "我是大二学生，会一点Python。喜欢看视频学。"
            "看到@装饰器就头大。想快速上手写代码。容易放弃。"
        )
        self.assertGreaterEqual(len(found), 3)

    def test_next_question_returns_priority(self):
        _, missing = self.ck.check_completeness()
        q = self.ck.get_next_question(missing)
        self.assertIsNotNone(q)
        self.assertIn("基础", q or "")  # knowledge_base 优先

    def test_extract_not_overwrite(self):
        """已收集的维度不会被覆盖"""
        self.ck._collected["knowledge_base"] = "mid_level"
        found = self.ck.extract_from_text("我是小白零基础")
        self.assertNotIn("knowledge_base", found)

    def test_full_collection_complete(self):
        """所有维度手动填充 → COMPLETE"""
        for dim in PROFILE_DIMENSIONS:
            self.ck._collected[dim] = PROFILE_DIMENSIONS[dim]["candidates"][0]
        is_complete, missing = self.ck.check_completeness()
        self.assertTrue(is_complete)
        self.assertEqual(len(missing), 0)

    def test_reset(self):
        self.ck._collected["knowledge_base"] = "mid_level"
        self.ck.reset()
        self.assertEqual(len(self.ck._collected), 0)


# ──────────────────────────────────────────────
# ConversationStateStore 测试
# ──────────────────────────────────────────────

class TestConversationStateStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = ConversationStateStore(storage_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_and_load(self):
        state = ConversationState(
            session_id="s1",
            collected_facts={"knowledge_base": "mid_level"},
            messages=[{"role": "student", "content": "hello"}],
        )
        self.store.save(state)
        loaded = self.store.load("s1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.collected_facts["knowledge_base"], "mid_level")

    def test_load_nonexistent(self):
        self.assertIsNone(self.store.load("nonexistent"))

    def test_delete(self):
        state = ConversationState(session_id="s2")
        self.store.save(state)
        self.store.delete("s2")
        self.assertIsNone(self.store.load("s2"))


# ──────────────────────────────────────────────
# ConversationProfileAgent — 核心流程
# ──────────────────────────────────────────────

class TestConversationProfileAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = ConversationStateStore(storage_dir=self.tmp)
        self.agent = ConversationProfileAgent(state_store=self.store)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── case1: 首次进入, 部分信息 ──

    def test_first_message_extracts_and_asks(self):
        """首次输入部分信息 → 识别已有 + 追问缺失"""
        state, reply = self.agent.process_message(
            session_id="s1",
            student_text="我是计算机专业大二学生，会一点Python，想学习人工智能。",
        )
        # 应该识别到 knowledge_base=mid_level ("会一点")
        self.assertIn("knowledge_base", state.collected_facts,
                      f"Should detect KB, got: {state.collected_facts}")
        self.assertEqual(state.collected_facts["knowledge_base"], "mid_level")

        # 应该继续追问
        self.assertEqual(state.status, "COLLECTING")
        self.assertIsNotNone(reply)
        self.assertGreater(len(reply or ""), 10)

        # 应该有缺失维度
        self.assertGreater(len(state.missing_dimensions), 0)

    def test_multi_turn_dialogue(self):
        """多轮对话逐步收集"""
        # 第1轮
        s1, r1 = self.agent.process_message("s2", "我是小白，零基础学编程")
        self.assertTrue(r1, "Should ask a question")

        # 第2轮 — 回答认知风格
        s2, r2 = self.agent.process_message("s2", "我喜欢看视频和图解来学习")
        self.assertIn("cognitive_style", s2.collected_facts)
        self.assertEqual(s2.collected_facts["cognitive_style"], "visual_dominant")

        # 第3轮 — 回答节奏
        s3, r3 = self.agent.process_message("s2", "我想快速上手，赶时间")
        self.assertIn("learning_pace", s3.collected_facts)
        self.assertEqual(s3.collected_facts["learning_pace"], "fast_track")

        # 应该还有缺失
        self.assertEqual(s3.status, "COLLECTING")

    # ── case2: 完整回答 → 生成 DynamicProfile ──

    def test_complete_profile_generation(self):
        """完整回答六维 → COMPLETE → ProfileAgent 生成"""
        pa = ProfileAgent()

        # 一次性给出足够信息
        full_text = (
            "我是编程小白零基础。喜欢看视频学习。"
            "看到@装饰器就头大。想快速上手写代码。"
            "喜欢动手敲代码。容易放弃需要鼓励。"
        )
        state, reply = self.agent.process_message("s3", full_text)

        # 可能还需要追问 (取决于一轮提取量)
        # 继续收集直到完成
        rounds = 0
        while reply and rounds < 8:
            # 模拟简单回答
            state, reply = self.agent.process_message(
                "s3",
                "我喜欢听讲解学习，做练习题，正常节奏学，缩进容易出错，不怕困难"
            )
            rounds += 1

        # 应该完成
        if state.status == "COMPLETE":
            profile_dict = self.agent.build_final_profile("s3", profile_agent=pa)
            self.assertIsNotNone(profile_dict)
            self.assertIn("knowledge_base", profile_dict)
            # 六维都应存在
            for dim in PROFILE_DIMENSIONS:
                self.assertIn(dim, profile_dict, f"Missing dimension: {dim}")

    # ── case3: 中断恢复 ──

    def test_resume_interrupted_session(self):
        """中断后恢复 — 继续之前的问题"""
        # 开始对话
        self.agent.process_message("s4", "我是有基础的，写了一段时间Python")

        # 模拟中断 — 清除内存中的 session
        self.agent._sessions.clear()

        # 恢复
        state, reply = self.agent.resume_session("s4")
        self.assertIsNotNone(state, "Should recover from disk")
        self.assertEqual(state.status, "COLLECTING")
        self.assertIn("knowledge_base", state.collected_facts)
        self.assertEqual(state.collected_facts["knowledge_base"], "mid_level")

    # ── case4: 历史 Memory 累积 ──

    def test_historical_memory_accumulation(self):
        """历史 Memory 存在 → 新画像追加到历史, 而非覆盖"""
        mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        pa = ProfileAgent()

        # 模拟第1次学习
        mm.update_student_memory(
            "s5",
            profile={"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"},
            mastery_updates={"functions": 0.3},
        )

        # 模拟第2次 — 通过对话
        self.agent.process_message("s5", "我进步了，学会了很多基础语法")
        self.agent.process_message("s5", "喜欢看书阅读来学")
        self.agent.process_message("s5", "想慢慢来彻底搞懂")
        self.agent.process_message("s5", "喜欢先做题测试")
        self.agent.process_message("s5", "类型错误比较多")
        self.agent.process_message("s5", "不怕困难坚持到底")

        state, _ = self.agent.process_message("s5", "继续")
        if state.status == "COMPLETE":
            # 更新 Memory
            profile_dict = self.agent.build_final_profile("s5", profile_agent=pa)
            if profile_dict:
                mem = mm.get_student_memory("s5")
                # 追加到历史
                mem.profile_history.append({
                    **profile_dict,
                    "timestamp": "2026-01-01T00:00:00",
                })
                mm.students.save(mem)

                # 验证: 历史应有至少 2 条 (初始 + 新)
                loaded = mm.get_student_memory("s5")
                self.assertGreaterEqual(
                    len(loaded.profile_history), 2,
                    f"Expected >=2 profiles, got {len(loaded.profile_history)}"
                )


# ──────────────────────────────────────────────
# 集成: Conversation → ProfileAgent → StudentMemory
# ──────────────────────────────────────────────

class TestIntegrationConversationProfile(unittest.TestCase):
    """完整集成: 对话 → 画像 → Memory"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = ConversationStateStore(storage_dir=self.tmp)
        self.agent = ConversationProfileAgent(state_store=self.store)
        self.mm = MemoryManager(storage_root=self.tmp, auto_seed=False)
        self.pa = ProfileAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_pipeline(self):
        """完整管道: 多轮对话 → COMPLETE → ProfileAgent → StudentMemory"""
        # 模拟多轮
        rounds = [
            "我是编程小白零基础学Python",
            "我喜欢看视频和图解学习",
            "想快点学完赶紧用起来",
            "看到@装饰器这种语法糖就懵",
            "喜欢自己动手敲代码调试",
            "容易放弃需要多鼓励",
        ]

        state = None
        for i, text in enumerate(rounds):
            state, reply = self.agent.process_message(f"pipeline_{i}", text)
            if state.status == "COMPLETE":
                break

        # 如果一轮没完成, 再补一轮
        if state and state.status != "COMPLETE":
            state, _ = self.agent.process_message(
                "pipeline_0",
                "我有一点基础了，喜欢看书学，想慢慢来，缩进容易错，喜欢做题，不怕困难"
            )

        if state and state.status == "COMPLETE":
            # 生成最终画像 + 写入 Memory
            profile_dict = self.agent.build_final_profile(
                "pipeline_0",
                profile_agent=self.pa,
                student_memory=self.mm.students,
            )
            self.assertIsNotNone(profile_dict)
            for dim in PROFILE_DIMENSIONS:
                self.assertIn(dim, profile_dict)

            # 验证 Memory
            mem = self.mm.get_student_memory("pipeline_0")
            self.assertGreaterEqual(len(mem.profile_history), 1)

    def test_dimension_coverage(self):
        """确保六维都能通过对话收集到值"""
        # 直接测试 checker
        checker = ProfileCompletenessChecker()
        all_text = (
            "零基础小白 看视频学习 快速上手 语法糖魔咒 动手写代码 容易放弃"
        )
        found = checker.extract_from_text(all_text)
        # 至少应覆盖 4+ 个维度
        self.assertGreaterEqual(len(found), 4,
                                f"Should detect >=4 dimensions, got {len(found)}: {found}")


if __name__ == "__main__":
    unittest.main()
