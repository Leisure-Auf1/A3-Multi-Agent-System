"""
Phase 9.4 — Evaluation API

POST   /api/v2/evaluation/quiz/generate
POST   /api/v2/evaluation/quiz/score
POST   /api/v2/evaluation/open/assess
GET    /api/v2/evaluation/results
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.auth.middleware import require_auth
from src.auth.models import AuthUser
from src.agents.evaluation_agent import (
    EvaluationAgent, QuizQuestion, StudentAnswer, QuizResult,
)
from src.data.learning_records import record_agent_action, get_history
import uuid

router = APIRouter(prefix="/api/v2/evaluation", tags=["evaluation"])


class QuizGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    student_level: str = "beginner"
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: str = "auto"


class QuestionResponse(BaseModel):
    id: str
    question: str
    options: List[str]
    difficulty: str


class QuizGenerateResponse(BaseModel):
    quiz_id: str
    topic: str
    questions: List[QuestionResponse]


class QuizScoreRequest(BaseModel):
    quiz_id: str = ""
    topic: str = ""
    answers: List[Dict[str, Any]]  # [{question_id, selected_index}]


class QuizScoreResponse(BaseModel):
    quiz_id: str
    score_percent: float
    correct_count: int
    total_questions: int
    weak_areas: List[str]
    strong_areas: List[str]
    recommendations: List[str]


class OpenAssessRequest(BaseModel):
    question: str
    answer: str
    topic: str = ""


class OpenAssessResponse(BaseModel):
    score: int
    feedback: str
    suggestion: str


class ResultHistoryResponse(BaseModel):
    id: str
    agent: str
    action: str
    score: float
    created_at: str


@router.post("/quiz/generate", response_model=QuizGenerateResponse)
def generate_quiz(
    req: QuizGenerateRequest,
    user: AuthUser = Depends(require_auth),
):
    """Generate a quiz for a topic."""
    agent = EvaluationAgent()
    quiz_id = uuid.uuid4().hex[:12]
    questions = agent.generate_quiz(
        req.topic, req.student_level, req.num_questions, req.difficulty)

    return QuizGenerateResponse(
        quiz_id=quiz_id,
        topic=req.topic,
        questions=[
            QuestionResponse(
                id=q.id, question=q.question,
                options=q.options, difficulty=q.difficulty)
            for q in questions
        ],
    )


@router.post("/quiz/score", response_model=QuizScoreResponse)
def score_quiz(
    req: QuizScoreRequest,
    user: AuthUser = Depends(require_auth),
):
    """Score a completed quiz."""
    agent = EvaluationAgent()
    quiz_id = req.quiz_id or uuid.uuid4().hex[:12]

    # Reconstruct questions from answers
    # (In production, questions would be stored server-side)
    questions = []
    for a in req.answers:
        questions.append(QuizQuestion(
            id=a.get("question_id", ""),
            question="",
            options=a.get("options", ["A", "B", "C", "D"]),
            correct_index=a.get("correct_index", 0),
            topic=req.topic,
        ))

    answers = [
        StudentAnswer(
            question_id=a["question_id"],
            selected_index=a.get("selected_index", -1),
        )
        for a in req.answers
    ]

    result = agent.score_quiz(questions, answers, quiz_id)

    # Record evaluation event
    record_agent_action(
        user_id=user.id,
        agent="evaluation",
        action="quiz",
        course_id=req.topic,
        score=result.score_percent,
    )

    return QuizScoreResponse(
        quiz_id=result.quiz_id,
        score_percent=result.score_percent,
        correct_count=result.correct_count,
        total_questions=result.total_questions,
        weak_areas=result.weak_areas,
        strong_areas=result.strong_areas,
        recommendations=result.recommendations,
    )


@router.post("/open/assess", response_model=OpenAssessResponse)
def assess_open_answer(
    req: OpenAssessRequest,
    user: AuthUser = Depends(require_auth),
):
    """Evaluate an open-ended answer."""
    agent = EvaluationAgent()
    result = agent.evaluate_open_answer(req.question, req.answer, req.topic)
    return OpenAssessResponse(**result)


@router.get("/results", response_model=List[ResultHistoryResponse])
def get_evaluation_results(user: AuthUser = Depends(require_auth)):
    """Get evaluation history."""
    records = get_history(user.id)
    eval_records = [r for r in records if r["agent"] == "evaluation"]
    return [
        ResultHistoryResponse(
            id=r["id"], agent=r["agent"], action=r["action"],
            score=r.get("score", 0), created_at=r["created_at"],
        )
        for r in eval_records[:20]
    ]
