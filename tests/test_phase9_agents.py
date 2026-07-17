"""
Phase 9.2 — Agent Tests

Tests for TutorAgent, EvaluationAgent.
"""
from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ── TutorAgent Tests ──────────────────────────────────────

class TestTutorAgent:
    """Test the conversational tutor."""

    def test_fallback_explain_no_llm(self):
        from src.agents.tutor_agent import TutorAgent, TutorContext
        agent = TutorAgent()
        ctx = TutorContext(current_topic="Python decorators")
        resp = agent.explain("What is a decorator?", ctx)
        assert resp.content
        assert "Python decorators" in resp.content or "the topic" in resp.content
        assert len(resp.follow_up_questions) >= 1
        assert resp.teaching_style in ("socratic", "explanation")

    def test_explain_with_context(self):
        from src.agents.tutor_agent import TutorAgent, TutorContext
        agent = TutorAgent()
        ctx = TutorContext(
            student_profile={"cognitive_style": "visual_dominant", "knowledge_base": "beginner"},
            learning_goal="Learn Python OOP",
            knowledge_gaps=["inheritance", "polymorphism"],
        )
        resp = agent.explain("How does inheritance work?", ctx)
        assert resp.content
        assert resp.confidence == 0.8
        assert isinstance(resp.to_dict(), dict)

    def test_streaming_yields_content(self):
        from src.agents.tutor_agent import TutorAgent, TutorContext
        agent = TutorAgent()
        ctx = TutorContext(current_topic="variables")
        chunks = list(agent.explain_stream("What is a variable?", ctx))
        assert len(chunks) >= 1
        assert isinstance(chunks[0], str)

    def test_followup_extraction(self):
        from src.agents.tutor_agent import TutorAgent
        agent = TutorAgent()
        text = (
            "That's correct!\n"
            "Have you tried using this pattern?\n"
            "What challenges did you face?\n"
            "Are you ready for more?"
        )
        followups = agent._extract_followups(text)
        assert len(followups) == 3

    def test_style_detection(self):
        from src.agents.tutor_agent import TutorAgent
        agent = TutorAgent()

        assert agent._detect_style("```python\nprint('hello')\n```") == "example_driven"
        assert agent._detect_style("Why do you think this happens?") == "socratic"
        assert agent._detect_style("Imagine a bridge connecting two cities") == "analogy"
        assert agent._detect_style("Step 1: First, create the class") == "step_by_step"
        assert agent._detect_style("This is a concept.") == "explanation"

    def test_style_instruction_maps(self):
        from src.agents.tutor_agent import TutorAgent
        agent = TutorAgent()
        visual = agent._get_style_instruction({"cognitive_style": "visual_dominant"})
        assert "imagery" in visual.lower()
        sandbox = agent._get_style_instruction({"cognitive_style": "code_sandbox"})
        assert "code" in sandbox.lower()
        unknown = agent._get_style_instruction({"cognitive_style": "unknown"})
        assert "clear" in unknown.lower()

    def test_system_prompt_includes_context(self):
        from src.agents.tutor_agent import TutorAgent, TutorContext
        agent = TutorAgent()
        ctx = TutorContext(
            student_profile={"knowledge_base": "intermediate"},
            learning_goal="Learn async Python",
            current_topic="asyncio",
            knowledge_gaps=["coroutines"],
        )
        prompt = agent._build_system_prompt(ctx)
        assert "intermediate" in prompt
        assert "coroutines" in prompt
        assert "asyncio" in prompt


# ── EvaluationAgent Tests ─────────────────────────────────

