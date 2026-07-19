"""
Phase 11.5 — CourseKnowledgeBase Loader

Bridges the file-based knowledge_base/ directory with the agent system.
PlannerAgent reads from this instead of hardcoded DEFAULT_KNOWLEDGE_GRAPH.

Capabilities:
- Load markdown chapters with metadata extraction
- Parse resources.json for structured resource catalog
- Parse exercises.json for assessment rubric
- Chapter indexing and search
- Automatic course detection keywords

Usage:
    kb = CourseKnowledgeBase()
    course = kb.load_course("artificial_intelligence_multi_agent_course")
    chapters = kb.get_chapters()
    chapter = kb.get_chapter("chapter_01_intro_ai")
"""

from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

@dataclass
class ChapterInfo:
    """Metadata about a knowledge base chapter."""
    chapter_id: str
    title: str
    file_path: str
    order: int
    word_count: int = 0
    key_concepts: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)
    code_labs: int = 0


@dataclass
class CourseInfo:
    """Complete course information loaded from knowledge base."""
    course_id: str
    title: str
    description: str
    chapters: List[ChapterInfo] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    exercises: Dict[str, Any] = field(default_factory=dict)
    learning_paths: Dict[str, Any] = field(default_factory=dict)
    total_hours: int = 0

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    def to_knowledge_graph(self) -> Dict[str, Any]:
        """Convert to PlannerAgent-compatible knowledge graph format."""
        topics = []
        for ch in self.chapters:
            topics.append({
                "id": ch.chapter_id,
                "title": ch.title,
                "concept": "; ".join(ch.learning_objectives[:2]) if ch.learning_objectives else ch.title,
                "required": [],
                "base_depth": 2,
                "base_minutes": max(15, ch.word_count // 150 * 5),
                "exercise_count": 3,
            })
        # Link chapters sequentially
        for i in range(1, len(topics)):
            topics[i]["required"] = [topics[i - 1]["id"]]

        return {
            self.course_id: {
                "title": self.title,
                "topics": topics,
            }
        }


# ──────────────────────────────────────────────
# CourseKnowledgeBase
# ──────────────────────────────────────────────

class CourseKnowledgeBase:
    """
    File-based course knowledge base loader.

    Loads from: knowledge_base/<course_name>/

    Usage:
        kb = CourseKnowledgeBase("knowledge_base/artificial_intelligence_multi_agent_course")
        course = kb.load()
        plan = planner.plan_from_kb(profile, kb)
    """

    # Default course auto-detection keywords
    COURSE_KEYWORDS: Dict[str, List[str]] = {
        "multi_agent_ai": [
            "multi-agent", "multi agent", "agent system", "agent 系统",
            "multiagent", "多智能体", "多 agent", "智能体开发",
            "智能体", "agent开发", "agent 开发", "ai agent",
            "llm application", "llm app", "大模型应用", "大模型开发",
            "autonomous agent", "自主 agent", "agent architecture",
            "agent 架构", "agent协作", "agent 协作", "agent",
        ],
        "python_advanced": [
            "python", "Python", "装饰器", "闭包", "生成器",
            "迭代器", "decorator", "closure", "generator",
        ],
        "python_basics": [
            "python基础", "Python基础", "入门", "变量",
            "函数", "循环", "条件", "列表", "字典",
        ],
        "python_ai_engineer": [
            "python", "Python", "python ai", "Python AI",
            "ai工程师", "AI工程师", "ai engineer", "AI engineer",
            "python工程师",
            "numpy", "NumPy", "pandas", "Pandas",
            "机器学习", "Machine Learning", "machine learning",
            "神经网络", "neural network", "Neural Network",
            "深度学习", "deep learning", "Deep Learning",
            "大模型", "LLM", "llm", "RAG", "rag",
            "langchain", "LangChain", "CrewAI", "crewai",
            "agent框架", "agent framework",
            "python开发", "Python开发", "脚本开发",
        ],
    }

    def __init__(self, kb_path: str = ""):
        """
        Args:
            kb_path: Path to the course knowledge base directory.
                     Default auto-discovers from knowledge_base/.
        """
        self.kb_path = kb_path or self._auto_discover()
        self._course: Optional[CourseInfo] = None
        self._loaded = False

    def _auto_discover(self) -> str:
        """Auto-discover the first course directory in knowledge_base/."""
        candidates = [
            "knowledge_base/artificial_intelligence_multi_agent_course",
            "knowledge_base/python_for_ai_engineers",
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        return candidates[0]

    # ── Loading ────────────────────────────────

    def load(self) -> CourseInfo:
        """Load the complete course from the knowledge base."""
        if self._loaded and self._course:
            return self._course

        intro = self._read_file("course_intro.md")
        course_id = self._extract_course_id(intro)
        title = self._extract_title(intro)
        description = self._extract_description(intro)

        chapters = self._load_chapters()
        resources = self._load_json("resources.json")
        exercises = self._load_json("exercises.json")

        learning_paths = resources.get("learning_paths", {})
        total_hours = sum(ch.word_count // 150 * 5 for ch in chapters) // 60

        self._course = CourseInfo(
            course_id=course_id,
            title=title,
            description=description,
            chapters=chapters,
            resources=resources,
            exercises=exercises,
            learning_paths=learning_paths,
            total_hours=total_hours,
        )
        self._loaded = True
        return self._course

    def reload(self) -> CourseInfo:
        """Force reload from disk."""
        self._loaded = False
        self._course = None
        return self.load()

    # ── Chapter Loading ─────────────────────────

    def _load_chapters(self) -> List[ChapterInfo]:
        """Load all chapter markdown files from chapters/ directory."""
        chapters_dir = os.path.join(self.kb_path, "chapters")
        if not os.path.isdir(chapters_dir):
            return []

        chapter_files = sorted(
            [f for f in os.listdir(chapters_dir) if f.endswith(".md")],
            key=lambda x: self._extract_chapter_number(x),
        )

        chapters = []
        for order, filename in enumerate(chapter_files, 1):
            filepath = os.path.join(chapters_dir, filename)
            content = self._read_file(filepath)
            if not content:
                continue

            chapter_id = filename.replace(".md", "")
            chapters.append(ChapterInfo(
                chapter_id=chapter_id,
                title=self._extract_chapter_title(content),
                file_path=filepath,
                order=order,
                word_count=len(content.split()),
                key_concepts=self._extract_key_concepts(content),
                learning_objectives=self._extract_learning_objectives(content),
                sections=self._extract_sections(content),
                code_labs=content.count("Code Lab"),
            ))

        return chapters

    # ── Access API ──────────────────────────────

    def get_course(self) -> CourseInfo:
        """Get the loaded course (auto-loads if needed)."""
        if not self._loaded:
            return self.load()
        return self._course  # type: ignore[return-value]

    def get_chapters(self) -> List[ChapterInfo]:
        return self.get_course().chapters

    def get_chapter(self, chapter_id: str) -> Optional[ChapterInfo]:
        for ch in self.get_chapters():
            if ch.chapter_id == chapter_id:
                return ch
        return None

    def get_chapter_content(self, chapter_id: str) -> str:
        """Read the full raw content of a chapter."""
        ch = self.get_chapter(chapter_id)
        if ch and os.path.exists(ch.file_path):
            return self._read_file(ch.file_path)
        return ""

    def get_resources(self) -> Dict[str, Any]:
        return self.get_course().resources

    def get_exercises(self) -> Dict[str, Any]:
        return self.get_course().exercises

    def get_exercises_for_chapter(self, chapter_id: str) -> List[Dict[str, Any]]:
        """Get exercises for a specific chapter."""
        ex = self.get_exercises()
        return ex.get("exercises", {}).get(chapter_id, {}).get("questions", [])

    def get_learning_path(self, profile_type: str) -> Optional[Dict[str, Any]]:
        return self.get_course().learning_paths.get(profile_type)

    def search(self, query: str) -> List[ChapterInfo]:
        """Simple text search across chapter titles and concepts."""
        query_lower = query.lower()
        results = []
        for ch in self.get_chapters():
            score = 0
            if query_lower in ch.title.lower():
                score += 3
            for concept in ch.key_concepts:
                if query_lower in concept.lower():
                    score += 2
            if query_lower in " ".join(ch.learning_objectives).lower():
                score += 1
            if score > 0:
                results.append((score, ch))
        results.sort(key=lambda x: x[0], reverse=True)
        return [ch for _, ch in results]

    def to_knowledge_graph(self) -> Dict[str, Any]:
        """Convert to PlannerAgent.DEFAULT_KNOWLEDGE_GRAPH format."""
        return self.get_course().to_knowledge_graph()

    def get_keywords(self) -> Dict[str, List[str]]:
        """Get course detection keywords."""
        course = self.get_course()
        course_name = course.course_id
        # Build keywords from chapter titles and concepts
        keywords = []
        for ch in course.chapters:
            keywords.append(ch.title.lower())
            for concept in ch.key_concepts:
                keywords.append(concept.lower())
        return {course_name: list(set(keywords))}

    # ── Extraction Helpers ──────────────────────

    def _read_file(self, rel_path: str) -> str:
        path = os.path.join(self.kb_path, rel_path)
        if not os.path.exists(path):
            # Try direct absolute path
            if os.path.exists(rel_path):
                path = rel_path
            else:
                return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _load_json(self, rel_path: str) -> Dict[str, Any]:
        content = self._read_file(rel_path)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        return {}

    @staticmethod
    def _extract_chapter_number(filename: str) -> int:
        m = re.search(r"chapter[_-]?(\d+)", filename)
        return int(m.group(1)) if m else 99

    @staticmethod
    def _extract_course_id(intro: str) -> str:
        m = re.search(r"Course Code:\s*(\S+)", intro)
        raw = m.group(1) if m else "default_course"
        # Normalize: lowercase, hyphens→underscores
        return raw.lower().replace("-", "_")

    @staticmethod
    def _extract_title(intro: str) -> str:
        m = re.search(r"^#\s+(.+)", intro, re.MULTILINE)
        return m.group(1).strip() if m else "Untitled Course"

    @staticmethod
    def _extract_description(intro: str) -> str:
        # Find the first paragraph after the title
        lines = intro.split("\n")
        in_desc = False
        desc_lines = []
        for line in lines:
            if line.startswith("## ") and desc_lines:
                break
            if in_desc and line.strip() and not line.startswith(">"):
                desc_lines.append(line.strip())
            if line.startswith("## Course Description"):
                in_desc = True
                continue
        return " ".join(desc_lines[:3]) if desc_lines else ""

    @staticmethod
    def _extract_chapter_title(content: str) -> str:
        m = re.search(r"^#\s+(.+?)(?:\s*>|\n)", content, re.MULTILINE)
        return m.group(1).strip() if m else "Untitled Chapter"

    @staticmethod
    def _extract_key_concepts(content: str) -> List[str]:
        """Extract key concepts from the key terms section."""
        concepts = []
        in_section = False
        for line in content.split("\n"):
            if "Key Terms" in line:
                in_section = True
                continue
            if in_section and line.startswith("##"):
                break
            if in_section and "**" in line:
                # Extract terms wrapped in bold: **Term**
                terms = re.findall(r"\*\*(.+?)\*\*", line)
                concepts.extend(t.strip() for t in terms)
        return concepts

    @staticmethod
    def _extract_learning_objectives(content: str) -> List[str]:
        objectives = []
        for line in content.split("\n"):
            m = re.match(r"\d+\.\s+\*\*(.+?)\*\*", line)
            if m:
                objectives.append(m.group(1).strip())
                if len(objectives) >= 4:
                    break
        return objectives

    @staticmethod
    def _extract_sections(content: str) -> List[str]:
        return [
            line.strip("# ").strip()
            for line in content.split("\n")
            if line.startswith("## ") and not line.startswith("## Key Terms")
        ]

    # ── Course Detection ─────────────────────────

    def detect_course(self, goal_text: str) -> str:
        """Auto-detect the best matching course from goal text."""
        text = goal_text.lower()
        for course_id in ["multi_agent_ai", "python_advanced", "python_basics"]:
            keywords = self.COURSE_KEYWORDS.get(course_id, [])
            for kw in keywords:
                if kw.lower() in text:
                    return course_id
        return "multi_agent_ai"  # default

    # ── Pretty Print ────────────────────────────

    def summary(self) -> str:
        course = self.get_course()
        lines = [
            f"Course: {course.title} ({course.course_id})",
            f"Chapters: {len(course.chapters)}",
            f"Resources: {len(course.resources.get('resources', {}).get('lecture_notes', []))} lectures",
            f"Exercises: {sum(len(v.get('questions', [])) for v in course.exercises.get('exercises', {}).values())} questions",
            f"Paths: {list(course.learning_paths.keys())}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"CourseKnowledgeBase({os.path.basename(self.kb_path)}, loaded={self._loaded})"


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  CourseKnowledgeBase — Loader Demo      ║")
    print("╚══════════════════════════════════════════╝")
    print()

    kb = CourseKnowledgeBase()
    print(f"KB path: {kb.kb_path}")
    print(f"Loaded: {kb._loaded}")

    course = kb.load()
    print(f"\n{course.title}")
    print(f"  Chapters: {len(course.chapters)}")
    for ch in course.chapters:
        print(f"    [{ch.order}] {ch.title} ({ch.word_count} words, {len(ch.key_concepts)} concepts)")

    print(f"\n  Resources: {len(course.resources.get('resources', {}).get('lecture_notes', []))} lectures")
    exercises = course.exercises.get("exercises", {})
    for ch_id, ex_data in exercises.items():
        print(f"    {ch_id}: {len(ex_data.get('questions', []))} questions")

    kg = kb.to_knowledge_graph()
    print(f"\n  Knowledge Graph topics: {len(list(kg.values())[0]['topics'])}")

    # Search
    results = kb.search("agent")
    print(f"\n  Search 'agent': {len(results)} chapters found")
    for r in results:
        print(f"    - {r.title}")
