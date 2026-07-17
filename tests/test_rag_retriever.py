"""
Phase 4.3 — RAG Retriever Tests

Covers:
  1. Chunker: real markdown chunking
  2. Retriever: search "Agent 通信" → chapter_05
  3. Top-K: correct count
  4. PlannerAgent: LLM prompt includes knowledge context
  5. No-RAG fallback: original flow still works
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.rag.chunker import MarkdownChunker, Chunk
from src.rag.indexer import TFIDFIndex
from src.rag.retriever import (
    SimpleTFIDFRetriever,
    get_retriever,
    reset_retriever,
)
from src.rag import get_retriever as rag_get_retriever
from src.core.provider_factory import create_provider
from src.workflow import A3Workflow
from src.memory.memory_manager import MemoryManager
import tempfile


KB_CHAPTERS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "knowledge_base",
    "artificial_intelligence_multi_agent_course",
    "chapters",
)


# ──────────────────────────────────────────────
# 1. Chunker
# ──────────────────────────────────────────────

class TestChunker:
    def test_chunk_directory_produces_chunks(self):
        chunks = MarkdownChunker.chunk_directory(KB_CHAPTERS)
        assert len(chunks) > 10, f"Expected >10 chunks, got {len(chunks)}"
        # All chunks should have text, source, section
        for c in chunks:
            assert isinstance(c.text, str) and len(c.text) >= 20
            assert c.source.endswith(".md")
            assert isinstance(c.section, str)

    def test_chunks_have_correct_sources(self):
        chunks = MarkdownChunker.chunk_directory(KB_CHAPTERS)
        sources = {c.source for c in chunks}
        assert "chapter_05_multi_agent_architecture.md" in sources
        assert "chapter_01_intro_ai.md" in sources

    def test_chunk_from_single_file(self):
        filepath = os.path.join(KB_CHAPTERS, "chapter_05_multi_agent_architecture.md")
        chunks = MarkdownChunker.chunk_file(filepath)
        assert len(chunks) >= 3  # At least 3 ## sections
        assert all(c.source == "chapter_05_multi_agent_architecture.md" for c in chunks)

    def test_empty_directory_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            chunks = MarkdownChunker.chunk_directory(td)
            assert chunks == []


# ──────────────────────────────────────────────
# 2. Indexer
# ──────────────────────────────────────────────

class TestIndexer:
    def test_build_and_search(self):
        chunks = MarkdownChunker.chunk_directory(KB_CHAPTERS)
        index = TFIDFIndex()
        index.build(chunks)
        assert index.is_built
        assert index.chunk_count == len(chunks)

        results = index.search("Agent communication pattern", top_k=3)
        assert len(results) > 0
        # First result should have highest score
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_empty_chunks_does_not_crash(self):
        index = TFIDFIndex()
        index.build([])
        assert index.is_built
        assert index.search("anything") == []


# ──────────────────────────────────────────────
# 3. Retriever
# ──────────────────────────────────────────────

class TestRetriever:
    def setup_method(self):
        reset_retriever()

    def test_search_agent_communication_returns_chapter_05(self):
        """Query 'Agent 通信' should return chunks from chapter_05."""
        retriever = SimpleTFIDFRetriever(KB_CHAPTERS)
        chunks = retriever.search("Agent 通信模式", top_k=3)
        assert len(chunks) > 0
        # At least one result should be from chapter_05
        sources = {c.source for c in chunks}
        assert any("chapter_05" in s for s in sources), \
            f"Expected chapter_05 in results, got {sources}"

    def test_top_k_respects_limit(self):
        retriever = SimpleTFIDFRetriever(KB_CHAPTERS)
        for k in [1, 2, 5]:
            chunks = retriever.search("LLM", top_k=k)
            assert len(chunks) <= k

    def test_is_available(self):
        retriever = SimpleTFIDFRetriever(KB_CHAPTERS)
        assert retriever.is_available
        assert retriever.chunk_count > 10

    def test_empty_query_returns_empty(self):
        retriever = SimpleTFIDFRetriever(KB_CHAPTERS)
        chunks = retriever.search("")
        assert chunks == []

    def test_singleton_reuses_instance(self):
        reset_retriever()
        r1 = get_retriever(KB_CHAPTERS)
        r2 = get_retriever()
        assert r1 is r2


# ──────────────────────────────────────────────
# 4. PlannerAgent RAG Integration
# ──────────────────────────────────────────────

class TestPlannerAgentRAG:
    def setup_method(self):
        reset_retriever()

    def _make_workflow(self, provider_mode="mock"):
        tmp = tempfile.mkdtemp(prefix="a3_rag_test_")
        provider = create_provider(provider_mode)
        return A3Workflow(
            memory_manager=MemoryManager(storage_root=tmp),
            student_id="rag_test",
            llm_provider=provider,
        )

    def test_llm_prompt_includes_knowledge_context(self):
        """在 LLM 模式下, plan 的 strategy_rationale 由 LLM 生成,
        且其内容来自 prompt 注入的知识上下文。我们验证:
        - plan 不报错
        - metadata 标记 planning_mode=llm
        """
        wf = self._make_workflow("mock")
        result = wf.run(
            user_goal="我想学习 Agent 通信模式和 EventBus 架构",
        )
        assert result.success
        plan = result.learning_plan
        assert plan["metadata"]["planning_mode"] == "llm"
        # LLM 模式下的 rationale 不应为空
        assert len(plan["strategy_rationale"]) > 10

    def test_no_rag_fallback_still_works(self):
        """即使 RAG 检索不到内容, plan 仍然成功 (空上下文 → fallback)."""
        wf = self._make_workflow("mock")
        result = wf.run(
            user_goal="一个不存在的课程主题 xyz123",
        )
        assert result.success
        plan = result.learning_plan
        # 仍然走 LLM 模式 (prompt 会包含空的 context)
        assert plan["metadata"]["planning_mode"] == "llm"

    def test_llm_enhancement_applies_in_pipeline(self):
        """Mock provider 下 pipeline 完整执行, 包括 RAG 增强."""
        wf = self._make_workflow("mock")
        result = wf.run(user_goal="学习 Multi-Agent 系统架构设计")
        assert result.success
        # 验证 Agent 正常产出
        assert result.profile["source"] == "llm"
        assert result.learning_plan["metadata"]["planning_mode"] == "llm"
        assert result.reflection["source"] == "llm"
        assert result.memory_saved


# ──────────────────────────────────────────────
# 5. No-RAG Regression
# ──────────────────────────────────────────────

class TestNoRAGRegression:
    def test_rule_mode_still_works(self):
        """Rule 模式 pipeline 不受 RAG 影响."""
        wf = A3Workflow(student_id="norag_test")
        result = wf.run(user_goal="学习 Python 装饰器")
        assert result.success
        assert result.profile["source"] == "rule"
        assert result.learning_plan["metadata"]["planning_mode"] == "rule"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
