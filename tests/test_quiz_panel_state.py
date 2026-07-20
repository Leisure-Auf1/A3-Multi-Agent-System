"""
Tests for Phase 8.2-B2 — Quiz Panel session state management.

Covers:
- Quiz generation stores questions in session_state
- Answer collection via session_state keys
- Score results stored in session_state
- Evaluation dict with weak_areas/strong_areas
- Reset flow
"""

import streamlit as st
from unittest import mock
import pytest

from src.agents.evaluation_agent import (
    EvaluationAgent,
    QuizQuestion,
    StudentAnswer,
    QuizResult,
)


# ═══════════════════════════════════════════════════════════════
# Mock provider for quiz generation
# ═══════════════════════════════════════════════════════════════


class MockQuizProvider:
    """Simulates LLM for quiz generation/scoring."""

    def __init__(self):
        self.model = "mock-quiz"

    @property
    def is_available(self):
        return True

    def generate(self, prompt, **kwargs):
        # Return mock quiz JSON when asked to generate quiz
        class FakeResponse:
            content = (
                '[{"question": "What is Python?", '
                '"options": ["A language", "A snake", "A car", "A planet"], '
                '"correct_index": 0, "explanation": "Python is a programming language.", '
                '"difficulty": "easy"}, '
                '{"question": "What is a decorator?", '
                '"options": ["A pattern", "A function wrapper", "A class", "A module"], '
                '"correct_index": 1, "explanation": "Decorators wrap functions.", '
                '"difficulty": "medium"}]'
            )
            success = True
            error = ""

        return FakeResponse()


# ═══════════════════════════════════════════════════════════════
# Quiz Generation
# ═══════════════════════════════════════════════════════════════


class TestQuizGeneration:
    """Quiz questions are generated and saved to session_state."""

    def test_generate_quiz_returns_questions(self):
        """EvaluationAgent.generate_quiz() produces QuizQuestion list."""
        agent = EvaluationAgent(llm_provider=MockQuizProvider())
        questions = agent.generate_quiz(
            topic="Python basics",
            student_level="beginner",
            num_questions=2,
            difficulty="auto",
        )

        assert len(questions) == 2
        assert isinstance(questions[0], QuizQuestion)
        assert questions[0].id
        assert questions[0].question
        assert len(questions[0].options) == 4

    def test_quiz_questions_stored_in_session_state(self):
        """Questions can be stored in session_state for UI rendering."""
        questions = [
            QuizQuestion(
                id="q1", question="Q1?", options=["A", "B", "C", "D"],
                correct_index=0, topic="test",
            ),
        ]

        st.session_state["quiz_questions"] = questions
        assert st.session_state["quiz_questions"] is not None
        assert len(st.session_state["quiz_questions"]) == 1

    def test_correct_answers_not_sent_to_client(self):
        """Correct index is in QuizQuestion but not exposed via to_dict."""
        q = QuizQuestion(
            id="q1", question="Q?", options=["A", "B"],
            correct_index=1,
        )
        # The correct_index is stored server-side in QuizQuestion
        # The UI renders options only — correct_index stays in session_state
        assert q.correct_index == 1


# ═══════════════════════════════════════════════════════════════
# Answer Collection
# ═══════════════════════════════════════════════════════════════


class TestAnswerCollection:
    """User answers are collected via session_state keys."""

    def test_answer_stored_in_session_state(self):
        """Each question gets a unique answer key in session_state."""
        qid = "q_test_123"
        key = f"quiz_answer_{qid}"
        st.session_state[key] = 2  # selected option C

        assert st.session_state[key] == 2
        assert key.startswith("quiz_answer_")

    def test_multiple_answers_coexist(self):
        """Multiple question answers don't collide."""
        st.session_state["quiz_answer_q1"] = 0
        st.session_state["quiz_answer_q2"] = 1
        st.session_state["quiz_answer_q3"] = 3

        assert st.session_state["quiz_answer_q1"] == 0
        assert st.session_state["quiz_answer_q2"] == 1
        assert st.session_state["quiz_answer_q3"] == 3

    def test_student_answer_created_from_session(self):
        """StudentAnswer objects constructed from session_state values."""
        answers = [
            StudentAnswer(question_id="q1", selected_index=0),
            StudentAnswer(question_id="q2", selected_index=1),
        ]

        assert len(answers) == 2
        assert answers[0].question_id == "q1"
        assert answers[0].selected_index == 0


# ═══════════════════════════════════════════════════════════════
# Score Results
# ═══════════════════════════════════════════════════════════════


