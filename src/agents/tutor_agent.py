"""
Phase 9.2 / PR #4 — TutorAgent (with tool calling)

Conversational tutor agent. Explains concepts, answers questions,
adapts to learning style, and generates Socratic follow-ups.

PR #4: Optional ToolRegistry integration for web search and other tools.
When tools are available, the LLM may call them mid-conversation;
results are fed back and a final response is generated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Iterator
from datetime import datetime, timezone
import json

from src.tools.base import ToolResult


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
    tool_calls_made: int = 0          # PR #4

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "follow_up_questions": self.follow_up_questions,
            "suggested_resources": self.suggested_resources,
            "confidence": self.confidence,
            "teaching_style": self.teaching_style,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "tool_calls_made": self.tool_calls_made,
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
    """Conversational AI tutor with multi-style teaching and optional tool calling."""

    MAX_TOOL_ITERATIONS = 3  # PR #4 — prevent infinite loops

    def __init__(self, llm_provider: Any = None, tool_registry: Any = None):
        """
        Args:
            llm_provider: LLMProvider instance (or None for rule-only fallback)
            tool_registry: Optional ToolRegistry for tool-calling capability
        """
        self._llm = llm_provider
        self._tool_registry = tool_registry
        self._default_style = "explanation"

    @property
    def name(self) -> str:
        return "tutor"

    @property
    def has_tools(self) -> bool:
        return self._tool_registry is not None and len(self._tool_registry) > 0

    def _get_style_instruction(self, profile: Dict[str, Any]) -> str:
        cognitive = profile.get("cognitive_style", "default")
        return LEARNING_STYLES.get(cognitive, LEARNING_STYLES["default"])

    def _build_system_prompt(self, ctx: TutorContext) -> str:
        style = self._get_style_instruction(ctx.student_profile)
        gaps = ", ".join(ctx.knowledge_gaps) if ctx.knowledge_gaps else "none identified"
        level = ctx.student_profile.get("knowledge_base", "beginner")

        prompt = f"""You are a patient, knowledgeable AI tutor. Your student is at '{level}' level.

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

        if self.has_tools:
            prompt += "\n\nYou have access to tools. Use them when the student asks about current events, recent information, or facts beyond your knowledge. Always cite your sources when using search results."

        return prompt

    def _build_user_prompt(self, user_message: str, ctx: TutorContext) -> str:
        parts = []
        if ctx.learning_goal:
            parts.append(f"Student's learning goal: {ctx.learning_goal}")
        if ctx.current_topic:
            parts.append(f"Current topic: {ctx.current_topic}")
        parts.append(f"\nStudent's question: {user_message}")
        return "\n".join(parts)

    # ── Tool-calling loop (PR #4) ──────────────────────

    def _llm_chat(self, messages: list, **kwargs) -> Any:
        """Call LLM with a message list (for multi-turn tool calls)."""
        if len(messages) >= 2 and messages[0].get("role") == "system":
            system = messages[0]["content"]
            user = messages[-1].get("content", "")
            return self._llm.generate(user, system_prompt=system, **kwargs)
        # Fallback: join all user messages
        prompt = "\n".join(m.get("content", "") for m in messages if m.get("role") == "user")
        system = next((m["content"] for m in messages if m.get("role") == "system"), "")
        return self._llm.generate(prompt, system_prompt=system, **kwargs)

    def _handle_tool_calls(self, tool_calls: list) -> list:
        """Execute tool calls and return result messages."""
        results = []
        for tc in tool_calls:
            name = tc.get("name", "")
            args_str = tc.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}

            if self._tool_registry is None:
                results.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": "Tool registry not available.",
                })
                continue

            result = self._tool_registry.execute(name, args)
            results.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result.content if result.success else f"Error: {result.error}",
            })
        return results

    def _tool_loop_explain(self, user_prompt: str, ctx: TutorContext) -> tuple:
        """Run the LLM with tool-calling loop. Returns (content, tool_call_count)."""
        messages = [
            {"role": "system", "content": self._build_system_prompt(ctx)},
            {"role": "user", "content": user_prompt},
        ]

        tools = self._tool_registry.to_openai_tools() if self.has_tools else None
        tool_count = 0

        for _ in range(self.MAX_TOOL_ITERATIONS):
            kwargs = {}
            if tools:
                kwargs["tools"] = tools

            resp = self._llm_chat(messages, **kwargs)

            # Check for tool calls
            tool_calls = getattr(resp, "tool_calls", []) or []
            if not tool_calls:
                content = resp.content if hasattr(resp, "content") else str(resp)
                return content, tool_count

            # Execute tools
            tool_count += len(tool_calls)

            # Add assistant message with tool calls
            assistant_msg = {"role": "assistant", "content": resp.content or ""}
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in tool_calls
                ]
            messages.append(assistant_msg)

            # Execute and add tool results
            tool_results = self._handle_tool_calls(tool_calls)
            messages.extend(tool_results)

        # Max iterations reached — ask LLM for final answer
        messages.append({"role": "user", "content": "Please provide a final answer based on the tool results above."})
        resp = self._llm_chat(messages)
        content = resp.content if hasattr(resp, "content") else str(resp)
        return content, tool_count

    # ── Public API ─────────────────────────────────────

    def explain(self, question: str, ctx: Optional[TutorContext] = None) -> TutorResponse:
        """Generate a tutor response (non-streaming)."""
        import time
        ctx = ctx or TutorContext()
        start = time.time()
        tool_count = 0

        if self._llm is None:
            return self._fallback_explain(question, ctx)

        user_prompt = self._build_user_prompt(question, ctx)

        try:
            if self.has_tools:
                content, tool_count = self._tool_loop_explain(user_prompt, ctx)
            else:
                system_prompt = self._build_system_prompt(ctx)
                resp = self._llm.generate(user_prompt, system_prompt=system_prompt)
                content = resp.content if hasattr(resp, 'content') else str(resp)
        except Exception:
            content = self._fallback_explain(question, ctx).content

        return TutorResponse(
            content=content,
            follow_up_questions=self._extract_followups(content),
            teaching_style=self._detect_style(content),
            latency_ms=int((time.time() - start) * 1000),
            tool_calls_made=tool_count,
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

        # Streaming doesn't support tool-calling loop — delegate to non-streaming
        if self.has_tools:
            resp = self.explain(question, ctx)
            yield resp.content
            return

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
        questions = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.endswith("?") and len(stripped) > 10:
                questions.append(stripped)
        return questions[:3]

    def _detect_style(self, text: str) -> str:
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
