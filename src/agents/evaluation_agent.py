"""
Phase 9.2 — EvaluationAgent

Knowledge assessment agent. Generates quizzes, scores responses,
identifies weak areas, and tracks progress.

Uses Veritas-Core LLMProvider — zero Runtime modifications.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


@dataclass
class ErrorAnalysis:
    """Per-question error analysis for wrong answers. (Phase 8.2-C)"""
    question_id: str
    error_type: str = ""              # "concept_misunderstanding" | "syntax" | "logic" | "incomplete" | "unknown"
    explanation: str = ""             # 为什么错
    correct_reasoning: str = ""       # 正确思路
    related_concepts: List[str] = field(default_factory=list)  # 知识漏洞
    recovery_plan: str = ""           # 恢复学习计划
    next_exercise: str = ""           # 推荐练习
    generation_source: str = "rule"   # rule | llm

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "error_type": self.error_type,
            "explanation": self.explanation,
            "correct_reasoning": self.correct_reasoning,
            "related_concepts": self.related_concepts,
            "recovery_plan": self.recovery_plan,
            "next_exercise": self.next_exercise,
            "generation_source": self.generation_source,
        }


@dataclass
class QuizQuestion:
    """A single quiz question."""
    id: str
    question: str
    question_type: str = "multiple_choice"  # multiple_choice | open_ended | code
    options: List[str] = field(default_factory=list)
    correct_index: int = 0
    explanation: str = ""
    difficulty: str = "medium"  # easy | medium | hard
    points: int = 1
    topic: str = ""


@dataclass
class StudentAnswer:
    """Student's answer to a question."""
    question_id: str
    selected_index: int = -1  # -1 for open-ended
    text_answer: str = ""
    is_correct: Optional[bool] = None
    score: float = 0.0
    time_spent_ms: int = 0


@dataclass
class QuizResult:
    """Complete quiz result with analysis."""
    quiz_id: str
    total_questions: int = 0
    correct_count: int = 0
    total_points: int = 0
    earned_points: int = 0
    score_percent: float = 0.0
    weak_areas: List[str] = field(default_factory=list)
    strong_areas: List[str] = field(default_factory=list)
    answers: List[StudentAnswer] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    error_analyses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    completed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quiz_id": self.quiz_id,
            "total_questions": self.total_questions,
            "correct_count": self.correct_count,
            "total_points": self.total_points,
            "earned_points": self.earned_points,
            "score_percent": self.score_percent,
            "weak_areas": self.weak_areas,
            "strong_areas": self.strong_areas,
            "recommendations": self.recommendations,
            "error_analyses": self.error_analyses,
            "completed_at": self.completed_at,
        }


