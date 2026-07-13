""""
Phase 11 — ResourceGenerationAgent

Generates 6 types of learning resources from course content:
1. Course Notes — Structured lecture notes with key concepts
2. Mind Map — Mermaid-format visual knowledge maps
3. Exercises — Auto-generated questions with rubrics
4. Code Labs — Runnable code exercises with expected outputs
5. Video Scripts — Narration scripts for educational videos
6. Extended Reading — Curated references from knowledge base (Phase 14)

Design:
- Each generator is a separate method with a clear input/output contract
- All generators are rule-based (no LLM dependency for generation)
- LLM enrichment is optional via provider injection
- Outputs follow the ContentAgent 5-asset contract format
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.llm.provider import LLMProvider, LLMResponse


# ──────────────────────────────────────────────
# Resource Data Models
# ──────────────────────────────────────────────

@dataclass
class CourseNotes:
    """Generated course notes resource."""
    title: str
    topic: str
    sections: List[Dict[str, str]] = field(default_factory=list)
    key_concepts: List[str] = field(default_factory=list)
    summary: str = ""
    estimated_read_minutes: int = 15

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", f"**Topic:** {self.topic}", ""]
        for s in self.sections:
            lines.append(f"## {s['heading']}")
            lines.append(s["content"])
            lines.append("")
        lines.append("## Key Concepts")
        for c in self.key_concepts:
            lines.append(f"- **{c}**")
        lines.append("")
        if self.summary:
            lines.append(f"> {self.summary}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "document",
            "title": self.title,
            "topic": self.topic,
            "sections": self.sections,
            "key_concepts": self.key_concepts,
            "summary": self.summary,
            "estimated_read_minutes": self.estimated_read_minutes,
            "format": "markdown",
        }


@dataclass
class MindMap:
    """Generated mind map resource (Mermaid format)."""
    title: str
    central_topic: str
    branches: List[Dict[str, Any]] = field(default_factory=list)
    mermaid_code: str = ""

    def to_markdown(self) -> str:
        if not self.mermaid_code:
            self._build_mermaid()
        return f"```mermaid\n{self.mermaid_code}\n```"

    def _build_mermaid(self):
        lines = ["mindmap", f"  root(({self.central_topic}))"]
        for branch in self.branches:
            lines.append(f"    {branch['name']}")
            for child in branch.get("children", []):
                lines.append(f"      {child}")
        self.mermaid_code = "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        if not self.mermaid_code:
            self._build_mermaid()
        return {
            "type": "mindmap",
            "title": self.title,
            "central_topic": self.central_topic,
            "branches": self.branches,
            "mermaid_code": self.mermaid_code,
            "format": "mermaid",
        }


@dataclass
class Exercise:
    """Generated exercise resource."""
    title: str
    questions: List[Dict[str, Any]] = field(default_factory=list)
    total_points: int = 0
    estimated_minutes: int = 15

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", ""]
        for i, q in enumerate(self.questions, 1):
            lines.append(f"## Question {i} ({q.get('points', 0)} pts)")
            lines.append(q["question"])
            lines.append("")
            if "hint" in q:
                lines.append(f"*Hint: {q['hint']}*")
            if "rubric" in q:
                lines.append("**Grading Rubric:**")
                for r in q["rubric"]:
                    lines.append(f"- {r}")
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "exercise",
            "title": self.title,
            "questions": self.questions,
            "total_points": self.total_points,
            "estimated_minutes": self.estimated_minutes,
            "format": "markdown",
        }


@dataclass
class CodeLab:
    """Generated code lab resource."""
    title: str
    description: str
    language: str = "python"
    starter_code: str = ""
    expected_output: str = ""
    hints: List[str] = field(default_factory=list)
    solution: str = ""

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            self.description,
            "",
            "## Starter Code",
            f"```{self.language}",
            self.starter_code,
            "```",
            "",
            "## Expected Output",
            "```",
            self.expected_output,
            "```",
        ]
        if self.hints:
            lines.append("")
            lines.append("## Hints")
            for i, h in enumerate(self.hints, 1):
                lines.append(f"{i}. {h}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "code",
            "title": self.title,
            "language": self.language,
            "description": self.description,
            "starter_code": self.starter_code,
            "expected_output": self.expected_output,
            "hints": self.hints,
            "format": "markdown",
        }


@dataclass
class VideoScript:
    """Generated video script resource."""
    title: str
    duration_seconds: int = 300
    scenes: List[Dict[str, str]] = field(default_factory=list)
    narration: str = ""

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            f"**Duration:** {self.duration_seconds // 60}:{self.duration_seconds % 60:02d}",
            "",
        ]
        for i, scene in enumerate(self.scenes, 1):
            lines.append(f"## Scene {i}: {scene.get('title', '')} ({scene.get('duration', '')})")
            lines.append(f"**Visual:** {scene.get('visual', '')}")
            lines.append(f"**Narration:** {scene.get('narration', '')}")
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "video",
            "title": self.title,
            "duration_seconds": self.duration_seconds,
            "scenes": self.scenes,
            "format": "markdown",
        }


# ──────────────────────────────────────────────
# Resource Generation Agent
# ──────────────────────────────────────────────

class ResourceGenerationAgent:
    """
    Generates 6 types of learning resources from structured input.

    The agent is primarily rule-based — it structures and formats content
    without requiring LLM calls. An optional LLM provider can enrich outputs.

    Usage:
        agent = ResourceGenerationAgent()
        notes = agent.generate_course_notes(
            title="Intro to AI",
            topic="AI Fundamentals",
            concepts=["Machine Learning", "Neural Networks", "Transformers"],
        )
        print(notes.to_markdown())
    """

    # ── Resource Type Registry ──
    RESOURCE_TYPES = {
        "document": {"icon": "📄", "label": "Course Notes"},
        "mindmap": {"icon": "🧠", "label": "Mind Map"},
        "exercise": {"icon": "✏️", "label": "Exercises"},
        "code": {"icon": "💻", "label": "Code Lab"},
        "video": {"icon": "🎬", "label": "Video Script"},
        "extended_reading": {"icon": "📖", "label": "Extended Reading"},
    }

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider
        self._generation_history: List[Dict[str, Any]] = []

    # ── Generator 1: Course Notes ──

    def generate_course_notes(
        self,
        title: str,
        topic: str,
        concepts: List[str],
        content_blocks: Optional[List[Dict[str, str]]] = None,
        enrich: bool = False,
    ) -> CourseNotes:
        """Generate structured course notes."""
        sections = []
        if content_blocks:
            for block in content_blocks:
                content = block.get("content", "")
                if enrich and self.llm:
                    enriched = self._enrich_content(content, topic)
                    content = enriched if enriched else content
                sections.append({
                    "heading": block.get("heading", "Section"),
                    "content": content,
                })
        else:
            for concept in concepts:
                sections.append({
                    "heading": concept,
                    "content": self._default_section_content(concept, topic),
                })

        notes = CourseNotes(
            title=title, topic=topic, sections=sections, key_concepts=concepts,
            summary=self._generate_summary(concepts, topic),
            estimated_read_minutes=max(5, len(sections) * 3),
        )
        self._record("course_notes", notes.to_dict())
        return notes

    def _default_section_content(self, concept: str, topic: str) -> str:
        return (
            f"{concept} is a fundamental concept in {topic}. "
            f"Understanding {concept} provides the foundation for "
            f"advanced topics in this field."
        )

    def _generate_summary(self, concepts: List[str], topic: str) -> str:
        concept_list = ", ".join(concepts[:5])
        if len(concepts) > 5:
            concept_list += f", and {len(concepts) - 5} more"
        return (
            f"This module covers {len(concepts)} key concepts in {topic}: "
            f"{concept_list}. Each section provides detailed explanations "
            f"with examples and exercises."
        )

    def _enrich_content(self, content: str, topic: str) -> Optional[str]:
        if not self.llm:
            return None
        try:
            response = self.llm.generate(
                prompt=f"Expand this educational content about {topic}. Add concrete examples. Keep concise (2-3 paragraphs):\n\n{content}",
                system_prompt="You are an expert educator. Be clear and engaging.",
                temperature=0.5, max_tokens=500,
            )
            return response.content if response.success else None
        except Exception:
            return None

    # ── Generator 2: Mind Map ──

    def generate_mind_map(
        self, title: str, central_topic: str, subtopics: List[Dict[str, Any]],
    ) -> MindMap:
        mindmap = MindMap(title=title, central_topic=central_topic, branches=subtopics)
        mindmap._build_mermaid()
        self._record("mind_map", mindmap.to_dict())
        return mindmap

    # ── Generator 3: Exercises ──

    def generate_exercises(
        self, title: str, topic: str, num_questions: int = 3, difficulty: str = "intermediate",
    ) -> Exercise:
        templates = self._get_question_templates(difficulty)
        questions = []
        for i in range(min(num_questions, len(templates))):
            tmpl = templates[i]
            questions.append({
                "question": tmpl["template"].format(topic=topic),
                "points": tmpl.get("points", 10),
                "hint": tmpl.get("hint", ""),
                "rubric": tmpl.get("rubric", []),
                "type": tmpl.get("type", "short_answer"),
            })
        exercise = Exercise(
            title=title, questions=questions,
            total_points=sum(q["points"] for q in questions),
            estimated_minutes=num_questions * 5,
        )
        self._record("exercises", exercise.to_dict())
        return exercise

    def _get_question_templates(self, difficulty: str) -> List[Dict[str, Any]]:
        return [
            {"template": "Explain {topic} in your own words. Include a concrete example.", "points": 10, "type": "explanation", "rubric": ["Accurate definition", "Concrete example", "Clarity"]},
            {"template": "What are the three most important aspects of {topic}? Justify each with a real-world scenario.", "points": 15, "type": "analysis", "rubric": ["3 aspects", "Justification", "Real-world scenarios"]},
            {"template": "Compare and contrast two different approaches to {topic}.", "points": 12, "type": "comparison", "rubric": ["Two approaches", "Accurate comparison", "Reasoning"]},
            {"template": "Implement a minimal example of {topic} in Python. Include comments.", "points": 20, "type": "implementation", "hint": "Focus on clarity. 20-30 lines.", "rubric": ["Runnable code", "Comments", "Minimal example"]},
            {"template": "Identify a common misconception about {topic} and explain why it's wrong.", "points": 8, "type": "debugging", "rubric": ["Identifies misconception", "Clear explanation", "Correct understanding"]},
        ]

    # ── Generator 4: Code Labs ──

    def generate_code_lab(
        self, title: str, description: str, language: str = "python",
        starter_code: str = "", expected_output: str = "", hints: Optional[List[str]] = None,
    ) -> CodeLab:
        lab = CodeLab(title=title, description=description, language=language,
                       starter_code=starter_code, expected_output=expected_output, hints=hints or [])
        self._record("code_lab", lab.to_dict())
        return lab

    # ── Generator 5: Video Scripts ──

    def generate_video_script(
        self, title: str, topic: str, key_points: List[str], duration_seconds: int = 300,
    ) -> VideoScript:
        scene_duration = max(15, duration_seconds // len(key_points))
        scenes = []
        for i, point in enumerate(key_points, 1):
            scenes.append({
                "title": f"Point {i}: {point[:40]}",
                "duration": f"{scene_duration}s",
                "visual": f"Slide {i}: {point} — diagram, code, or animation",
                "narration": f"Now let's explore {point}. {self._expand_point(point, topic)}",
            })
        script = VideoScript(title=title, duration_seconds=duration_seconds, scenes=scenes,
                             narration="\n\n".join(s["narration"] for s in scenes))
        self._record("video_script", script.to_dict())
        return script

    def _expand_point(self, point: str, topic: str) -> str:
        return f"This is a critical concept in {topic}. Understanding {point} will help build a solid foundation."

    # ── Generator 6: Extended Reading (Phase 14) ──

    def generate_extended_reading(
        self, title: str, topic: str = "", chapter_ids=None, difficulty: str = "intermediate",
        kb_loader: Any = None,
    ) -> Dict[str, Any]:
        """Generate extended reading list from curated references (no LLM)."""
        if kb_loader:
            try:
                resources_data = kb_loader.get_resources()
                all_refs = resources_data.get("resources", {}).get("external_references", [])
            except Exception:
                all_refs = self._get_default_references()
        else:
            all_refs = self._get_default_references()

        if chapter_ids:
            all_refs = [r for r in all_refs if r.get("chapter") in chapter_ids]

        references = []
        for ref in all_refs[:5]:
            references.append({
                "title": ref.get("title", ""),
                "source": ref.get("url", ""),
                "type": ref.get("type", "paper"),
                "difficulty": ref.get("difficulty", "intermediate"),
                "relevance": f"Core reading for understanding {topic or ref.get('title', 'this topic')}.",
                "estimated_read_minutes": 30,
            })

        result = {
            "type": "extended_reading", "title": title,
            "summary": f"Curated references for deeper understanding of {topic}.",
            "references": references,
            "discussion_prompts": [
                f"How does the architecture described in the readings compare to A3's design?",
                f"What trade-offs exist between the approaches in the references?",
                f"Which reference is most relevant to your current learning goals? Why?",
            ][:len(references)],
            "estimated_total_minutes": sum(r["estimated_read_minutes"] for r in references),
            "difficulty": difficulty, "format": "json",
        }
        self._record("extended_reading", result)
        return result

    def _get_default_references(self) -> List[Dict[str, Any]]:
        """Hardcoded fallback references when KB is unavailable."""
        return [
            {"title": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762", "type": "paper", "chapter": 2, "difficulty": "advanced"},
            {"title": "Chain-of-Thought Prompting", "url": "https://arxiv.org/abs/2201.11903", "type": "paper", "chapter": 3, "difficulty": "intermediate"},
            {"title": "RAG: A Survey", "url": "https://arxiv.org/abs/2312.10997", "type": "paper", "chapter": 4, "difficulty": "intermediate"},
            {"title": "Generative Agents", "url": "https://arxiv.org/abs/2304.03442", "type": "paper", "chapter": 5, "difficulty": "advanced"},
            {"title": "HELM: Holistic Evaluation", "url": "https://arxiv.org/abs/2211.09110", "type": "paper", "chapter": 6, "difficulty": "intermediate"},
        ]

    # ── Batch Generation ──

    def generate_all(self, topic: str, concepts: List[str]) -> Dict[str, Any]:
        """Generate all 6 resource types for a topic."""
        return {
            "document": self.generate_course_notes(title=f"{topic} — Course Notes", topic=topic, concepts=concepts).to_dict(),
            "mindmap": self.generate_mind_map(title=f"{topic} — Mind Map", central_topic=topic, subtopics=[{"name": c, "children": []} for c in concepts[:6]]).to_dict(),
            "exercise": self.generate_exercises(title=f"{topic} — Exercises", topic=topic, num_questions=3).to_dict(),
            "code": self.generate_code_lab(title=f"{topic} — Code Lab", description=f"Implement a simple {topic} example.", language="python", starter_code=f"# TODO: implement {topic} example\n", expected_output="Expected output: [your result here]").to_dict(),
            "video": self.generate_video_script(title=f"{topic} — Video Script", topic=topic, key_points=concepts[:4]).to_dict(),
            "extended_reading": self.generate_extended_reading(title=f"{topic} — Extended Reading", topic=topic),
        }

    # ── History ──

    def _record(self, resource_type: str, data: Dict[str, Any]):
        self._generation_history.append({
            "type": resource_type,
            "title": data.get("title", ""),
            "timestamp": __import__("time").time(),
        })

    @property
    def history(self) -> List[Dict[str, Any]]:
        return self._generation_history

    @classmethod
    def resource_type_info(cls, resource_type: str) -> Dict[str, str]:
        return cls.RESOURCE_TYPES.get(resource_type, {"icon": "❓", "label": "Unknown"})


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  ResourceGenerationAgent — Demo         ║")
    print("╚══════════════════════════════════════════╝")
    print()

    agent = ResourceGenerationAgent()

    # Demo: Generate all 6 types
    all_resources = agent.generate_all(
        topic="Prompt Engineering",
        concepts=["Zero-shot", "Few-shot", "Chain-of-Thought", "System Prompts"],
    )
    print("─── All Resources Generated ───")
    for rtype, data in all_resources.items():
        info = agent.resource_type_info(data["type"])
        print(f"  {info['icon']} {info['label']}: {data['title']}")

    print(f"\nGeneration history: {len(agent.history)} items")

    # Demo: Extended reading
    reading = agent.generate_extended_reading(
        title="Further Reading: Multi-Agent AI", topic="Multi-Agent Architecture"
    )
    print(f"\n─── Extended Reading ───")
    print(f"References: {len(reading['references'])}")
    for ref in reading['references']:
        print(f"  - {ref['title'][:60]}... ({ref['difficulty']})")
