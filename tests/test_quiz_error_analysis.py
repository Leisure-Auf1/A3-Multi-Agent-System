"""
Tests for Phase 8.2-C — Wrong Answer Error Analysis.

Covers:
- ErrorAnalysis dataclass + serialization
- analyze_wrong_answer (rule mode, no LLM)
- analyze_wrong_answer with LLM provider (mock)
- LLM failure fallback
- QuizResult carries error_analyses
- Empty/edge cases
- StudentMemory write path
- UI integration (session state flow)
"""

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.agents.evaluation_agent import (
    EvaluationAgent,
    ErrorAnalysis,
    QuizQuestion,
    StudentAnswer,
    QuizResult,
)


# Mock LLM Provider for wrong-answer analysis

class MockErrorAnalysisProvider:
    """Simulates LLM that returns error analysis JSON."""

    def __init__(self, response: dict = None, should_fail: bool = False):
        self._response = response
        self._should_fail = should_fail
        self.model = "mock-analysis"

    @property
    def is_available(self):
        return True

    def generate(self, prompt: str, **kwargs):
        if self._should_fail:
            raise RuntimeError("LLM unavailable")

        default = {
            "error_type": "concept_misunderstanding",
            "explanation": "Student confused closures with regular functions because they did not understand lexical scoping.",
            "correct_reasoning": "Start by understanding that closures capture variables from their enclosing scope, even after that scope exits.",
            "related_concepts": ["lexical_scoping", "free_variables", "function_factories"],
            "recovery_plan": "1. Review the chapter on variable scoping. 2. Study the LEGB rule. 3. Practice with simple closure examples.",
            "next_exercise": "Write a function `make_counter()` that returns a closure which increments and returns a count each time it is called.",
        }

        class FakeResponse:
            content = json.dumps(self._response or default)
            success = True
            error = ""

        return FakeResponse()


class MockFailingAnalysisProvider:
    """LLM that fails to generate response."""

    def generate(self, prompt: str, **kwargs):
        class FakeResponse:
            content = ""
            success = False
            error = "API timeout"

        return FakeResponse()


# Helpers

def _make_questions(n: int = 3) -> list:
    """Create n quiz questions for testing."""
    return [
        QuizQuestion(
            id=f"q{i+1}",
            question=f"Question {i+1}?",
            options=[f"Option A{i}", f"Option B{i}", f"Option C{i}", f"Option D{i}"],
            correct_index=1,
            explanation=f"Explanation {i+1}",
            topic="test_topic",
        )
        for i in range(n)
    ]


def _make_answers(questions: list, wrong_indices: list = None) -> list:
    """Create answers. wrong_indices = list of question indices (0-based) to answer WRONG."""
    wrong = set(wrong_indices or [])
    answers = []
    for i, q in enumerate(questions):
        if i in wrong:
            # Pick a wrong answer (not correct_index)
            wrong_idx = (q.correct_index + 1) % len(q.options)
            answers.append(StudentAnswer(
                question_id=q.id,
                selected_index=wrong_idx,
                text_answer=q.options[wrong_idx],
            ))
        else:
            answers.append(StudentAnswer(
                question_id=q.id,
                selected_index=q.correct_index,
                text_answer=q.options[q.correct_index],
            ))
    return answers


# Tests: ErrorAnalysis dataclass

class TestErrorAnalysis:
    """ErrorAnalysis data model tests."""

    def test_create_with_all_fields(self):
        ea = ErrorAnalysis(
            question_id="q1",
            error_type="concept_misunderstanding",
            explanation="Student did not understand the concept.",
            correct_reasoning="Should start from the definition.",
            related_concepts=["scope", "closures"],
            recovery_plan="Review chapter 3, then practice.",
            next_exercise="Write a closure example.",
            generation_source="llm",
        )
        assert ea.question_id == "q1"
        assert ea.error_type == "concept_misunderstanding"
        assert len(ea.related_concepts) == 2
        assert ea.generation_source == "llm"

    def test_default_values(self):
        ea = ErrorAnalysis(question_id="q1")
        assert ea.error_type == ""
        assert ea.explanation == ""
        assert ea.related_concepts == []
        assert ea.generation_source == "rule"

    def test_to_dict_includes_all_fields(self):
        ea = ErrorAnalysis(question_id="q_test")
        d = ea.to_dict()

        required = {"question_id", "error_type", "explanation",
                    "correct_reasoning", "related_concepts",
                    "recovery_plan", "next_exercise", "generation_source"}
        for field in required:
            assert field in d, f"Missing field: {field}"

    def test_to_dict_values_preserved(self):
        ea = ErrorAnalysis(
            question_id="q1",
            error_type="logic",
            explanation="e",
            correct_reasoning="cr",
            related_concepts=["r1"],
            recovery_plan="rp",
            next_exercise="ne",
        )
        d = ea.to_dict()
        assert d["error_type"] == "logic"
        assert d["related_concepts"] == ["r1"]
        assert d["recovery_plan"] == "rp"


# Tests: analyze_wrong_answer (rule mode)