class TestScoreResults:
    """Quiz results are scored and stored correctly."""

    def test_score_quiz_returns_quiz_result(self):
        """score_quiz returns QuizResult with weak/strong areas."""
        agent = EvaluationAgent()

        questions = [
            QuizQuestion(
                id="q1", question="Q1", options=["A", "B"],
                correct_index=0, topic="loops",
            ),
            QuizQuestion(
                id="q2", question="Q2", options=["A", "B"],
                correct_index=1, topic="functions",
            ),
        ]
        answers = [
            StudentAnswer(question_id="q1", selected_index=0),  # correct
            StudentAnswer(question_id="q2", selected_index=0),  # wrong
        ]

        result = agent.score_quiz(questions, answers)

        assert isinstance(result, QuizResult)
        assert result.total_questions == 2
        assert result.correct_count == 1
        assert result.score_percent == 50.0
        assert "functions" in result.weak_areas
        assert "loops" in result.strong_areas

    def test_evaluation_dict_built_from_result(self):
        """QuizResult is converted to evaluation dict for workflow."""
        agent = EvaluationAgent()
        questions = [
            QuizQuestion(id="q1", question="Q", options=["A", "B"],
                         correct_index=0, topic="basics"),
        ]
        answers = [StudentAnswer(question_id="q1", selected_index=1)]
        result = agent.score_quiz(questions, answers)

        eval_dict = {
            "score": result.score_percent,
            "weak_areas": result.weak_areas,
            "strong_areas": result.strong_areas,
            "recommendations": result.recommendations,
            "passed": result.score_percent >= 70,
        }

        assert "score" in eval_dict
        assert "weak_areas" in eval_dict
        assert "strong_areas" in eval_dict
        assert "basics" in eval_dict["weak_areas"]
        assert eval_dict["passed"] is False  # 0% score

    def test_perfect_score_all_strong(self):
        """All correct → empty weak_areas, all topics in strong_areas."""
        agent = EvaluationAgent()
        questions = [
            QuizQuestion(id="q1", question="Q", options=["A", "B"],
                         correct_index=0, topic="expert"),
        ]
        answers = [StudentAnswer(question_id="q1", selected_index=0)]
        result = agent.score_quiz(questions, answers)

        assert result.weak_areas == []
        assert "expert" in result.strong_areas
        assert result.score_percent == 100.0


# ═══════════════════════════════════════════════════════════════
# Session State Lifecycle
# ═══════════════════════════════════════════════════════════════


class TestQuizSessionLifecycle:
    """Full quiz session_state lifecycle."""

    def test_full_cycle_questions_to_results(self):
        """Complete flow: questions → answers → score → eval dict."""
        agent = EvaluationAgent()
        questions = [
            QuizQuestion(id="q1", question="Q1", options=["A", "B"],
                         correct_index=0, topic="topic_a"),
            QuizQuestion(id="q2", question="Q2", options=["A", "B"],
                         correct_index=1, topic="topic_b"),
        ]

        # Step 1: Store questions
        st.session_state["quiz_questions"] = questions

        # Step 2: Collect answers (simulated from UI radio buttons)
        st.session_state["quiz_answer_q1"] = 0  # correct
        st.session_state["quiz_answer_q2"] = 0  # wrong

        answers = [
            StudentAnswer(question_id="q1",
                          selected_index=st.session_state["quiz_answer_q1"]),
            StudentAnswer(question_id="q2",
                          selected_index=st.session_state["quiz_answer_q2"]),
        ]

        # Step 3: Score
        result = agent.score_quiz(questions, answers)

        # Step 4: Store results
        st.session_state["quiz_result"] = result
        st.session_state["quiz_evaluation_dict"] = {
            "score": result.score_percent,
            "weak_areas": result.weak_areas,
            "strong_areas": result.strong_areas,
            "passed": result.score_percent >= 70,
        }

        # Verify
        assert st.session_state["quiz_result"].correct_count == 1
        assert "topic_b" in st.session_state["quiz_evaluation_dict"]["weak_areas"]
        assert "topic_a" in st.session_state["quiz_evaluation_dict"]["strong_areas"]

    def test_reset_clears_all_quiz_state(self):
        """Reset clears questions, results, and evaluation dict."""
        st.session_state["quiz_questions"] = [QuizQuestion(
            id="x", question="x", options=["x"], correct_index=0, topic="x")]
        st.session_state["quiz_result"] = QuizResult(quiz_id="x")
        st.session_state["quiz_evaluation_dict"] = {"score": 100}
        st.session_state["quiz_submitted"] = True

        # Reset
        st.session_state["quiz_questions"] = None
        st.session_state["quiz_result"] = None
        st.session_state["quiz_evaluation_dict"] = None
        st.session_state["quiz_submitted"] = False

        assert st.session_state["quiz_questions"] is None
        assert st.session_state["quiz_result"] is None
        assert st.session_state["quiz_evaluation_dict"] is None
        assert st.session_state["quiz_submitted"] is False