class TestEvaluationAgent:
    """Test the quiz/evaluation agent."""

    def test_rule_quiz_generation(self):
        from src.agents.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()
        quiz = agent.generate_quiz("Machine Learning", "beginner", 3)
        assert len(quiz) == 3
        assert all(isinstance(q.question, str) for q in quiz)
        assert all(len(q.options) == 4 for q in quiz)
        assert quiz[0].correct_index == 0

    def test_score_quiz_perfect(self):
        from src.agents.evaluation_agent import EvaluationAgent, QuizQuestion, StudentAnswer
        agent = EvaluationAgent()
        questions = [
            QuizQuestion(id="q1", question="Q1?", options=["A", "B", "C", "D"], correct_index=0, points=2),
            QuizQuestion(id="q2", question="Q2?", options=["A", "B", "C", "D"], correct_index=1, points=3),
        ]
        answers = [
            StudentAnswer(question_id="q1", selected_index=0),
            StudentAnswer(question_id="q2", selected_index=1),
        ]
        result = agent.score_quiz(questions, answers, "quiz-1")
        assert result.total_questions == 2
        assert result.correct_count == 2
        assert result.earned_points == 5
        assert result.score_percent == 100.0
        assert len(result.weak_areas) == 0

    def test_score_quiz_partial(self):
        from src.agents.evaluation_agent import EvaluationAgent, QuizQuestion, StudentAnswer
        agent = EvaluationAgent()
        questions = [
            QuizQuestion(id="q1", question="Q1?", options=["A", "B", "C", "D"], correct_index=0, points=1, topic="topic_a"),
            QuizQuestion(id="q2", question="Q2?", options=["A", "B", "C", "D"], correct_index=1, points=1, topic="topic_b"),
            QuizQuestion(id="q3", question="Q3?", options=["A", "B", "C", "D"], correct_index=2, points=1, topic="topic_a"),
        ]
        answers = [
            StudentAnswer(question_id="q1", selected_index=0),  # correct
            StudentAnswer(question_id="q2", selected_index=0),  # wrong
            StudentAnswer(question_id="q3", selected_index=0),  # wrong
        ]
        result = agent.score_quiz(questions, answers, "quiz-2")
        assert result.correct_count == 1
        assert result.score_percent == pytest.approx(33.3, rel=0.5)
        assert "topic_a" in result.strong_areas
        assert "topic_a" in result.weak_areas  # got one wrong
        assert len(result.recommendations) >= 1

    def test_score_percent_bands(self):
        from src.agents.evaluation_agent import EvaluationAgent, QuizQuestion, StudentAnswer
        agent = EvaluationAgent()

        # 80%+ → excellent
        qs = [QuizQuestion(id="q1", question="?", options=["A", "B", "C", "D"], correct_index=0, points=5)]
        ans = [StudentAnswer(question_id="q1", selected_index=0)]
        r = agent.score_quiz(qs, ans, "q")
        assert any("Excellent" in rec or "advanced" in rec for rec in r.recommendations)

        # <60% → revisit
        ans2 = [StudentAnswer(question_id="q1", selected_index=1)]
        r2 = agent.score_quiz(qs, ans2, "q2")
        assert any("revisit" in rec.lower() or "fundamental" in rec.lower() for rec in r2.recommendations)

    def test_rule_evaluate_open_answer(self):
        from src.agents.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()
        result = agent.evaluate_open_answer(
            "Explain recursion.", "A function that calls itself.", "recursion")
        assert "score" in result
        assert 0 <= result["score"] <= 100
        assert "feedback" in result

    def test_evaluate_empty_answer(self):
        from src.agents.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()
        result = agent.evaluate_open_answer("What is OOP?", "", "OOP")
        assert result["score"] <= 30

    def test_quiz_question_dataclass(self):
        from src.agents.evaluation_agent import QuizQuestion
        q = QuizQuestion(
            id="q1", question="What is 2+2?",
            options=["3", "4", "5", "6"], correct_index=1,
            explanation="Basic arithmetic.", difficulty="easy", topic="math")
        assert q.id == "q1"
        assert q.correct_index == 1
        assert len(q.options) == 4

    def test_result_to_dict(self):
        from src.agents.evaluation_agent import QuizResult
        r = QuizResult(quiz_id="test", total_questions=5, correct_count=4,
                       total_points=10, earned_points=8, score_percent=80.0,
                       weak_areas=["inheritance"])
        d = r.to_dict()
        assert d["score_percent"] == 80.0
        assert "inheritance" in d["weak_areas"]


# ── Agent Integration Tests ───────────────────────────────

class TestAgentIntegration:
    """Test TutorAgent + EvaluationAgent together."""

    def test_tutor_then_evaluate(self):
        from src.agents.tutor_agent import TutorAgent, TutorContext
        from src.agents.evaluation_agent import EvaluationAgent

        # Step 1: Tutor explains a topic
        tutor = TutorAgent()
        ctx = TutorContext(current_topic="Python lists", learning_goal="Learn Python basics")
        resp = tutor.explain("What are lists?", ctx)
        assert resp.content

        # Step 2: Evaluate understanding with a quiz
        evaluator = EvaluationAgent()
        quiz = evaluator.generate_quiz("Python lists", "beginner", 3)
        assert len(quiz) == 3

        # Step 3: Score the quiz
        from src.agents.evaluation_agent import StudentAnswer
        answers = [StudentAnswer(question_id=q.id, selected_index=q.correct_index) for q in quiz]
        result = evaluator.score_quiz(quiz, answers, "test-flow")
        assert result.score_percent == 100.0
        assert "Python lists" in result.strong_areas or len(result.strong_areas) >= 1

    def test_tutor_with_different_levels(self):
        from src.agents.tutor_agent import TutorAgent, TutorContext
        agent = TutorAgent()
        for level in ["beginner", "intermediate", "advanced"]:
            ctx = TutorContext(
                student_profile={"knowledge_base": level},
                current_topic=f"{level} math")
            resp = agent.explain("Explain a concept", ctx)
            assert resp.content
