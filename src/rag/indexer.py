"""
Phase 4.3 — TF-IDF Index

Builds a lightweight in-memory search index from Chunks.
Uses sklearn.feature_extraction.text.TfidfVectorizer.

Zero external services. 46K text indexed in <100ms.
"""

from __future__ import annotations
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.rag.chunker import Chunk


class TFIDFIndex:
    """
    TF-IDF index over a list of Chunks.

    Usage:
        index = TFIDFIndex()
        index.build(chunks)

        results = index.search("Agent communication patterns", top_k=3)
        # → [(chunk, score), ...]  —  sorted by score descending
    """

    def __init__(self):
        self._chunks: List[Chunk] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix: np.ndarray | None = None
        self._built = False

    @property
    def is_built(self) -> bool:
        return self._built

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def build(self, chunks: List[Chunk]) -> None:
        """
        Build the TF-IDF index from chunks.

        Args:
            chunks: List of Chunk objects to index.
        """
        if not chunks:
            self._built = True
            return

        self._chunks = list(chunks)
        texts = [c.text for c in chunks]

        self._vectorizer = TfidfVectorizer(
            max_features=2000,
            strip_accents="unicode",
            stop_words=None,  # Keep all words for technical content
            ngram_range=(1, 2),  # Unigrams + bigrams for phrase matching
        )

        try:
            self._matrix = self._vectorizer.fit_transform(texts)
        except ValueError:
            # Fallback if texts are too short / empty
            self._matrix = None

        self._built = True

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for chunks most similar to the query.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of (Chunk, score) tuples, sorted by score descending.
        """
        if not self._built or self._matrix is None or not self._chunks:
            return []

        try:
            query_vec = self._vectorizer.transform([query])
        except Exception:
            return []

        # Cosine similarity between query vector and all document vectors
        scores = cosine_similarity(query_vec, self._matrix).flatten()

        # Get top-k indices sorted by score descending
        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:top_k]

        results: List[Tuple[Chunk, float]] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0.0:  # Skip zero-score matches
                results.append((self._chunks[idx], score))

        return results
