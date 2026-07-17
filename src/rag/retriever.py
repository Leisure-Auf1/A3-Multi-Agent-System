"""
Phase 4.3 — Retriever Interface + SimpleTFIDFRetriever

Lazy singleton pattern: first call to get_retriever()
builds the index; subsequent calls return the cached instance.
"""

from __future__ import annotations
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from src.rag.chunker import Chunk, MarkdownChunker
from src.rag.indexer import TFIDFIndex


# ──────────────────────────────────────────────
# Retriever Interface
# ──────────────────────────────────────────────

class Retriever(ABC):
    """Abstract retriever for knowledge base content."""

    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> List[Chunk]:
        """Retrieve top-k chunks relevant to the query."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the retriever is built and ready."""
        ...


# ──────────────────────────────────────────────
# SimpleTFIDFRetriever
# ──────────────────────────────────────────────

_DEFAULT_KB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "knowledge_base",
    "artificial_intelligence_multi_agent_course",
    "chapters",
)


class SimpleTFIDFRetriever(Retriever):
    """
    TF-IDF based retriever over markdown chapters.

    Builds index from chunks on first search() call.
    """

    def __init__(self, kb_path: str = ""):
        self._kb_path = kb_path or _DEFAULT_KB_PATH
        self._chunks: List[Chunk] = []
        self._index = TFIDFIndex()
        self._built = False

    def _ensure_built(self) -> None:
        """Lazy build: load chunks and build index on first use."""
        if self._built:
            return
        self._chunks = MarkdownChunker.chunk_directory(self._kb_path)
        if self._chunks:
            self._index.build(self._chunks)
        self._built = True

    def search(self, query: str, top_k: int = 3) -> List[Chunk]:
        self._ensure_built()
        if not self._chunks:
            return []
        results = self._index.search(query, top_k=top_k)
        return [chunk for chunk, _score in results]

    @property
    def is_available(self) -> bool:
        self._ensure_built()
        return len(self._chunks) > 0 and self._index.is_built

    @property
    def chunk_count(self) -> int:
        self._ensure_built()
        return len(self._chunks)

    def reload(self) -> None:
        """Force rebuild index (e.g. after KB file changes)."""
        self._built = False
        self._chunks = []
        self._index = TFIDFIndex()


# ──────────────────────────────────────────────
# Lazy Singleton
# ──────────────────────────────────────────────

_retriever: Optional[Retriever] = None


def get_retriever(kb_path: str = "") -> Retriever:
    """
    Get the global TF-IDF retriever singleton.

    First call: builds index from knowledge_base/ chapters.
    Subsequent calls: returns cached instance.
    """
    global _retriever
    if _retriever is None:
        _retriever = SimpleTFIDFRetriever(kb_path)
    return _retriever


def reset_retriever() -> None:
    """Reset the global retriever (useful for testing)."""
    global _retriever
    _retriever = None
