"""
Phase 4.3 — Markdown Chunker

Splits course markdown chapters into semantic chunks
by ## heading sections. Each chunk preserves source
file and section title metadata.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class Chunk:
    """A single retrievable text chunk from a course chapter."""

    text: str
    source: str  # filename, e.g. "chapter_05_multi_agent_architecture.md"
    section: str  # heading title, e.g. "Agent Communication"

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "source": self.source,
            "section": self.section,
        }


class MarkdownChunker:
    """
    Splits markdown content into chunks by ## heading boundaries.

    Usage:
        chunks = MarkdownChunker.chunk(markdown_text, source="chapter_01.md")
        # → [Chunk("...", "chapter_01.md", "1.1 What is AI?"), ...]
    """

    @staticmethod
    def chunk(content: str, source: str = "") -> List[Chunk]:
        """
        Split markdown by ## headings. Each chunk = heading line + body
        until the next ## heading or end of content.

        Skips:
          - Top-level # headings (chapter title) — merged into content
          - Empty sections
          - Sections shorter than 20 chars (noise)
        """
        lines = content.split("\n")
        chunks: List[Chunk] = []
        current_section = ""
        current_lines: List[str] = []

        for line in lines:
            if line.startswith("## ") and not line.startswith("### "):
                # Flush previous section
                if current_lines:
                    text = "\n".join(current_lines).strip()
                    if len(text) >= 20:
                        chunks.append(Chunk(
                            text=text,
                            source=source,
                            section=current_section,
                        ))
                current_section = line[3:].strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        # Flush last section
        if current_lines:
            text = "\n".join(current_lines).strip()
            if len(text) >= 20:
                chunks.append(Chunk(
                    text=text,
                    source=source,
                    section=current_section,
                ))

        return chunks

    @staticmethod
    def chunk_file(filepath: str) -> List[Chunk]:
        """Read a markdown file and chunk it."""
        import os
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        source = os.path.basename(filepath)
        return MarkdownChunker.chunk(content, source=source)

    @staticmethod
    def chunk_directory(dirpath: str) -> List[Chunk]:
        """Chunk all .md files in a directory (sorted by name)."""
        import os
        all_chunks: List[Chunk] = []
        if not os.path.isdir(dirpath):
            return all_chunks
        for filename in sorted(os.listdir(dirpath)):
            if filename.endswith(".md") and not filename.startswith("_"):
                filepath = os.path.join(dirpath, filename)
                all_chunks.extend(MarkdownChunker.chunk_file(filepath))
        return all_chunks