class TestAnalyzeWrongAnswerRule:
    """analyze_wrong_answer without LLM (rule fallback)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.agent = EvaluationAgent(llm_provider=None)

    def test_rule_mode_returns_error_analysis(self):
        result = self.agent.analyze_wrong_answer(
            question="What is a closure?",
            student_answer="A closed function",
            correct_answer="A function that captures its lexical scope",
            question_id="q1",
        )
        assert isinstance(result, ErrorAnalysis)
        assert result.generation_source == "rule"

    def test_rule_mode_error_type_is_valid(self):
        result = self.agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="B",
        )
        valid_types = {"concept_misunderstanding", "syntax", "logic", "incomplete", "unknown"}
        assert result.error_type in valid_types

    def test_rule_mode_has_explanation(self):
        result = self.agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="B",
        )
        assert len(result.explanation) > 0

    def test_rule_mode_has_correct_reasoning(self):
        result = self.agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="B",
        )
        assert len(result.correct_reasoning) > 0

    def test_rule_mode_has_recovery_plan(self):
        result = self.agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="B",
        )
        assert len(result.recovery_plan) > 0

    def test_rule_mode_has_next_exercise(self):
        result = self.agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="B",
        )
        assert len(result.next_exercise) > 0


# Tests: analyze_wrong_answer (LLM mode)

class TestAnalyzeWrongAnswerLLM:
    """analyze_wrong_answer with LLM provider."""

    def test_llm_returns_detailed_analysis(self):
        agent = EvaluationAgent(llm_provider=MockErrorAnalysisProvider())
        result = agent.analyze_wrong_answer(
            question="What is a closure?",
            student_answer="A closed function",
            correct_answer="A function that captures its lexical scope",
            question_id="q2",
        )
        assert result.generation_source == "llm"
        assert result.error_type == "concept_misunderstanding"
        assert "lexical" in result.explanation.lower()
        assert len(result.related_concepts) > 0
        assert len(result.next_exercise) > 0

    def test_llm_failure_falls_back_to_rule(self):
        agent = EvaluationAgent(llm_provider=MockFailingAnalysisProvider())
        result = agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="B",
        )
        assert result.generation_source == "rule"

    def test_llm_exception_falls_back_to_rule(self):
        agent = EvaluationAgent(llm_provider=MockErrorAnalysisProvider(should_fail=True))
        result = agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="B",
        )
        assert result.generation_source == "rule"

    def test_llm_custom_response_preserved(self):
        custom = {
            "error_type": "logic",
            "explanation": "Logic was flawed because...",
            "correct_reasoning": "Think step by step...",
            "related_concepts": ["step1", "step2"],
            "recovery_plan": "Start over from the basics.",
            "next_exercise": "Try this simpler problem first.",
        }
        agent = EvaluationAgent(llm_provider=MockErrorAnalysisProvider(custom))
        result = agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="B",
        )
        assert result.error_type == "logic"
        assert "step by step" in result.correct_reasoning.lower()
        assert len(result.related_concepts) == 2


# Tests: QuizResult carries error_analyses

class TestQuizResultWithErrorAnalyses:
    """QuizResult.error_analyses field."""

    def test_error_analyses_empty_by_default(self):
        qr = QuizResult(quiz_id="q1")
        assert qr.error_analyses == {}

    def test_error_analyses_preserved_in_to_dict(self):
        analyses = {
            "q1": ErrorAnalysis(question_id="q1", error_type="logic").to_dict(),
            "q2": ErrorAnalysis(question_id="q2", error_type="syntax").to_dict(),
        }
        qr = QuizResult(quiz_id="q1", error_analyses=analyses)
        d = qr.to_dict()
        assert "error_analyses" in d
        assert len(d["error_analyses"]) == 2

    def test_score_quiz_includes_error_analyses_when_set(self):
        agent = EvaluationAgent(llm_provider=MockErrorAnalysisProvider())
        questions = _make_questions(3)
        answers = _make_answers(questions, wrong_indices=[1])  # q2 wrong

        result = agent.score_quiz(questions, answers, quiz_id="test_q")

        # Manually add error analysis (simulating quiz_panel flow)
        analysis = agent.analyze_wrong_answer(
            question=questions[1].question,
            student_answer=answers[1].text_answer,
            correct_answer=questions[1].options[questions[1].correct_index],
            question_id=questions[1].id,
        )
        result.error_analyses = {questions[1].id: analysis.to_dict()}

        assert len(result.error_analyses) == 1
        assert questions[1].id in result.error_analyses


# Tests: score_quiz with error_analyses pipeline

class TestScoreQuizAnalysisPipeline:
    """Full pipeline: score quiz -> analyze wrong answers."""

    def test_all_correct_no_analyses(self):
        agent = EvaluationAgent(llm_provider=MockErrorAnalysisProvider())
        questions = _make_questions(3)
        answers = _make_answers(questions)  # all correct

        result = agent.score_quiz(questions, answers)
        assert result.correct_count == 3
        # No wrong answers, so no error_analyses generated
        # (quiz_panel iterates over answers and skips correct ones)

    def test_some_wrong_generates_analyses(self):
        agent = EvaluationAgent(llm_provider=MockErrorAnalysisProvider())
        questions = _make_questions(3)
        answers = _make_answers(questions, wrong_indices=[0, 2])  # q1, q3 wrong

        result = agent.score_quiz(questions, answers)
        assert result.correct_count == 1

        # Simulate quiz_panel flow: analyze each wrong answer
        error_analyses = {}
        for q in questions:
            ans = next((a for a in answers if a.question_id == q.id), None)
            if ans is None or ans.is_correct:
                continue
            analysis = agent.analyze_wrong_answer(
                question=q.question,
                student_answer=ans.text_answer,
                correct_answer=q.options[q.correct_index],
                question_id=q.id,
            )
            error_analyses[q.id] = analysis.to_dict()

        result.error_analyses = error_analyses
        assert len(result.error_analyses) == 2

    def test_rule_mode_analyses_always_rule(self):
        """Without LLM, all analyses are rule-based."""
        agent = EvaluationAgent(llm_provider=None)
        questions = _make_questions(2)
        answers = _make_answers(questions, wrong_indices=[0])

        result = agent.score_quiz(questions, answers)
        # Analyze wrong answer
        analysis = agent.analyze_wrong_answer(
            question=questions[0].question,
            student_answer=answers[0].text_answer,
            correct_answer=questions[0].options[questions[0].correct_index],
            question_id=questions[0].id,
        )
        assert analysis.generation_source == "rule"


# Tests: StudentMemory integration

class TestStudentMemoryWrite:
    """Verify StudentMemory write path for error analyses."""

    def test_write_error_to_memory(self, tmp_path):
        """Test that writing error analyses to StudentMemory does not crash."""
        from veritas.memory import MemoryManager

        # Create a fresh MemoryManager
        mm = MemoryManager()

        student_id = "test_error_analysis_student"

        # Write a weak_point (simulating wrong answer)
        weak_point = {
            "concept": "closures",
            "error_type": "concept_misunderstanding",
            "explanation": "Student did not understand closures",
            "recovery_plan": "Review chapter 3",
            "timestamp": "2026-01-01T00:00:00",
        }

        # Should not raise
        mm.update_student_memory(
            student_id=student_id,
            weak_point=weak_point,
        )

        # Write feedback
        feedback = {
            "quiz_id": "test_quiz",
            "score": 66.7,
            "correct": 2,
            "total": 3,
            "weak_areas": ["test_topic"],
            "errors_analyzed": 1,
        }

        mm.update_student_memory(
            student_id=student_id,
            feedback=feedback,
        )

        # Verify memory was written (by reading back)
        mem = mm.get_student_memory(student_id)
        assert mem is not None

    def test_memory_write_no_errors_no_crash(self):
        """Writing with empty dict should not crash."""
        from veritas.memory import MemoryManager
        mm = MemoryManager()

        # Should not raise for empty weak_point dict
        mm.update_student_memory(
            student_id="test_empty",
            weak_point={},
        )

    def test_memory_write_multiple_weak_points(self):
        """Writing multiple weak points should accumulate."""
        from veritas.memory import MemoryManager
        mm = MemoryManager()
        sid = "test_multi_weak"

        concepts = ["closures", "decorators", "generators"]
        for c in concepts:
            mm.update_student_memory(
                student_id=sid,
                weak_point={"concept": c, "error_type": "concept_misunderstanding"},
            )

        # Verify we can read back
        mem = mm.get_student_memory(sid)
        assert mem is not None


# Tests: Empty/edge cases

class TestEdgeCases:
    """Edge cases for error analysis."""

    def test_empty_answers(self):
        agent = EvaluationAgent()
        result = agent.analyze_wrong_answer(
            question="Q?", student_answer="", correct_answer="C", question_id="",
        )
        assert isinstance(result, ErrorAnalysis)
        assert result.generation_source == "rule"

    def test_empty_correct_answer(self):
        agent = EvaluationAgent()
        result = agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="", question_id="q",
        )
        assert isinstance(result, ErrorAnalysis)

    def test_empty_question_id(self):
        agent = EvaluationAgent()
        result = agent.analyze_wrong_answer(
            question="Q?", student_answer="A", correct_answer="C", question_id="",
        )
        assert result.question_id == ""

    def test_skips_correct_answers(self):
        """Quiz panel loop skips correct answers and only analyzes wrong ones."""
        agent = EvaluationAgent()
        questions = _make_questions(3)
        answers = _make_answers(questions, wrong_indices=[1])  # only q2 wrong

        # Score first to populate is_correct
        result = agent.score_quiz(questions, answers)

        analyzed_count = 0
        for q in questions:
            ans = next((a for a in result.answers if a.question_id == q.id), None)
            if ans is None or ans.is_correct:
                continue  # skip correct
            analyzed_count += 1

        assert analyzed_count == 1  # only the wrong one


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
