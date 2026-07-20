"""
Phase 9.2 — TutorAgent

Conversational tutor agent. Explains concepts, answers questions,
adapts to learning style, and generates Socratic follow-ups.

Uses Veritas-Core LLMProvider — zero Runtime modifications.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Iterator
from datetime import datetime, timezone


@dataclass
class TutorContext:
    """Context for a tutoring session."""
    student_profile: Dict[str, Any] = field(default_factory=dict)
    learning_goal: str = ""
    current_topic: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)


@dataclass
class TutorResponse:
    """A single tutor response."""
    content: str
    follow_up_questions: List[str] = field(default_factory=list)
    suggested_resources: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.8
    teaching_style: str = "explanation"
    tokens_used: int = 0
    latency_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "follow_up_questions": self.follow_up_questions,
            "suggested_resources": self.suggested_resources,
            "confidence": self.confidence,
            "teaching_style": self.teaching_style,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
        }


LEARNING_STYLES = {
    "visual_dominant": "Use vivid imagery, diagrams (described), and spatial metaphors. Emphasize structure and patterns.",
    "auditory_dominant": "Use rhythmic language, verbal analogies, and dialogue. Emphasize sound patterns and mnemonics.",
    "reading_writing": "Use precise terminology, structured outlines, and clear examples. Emphasize definitions and lists.",
    "code_sandbox": "Use code examples, function signatures, and practical exercises. Emphasize hands-on coding.",
    "default": "Use clear explanations with concrete examples and follow-up questions.",
}

TEACHING_STYLES = ["explanation", "socratic", "example_driven", "analogy", "step_by_step"]


class TutorAgent:
    """Conversational AI tutor with multi-style teaching."""

    def __init__(self, llm_provider: Any = None):
        self._llm = llm_provider
        self._default_style = "explanation"

    @property
    def name(self) -> str:
        return "tutor"

    def _get_style_instruction(self, profile: Dict[str, Any]) -> str:
        """Map student profile to teaching style instruction."""
        cognitive = profile.get("cognitive_style", "default")
        return LEARNING_STYLES.get(cognitive, LEARNING_STYLES["default"])

    def _build_system_prompt(self, ctx: TutorContext) -> str:
        """Build a structured system prompt for the tutor."""
        style = self._get_style_instruction(ctx.student_profile)
        gaps = ", ".join(ctx.knowledge_gaps) if ctx.knowledge_gaps else "none identified"
        level = ctx.student_profile.get("knowledge_base", "beginner")

        return f"""You are a patient, knowledgeable AI tutor. Your student is at '{level}' level.

Teaching approach: {style}
Current topic: {ctx.current_topic or ctx.learning_goal or 'general learning'}
Known knowledge gaps: {gaps}

Guidelines:
1. Start with a brief, engaging explanation of the concept.
2. Provide 1-2 concrete examples that match the student's level.
3. End with 1-2 follow-up questions to check understanding (Socratic method).
4. If the student seems confused, simplify — don't add complexity.
5. Keep responses focused (2-4 paragraphs max).
6. Use the student's preferred learning style as described above.

Do NOT provide generic advice. Tailor every response to this specific student."""

    def _build_user_prompt(self, user_message: str, ctx: TutorContext) -> str:
        parts = []
        if ctx.learning_goal:
            parts.append(f"Student's learning goal: {ctx.learning_goal}")
        if ctx.current_topic:
            parts.append(f"Current topic: {ctx.current_topic}")
        parts.append(f"\nStudent's question: {user_message}")
        return "\n".join(parts)

    def explain(self, question: str, ctx: Optional[TutorContext] = None) -> TutorResponse:
        """Generate a tutor response (non-streaming)."""
        import time
        ctx = ctx or TutorContext()
        start = time.time()

        if self._llm is None:
            return self._fallback_explain(question, ctx)

        system_prompt = self._build_system_prompt(ctx)
        user_prompt = self._build_user_prompt(question, ctx)

        try:
            resp = self._llm.generate(user_prompt, system_prompt=system_prompt)
            content = resp.content if hasattr(resp, 'content') else str(resp)
        except Exception:
            content = ""

        # Fallback if LLM returns empty or unavailable
        if not content or not content.strip():
            return self._fallback_explain(question, ctx)

        return TutorResponse(
            content=content,
            follow_up_questions=self._extract_followups(content),
            teaching_style=self._detect_style(content),
            latency_ms=int((time.time() - start) * 1000),
        )

    def explain_stream(self, question: str, ctx: Optional[TutorContext] = None):
        """Generator that yields text chunks as they arrive."""
        ctx = ctx or TutorContext()

        if self._llm is None:
            resp = self._fallback_explain(question, ctx)
            yield resp.content
            return

        system_prompt = self._build_system_prompt(ctx)
        user_prompt = self._build_user_prompt(question, ctx)

        try:
            if hasattr(self._llm, 'generate_stream'):
                for chunk in self._llm.generate_stream(user_prompt, system_prompt=system_prompt):
                    yield chunk
            else:
                resp = self._llm.generate(user_prompt, system_prompt=system_prompt)
                content = resp.content if hasattr(resp, 'content') else str(resp)
                yield content
        except Exception:
            resp = self._fallback_explain(question, ctx)
            yield resp.content

    def _fallback_explain(self, question: str, ctx: TutorContext) -> TutorResponse:
        """Rule-based fallback when no LLM provider is available."""
        topic = ctx.current_topic or "the topic"
        return TutorResponse(
            content=(
                f"Great question about {topic}! Let me explain the key concepts:\n\n"
                f"1. **Core Idea**: Think of this as building blocks — each concept "
                f"supports the next.\n\n"
                f"2. **Key Point**: Focus on understanding WHY before HOW. "
                f"The 'why' is what makes the 'how' stick.\n\n"
                f"3. **Your Turn**: Try to explain {topic} in your own words. "
                f"What part is clearest? What's still fuzzy?\n\n"
                f"This is a rule-based response. For richer tutoring, "
                f"connect an LLM provider."
            ),
            follow_up_questions=[
                f"What's your current understanding of {topic}?",
                f"Can you give an example of {topic} from your own experience?",
            ],
            teaching_style="socratic",
        )

    def _extract_followups(self, text: str) -> List[str]:
        """Extract questions from the response for follow-up."""
        questions = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.endswith("?") and len(stripped) > 10:
                questions.append(stripped)
        return questions[:3]

    def _detect_style(self, text: str) -> str:
        """Heuristic detection of teaching style used."""
        lower = text.lower()
        if "example" in lower or "```" in lower:
            return "example_driven"
        if "think about" in lower or "why do you" in lower:
            return "socratic"
        if "imagine" in lower or "like a" in lower:
            return "analogy"
        if "step 1" in lower or "first," in lower:
            return "step_by_step"
        return "explanation"