class EvaluationAgent:
    """Knowledge assessment engine."""

    def __init__(self, llm_provider: Any = None):
        self._llm = llm_provider
        self._orchestrator = None  # Phase 9.3-B

    @property
    def name(self) -> str:
        return "evaluation"

    def set_orchestrator(self, orchestrator: Any) -> None:
        """Phase 9.3-B: inject OrchestratorRuntime (preferred over llm_provider)."""
        self._orchestrator = orchestrator

    # ── Quiz Generation ────────────────────────────────────

    def generate_quiz(
        self,
        topic: str,
        student_level: str = "beginner",
        num_questions: int = 5,
        difficulty: str = "auto",
    ) -> List[QuizQuestion]:
        """Generate a quiz for a given topic."""
        if self._llm is not None:
            return self._llm_generate_quiz(topic, student_level, num_questions, difficulty)
        return self._rule_generate_quiz(topic, student_level, num_questions)

    def _llm_generate_quiz(
        self, topic: str, level: str, num: int, difficulty: str
    ) -> List[QuizQuestion]:
        """Use LLM to generate quiz questions."""
        prompt = (
            f"Generate {num} multiple-choice quiz questions about '{topic}' "
            f"for a {level}-level student. Difficulty: {difficulty}.\n\n"
            f"For each question, provide:\n"
            f"1. The question text\n"
            f"2. Four options (A-D)\n"
            f"3. The correct answer index (0-3)\n"
            f"4. A brief explanation of the correct answer\n\n"
            f"Format as JSON array of objects with keys: question, options (array), "
            f"correct_index (int), explanation, difficulty."
        )
        try:
            resp = self._llm.generate(prompt)
            import json
            raw = resp.content if hasattr(resp, 'content') else str(resp)
            # Extract JSON from response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                return [
                    QuizQuestion(
                        id=f"q{i+1}",
                        question=q["question"],
                        options=q.get("options", []),
                        correct_index=q.get("correct_index", 0),
                        explanation=q.get("explanation", ""),
                        difficulty=q.get("difficulty", "medium"),
                        topic=topic,
                    )
                    for i, q in enumerate(data)
                ]
        except Exception:
            pass
        return self._rule_generate_quiz(topic, level, num)

    def _rule_generate_quiz(
        self, topic: str, level: str, num: int
    ) -> List[QuizQuestion]:
        """Rule-based quiz generation (no LLM dependency)."""
        templates = [
            QuizQuestion(
                id="q1",
                question=f"What is the primary purpose of {topic}?",
                options=[
                    "To solve specific problems efficiently",
                    "To replace human decision-making entirely",
                    "To store large amounts of unstructured data",
                    "To generate random outputs for testing",
                ],
                correct_index=0,
                explanation=f"{topic} is designed to address concrete problems through systematic approaches.",
                topic=topic,
            ),
            QuizQuestion(
                id="q2",
                question=f"Which of these is a key concept in {topic}?",
                options=[
                    "Random guessing",
                    "Structured reasoning",
                    "File compression",
                    "Network latency",
                ],
                correct_index=1,
                explanation=f"Structured reasoning is fundamental to {topic}.",
                topic=topic,
            ),
            QuizQuestion(
                id="q3",
                question=f"How does {topic} improve over traditional approaches?",
                options=[
                    "It's always slower but more accurate",
                    "It automates repetitive patterns while adapting to new inputs",
                    "It requires no data to function",
                    "It only works on specific hardware",
                ],
                correct_index=1,
                explanation=f"{topic} leverages automation and adaptation as key advantages.",
                topic=topic,
            ),
        ]
        return templates[:num]

    # ── Scoring ────────────────────────────────────────────

    def score_quiz(
        self,
        questions: List[QuizQuestion],
        answers: List[StudentAnswer],
        quiz_id: str = "",
    ) -> QuizResult:
        """Score a completed quiz and produce analysis."""
        total = len(questions)
        correct = 0
        total_points = sum(q.points for q in questions)
        earned = 0
        weak = set()
        strong = set()

        q_map = {q.id: q for q in questions}
        scored_answers = []

        for ans in answers:
            q = q_map.get(ans.question_id)
            if q is None:
                continue
            is_correct = ans.selected_index == q.correct_index
            ans.is_correct = is_correct
            ans.score = q.points if is_correct else 0
            scored_answers.append(ans)

            if is_correct:
                correct += 1
                earned += q.points
                strong.add(q.topic)
            else:
                weak.add(q.topic)

        score = (earned / max(total_points, 1)) * 100

        # Build recommendations
        recs = []
        if score >= 80:
            recs.append("Excellent work! Consider exploring advanced topics in this area.")
        elif score >= 60:
            recs.append("Good progress. Review the missed concepts and retry the quiz.")
        else:
            recs.append("Let's revisit the fundamentals. Try the beginner-level material first.")
        for area in weak:
            recs.append(f"Focus on: {area} — review the core concepts and try practice exercises.")

        return QuizResult(
            quiz_id=quiz_id,
            total_questions=total,
            correct_count=correct,
            total_points=total_points,
            earned_points=earned,
            score_percent=round(score, 1),
            weak_areas=sorted(weak),
            strong_areas=sorted(strong),
            answers=scored_answers,
            recommendations=recs,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    # ── Wrong Answer Analysis (Phase 8.2-C) ────────────────

    WRONG_ANSWER_PROMPT = """你是一个教学诊断专家。请分析以下学生的错误答案，并提供详细的纠错指导。

[题目]
{question}

[正确答案]
{correct_answer}

[学生答案]
{student_answer}

请输出纯 JSON，包含以下字段：
{{
  "error_type": "concept_misunderstanding | syntax | logic | incomplete | unknown",
  "explanation": "为什么错了 — 具体分析学生的错误思维过程 (2-3句)",
  "correct_reasoning": "正确思路 — 应该怎么想 (2-3句)",
  "related_concepts": ["相关知识点1", "相关知识点2"],
  "recovery_plan": "恢复学习计划 — 建议先复习什么，再看什么 (2-3句)",
  "next_exercise": "推荐的下一道练习题目"
}}

要求:
- error_type 必须从候选值中选择
- explanation 要具体到学生的错误点，不要泛泛而谈
- recovery_plan 要给出具体可操作的学习步骤
- 所有内容用中文编写

只输出 JSON，不要任何额外文本。"""

    ERROR_RULE_ANALYSES = {
        "concept_misunderstanding": {
            "error_type": "concept_misunderstanding",
            "explanation": "你对这个概念的理解可能有些偏差。请重新阅读相关内容，注意核心定义和关键特征。",
            "correct_reasoning": "应该从概念的基本定义出发，理解其适用范围和局限性，然后结合具体场景进行判断。",
            "related_concepts": [],
            "recovery_plan": "建议回到相关章节，重新阅读概念定义部分，然后用自己的话复述一遍。",
            "next_exercise": "请用自己的话重新解释这个概念，并举一个实际应用的例子。",
        },
    }

    def analyze_wrong_answer(
        self,
        question: str,
        student_answer: str,
        correct_answer: str,
        question_id: str = "",
    ) -> ErrorAnalysis:
        """
        Analyze a wrong answer and produce detailed error guidance.

        LLM available → LLM-generated deep analysis
        No LLM → rule-based analysis with sensible defaults

        Args:
            question: The question text
            student_answer: What the student answered (incorrect)
            correct_answer: The correct answer
            question_id: Optional question identifier

        Returns:
            ErrorAnalysis with explanation, correct_reasoning, recovery_plan, next_exercise
        """
        if self._llm is not None:
            try:
                return self._llm_analyze_wrong_answer(
                    question, student_answer, correct_answer, question_id
                )
            except Exception:
                pass  # fallback to rule

        return self._rule_analyze_wrong_answer(
            question, student_answer, correct_answer, question_id
        )

    def _llm_analyze_wrong_answer(
        self,
        question: str,
        student_answer: str,
        correct_answer: str,
        question_id: str,
    ) -> ErrorAnalysis:
        """Use LLM for detailed error analysis."""
        prompt = self.WRONG_ANSWER_PROMPT.format(
            question=question,
            correct_answer=correct_answer,
            student_answer=student_answer,
        )
        resp = self._llm.generate(prompt)
        raw = resp.content if hasattr(resp, "content") else str(resp)

        import json
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            raise ValueError("No JSON found in LLM response")

        data = json.loads(raw[start:end])

        return ErrorAnalysis(
            question_id=question_id,
            error_type=data.get("error_type", "unknown"),
            explanation=data.get("explanation", ""),
            correct_reasoning=data.get("correct_reasoning", ""),
            related_concepts=data.get("related_concepts", []),
            recovery_plan=data.get("recovery_plan", ""),
            next_exercise=data.get("next_exercise", ""),
            generation_source="llm",
        )

    def _rule_analyze_wrong_answer(
        self,
        question: str,
        student_answer: str,
        correct_answer: str,
        question_id: str,
    ) -> ErrorAnalysis:
        """Rule-based error analysis (no LLM dependency)."""
        analysis = self.ERROR_RULE_ANALYSES["concept_misunderstanding"]

        return ErrorAnalysis(
            question_id=question_id,
            error_type=analysis["error_type"],
            explanation=analysis["explanation"],
            correct_reasoning=analysis["correct_reasoning"],
            related_concepts=analysis["related_concepts"],
            recovery_plan=analysis["recovery_plan"],
            next_exercise=analysis["next_exercise"],
            generation_source="rule",
        )

    def analyze_wrong_answer_with_kg(
        self,
        question: str,
        student_answer: str,
        correct_answer: str,
        question_id: str = "",
        knowledge_graph: Any = None,
        mastery_map: Dict[str, float] = None,
    ) -> ErrorAnalysis:
        """
        Analyze wrong answer with Knowledge Graph enrichment. (Phase 8.3-D1)

        Extends analyze_wrong_answer() by using KG to find missing prerequisites.

        Args:
            question, student_answer, correct_answer, question_id: same as analyze_wrong_answer
            knowledge_graph: InMemoryKnowledgeGraph instance (optional)
            mastery_map: concept_id → mastery (0.0-1.0)

        Returns:
            ErrorAnalysis with KG-enriched related_concepts and recovery_plan
        """
        # First get the standard analysis
        analysis = self.analyze_wrong_answer(
            question, student_answer, correct_answer, question_id
        )

        # Enrich with KG gap analysis
        if knowledge_graph is not None and mastery_map:
            try:
                from src.knowledge_graph.bridge import map_error_to_prerequisites

                # Use existing related_concepts from analysis + try concept matching
                concepts_to_check = analysis.related_concepts or []
                if not concepts_to_check:
                    # Try to extract concept from question text
                    concepts_to_check = [question_id] if question_id else []

                for concept in concepts_to_check[:3]:
                    gap = map_error_to_prerequisites(
                        knowledge_graph, concept, mastery_map or {}
                    )
                    missing = gap.get("missing_prerequisites", [])
                    if missing:
                        # Add missing prerequisites to related_concepts
                        existing = set(analysis.related_concepts)
                        for m in missing:
                            if m not in existing:
                                analysis.related_concepts.append(m)
                        # Enhance recovery plan
                        analysis.recovery_plan = (
                            f"Before studying '{concept}', you should first review these prerequisites: "
                            f"{', '.join(missing)}. " + analysis.recovery_plan
                        )
            except Exception:
                pass  # KG enrichment is best-effort

        return analysis

    # ── Open-ended Evaluation ──────────────────────────────

    def evaluate_open_answer(self, question: str, student_answer: str, topic: str = "") -> Dict[str, Any]:
        """Evaluate an open-ended answer (with LLM if available)."""
        if self._llm is not None and student_answer.strip():
            return self._llm_evaluate_open(question, student_answer, topic)
        return self._rule_evaluate_open(question, student_answer)

    def _llm_evaluate_open(self, question: str, answer: str, topic: str) -> Dict[str, Any]:
        prompt = (
            f"Evaluate this student's answer to the following question.\n\n"
            f"Topic: {topic}\n"
            f"Question: {question}\n"
            f"Student's Answer: {answer}\n\n"
            f"Provide:\n"
            f"1. Score (0-100)\n"
            f"2. Brief feedback (1-2 sentences)\n"
            f"3. One specific suggestion for improvement\n\n"
            f"Format: JSON with keys: score, feedback, suggestion"
        )
        try:
            resp = self._llm.generate(prompt)
            raw = resp.content if hasattr(resp, 'content') else str(resp)
            import json
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except Exception:
            pass
        return self._rule_evaluate_open(question, answer)

    def _rule_evaluate_open(self, question: str, answer: str) -> Dict[str, Any]:
        length = len(answer.strip())
        score = min(85, max(20, length // 3))
        return {
            "score": score,
            "feedback": "Answer received. For best results, connect an LLM provider for detailed evaluation.",
            "suggestion": "Try to be more specific and include examples in your answer.",
        }
